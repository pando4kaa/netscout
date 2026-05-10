"""
Investigation endpoints - CRUD, add entity, run enricher.
Requires authentication and a reachable Neo4j instance.
"""

import asyncio
import csv
import logging
from io import StringIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_required
from app.db.database import SessionLocal, get_db
from app.db.models import User
from app.services.auth_service import decode_token
from app.services.investigation_service import (
    add_entity,
    create_investigation,
    create_share_link,
    delete_investigation,
    get_investigation,
    get_investigation_by_share_token,
    list_investigations,
    require_neo4j_for_investigation,
    run_enricher,
    update_entity_metadata,
    update_investigation,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/investigations", tags=["investigations"])


def neo4j_required() -> None:
    """FastAPI dependency that translates Neo4j availability errors into HTTP 503."""
    try:
        require_neo4j_for_investigation()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


class CreateInvestigationRequest(BaseModel):
    name: str = "New Investigation"


class UpdateInvestigationRequest(BaseModel):
    name: str


class AddEntityRequest(BaseModel):
    entity_type: str
    entity_value: str


class RunEnricherRequest(BaseModel):
    entity_type: str
    entity_value: str
    enricher_name: str


class UpdateEntityMetadataRequest(BaseModel):
    cy_id: str
    notes: Optional[str] = None
    tags: Optional[list[str]] = None


class CreateShareLinkRequest(BaseModel):
    expires_days: int = 7


@router.get("")
async def list_user_investigations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
    _: None = Depends(neo4j_required),
):
    """List investigations belonging to the current user."""
    return {"investigations": list_investigations(db, user.id)}


@router.post("")
async def create_new_investigation(
    request: CreateInvestigationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
    _: None = Depends(neo4j_required),
):
    """Create a new investigation."""
    return create_investigation(db, user.id, request.name)


@router.get("/shared/{token}")
async def get_shared_investigation(
    token: str,
    db: Session = Depends(get_db),
    _: None = Depends(neo4j_required),
):
    """Resolve a share token to a read-only investigation payload."""
    inv = get_investigation_by_share_token(db, token)
    if not inv:
        raise HTTPException(status_code=404, detail="Share link not found or expired")
    return inv


@router.get("/{investigation_id}")
async def get_investigation_by_id(
    investigation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
    _: None = Depends(neo4j_required),
):
    """Return investigation metadata and the associated Neo4j graph."""
    inv = get_investigation(db, investigation_id, user.id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return inv


@router.post("/{investigation_id}/share")
async def create_share_link_for_investigation(
    investigation_id: str,
    request: CreateShareLinkRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Create a share link for the investigation."""
    result = create_share_link(db, investigation_id, user.id, request.expires_days)
    if not result:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return result


@router.patch("/{investigation_id}")
async def patch_investigation(
    investigation_id: str,
    request: UpdateInvestigationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Update investigation name."""
    inv = update_investigation(db, investigation_id, user.id, request.name)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return inv


@router.delete("/{investigation_id}")
async def remove_investigation(
    investigation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Delete investigation (PostgreSQL + Neo4j)."""
    ok = delete_investigation(db, investigation_id, user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return {"success": True}


@router.patch("/{investigation_id}/entities")
async def patch_entity_metadata(
    investigation_id: str,
    request: UpdateEntityMetadataRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
    _: None = Depends(neo4j_required),
):
    """Update notes and tags for an entity in the investigation graph."""
    ok = update_entity_metadata(
        db, investigation_id, user.id, request.cy_id, request.notes, request.tags
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Investigation or entity not found")
    return {"success": True}


@router.post("/{investigation_id}/entities")
async def add_entity_to_investigation(
    investigation_id: str,
    request: AddEntityRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
    _: None = Depends(neo4j_required),
):
    """Add an entity to the investigation graph manually."""
    result = add_entity(db, investigation_id, user.id, request.entity_type, request.entity_value)
    if not result:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return result


@router.get("/{investigation_id}/export/json")
async def export_investigation_json(
    investigation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Export investigation graph as JSON."""
    inv = get_investigation(db, investigation_id, user.id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return inv


@router.get("/{investigation_id}/export/csv")
async def export_investigation_csv(
    investigation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Export investigation nodes and edges as a CSV download."""
    inv = get_investigation(db, investigation_id, user.id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    graph = inv.get("graph") or {}
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["type", "id", "value"])
    for node in nodes:
        node_data = node.get("data") or {}
        writer.writerow(["node", node_data.get("id", ""), node_data.get("label", "")])
    writer.writerow(["type", "source", "target"])
    for edge in edges:
        edge_data = edge.get("data") or {}
        writer.writerow(["edge", edge_data.get("source", ""), edge_data.get("target", "")])

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=investigation_{investigation_id}.csv"
        },
    )


@router.post("/{investigation_id}/run-enricher")
def run_enricher_on_entity(
    investigation_id: str,
    request: RunEnricherRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
    _: None = Depends(neo4j_required),
):
    """Run an enricher asynchronously via Celery. Returns the task_id for polling."""
    try:
        from app.tasks.investigation_tasks import run_enricher_task

        task = run_enricher_task.delay(
            investigation_id,
            user.id,
            request.entity_type,
            request.entity_value,
            request.enricher_name,
        )
        return {"task_id": task.id, "status": "pending"}
    except Exception as exc:
        # Celery/Redis unavailable - run synchronously as a graceful fallback.
        logger.warning("Falling back to sync enricher %s for %s/%s: %s",
                       request.enricher_name, request.entity_type, request.entity_value, exc)
        result = run_enricher(
            db,
            investigation_id,
            user.id,
            request.entity_type,
            request.entity_value,
            request.enricher_name,
        )
        if not result.get("success"):
            raise HTTPException(
                status_code=500, detail=result.get("error", "Enricher failed")
            )
        return result


@router.get("/{investigation_id}/tasks/{task_id}")
def get_enricher_task_status(
    investigation_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Return the current Celery task status; used for polling after run-enricher."""
    inv = get_investigation(db, investigation_id, user.id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    try:
        from app.tasks.investigation_tasks import run_enricher_task

        task = run_enricher_task.AsyncResult(task_id)
        if task.state == "PENDING":
            return {"task_id": task_id, "status": "pending"}
        if task.state == "SUCCESS":
            return {"task_id": task_id, "status": "success", **(task.result or {})}
        if task.state == "FAILURE":
            return {"task_id": task_id, "status": "failure", "error": str(task.result)}
        return {"task_id": task_id, "status": task.state.lower()}
    except Exception as exc:
        logger.debug("Celery backend unavailable for %s: %s", task_id, exc)
        return {"task_id": task_id, "status": "unknown", "error": "Task backend unavailable"}


@router.websocket("/ws/{investigation_id}")
async def websocket_investigation(websocket: WebSocket, investigation_id: str):
    """
    WebSocket: run enricher with real-time progress.
    Client sends: {"token": "jwt", "action": "run_enricher", "entity_type": "domain", "entity_value": "example.com", "enricher_name": "dns"}
    Server sends: {"stage": "dns", "progress": 50, "message": "..."} then {"stage": "done", "success": true, "new_nodes": [...], "new_edges": [...]}
    """
    await websocket.accept()
    progress_queue: asyncio.Queue = asyncio.Queue()

    def on_progress(stage: str, progress: int, message: str) -> None:
        progress_queue.put_nowait({"stage": stage, "progress": progress, "message": message})

    async def send_progress() -> None:
        while True:
            msg = await progress_queue.get()
            if msg.get("stage") in ("done", "error"):
                break
            try:
                await websocket.send_json(msg)
            except Exception as send_exc:
                logger.debug("WebSocket progress send failed, stopping: %s", send_exc)
                break

    try:
        request = await websocket.receive_json()
        token = request.get("token")
        if not token:
            await websocket.send_json({"error": "token required"})
            await websocket.close()
            return

        payload = decode_token(token)
        if not payload or "sub" not in payload:
            await websocket.send_json({"error": "invalid token"})
            await websocket.close()
            return
        try:
            user_id = int(payload["sub"])
        except (ValueError, TypeError):
            await websocket.send_json({"error": "invalid token"})
            await websocket.close()
            return

        if request.get("action") != "run_enricher":
            await websocket.send_json({"error": "unknown action"})
            await websocket.close()
            return

        entity_type = request.get("entity_type")
        entity_value = request.get("entity_value")
        enricher_name = request.get("enricher_name")
        if not all([entity_type, entity_value, enricher_name]):
            await websocket.send_json(
                {"error": "entity_type, entity_value, enricher_name required"}
            )
            await websocket.close()
            return

        db = SessionLocal()
        progress_task = asyncio.create_task(send_progress())
        try:
            result = await asyncio.to_thread(
                run_enricher,
                db,
                investigation_id,
                user_id,
                entity_type,
                entity_value,
                enricher_name,
                on_progress,
            )
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass

            await websocket.send_json({"stage": "done", "progress": 100, **result})
        finally:
            db.close()
    except WebSocketDisconnect:
        logger.debug("WebSocket investigation client disconnected")
    except Exception as exc:
        logger.warning("WebSocket investigation enricher failed: %s", exc)
        try:
            await websocket.send_json({"error": str(exc), "stage": "error"})
        except Exception as send_exc:
            logger.debug("Failed to push WebSocket error frame: %s", send_exc)

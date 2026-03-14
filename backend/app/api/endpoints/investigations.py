"""
Investigation endpoints — CRUD, add entity, run enricher.
Requires authentication. Neo4j required.
"""

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_required
from app.db.database import get_db
from app.db.models import User
from app.services.investigation_service import (
    list_investigations,
    create_investigation,
    get_investigation,
    update_investigation,
    delete_investigation,
    add_entity,
    run_enricher,
    update_entity_metadata,
    create_share_link,
    get_investigation_by_share_token,
    require_neo4j_for_investigation,
)

router = APIRouter(prefix="/investigations", tags=["investigations"])


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
):
    """List investigations for the current user."""
    try:
        require_neo4j_for_investigation()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"investigations": list_investigations(db, user.id)}


@router.post("")
async def create_new_investigation(
    request: CreateInvestigationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Create a new investigation."""
    try:
        require_neo4j_for_investigation()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    inv = create_investigation(db, user.id, request.name)
    return inv


@router.get("/shared/{token}")
async def get_shared_investigation(
    token: str,
    db: Session = Depends(get_db),
):
    """Get investigation by share token (read-only, no auth required)."""
    try:
        require_neo4j_for_investigation()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    inv = get_investigation_by_share_token(db, token)
    if not inv:
        raise HTTPException(status_code=404, detail="Share link not found or expired")
    return inv


@router.get("/{investigation_id}")
async def get_investigation_by_id(
    investigation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Get investigation metadata and graph from Neo4j."""
    try:
        require_neo4j_for_investigation()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
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
):
    """Update notes and tags for an entity in the investigation graph."""
    try:
        require_neo4j_for_investigation()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    ok = update_entity_metadata(db, investigation_id, user.id, request.cy_id, request.notes, request.tags)
    if not ok:
        raise HTTPException(status_code=404, detail="Investigation or entity not found")
    return {"success": True}


@router.post("/{investigation_id}/entities")
async def add_entity_to_investigation(
    investigation_id: str,
    request: AddEntityRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Add entity to investigation graph manually."""
    try:
        require_neo4j_for_investigation()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
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
    """Export investigation nodes and edges as CSV."""
    import csv
    from fastapi.responses import StreamingResponse
    from io import StringIO

    inv = get_investigation(db, investigation_id, user.id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    graph = inv.get("graph") or {}
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["type", "id", "value"])
    for n in nodes:
        d = n.get("data") or {}
        writer.writerow(["node", d.get("id", ""), d.get("label", "")])
    writer.writerow(["type", "source", "target"])
    for e in edges:
        d = e.get("data") or {}
        writer.writerow(["edge", d.get("source", ""), d.get("target", "")])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=investigation_{investigation_id}.csv"},
    )


@router.post("/{investigation_id}/run-enricher")
def run_enricher_on_entity(
    investigation_id: str,
    request: RunEnricherRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Run enricher on entity (async via Celery). Returns task_id for polling."""
    try:
        require_neo4j_for_investigation()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

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
    except Exception as e:
        # Fallback to sync if Celery/Redis unavailable
        result = run_enricher(
            db,
            investigation_id,
            user.id,
            request.entity_type,
            request.entity_value,
            request.enricher_name,
        )
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Enricher failed"))
        return result


@router.get("/{investigation_id}/tasks/{task_id}")
def get_enricher_task_status(
    investigation_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """Get Celery task status and result. Used for polling after run-enricher."""
    inv = get_investigation(db, investigation_id, user.id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    try:
        from app.tasks.investigation_tasks import run_enricher_task

        task = run_enricher_task.AsyncResult(task_id)
        if task.state == "PENDING":
            return {"task_id": task_id, "status": "pending"}
        if task.state == "SUCCESS":
            result = task.result or {}
            return {"task_id": task_id, "status": "success", **result}
        if task.state == "FAILURE":
            return {"task_id": task_id, "status": "failure", "error": str(task.result)}
        return {"task_id": task_id, "status": task.state.lower()}
    except Exception:
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

    def on_progress(stage: str, progress: int, message: str):
        progress_queue.put_nowait({"stage": stage, "progress": progress, "message": message})

    async def send_progress():
        while True:
            msg = await progress_queue.get()
            if msg.get("stage") in ("done", "error"):
                break
            try:
                await websocket.send_json(msg)
            except Exception:
                break

    try:
        data = await websocket.receive_json()
        token = data.get("token")
        if not token:
            await websocket.send_json({"error": "token required"})
            await websocket.close()
            return

        from app.services.auth_service import decode_token
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

        action = data.get("action")
        if action != "run_enricher":
            await websocket.send_json({"error": "unknown action"})
            await websocket.close()
            return

        entity_type = data.get("entity_type")
        entity_value = data.get("entity_value")
        enricher_name = data.get("enricher_name")
        if not all([entity_type, entity_value, enricher_name]):
            await websocket.send_json({"error": "entity_type, entity_value, enricher_name required"})
            await websocket.close()
            return

        from app.db.database import SessionLocal
        db = SessionLocal()

        progress_task = asyncio.create_task(send_progress())
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

        await websocket.send_json({
            "stage": "done",
            "progress": 100,
            **result,
        })
        db.close()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"error": str(e), "stage": "error"})
        except Exception:
            pass

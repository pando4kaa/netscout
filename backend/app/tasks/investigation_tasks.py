"""
Celery tasks for investigation enrichers.
"""

from app.celery_app import celery_app
from app.db.database import SessionLocal
from app.services.investigation_service import run_enricher


@celery_app.task(bind=True)
def run_enricher_task(
    self,
    investigation_id: str,
    user_id: int,
    entity_type: str,
    entity_value: str,
    enricher_name: str,
):
    """
    Run enricher on entity. Uses new DB session per task.
    Returns {success, new_nodes, new_edges, error}.
    """
    db = SessionLocal()
    try:
        result = run_enricher(
            db,
            investigation_id,
            user_id,
            entity_type,
            entity_value,
            enricher_name,
            on_progress=None,
        )
        return result
    finally:
        db.close()

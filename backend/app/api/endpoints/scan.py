"""
Scan endpoints
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
from typing import List
import sys
import os

# Add parent directory to path to import src modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from src.main import scan_domain

router = APIRouter()


class ScanRequest(BaseModel):
    domain: str


@router.post("/scan")
async def start_scan(request: ScanRequest):
    """
    Start domain scan
    """
    try:
        results = scan_domain(request.domain)
        return {
            "success": True,
            "scan_id": f"scan_{request.domain}_{hash(request.domain)}",
            "results": results
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/scan/{scan_id}")
async def get_scan_results(scan_id: str):
    """
    Get scan results by scan_id
    """
    # TODO: Implement getting results from database
    return {"scan_id": scan_id, "status": "completed"}


@router.get("/scan/history")
async def get_scan_history():
    """
    Get scan history
    """
    # TODO: Implement getting history from database
    return {"scans": []}


@router.websocket("/ws/scan/{scan_id}")
async def websocket_scan(websocket: WebSocket, scan_id: str):
    """
    WebSocket endpoint for real-time scan updates
    """
    await websocket.accept()
    try:
        while True:
            # TODO: Implement real-time updates
            data = await websocket.receive_text()
            await websocket.send_json({"progress": 50, "message": "Scanning..."})
    except WebSocketDisconnect:
        pass

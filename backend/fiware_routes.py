import logging
import json
from typing import Dict, Any
from datetime import datetime
from dateutil.parser import parse as parse_datetime

from fastapi import APIRouter, HTTPException, Request, Body
from models import FiwareSensorData, FiwareWebhookData

router = APIRouter()

@router.post("/fiware/webhook")
async def fiware_webhook(request: Request, webhook_data: FiwareWebhookData):
    fiware_processor = request.app.state.fiware_processor
    try:
        results = await fiware_processor.process_fiware_data(webhook_data)
        return {"status": "success", **results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fiware/search")
async def fiware_search(request: Request, query: dict = Body(...)):
    """
    Search Fiware entities using a natural language query.
    Accepts JSON body: {"query": <str>, "limit": <int>}.
    Returns: {"results": [ ... ]}
    """
    fiware_processor = request.app.state.fiware_processor
    try:
        # Accept both {"query": ...} and {"search_term": ...}
        search_term = query.get("query") or query.get("search_term")
        if not search_term or not isinstance(search_term, str):
            raise HTTPException(status_code=400, detail="Missing or invalid search term.")
        limit = query.get("limit", 10)
        if not isinstance(limit, int) or limit <= 0:
            limit = 10
        results = await fiware_processor.search_fiware_data(search_term, limit)
        return {"results": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

@router.get("/fiware/health")
async def fiware_health():
    try:
        # Simple health check: try a trivial search or return ok
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

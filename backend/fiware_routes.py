from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from models import FiwareWebhookData
from fiware_processor import fiware_processor
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fiware", tags=["fiware"])

class SensorSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10

class SensorSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total_count: int

class SensorStatisticsResponse(BaseModel):
    total_sensors: int
    sensor_types: int
    earliest_reading: Optional[str]
    latest_reading: Optional[str]

@router.post("/webhook")
async def receive_fiware_webhook(webhook_data: FiwareWebhookData):
    """
    Receive Fiware entity data webhook and process it.
    This endpoint accepts Fiware entity data in the standard format and stores it using Graphiti.
    """
    try:
        logger.info(f"Received Fiware webhook with {len(webhook_data.data)} entity readings")
        result = await fiware_processor.process_fiware_data(webhook_data)
        logger.info(f"Successfully processed {result['processed_entities']} entities")
        return {
            "status": "success",
            "message": f"Processed {result['processed_entities']} entity readings",
            "processed_entities": result["processed_entities"],
            "entity_ids": result["entity_ids"],
            "errors": result["errors"]
        }
    except Exception as e:
        logger.error(f"Error processing Fiware webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {str(e)}")

@router.post("/search")
async def search_fiware_data(search_request: SensorSearchRequest):
    """
    Search Fiware entity data using semantic search via Graphiti.
    This endpoint allows you to search through stored Fiware entity data using natural language queries.
    """
    try:
        logger.info(f"Searching fiware data with query: '{search_request.query}'")
        results = await fiware_processor.search_fiware_data(
            query=search_request.query,
            limit=search_request.limit or 10
        )
        return {
            "results": results,
            "total_count": len(results)
        }
    except Exception as e:
        logger.error(f"Error searching fiware data: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching fiware data: {str(e)}")

@router.get("/health")
async def fiware_health_check():
    """
    Health check endpoint for Fiware integration.
    
    Returns the status of the Fiware data processor and Graphiti integration.
    """
    try:
        # Test Graphiti connection (no direct Neo4j check)
        stats = fiware_processor.get_sensor_statistics()
        
        return {
            "status": "healthy",
            "graphiti_initialized": True,
            "total_sensors": stats.get("total_sensors", None),
            "sensor_types": stats.get("sensor_types", None)
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        } 
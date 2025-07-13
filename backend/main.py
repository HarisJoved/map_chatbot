from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Union, Any
import uvicorn
from pydantic import BaseModel
import logging
from agent import generate_response
from tools.schema import fetch_schema
from tools.upsert_liked_response import router as upsert_liked_response_router
from fiware_routes import router as fiware_router
from fiware_processor import fiware_processor

from models import Location, SearchRequest, SearchResponse
from database import neo4j_connection
from config import API_PREFIX, DEBUG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Map Chat API",
    description="API for Map Chat Application with Neo4j integration",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify your frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to Map Chat API"}

@app.get(f"{API_PREFIX}/locations/search", response_model=SearchResponse)
async def search_locations(
    query: str = Query(..., description="Search term for locations"),
    limit: int = Query(10, description="Maximum number of results to return")
):
    try:
        results = neo4j_connection.search_locations(query, limit)
        return SearchResponse(results=[
            Location(
                address=result["address"],
                postcode=result["postcode"],
                latitude=result["latitude"],
                longitude=result["longitude"]
            ) for result in results
        ])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post(f"{API_PREFIX}/locations/search", response_model=SearchResponse)
async def search_locations_post(search_request: SearchRequest):
    try:
        results = neo4j_connection.search_locations(
            search_request.search_term, 
            search_request.limit or 10
        )
        return SearchResponse(results=[
            Location(
                address=result["address"],
                postcode=result["postcode"],
                latitude=result["latitude"],
                longitude=result["longitude"]
            ) for result in results
        ])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

class ChatRequest(BaseModel):
    message: str

from typing import Union

class ChatResponse(BaseModel):
    response: Union[str, List[Any]]
    location: Optional[Location] = None
    locations: Optional[List[Location]] = None

# Store last locations in a global variable (for demo; in production, use session/user context)
last_locations = []

@app.post(f"{API_PREFIX}/chat")
async def chat(request: ChatRequest):
    global last_locations
    try:
        logger.info(f"Received chat request: {request.message}")
        # Always use the new agent/LLM logic for all queries
        result = generate_response(request.message)
        return result
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")

@app.get(f"{API_PREFIX}/schema")
async def get_schema():
    return {"schema": fetch_schema()}

@app.get(f"{API_PREFIX}/defect-by-location")
async def get_defect_by_location(latitude: float, longitude: float):
    try:
        # First get the defect
        query = """
        MATCH (d:Defect)-[:HAS_LOCATION]->(l:Location)
        WHERE l.location_lat = $latitude AND l.location_lon = $longitude
        RETURN d
        """
        defect_result = neo4j_connection.query(query, {"latitude": latitude, "longitude": longitude})
        
        if not defect_result:
            return {"error": "No defect found at this location"}
            
        defect = defect_result[0]['d']
        
        # Get associated CRM case
        crm_query = """
        MATCH (d:Defect {defect_id: $defect_id})-[:ASSOCIATED_WITH]-(c:CRMCase)
        RETURN c
        """
        crm_result = neo4j_connection.query(crm_query, {"defect_id": defect['defect_id']})
        
        # Prepare the response
        response = {
            "defect": {
                "defect_id": defect['defect_id'],
                "category": defect['category'],
                "severity": defect['severity'],
                "description": defect['description'],
                "timesDetected": defect['timesDetected'],
                "detectedAt": defect['detectedAt']
            }
        }
        
        # Add CRM case if exists
        if crm_result and len(crm_result) > 0:
            crm_case = crm_result[0]['c']
            response["defect"]["crm_case"] = {
                "case_id": crm_case['case_id'],
                "status": crm_case['status'],
                "description": crm_case['description'],
                "createdAt": crm_case['createdAt']
            }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Shutdown event handler
@app.on_event("shutdown")
def shutdown_event():
    neo4j_connection.close()

app.include_router(upsert_liked_response_router, prefix=API_PREFIX)
app.include_router(fiware_router, prefix=API_PREFIX)

# Ensure Graphiti indexes/constraints are built at startup
@app.on_event("startup")
async def build_graphiti_indexes():
    await fiware_processor.graphiti.build_indices_and_constraints()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=DEBUG) 
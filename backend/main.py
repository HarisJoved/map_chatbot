from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import uvicorn
from pydantic import BaseModel
import logging
from agent import generate_response
from tools.schema import fetch_schema

from models import Location, SearchRequest, SearchResponse
from database import neo4j_connection
from config import API_PREFIX, DEBUG

# Configure logging
logging.basicConfig(level=logging.INFO)
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
            search_request.limit
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

class ChatResponse(BaseModel):
    response: str
    location: Optional[Location] = None
    locations: Optional[List[Location]] = None

# Store last locations in a global variable (for demo; in production, use session/user context)
last_locations = []

@app.post(f"{API_PREFIX}/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    global last_locations
    try:
        logger.info(f"Received chat request: {request.message}")
        message_lower = request.message.lower()
        # If user asks for locations in an area
        if "locations in" in message_lower or "list locations" in message_lower or "show locations" in message_lower:
            # Extract area name
            import re
            match = re.search(r"locations in (.+)", message_lower)
            area_name = match.group(1).strip() if match else ""
            # Remove leading 'area' if present
            if area_name.startswith('area '):
                area_name = area_name[5:]
            area_name = area_name.strip()
            logger.info(f"Searching for locations in area: '{area_name}'")
            # Search for locations in area (match as substring in address or postcode)
            results = neo4j_connection.search_locations(area_name, limit=20)
            last_locations = [Location(address=r["address"], postcode=r["postcode"], latitude=r["latitude"], longitude=r["longitude"]) for r in results]
            if last_locations:
                response = f"<b>Locations in {area_name}:</b><ul>" + ''.join(f'<li>{loc.address} ({loc.postcode})</li>' for loc in last_locations) + "</ul>"
                return ChatResponse(response=response, locations=last_locations)
            else:
                return ChatResponse(response=f"No locations found in {area_name}.", locations=[])
        # If user says 'show me these locations'
        if "show me these locations" in message_lower or "display these locations" in message_lower:
            if last_locations:
                response = f"Showing {len(last_locations)} locations on the map."
                return ChatResponse(response=response, locations=last_locations)
            else:
                return ChatResponse(response="No locations to show. Please ask for locations in an area first.", locations=[])
        # Check if the message is asking about a location
        location_keywords = ["show", "where is", "locate", "find", "display", "show me"]
        if any(keyword in message_lower for keyword in location_keywords):
            # Extract the location name from the message
            words = message_lower.split()
            try:
                keyword_index = next(i for i, word in enumerate(words) if word in location_keywords)
                location_name = " ".join(words[keyword_index + 1:])
                logger.info(f"Extracted location name: {location_name}")
            except StopIteration:
                logger.warning("No location keyword found in message")
                return ChatResponse(response="I couldn't understand which location you're looking for.")
            
            # Search for the location in Neo4j
            try:
                results = neo4j_connection.search_locations(location_name, limit=1)
                logger.info(f"Search results: {results}")
                
                if results:
                    location = results[0]
                    # Check if this is an exact match
                    if location['address'].lower() == location_name.lower():
                        response = f"I found {location['address']}. Showing it on the map."
                    else:
                        response = f"I found a location that might match what you're looking for: {location['address']}. Showing it on the map."
                    
                    return ChatResponse(
                        response=response,
                        location=Location(
                            address=location['address'],
                            postcode=location['postcode'],
                            latitude=location['latitude'],
                            longitude=location['longitude']
                        )
                    )
                else:
                    return ChatResponse(
                        response=f"I couldn't find any location matching '{location_name}' in our database. Please try a different location or check the spelling."
                    )
            except Exception as db_error:
                logger.error(f"Database error while searching for location: {str(db_error)}")
                return ChatResponse(
                    response="I'm having trouble searching for locations right now. Please try again later."
                )
        
        # If not a location query, use the regular chat response
        response = generate_response(request.message)
        return ChatResponse(response=response)
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")

@app.get(f"{API_PREFIX}/schema")
async def get_schema():
    return {"schema": fetch_schema()}

# Shutdown event handler
@app.on_event("shutdown")
def shutdown_event():
    neo4j_connection.close()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=DEBUG) 
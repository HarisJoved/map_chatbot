from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from llm import embeddings
from pinecone import Pinecone
import logging

logger = logging.getLogger(__name__)

# Pinecone setup (reuse logic from upsert_all_to_pinecone.py)
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "locations-index")

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX)

router = APIRouter()

class LikedResponseRequest(BaseModel):
    user_message: str
    bot_response: str

@router.post("/upsert-liked-response")
async def upsert_liked_response(payload: LikedResponseRequest):
    try:
        # Use the bot response as the text to embed
        embedding = embeddings.embed_query(payload.bot_response)
        # Use a unique ID (hash of user_message + bot_response)
        import hashlib
        vector_id = hashlib.sha256((payload.user_message + payload.bot_response).encode("utf-8")).hexdigest()
        metadata = {
            "user_message": payload.user_message,
            "bot_response": payload.bot_response,
            "type": "liked_response"
        }
        index.upsert([(vector_id, embedding, metadata)])
        logger.info(f"Upserted liked response to Pinecone with id {vector_id}")
        return {"status": "success", "vector_id": vector_id}
    except Exception as e:
        logger.error(f"Error upserting liked response: {e}")
        raise HTTPException(status_code=500, detail=f"Error upserting liked response: {str(e)}") 
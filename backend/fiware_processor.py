import logging
import json
import asyncio
from typing import Dict, Any, List
from datetime import datetime
from dateutil.parser import parse as parse_datetime

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.llm_client.gemini_client import GeminiClient, LLMConfig
from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig
from graphiti_core.cross_encoder.gemini_reranker_client import GeminiRerankerClient

from config import (
    GOOGLE_API_KEY,
    GRAPHITI_NEO4J_URI,
    GRAPHITI_NEO4J_USER,
    GRAPHITI_NEO4J_PASSWORD
)
from models import FiwareSensorData, FiwareWebhookData

logger = logging.getLogger(__name__)

class FiwareDataProcessor:
    def __init__(self):
        """Initialize the Fiware data processor with Graphiti integration."""
        import os
        print(f"[DEBUG] Neo4j URI in use: {os.getenv('NEO4J_URI')}")
        print(f"[DEBUG] Neo4j USER in use: {os.getenv('NEO4J_USERNAME')}")
        self.graphiti = self._initialize_graphiti()
        self.group_id = "fiware_data"

    def _initialize_graphiti(self) -> Graphiti:
        llm_cfg = LLMConfig(
            api_key=GOOGLE_API_KEY,
            model="gemini-2.0-flash",
            small_model="gemini-2.0-flash"
        )
        llm_client = GeminiClient(config=llm_cfg)
        embedder = GeminiEmbedder(config=GeminiEmbedderConfig(
            api_key=GOOGLE_API_KEY,
            embedding_model="embedding-001"
        ))
        reranker = GeminiRerankerClient(config=LLMConfig(
            api_key=GOOGLE_API_KEY,
            model="gemini-2.5-flash-lite-preview-06-17"
        ))

        graphiti = Graphiti(
            GRAPHITI_NEO4J_URI,
            GRAPHITI_NEO4J_USER,
            GRAPHITI_NEO4J_PASSWORD,
            llm_client=llm_client,
            embedder=embedder,
            cross_encoder=reranker
        )
        logger.info("Graphiti initialized successfully")
        return graphiti

    async def process_fiware_data(self, webhook_data: FiwareWebhookData) -> Dict[str, Any]:
        results = {"processed_entities": 0, "errors": [], "entity_ids": []}
        for entity in webhook_data.data:
            try:
                await self._create_graphiti_episode(entity)
                eid = entity.root.get("id", None)
                results["processed_entities"] += 1
                results["entity_ids"].append(eid)
                logger.info(f"Processed entity {eid}")
            except Exception as e:
                msg = f"Error entity {entity.root.get('id', '?')}: {e}"
                logger.error(msg)
                results["errors"].append(msg)
        return results

    def _create_entity_description(self, data: FiwareSensorData) -> Dict[str, Any]:
        r = data.root
        eid = r.get("id", "unknown")
        etype = r.get("type", "unknown")
        # Try to extract location if present
        coords = None
        if "location" in r and "value" in r["location"] and "coordinates" in r["location"]["value"]:
            coords = r["location"]["value"]["coordinates"]
        ts_val = r.get("TimeInstant", {}).get("value") if isinstance(r.get("TimeInstant"), dict) else r.get("TimeInstant")
        ts = parse_datetime(ts_val).isoformat() if ts_val else None
        attrs = {k: (v["value"] if isinstance(v, dict) and "value" in v else v) for k, v in r.items() if k not in ["id", "type", "location", "TimeInstant"]}
        description = f"Entity {eid} ({etype})"
        if coords:
            description += f" at lat {coords[1]}, lon {coords[0]}"
        if ts:
            description += f" on {ts}"
        if attrs:
            description += ". Attributes: " + ", ".join(f"{k}={v}" for k, v in attrs.items())
        return {"text": description, "body": {"id": eid, **attrs}, "timestamp": ts}

    async def _create_graphiti_episode(self, data: FiwareSensorData) -> None:
        desc = self._create_entity_description(data)
        await self.graphiti.add_episode(
            name=f"Entity {data.root.get('id', '?')}",
            episode_body=json.dumps(desc["body"]),
            source=EpisodeType.json,
            source_description=desc["text"],
            reference_time=parse_datetime(desc["timestamp"]) if desc["timestamp"] else None,
            group_id=self.group_id
        )
        logger.info(f"Graphiti episode added for {data.root.get('id', '?')}")

    async def search_fiware_data(self, query: str, limit: int = 10) -> list:
        """Search sensor data using Graphiti's semantic search capabilities. Only use Graphiti, no Cypher fallback."""
        try:
            # Try Graphiti semantic search only
            results = await self.graphiti.search(query)
            results = results[:limit]
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.metadata.get("id"),
                    "type": result.metadata.get("type"),
                    "timestamp": result.metadata.get("timestamp"),
                    "relevance_score": getattr(result, 'score', None),
                    "text": getattr(result, 'text', None)
                })
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching fiware data with Graphiti: {e}")
            raise

# Singleton instance
fiware_processor = FiwareDataProcessor()

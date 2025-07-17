import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("fiware_processor").setLevel(logging.DEBUG)
import json
from typing import Dict, Any
from datetime import datetime
from dateutil.parser import parse as parse_datetime

from graphiti_core import Graphiti
from graphiti_core.nodes import EntityNode
from graphiti_core.edges import EntityEdge
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

# Enable DEBUG logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class FiwareDataProcessor:
    def __init__(self):
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
        # Ensure all required Neo4j constraints and indexes are created
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already running (e.g., in FastAPI), schedule as a task
                loop.create_task(graphiti.build_indices_and_constraints())
            else:
                loop.run_until_complete(graphiti.build_indices_and_constraints())
            logger.info("Graphiti indices and constraints initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Graphiti indices/constraints: {e}")
        return graphiti

    async def process_fiware_data(self, webhook_data: FiwareWebhookData) -> Dict[str, Any]:
        results = {"processed_entities": 0, "errors": [], "entity_ids": []}
        for entity in webhook_data.data:
            try:
                await self._create_graph_nodes(entity)
                eid = entity.root.get("id", None)
                results["processed_entities"] += 1
                results["entity_ids"].append(eid)
                logger.info(f"Processed entity {eid}")
            except Exception as e:
                msg = f"Error entity {entity.root.get('id', '?')}: {e}"
                logger.error(msg)
                results["errors"].append(msg)
        return results

    async def _create_graph_nodes(self, data: FiwareSensorData) -> None:
        r = data.root
        eid = r.get("id")
        etype = r.get("type", "unknown")
        # Extract location if present
        coords = None
        if "location" in r and "value" in r["location"] and "coordinates" in r["location"]["value"]:
            coords = r["location"]["value"]["coordinates"]
        # Extract timestamp
        ts_val = r.get("TimeInstant", {}).get("value") if isinstance(r.get("TimeInstant"), dict) else r.get("TimeInstant")
        timestamp = parse_datetime(ts_val).isoformat() if ts_val else datetime.utcnow().isoformat()
        # Dynamic properties for Measurement node
        measurement_props = {"timestamp": timestamp}
        for k, v in r.items():
            if k in ["id", "type", "location", "TimeInstant"]:
                continue
            if isinstance(v, dict) and "value" in v:
                value = v["value"]
                if isinstance(value, dict):
                    value = json.dumps(value)
                measurement_props[k] = value
            else:
                measurement_props[k] = v
        # Helper to get or create a node by name and group_id
        async def get_or_create_entity_node(name, group_id, labels, summary, attributes):
            existing_nodes = await EntityNode.get_by_group_ids(self.graphiti.driver, [group_id])
            for node in existing_nodes:
                if node.name == name:
                    logger.info(f"Reusing existing node: {name} ({node.uuid})")
                    return node
            node = EntityNode(
                name=name,
                group_id=group_id,
                labels=labels,
                summary=summary,
                attributes=attributes
            )
            await node.generate_name_embedding(self.graphiti.embedder)
            await node.save(self.graphiti.driver)
            logger.info(f"Created new node: {name} ({node.uuid})")
            return node

        # Device node
        device_node = await get_or_create_entity_node(
            eid,
            self.group_id,
            ["Device"],
            f"Device {eid} of type {etype}.",
            {"device_type": etype}
        )
        # Measurement node (unique per reading)
        measurement_node = await get_or_create_entity_node(
            f"Measurement for {eid} at {timestamp}",
            self.group_id,
            ["Measurement"],
            f"Measurement at {timestamp}",
            measurement_props
        )
        # Edge: Device HAS_MEASUREMENT Measurement
        logger.info(f"Creating edge HAS_MEASUREMENT from {device_node.uuid} to {measurement_node.uuid}")
        try:
            has_measurement_edge = EntityEdge(
                name="HAS_MEASUREMENT",
                group_id=self.group_id,
                source_node_uuid=device_node.uuid,
                target_node_uuid=measurement_node.uuid,
                fact=f"Device {eid} has measurement at {timestamp}",
                attributes={},
                created_at=datetime.utcnow()
            )
            await has_measurement_edge.generate_embedding(self.graphiti.embedder)
            await has_measurement_edge.save(self.graphiti.driver)
        except Exception as e:
            logger.error(f"Failed to save edge HAS_MEASUREMENT: {e}")

        # Optional location node and edge
        if coords:
            # Helper to find existing Location node by coordinates and device
            async def find_location_node_by_coords(group_id, eid, coords):
                existing_nodes = await EntityNode.get_by_group_ids(self.graphiti.driver, [group_id])
                for node in existing_nodes:
                    if (
                        "Location" in node.labels and
                        node.name.startswith(f"Location for {eid}") and
                        node.attributes.get("lat") == coords[1] and
                        node.attributes.get("lon") == coords[0]
                    ):
                        return node
                return None

            loc_node = await find_location_node_by_coords(self.group_id, eid, coords)
            if not loc_node:
                loc_node = await get_or_create_entity_node(
                    f"Location for {eid} at {coords[1]},{coords[0]}",
                    self.group_id,
                    ["Location"],
                    f"Located at lat={coords[1]}, lon={coords[0]}",
                    {"lat": coords[1], "lon": coords[0]}
                )
            logger.info(f"Creating edge LOCATED_AT from {device_node.uuid} to {loc_node.uuid}")
            try:
                located_at_edge = EntityEdge(
                    name="LOCATED_AT",
                    group_id=self.group_id,
                    source_node_uuid=device_node.uuid,
                    target_node_uuid=loc_node.uuid,
                    fact=f"Device {eid} is located at lat={coords[1]}, lon={coords[0]}",
                    attributes={},
                    created_at=datetime.utcnow()
                )
                await located_at_edge.generate_embedding(self.graphiti.embedder)
                await located_at_edge.save(self.graphiti.driver)
            except Exception as e:
                logger.error(f"Failed to save edge LOCATED_AT: {e}")
        logger.info(f"Stored entity {eid} with graph structure.")

    async def search_fiware_data(self, query: str, limit: int = 10) -> list:
        """
        Search Fiware entities using a natural language query.
        Args:
            query (str): The search query string.
            limit (int): Max number of results to return.
        Returns:
            List[dict]: Each dict contains id, type, timestamp, relevance_score, text, source, target, attributes.
        """
        try:
            results = await self.graphiti.search(query)
            results = results[:limit]
            formatted_results = []
            for idx, result in enumerate(results):
                logger.debug(f"Raw search result {idx}: {result}")
                logger.debug(f"Result {idx} __dict__: {getattr(result, '__dict__', str(result))}")
                created_at = getattr(result, 'created_at', None)
                if created_at and hasattr(created_at, 'isoformat'):
                    created_at = created_at.isoformat()
                formatted_results.append({
                    "id": getattr(result, 'uuid', None),
                    "type": getattr(result, 'name', None),
                    "timestamp": created_at,
                    "relevance_score": getattr(result, 'score', None),
                    "text": getattr(result, 'fact', None),
                    "source": getattr(result, 'source_node_uuid', None),
                    "target": getattr(result, 'target_node_uuid', None),
                    "attributes": getattr(result, 'attributes', None),
                })
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching fiware data with Graphiti: {e}")
            raise

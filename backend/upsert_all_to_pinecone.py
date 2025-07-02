import os
import logging
from llm import embeddings
from database import neo4j_connection
from pinecone import Pinecone
from datetime import datetime
from neo4j.time import DateTime as Neo4jDateTime

logger = logging.getLogger(__name__)

# Initialize Pinecone
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENVIRONMENT")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "locations-index")

# Initialize Pinecone client
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX)

def convert_value_for_pinecone(value):
    """Convert values to Pinecone-compatible format."""
    if value is None:
        return ""  # Convert None to empty string
    if isinstance(value, (datetime, Neo4jDateTime)):
        return value.isoformat()
    elif hasattr(value, 'ticks'):  # Handle other Neo4j time types
        return str(value)
    elif isinstance(value, (int, float)):
        return value  # Keep numbers as is
    elif isinstance(value, bool):
        return value  # Keep booleans as is
    elif isinstance(value, (list, tuple)):
        return [str(item) if item is not None else "" for item in value]  # Convert list items to strings
    return str(value)  # Convert everything else to string

def prepare_metadata(data):
    """Prepare metadata by converting all values to Pinecone-compatible format."""
    if isinstance(data, dict):
        return {k: prepare_metadata(v) for k, v in data.items() if k is not None}
    elif isinstance(data, (list, tuple)):
        return [prepare_metadata(item) for item in data]
    else:
        return convert_value_for_pinecone(data)

def upsert_all_locations_to_pinecone():
    """Fetch all Location nodes from Neo4j, embed, and upsert to Pinecone."""
    query = """
    MATCH (l:Location)
    RETURN l.address AS address, l.postcode AS postcode, l.latitude AS latitude, l.longitude AS longitude
    """
    locations = neo4j_connection.query(query)
    if not locations:
        print("No locations found in Neo4j.")
        return
    vectors = []
    for loc in locations:
        text = f"{loc['address']} {loc['postcode']} {loc['latitude']} {loc['longitude']}"
        embedding = embeddings.embed_query(text)
        vector_id = f"{loc['address']}_{loc['postcode']}"
        metadata = {
            "address": loc['address'],
            "postcode": loc['postcode'],
            "latitude": loc['latitude'],
            "longitude": loc['longitude']
        }
        vectors.append((vector_id, embedding, metadata))
    index.upsert(vectors)
    print(f"Upserted {len(vectors)} locations to Pinecone.")

def upsert_all_nodes_to_pinecone():
    """Embed and upsert all major node types from Neo4j into Pinecone."""
    node_types = [
        {
            "label": "Defect",
            "id_field": "defect_id",
            "query": """
                MATCH (d:Defect)
                RETURN d.defect_id AS defect_id, d.category AS category, d.description AS description, d.detectedAt AS detectedAt, d.severity AS severity, d.timesDetected AS timesDetected, d.location_lat AS location_lat, d.location_lon AS location_lon
            """
        },
        {
            "label": "Sensor",
            "id_field": "sensor_id",
            "query": """
                MATCH (s:Sensor)
                RETURN s.sensor_id AS sensor_id, s.category AS category, s.type AS type, s.location_lat AS location_lat, s.location_lon AS location_lon, s.accuracy AS accuracy, s.status AS status, s.controlledProperty AS controlledProperty
            """
        },
        {
            "label": "DetectionEvent",
            "id_field": "event_id",
            "query": """
                MATCH (e:DetectionEvent)
                RETURN e.event_id AS event_id, e.observedAt AS observedAt, e.image_url AS image_url, e.result AS result
            """
        },
        {
            "label": "CRMCase",
            "id_field": "case_id",
            "query": """
                MATCH (c:CRMCase)
                RETURN c.case_id AS case_id, c.status AS status, c.createdAt AS createdAt, c.severity AS severity, c.description AS description
            """
        },
        {
            "label": "RoadSegment",
            "id_field": "segment_id",
            "query": """
                MATCH (r:RoadSegment)
                RETURN r.segment_id AS segment_id, r.name AS name, r.refRoad AS refRoad, r.location_lat AS location_lat, r.location_lon AS location_lon, r.startKm AS startKm, r.endKm AS endKm, r.roadType AS roadType
            """
        },
        {
            "label": "Location",
            "id_field": "address_postcode",
            "query": """
                MATCH (l:Location)
                RETURN l.address AS address, l.postcode AS postcode, l.latitude AS latitude, l.longitude AS longitude
            """
        }
    ]
    for node in node_types:
        print(f"Processing {node['label']} nodes...")
        results = neo4j_connection.query(node["query"])
        if not results:
            print(f"No {node['label']} nodes found.")
            continue
        vectors = []
        for item in results:
            if node['label'] == 'Location':
                text = f"{item['address']} {item['postcode']} {item['latitude']} {item['longitude']}"
                vector_id = f"{item['address']}_{item['postcode']}"
                metadata = prepare_metadata(item)
            else:
                text = " ".join([str(v) for v in item.values() if v is not None])
                vector_id = str(item[node['id_field']])
                metadata = prepare_metadata(item)
            embedding = embeddings.embed_query(text)
            vectors.append((vector_id, embedding, metadata))
        index.upsert(vectors)
        print(f"Upserted {len(vectors)} {node['label']} nodes to Pinecone.")

if __name__ == "__main__":
    upsert_all_nodes_to_pinecone()
    print("All nodes embedded and upserted to Pinecone.") 
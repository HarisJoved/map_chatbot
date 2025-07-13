import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Neo4j Database Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# Graphiti Neo4j Instance Configuration
GRAPHITI_NEO4J_URI = os.getenv("NEO4J_URI")
GRAPHITI_NEO4J_USER = os.getenv("NEO4J_USERNAME")
GRAPHITI_NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
GRAPHITI_NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# App Configuration
API_PREFIX = "/api"
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t") 
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL") 
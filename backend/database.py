from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
import logging

logger = logging.getLogger(__name__)

class Neo4jConnection:
    def __init__(self):
        self._driver = None
        self._connect()

    def _connect(self):
        """Connect to Neo4j database."""
        try:
            self._driver = GraphDatabase.driver(
                NEO4J_URI, 
                auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            logger.info("Neo4j Database connection established")
        except Exception as e:
            logger.error(f"Neo4j Database connection failed: {e}")
            raise

    def close(self):
        """Close the driver connection."""
        if self._driver is not None:
            self._driver.close()
            logger.info("Neo4j Database connection closed")

    def query(self, query, parameters=None):
        """Execute a Cypher query."""
        assert self._driver is not None, "Driver not initialized!"
        
        if parameters is None:
            parameters = {}
            
        try:
            with self._driver.session() as session:
                result = session.run(query, parameters)
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            raise

    def search_locations(self, search_term, limit=10):
        """Search for locations based on a search term."""
        try:
            # Clean and normalize the search term
            search_term = search_term.strip()
            logger.info(f"Searching for location: '{search_term}'")
            
            # First try exact match
            exact_query = """
            MATCH (l:Location)
            WHERE toLower(l.address) = toLower($search_term)
            RETURN l.address as address, 
                   l.postcode as postcode, 
                   l.latitude as latitude, 
                   l.longitude as longitude
            LIMIT 1
            """
            
            exact_results = self.query(exact_query, {"search_term": search_term})
            
            if exact_results:
                logger.info(f"Found exact match for '{search_term}'")
                return exact_results
            
            # If no exact match, try partial match
            partial_query = """
            MATCH (l:Location)
            WHERE toLower(l.address) CONTAINS toLower($search_term)
            RETURN l.address as address, 
                   l.postcode as postcode, 
                   l.latitude as latitude, 
                   l.longitude as longitude
            ORDER BY length(l.address) ASC
            LIMIT $limit
            """
            
            partial_results = self.query(partial_query, {
                "search_term": search_term,
                "limit": limit
            })
            
            if partial_results:
                logger.info(f"Found {len(partial_results)} partial matches for '{search_term}'")
                return partial_results
            
            # If still no results, try searching by postcode
            postcode_query = """
            MATCH (l:Location)
            WHERE toLower(l.postcode) CONTAINS toLower($search_term)
            RETURN l.address as address, 
                   l.postcode as postcode, 
                   l.latitude as latitude, 
                   l.longitude as longitude
            LIMIT $limit
            """
            
            postcode_results = self.query(postcode_query, {
                "search_term": search_term,
                "limit": limit
            })
            
            if postcode_results:
                logger.info(f"Found {len(postcode_results)} postcode matches for '{search_term}'")
                return postcode_results
            
            logger.info(f"No matches found for '{search_term}'")
            return []
            
        except Exception as e:
            logger.error(f"Error searching locations: {str(e)}")
            raise

# Singleton instance
neo4j_connection = Neo4jConnection() 
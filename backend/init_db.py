from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
import logging

logger = logging.getLogger(__name__)

# Sample locations data
sample_locations = [
    {"address": "221B Baker Street", "postcode": "NW1 6XE", "latitude": 51.523767, "longitude": -0.1585557},
    {"address": "10 Downing Street", "postcode": "SW1A 2AA", "latitude": 51.5033635, "longitude": -0.1276248},
    {"address": "Buckingham Palace", "postcode": "SW1A 1AA", "latitude": 51.501364, "longitude": -0.14189},
    {"address": "London Eye", "postcode": "SE1 7PB", "latitude": 51.503324, "longitude": -0.119543},
    {"address": "Big Ben", "postcode": "SW1A 0AA", "latitude": 51.500729, "longitude": -0.124625},
    {"address": "105 Bevan Close", "postcode": "E16 4LZ", "latitude": 51.5089, "longitude": 0.0167}
]

class Neo4jInitializer:
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

    def create_constraints(self):
        """Create constraints for the Location nodes."""
        with self._driver.session() as session:
            # Drop existing constraints if they exist
            try:
                session.run("DROP CONSTRAINT location_address_postcode_constraint IF EXISTS")
            except Exception as e:
                print(f"Error dropping constraint: {e}")
            
            # Create unique constraint on Location.address and Location.postcode
            try:
                session.run("CREATE CONSTRAINT location_address_postcode_constraint FOR (l:Location) REQUIRE (l.address, l.postcode) IS UNIQUE")
                print("Created constraint: location_address_postcode_constraint")
            except Exception as e:
                print(f"Error creating constraint: {e}")

    def create_locations(self, locations):
        """Create Location nodes in the database."""
        with self._driver.session() as session:
            for location in locations:
                try:
                    session.run(
                        """
                        MERGE (l:Location {address: $address, postcode: $postcode})
                        SET l.latitude = $latitude,
                            l.longitude = $longitude
                        """,
                        address=location["address"],
                        postcode=location["postcode"],
                        latitude=location["latitude"],
                        longitude=location["longitude"]
                    )
                    print(f"Created/Updated location: {location['address']} {location['postcode']}")
                except Exception as e:
                    print(f"Error creating location {location['address']} {location['postcode']}: {e}")

    def initialize_database(self):
        """Initialize the database with constraints and sample data."""
        try:
            with self._driver.session() as session:
                # Clear existing data
                session.run("MATCH (n) DETACH DELETE n")
                
                # Create locations
                for location in sample_locations:
                    session.run("""
                        CREATE (l:Location {
                            address: $address,
                            postcode: $postcode,
                            latitude: $latitude,
                            longitude: $longitude
                        })
                    """, location)
                
                logger.info("Database initialized with sample data")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

if __name__ == "__main__":
    initializer = Neo4jInitializer()
    try:
        initializer.initialize_database()
    finally:
        initializer.close() 
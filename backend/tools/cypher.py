from llm import llm
from graph import graph
import logging

logger = logging.getLogger(__name__)

# Simple function to get defect information using Cypher
def cypher_qa(input):
    try:
        logger.info(f"Executing cypher query for: '{input}'")
        # Try a simple query to get relevant defect data
        cypher = """
        MATCH (d:Defect)
        WHERE toLower(d.description) CONTAINS toLower($search)
           OR toLower(d.category) CONTAINS toLower($search)
        OPTIONAL MATCH (e:DetectionEvent)-[:REPORTED_BY]->(d)
        RETURN d.defect_id AS defect_id, d.category AS category, d.description AS description, d.severity AS severity, d.timesDetected AS timesDetected, d.location_lat AS lat, d.location_lon AS lon, collect(DISTINCT e.event_id) AS detection_events
        LIMIT 5
        """
        # Extract potential search terms from user input
        search_term = input.lower()
        if "about" in search_term:
            search_term = search_term.split("about")[1].strip()
        logger.info(f"Search term for defects: '{search_term}'")
        result = graph.query(cypher, {"search": search_term})
        if result and len(result) > 0:
            logger.info(f"Found {len(result)} defects matching: '{search_term}'")
            # Format the results
            context = "\n".join([
                f"Defect ID: {item['defect_id']}, " +
                f"Category: {item['category']}, " +
                f"Description: {item.get('description', 'No description')}, " +
                f"Severity: {item.get('severity', 'Unknown')}, " +
                f"Times Detected: {item.get('timesDetected', 'Unknown')}, " +
                f"Location: ({item.get('lat', 'Unknown')}, {item.get('lon', 'Unknown')}), " +
                f"Detection Events: {', '.join(item['detection_events']) if item['detection_events'] else 'None'}"
                for item in result
            ])
            prompt = f"""
            These are the defects found in the database matching the query:
            {context}
            
            Based on this database information only, please answer: {input}
            
            Be specific that this information comes from the database. If the database information
            doesn't completely answer the question, just share what information is available in the database.
            DO NOT supplement with your general knowledge.
            """
            logger.info("Using database information to generate response")
            response = llm.invoke(prompt)
            return {"result": response.content}
        else:
            logger.info(f"No defects found matching: '{search_term}'")
            # Return None to try the next approach instead of using general knowledge
            return {"result": None}
    except Exception as e:
        logger.error(f"Error in cypher_qa: {e}")
        return {"result": None} 
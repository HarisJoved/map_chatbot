from llm import llm, embeddings
from graph import graph
import logging

logger = logging.getLogger(__name__)

# Function to get defect location information

def get_defect_location(input):
    try:
        logger.info(f"Searching for defects at locations matching: '{input}'")
        # Using direct Cypher query to find defects at specific locations or by description/category
        cypher = """
        MATCH (d:Defect)
        WHERE toLower(d.description) CONTAINS toLower($search)
           OR toLower(d.category) CONTAINS toLower($search)
        OPTIONAL MATCH (e:DetectionEvent)-[:REPORTED_BY]->(d)
        RETURN d.defect_id AS defect_id, d.category AS category, d.description AS description, d.severity AS severity, d.timesDetected AS timesDetected, d.location_lat AS lat, d.location_lon AS lon, collect(DISTINCT e.event_id) AS detection_events
        LIMIT 5
        """
        # Extract key terms from query
        search_terms = input.lower().split()
        search_terms = [term for term in search_terms if len(term) > 3]
        search_query = " ".join(search_terms) if search_terms else input.lower()
        logger.info(f"Search query for defects: '{search_query}'")
        result = graph.query(cypher, {"search": search_query})
        if not result or len(result) == 0:
            logger.info("No matching defects found")
            return {"output": None}
        # Format the results in a readable way
        context = "\n\n".join([
            f"Defect ID: {item['defect_id']}\n"
            f"Category: {item['category']}\n"
            f"Description: {item['description']}\n"
            f"Severity: {item['severity']}\n"
            f"Times Detected: {item['timesDetected']}\n"
            f"Location: ({item['lat']}, {item['lon']})\n"
            f"Detection Events: {', '.join(item['detection_events']) if item['detection_events'] else 'None'}"
            for item in result
        ])
        logger.info(f"Found {len(result)} defects with matching criteria")
        # Call the LLM with the retrieved context
        prompt = f"""
        Based on these defect details from our database, answer the question: {input}
        
        Defect Information from the database:
        {context}
        
        Base your answer only on the information provided above. Make it clear this information comes from the database.
        Do not supplement with your general knowledge. If the database information doesn't fully answer the question,
        just provide what information is available from these results.
        """
        response = llm.invoke(prompt)
        return {"output": response.content}
    except Exception as e:
        logger.error(f"Error in get_defect_location: {e}")
        return {"output": None} 
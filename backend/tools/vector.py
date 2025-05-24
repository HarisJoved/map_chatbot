from llm import llm, embeddings
from graph import graph
import logging

logger = logging.getLogger(__name__)

# Simple function to get crime location information
def get_crime_location(input):
    try:
        logger.info(f"Searching for crimes at locations matching: '{input}'")
        # Using direct Cypher query to find crimes at specific locations
        cypher = """
        MATCH (l:Location)
        WHERE l.address IS NOT NULL AND toLower(l.address) CONTAINS toLower($search)
        WITH l LIMIT 5
        OPTIONAL MATCH (c:Crime)-[:OCCURRED_AT]->(l)
        OPTIONAL MATCH (c)<-[:INVOLVED_IN]-(p:Person)
        OPTIONAL MATCH (l)-[:LOCATION_IN_AREA]->(a:Area)
        RETURN l.address AS address, 
               collect(distinct c.type) AS crime_types,
               collect(distinct c.date) AS dates,
               collect(distinct c.description) AS descriptions,
               collect(distinct p.name + ' ' + p.surname) AS people_involved,
               a.name AS area_name
        """
        
        # Extract key terms from query
        search_terms = input.lower().split()
        search_terms = [term for term in search_terms if len(term) > 3]
        search_query = " ".join(search_terms) if search_terms else input.lower()
        
        logger.info(f"Search query for locations: '{search_query}'")
        result = graph.query(cypher, {"search": search_query})
        
        if not result or len(result) == 0:
            logger.info("No matching locations found")
            return {"output": None}  # Return None to try other approaches
        
        # Format the results in a readable way
        context = "\n\n".join([
            f"Location: {item['address']}\n"
            f"Area: {item['area_name'] if item['area_name'] else 'Unknown'}\n"
            f"Crime Types: {', '.join(item['crime_types']) if item['crime_types'] else 'None'}\n"
            f"Dates: {', '.join(item['dates']) if item['dates'] else 'Unknown'}\n"
            f"Descriptions: {', '.join(item['descriptions']) if item['descriptions'] else 'No descriptions'}\n"
            f"People Involved: {', '.join(item['people_involved']) if item['people_involved'] else 'Unknown'}"
            for item in result
        ])
        
        logger.info(f"Found {len(result)} locations with matching crimes")
        
        # Call the LLM with the retrieved context
        prompt = f"""
        Based on these crime location details from our database, answer the question: {input}
        
        Crime Information from the database:
        {context}
        
        Base your answer only on the information provided above. Make it clear this information comes from the database.
        Do not supplement with your general knowledge. If the database information doesn't fully answer the question,
        just provide what information is available from these results.
        """
        
        response = llm.invoke(prompt)
        return {"output": response.content}
    except Exception as e:
        logger.error(f"Error in get_crime_location: {e}")
        return {"output": None}  # Return None to try other approaches 
from llm import llm
from graph import graph
import logging

logger = logging.getLogger(__name__)

# Simple function to get crime information using Cypher
def cypher_qa(input):
    try:
        logger.info(f"Executing cypher query for: '{input}'")
        # Try a simple query to get relevant crime data
        cypher = """
        MATCH (c:Crime)
        WHERE toLower(c.type) CONTAINS toLower($search)
        WITH c LIMIT 5
        OPTIONAL MATCH (c)-[:OCCURRED_AT]->(l:Location)
        RETURN c.type AS crime_type, 
               c.date AS date,
               c.description AS description,
               l.address AS location
        """
        
        # Extract potential search terms from user input
        search_term = input.lower()
        if "about" in search_term:
            search_term = search_term.split("about")[1].strip()
        
        logger.info(f"Search term for crimes: '{search_term}'")
        result = graph.query(cypher, {"search": search_term})
        
        if result and len(result) > 0:
            logger.info(f"Found {len(result)} crimes matching: '{search_term}'")
            # Format the results
            context = "\n".join([
                f"Crime Type: {item['crime_type']}, " +
                f"Date: {item['date']}, " +
                f"Description: {item.get('description', 'No description')}, " +
                f"Location: {item.get('location', 'Unknown')}"
                for item in result
            ])
            
            prompt = f"""
            These are the crimes found in the database matching the query:
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
            logger.info(f"No crimes found matching: '{search_term}'")
            # Return None to try the next approach instead of using general knowledge
            return {"result": None}
    except Exception as e:
        logger.error(f"Error in cypher_qa: {e}")
        return {"result": None} 
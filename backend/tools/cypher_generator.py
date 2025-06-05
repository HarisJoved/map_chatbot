from llm import llm
from graph import graph
import logging
import re
import json
from .schema import fetch_schema

logger = logging.getLogger(__name__)

# --- BEGIN NEW SCHEMA HARDCODE ---
SCHEMA_DESCRIPTION = '''
Nodes and Properties:
- Defect: defect_id (String), category (String), description (String), detectedAt (DateTime), severity (String), timesDetected (Integer), location_lat (Float), location_lon (Float)
- Sensor: sensor_id (String), category (String), type (String), location_lat (Float), location_lon (Float), accuracy (Float), status (String), controlledProperty (String)
- DetectionEvent: event_id (String), observedAt (DateTime), image_url (String), result (String)
- CRMCase: case_id (String), status (String), createdAt (DateTime), severity (String), description (String)
- RoadSegment: segment_id (String), name (String), refRoad (String), location_lat (Float), location_lon (Float), startKm (Float), endKm (Float), roadType (String)
- Location: location_lat (Float), location_lon (Float)
Relationships:
- REPORTED_BY: DetectionEvent -> Defect
- DETECTED_BY_SENSOR: DetectionEvent -> Sensor
- ASSOCIATED_WITH: CRMCase -> Defect
- HAS_LOCATION: Defect -> Location
Rules:
- CRMCaseCreation: Create CRMCase only if defect is detected by 4 or more detection events (any sensors).
'''
# --- END NEW SCHEMA HARDCODE ---

def get_schema():
    return SCHEMA_DESCRIPTION

def generate_cypher_query(user_input, context=None):
    """Generate Cypher queries based on user input and context."""
    try:
        logger.info(f"Generating Cypher query for: {user_input}")
        
        # Handle specific patterns first
        if "severity high" in user_input.lower() or "high severity" in user_input.lower():
            query = """
            MATCH (d:Defect)
            WHERE d.severity = 'high'
            RETURN d
            LIMIT 10
            """
            return [query]  # Return as list since execute_dynamic_query expects multiple queries
            
        # For other queries, use the LLM
        schema = get_schema()
        context_str = ""
        if context:
            context_items = {k: v for k, v in context.items() if v and k.startswith('last_')}
            if context_items:
                context_str = "The user previously mentioned the following entities in the conversation:\n"
                for key, value in context_items.items():
                    entity_type = key.replace('last_', '')
                    context_str += f"- {entity_type.capitalize()}: {value}\n"
        
        prompt = f"""
        You are an expert Neo4j Cypher query generator for a road defect and sensor management database. 
        Based on the database schema below, generate a Cypher query to answer the user's question.
        
        {schema}
        
        USER QUESTION: {user_input}
        
        STEP 1: ANALYZE THE QUESTION
        First, analyze the user's question to identify:
        1. Key entities (defects, sensors, detection events, CRM cases, road segments, locations) mentioned
        2. Any specific properties or attributes requested
        3. The relationship or action being asked about
        4. Any filters or constraints implied in the question
        
        STEP 2: CONSIDER CONTEXT
        {context_str}
        When the user refers to "this" or "that" with a noun, they're likely referring to these previously mentioned entities.
        
        STEP 3: GENERATE CYPHER QUERY
        Based on your analysis, generate a Cypher query that:
        1. Uses exactly the node labels, relationships and properties from the schema
        2. Includes appropriate filters based on your analysis
        3. Uses case-insensitive comparisons with toLower() for text searches
        4. Returns only the most relevant information
        5. Uses parameterized queries with $parameters
        6. Limits results to at most 10 items
        7. Contains properly structured relationships between nodes
        
        Return ONLY the Cypher query with no explanations or additional text. The query should be ready to execute.
        """
        
        response = llm.invoke(prompt)
        cypher_query = response.content.strip()
        
        # Clean up the query if it's wrapped in code blocks
        if "```" in cypher_query:
            matches = re.findall(r"```(?:cypher)?(.*?)```", cypher_query, re.DOTALL)
            if matches:
                cypher_query = matches[0].strip()
            else:
                cypher_query = cypher_query.replace("```cypher", "").replace("```", "").strip()
        
        return [cypher_query] if cypher_query else []
        
    except Exception as e:
        logger.error(f"Error generating Cypher query: {e}")
        return []

def validate_cypher_query(query):
    """Basic validation of a Cypher query"""
    try:
        # Check for basic syntax errors
        if not query or len(query) < 10:
            return False
        
        # Check for balanced parentheses and brackets
        if query.count('(') != query.count(')'):
            return False
        if query.count('[') != query.count(']'):
            return False
        if query.count('{') != query.count('}'):
            return False
        
        # Check for key Cypher keywords
        if not any(keyword in query.upper() for keyword in ['MATCH', 'RETURN', 'WHERE', 'WITH']):
            return False
        
        # Check for missing node labels - don't allow generic node patterns like (n)
        if re.search(r'\(\s*[a-zA-Z0-9_]+\s*\)', query):  # Matches (n) without :Label
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error validating query: {e}")
        return False

def fix_cypher_query(query, user_input, schema):
    """Attempt to fix common issues in generated Cypher queries"""
    try:
        # Create a prompt to fix the query
        prompt = f"""
        The following Cypher query has potential issues. Please fix it to make it valid for Neo4j:
        
        ```cypher
        {query}
        ```
        
        Database Schema:
        {schema}
        
        User's original question: {user_input}
        
        Common issues to fix:
        1. Incorrect node labels or relationship types (must match schema exactly)
        2. Missing or incorrect property names (must match schema exactly)
        3. Unbalanced parentheses or brackets
        4. Invalid Cypher syntax
        5. Missing RETURN clauses
        6. Incorrect parameter syntax (should be $paramName)
        7. Missing WITH clauses when aggregating before using aggregated results
        
        Return ONLY the fixed Cypher query, without any explanations.
        """
        
        response = llm.invoke(prompt)
        fixed_query = response.content.strip()
        
        # Clean up the query (remove markdown code blocks if present)
        if "```" in fixed_query:
            matches = re.findall(r"```(?:cypher)?(.*?)```", fixed_query, re.DOTALL)
            if matches:
                fixed_query = matches[0].strip()
            else:
                fixed_query = fixed_query.replace("```cypher", "").replace("```", "").strip()
        
        # Validate the fixed query
        if validate_cypher_query(fixed_query):
            logger.info("Fixed query passed validation")
            return fixed_query
        else:
            logger.warning("Fixed query also failed validation")
            return None
    except Exception as e:
        logger.error(f"Error fixing Cypher query: {e}")
        return None

def generate_fallback_query(user_input, context=None):
    """Generate a fallback query when query generation fails"""
    input_lower = user_input.lower()
    
    # Simple defect search
    if "defect" in input_lower or "issue" in input_lower or "problem" in input_lower or "fault" in input_lower:
        return """
        MATCH (d:Defect)
        WHERE toLower(d.description) CONTAINS toLower($search) OR toLower(d.category) CONTAINS toLower($search)
        OPTIONAL MATCH (e:DetectionEvent)-[:REPORTED_BY]->(d)
        RETURN d.defect_id AS defect_id, d.category AS category, d.description AS description, d.severity AS severity, d.timesDetected AS timesDetected, collect(DISTINCT e.event_id) AS detection_events
        LIMIT 5
        """
    # Simple sensor search
    elif "sensor" in input_lower:
        return """
        MATCH (s:Sensor)
        WHERE toLower(s.sensor_id) CONTAINS toLower($search) OR toLower(s.category) CONTAINS toLower($search) OR toLower(s.type) CONTAINS toLower($search)
        RETURN s.sensor_id AS sensor_id, s.category AS category, s.type AS type, s.status AS status, s.accuracy AS accuracy, s.controlledProperty AS controlledProperty
        LIMIT 5
        """
    # Simple detection event search
    elif "event" in input_lower or "detection" in input_lower:
        return """
        MATCH (e:DetectionEvent)
        WHERE toLower(e.event_id) CONTAINS toLower($search) OR toLower(e.result) CONTAINS toLower($search)
        RETURN e.event_id AS event_id, e.observedAt AS observedAt, e.result AS result, e.image_url AS image_url
        LIMIT 5
        """
    # Simple CRM case search
    elif "crmcase" in input_lower or "case" in input_lower:
        return """
        MATCH (c:CRMCase)
        WHERE toLower(c.case_id) CONTAINS toLower($search) OR toLower(c.status) CONTAINS toLower($search)
        RETURN c.case_id AS case_id, c.status AS status, c.createdAt AS createdAt, c.severity AS severity, c.description AS description
        LIMIT 5
        """
    # Simple road segment search
    elif "roadsegment" in input_lower or "road segment" in input_lower or "road" in input_lower:
        return """
        MATCH (r:RoadSegment)
        WHERE toLower(r.name) CONTAINS toLower($search) OR toLower(r.refRoad) CONTAINS toLower($search)
        RETURN r.segment_id AS segment_id, r.name AS name, r.refRoad AS refRoad, r.startKm AS startKm, r.endKm AS endKm, r.roadType AS roadType
        LIMIT 5
        """
    # Simple location search
    elif "location" in input_lower:
        return """
        MATCH (l:Location)
        RETURN l.location_lat AS latitude, l.location_lon AS longitude
        LIMIT 5
        """
    # Default defect search
    else:
        return """
        MATCH (d:Defect)
        WHERE toLower(d.description) CONTAINS toLower($search)
        RETURN d.defect_id AS defect_id, d.category AS category, d.description AS description
        LIMIT 5
        """

def extract_parameters(query, user_input, context=None):
    """Extract parameters from the query and user input using LLM"""
    try:
        # Extract all parameter names from the query
        param_matches = re.findall(r'\$(\w+)', query)
        
        if not param_matches:
            logger.info("No parameters found in the query")
            return {"search": user_input.lower()}
        
        # Default search parameter
        params = {"search": user_input.lower()}
        
        # Format context for LLM
        context_str = ""
        if context:
            context_items = {k: v for k, v in context.items() if v and k.startswith('last_')}
            if context_items:
                context_str = "The user previously mentioned these entities:\n"
                for key, value in context_items.items():
                    entity_type = key.replace('last_', '')
                    context_str += f"- {entity_type}: {value}\n"
        
        # Create a prompt for the LLM to extract parameters
        prompt = f"""
        I need to extract parameter values for a Neo4j Cypher query.

        USER QUESTION: {user_input}
        
        CYPHER QUERY WITH PARAMETERS:
        ```
        {query}
        ```
        
        The query contains these parameters: {', '.join(['$' + p for p in param_matches])}
        
        CONTEXT:
        {context_str}
        
        Extract the appropriate values for each parameter based on the user's question and context.
        If the parameter seems to refer to a previously mentioned entity in the context, use that value.
        If a parameter value cannot be determined, use a reasonable default from the user's question.
        
        Return ONLY a valid JSON object with parameter names (without $) as keys and their values as strings.
        Example format: {{"name": "John Smith", "age": "30"}}
        """
        
        response = llm.invoke(prompt)
        llm_params = response.content.strip()
        
        # Extract JSON from the response
        if "```json" in llm_params:
            llm_params = re.search(r'```json(.+?)```', llm_params, re.DOTALL).group(1).strip()
        elif "```" in llm_params:
            llm_params = re.search(r'```(.+?)```', llm_params, re.DOTALL).group(1).strip()
        
        try:
            # Parse JSON response
            extracted_params = json.loads(llm_params)
            # Update params with extracted values
            params.update(extracted_params)
            
            # Log the extracted parameters
            logger.info("════════════════════ QUERY PARAMETERS ════════════════════")
            for key, value in params.items():
                logger.info(f"${key} = {value}")
            logger.info("═════════════════════════════════════════════════════════")
            
            return params
        except json.JSONDecodeError:
            logger.error(f"Failed to parse parameter JSON: {llm_params}")
            # Fall back to basic extraction
            return fallback_parameter_extraction(query, user_input, context, param_matches)
            
    except Exception as e:
        logger.error(f"Error extracting parameters: {e}")
        # Fall back to basic extraction
        return fallback_parameter_extraction(query, user_input, context, param_matches if 'param_matches' in locals() else [])

def fallback_parameter_extraction(query, user_input, context, param_matches):
    """Basic parameter extraction as a fallback"""
    params = {"search": user_input.lower()}
    
    # Include context information in parameters if available
    if context:
        for key, value in context.items():
            if key.startswith('last_') and value:
                # Extract the entity type (remove 'last_')
                entity_type = key[5:]
                # Add to parameters
                params[entity_type] = value
    
    # Add any missing parameters from the query
    for param in param_matches:
        if param not in params:
            params[param] = user_input.lower()
    
    logger.info("════════════════════ FALLBACK PARAMETERS ════════════════════")
    for key, value in params.items():
        logger.info(f"${key} = {value}")
    logger.info("═════════════════════════════════════════════════════════")
    
    return params

def flatten_result(item):
    """Flatten Neo4j result if it's wrapped in a single key (e.g., 'd', 's', etc.)"""
    if isinstance(item, dict) and len(item) == 1 and isinstance(list(item.values())[0], dict):
        return list(item.values())[0]
    return item

def execute_dynamic_query(user_input, context=None):
    """Generate and execute a dynamic Cypher query based on user input and context."""
    try:
        logger.info("═══════════════ DYNAMIC QUERY EXECUTION ═══════════════")
        logger.info(f"User input: '{user_input}'")

        # Generate and try multiple queries
        queries = generate_cypher_query(user_input, context)
        last_query = None
        
        for query in queries:
            try:
                logger.info(f"Trying query: {query}")
                # Extract and validate parameters
                params = extract_parameters(query, user_input, context)
                logger.info(f"Extracted parameters: {params}")
                
                # Execute query
                result = graph.query(query, params)
                result_count = len(result) if result else 0
                logger.info(f"Query returned {result_count} results")
                logger.info(f"Raw results: {result}")
                
                if result and len(result) > 0:
                    logger.info("Results found, processing...")
                    # --- FLATTEN RESULTS ---
                    flat_results = [flatten_result(item) for item in result]
                    logger.info(f"Flattened results: {flat_results}")
                    
                    # --- FORMAT RESULTS FOR LLM ---
                    formatted_context = format_query_results(flat_results, user_input)
                    logger.info(f"Formatted context (HTML): {formatted_context}")
                    
                    # --- COLLECT LOCATIONS FOR MAP MARKERS ---
                    locations = []
                    for item in flat_results:
                        loc_id = item.get('location_id')
                        logger.info(f"Processing location_id: {loc_id}")
                        if loc_id:
                            loc_query = "MATCH (l:Location {location_id: $loc_id}) RETURN l.location_lat AS latitude, l.location_lon AS longitude, l.location_id AS location_id"
                            loc_result = graph.query(loc_query, {"loc_id": loc_id})
                            logger.info(f"Location query result: {loc_result}")
                            for loc in loc_result:
                                if loc["latitude"] is not None and loc["longitude"] is not None:
                                    locations.append({
                                        "latitude": loc["latitude"],
                                        "longitude": loc["longitude"],
                                        "location_id": loc["location_id"],
                                        "address": "N/A",  # Adding required address field
                                        "postcode": "N/A"  # Adding required postcode field
                                    })
                    logger.info(f"Collected locations: {locations}")
                    
                    # --- RETURN FORMATTED RESPONSE AND LOCATIONS ---
                    logger.info("Returning formatted response with locations")
                    return {
                        "response": formatted_context,
                        "location": None,
                        "locations": locations
                    }
                
                last_query = query
            except Exception as e:
                logger.error(f"Error executing query: {e}")
                continue
        
        # If we get here, no successful results were found
        logger.info("No results found through any method")
        return {
            "response": "No defects found matching your query.",
            "location": None,
            "locations": []
        }
    except Exception as e:
        logger.error(f"Error in execute_dynamic_query: {e}")
        return {
            "response": "An error occurred while processing your query.",
            "location": None,
            "locations": []
        }

def format_query_results(results, user_input):
    """Format query results in a friendly, conversational manner"""
    try:
        if not results or len(results) == 0:
            return "I looked in the database but couldn't find any matching results. Could you try rephrasing your question or providing more details?"
        
        # Start with a friendly intro based on result count
        formatted_text = f"I found {len(results)} {'result' if len(results) == 1 else 'results'} that might help you:<br/><br/>"
        
        for i, item in enumerate(results, 1):
            # Add a divider between results if there are multiple
            if i > 1:
                formatted_text += "<br/>"
            
            # Group the data fields logically
            core_fields = ['defect_id', 'category', 'type', 'description', 'severity']
            location_fields = ['location_lat', 'location_lon', 'address', 'postcode']
            time_fields = ['detectedAt', 'createdAt', 'observedAt']
            status_fields = ['status', 'timesDetected', 'accuracy']
            
            # Start with core information
            core_info = [f"{key}: {item[key]}" for key in core_fields if key in item and item[key] is not None]
            if core_info:
                formatted_text += f"<b>{i}.</b> Here's what I found: {', '.join(core_info)}<br/>"
            
            # Add location information if available
            loc_info = [f"{key.replace('location_', '')}: {item[key]}" for key in location_fields if key in item and item[key] is not None]
            if loc_info:
                formatted_text += f"📍 Location details: {', '.join(loc_info)}<br/>"
            
            # Add timing information if available
            time_info = [f"{key}: {item[key]}" for key in time_fields if key in item and item[key] is not None]
            if time_info:
                formatted_text += f"⏰ Timing information: {', '.join(time_info)}<br/>"
            
            # Add status and other details if available
            status_info = [f"{key}: {item[key]}" for key in status_fields if key in item and item[key] is not None]
            if status_info:
                formatted_text += f"ℹ️ Additional details: {', '.join(status_info)}<br/>"
            
            # Handle any remaining fields that weren't covered above
            other_fields = [key for key in item.keys() if key not in core_fields + location_fields + time_fields + status_fields]
            other_info = []
            for key in other_fields:
                value = item[key]
                if value is not None:
                    if isinstance(value, list):
                        value = ', '.join(str(v) for v in value) if value else 'none'
                    other_info.append(f"{key}: {value}")
            if other_info:
                formatted_text += f"📌 Other information: {', '.join(other_info)}<br/>"
        
        # Add a helpful closing note
        formatted_text += "<br/>Is there anything specific about these results you'd like me to explain further?"
        
        return formatted_text
    except Exception as e:
        logger.error(f"Error formatting query results: {e}")
        return "I found some results but had trouble formatting them nicely. Would you like me to try presenting them in a simpler way?"

def repair_query_from_error(query, error_message, error_type):
    """Attempt to repair a query based on the error message"""
    try:
        # Create a prompt to fix the query using the error message
        prompt = f"""
        The following Cypher query failed with this error:
        
        Query:
        ```
        {query}
        ```
        
        Error: {error_message}
        Error type: {error_type}
        
        Please fix the query to make it valid for Neo4j. Common issues with this error type are:
        
        {"- Incorrect property names or missing properties" if error_type == "property" else ""}
        {"- Syntax errors like missing brackets or commas" if error_type == "syntax" else ""}
        {"- Incorrect node labels or relationship types" if error_type == "semantic" else ""}
        {"- Constraint violations or type mismatches" if error_type == "constraint" else ""}
        {"- Labels or relationships not found in the database" if error_type == "notfound" else ""}
        
        Return ONLY the fixed Cypher query with no explanations.
        """
        
        response = llm.invoke(prompt)
        fixed_query = response.content.strip()
        
        # Clean up the query
        if "```" in fixed_query:
            matches = re.findall(r"```(?:cypher)?(.*?)```", fixed_query, re.DOTALL)
            if matches:
                fixed_query = matches[0].strip()
            else:
                fixed_query = fixed_query.replace("```cypher", "").replace("```", "").strip()
        
        return fixed_query
    except Exception as e:
        logger.error(f"Error repairing query from error: {e}")
        return None

def try_entity_specific_queries(user_input, params):
    """Try entity-specific queries as a last resort"""
    try:
        search_term = params.get("search", "")
        if not search_term:
            search_term = user_input.lower()
        
        # Try defect search
        defect_query = """
        MATCH (d:Defect)
        WHERE toLower(d.description) CONTAINS toLower($search) OR toLower(d.category) CONTAINS toLower($search)
        OPTIONAL MATCH (e:DetectionEvent)-[:REPORTED_BY]->(d)
        RETURN d.defect_id AS defect_id, d.category AS category, d.description AS description, d.severity AS severity, d.timesDetected AS timesDetected, collect(DISTINCT e.event_id) AS detection_events
        LIMIT 5
        """
        
        try:
            defect_result = graph.query(defect_query, {"search": search_term})
            if defect_result and len(defect_result) > 0:
                logger.info(f"Defect entity query returned {len(defect_result)} results")
                formatted_result = format_query_results(defect_result, user_input)
                prompt = f"Based on these defect records from the database, answer: '{user_input}'\n\n{formatted_result}\n\nMake it clear this information comes from the database."
                response = llm.invoke(prompt)
                return response.content
        except Exception as e:
            logger.error(f"Error in defect entity query: {e}")
        
        # Try sensor search
        sensor_query = """
        MATCH (s:Sensor)
        WHERE toLower(s.sensor_id) CONTAINS toLower($search) OR toLower(s.category) CONTAINS toLower($search) OR toLower(s.type) CONTAINS toLower($search)
        RETURN s.sensor_id AS sensor_id, s.category AS category, s.type AS type, s.status AS status, s.accuracy AS accuracy, s.controlledProperty AS controlledProperty
        LIMIT 5
        """
        
        try:
            sensor_result = graph.query(sensor_query, {"search": search_term})
            if sensor_result and len(sensor_result) > 0:
                logger.info(f"Sensor entity query returned {len(sensor_result)} results")
                formatted_result = format_query_results(sensor_result, user_input)
                prompt = f"Based on these sensor records from the database, answer: '{user_input}'\n\n{formatted_result}\n\nMake it clear this information comes from the database."
                response = llm.invoke(prompt)
                return response.content
        except Exception as e:
            logger.error(f"Error in sensor entity query: {e}")
        
        # Try detection event search
        event_query = """
        MATCH (e:DetectionEvent)
        WHERE toLower(e.event_id) CONTAINS toLower($search) OR toLower(e.result) CONTAINS toLower($search)
        RETURN e.event_id AS event_id, e.observedAt AS observedAt, e.result AS result, e.image_url AS image_url
        LIMIT 5
        """
        
        try:
            event_result = graph.query(event_query, {"search": search_term})
            if event_result and len(event_result) > 0:
                logger.info(f"Detection event entity query returned {len(event_result)} results")
                formatted_result = format_query_results(event_result, user_input)
                prompt = f"Based on these detection event records from the database, answer: '{user_input}'\n\n{formatted_result}\n\nMake it clear this information comes from the database."
                response = llm.invoke(prompt)
                return response.content
        except Exception as e:
            logger.error(f"Error in detection event entity query: {e}")
        
        # Try CRM case search
        case_query = """
        MATCH (c:CRMCase)
        WHERE toLower(c.case_id) CONTAINS toLower($search) OR toLower(c.status) CONTAINS toLower($search)
        RETURN c.case_id AS case_id, c.status AS status, c.createdAt AS createdAt, c.severity AS severity, c.description AS description
        LIMIT 5
        """
        
        try:
            case_result = graph.query(case_query, {"search": search_term})
            if case_result and len(case_result) > 0:
                logger.info(f"CRM case entity query returned {len(case_result)} results")
                formatted_result = format_query_results(case_result, user_input)
                prompt = f"Based on these CRM case records from the database, answer: '{user_input}'\n\n{formatted_result}\n\nMake it clear this information comes from the database."
                response = llm.invoke(prompt)
                return response.content
        except Exception as e:
            logger.error(f"Error in CRM case entity query: {e}")
        
        # Try road segment search
        segment_query = """
        MATCH (r:RoadSegment)
        WHERE toLower(r.name) CONTAINS toLower($search) OR toLower(r.refRoad) CONTAINS toLower($search)
        RETURN r.segment_id AS segment_id, r.name AS name, r.refRoad AS refRoad, r.startKm AS startKm, r.endKm AS endKm, r.roadType AS roadType
        LIMIT 5
        """
        
        try:
            segment_result = graph.query(segment_query, {"search": search_term})
            if segment_result and len(segment_result) > 0:
                logger.info(f"Road segment entity query returned {len(segment_result)} results")
                formatted_result = format_query_results(segment_result, user_input)
                prompt = f"Based on these road segment records from the database, answer: '{user_input}'\n\n{formatted_result}\n\nMake it clear this information comes from the database."
                response = llm.invoke(prompt)
                return response.content
        except Exception as e:
            logger.error(f"Error in road segment entity query: {e}")
        
        # Try location search
        location_query = """
        MATCH (l:Location)
        WHERE toLower(l.location_lat) CONTAINS toLower($search) OR toLower(l.location_lon) CONTAINS toLower($search)
        RETURN l.location_lat AS latitude, l.location_lon AS longitude
        LIMIT 5
        """
        
        try:
            location_result = graph.query(location_query, {"search": search_term})
            if location_result and len(location_result) > 0:
                logger.info(f"Location entity query returned {len(location_result)} results")
                formatted_result = format_query_results(location_result, user_input)
                prompt = f"Based on these location records from the database, answer: '{user_input}'\n\n{formatted_result}\n\nMake it clear this information comes from the database."
                response = llm.invoke(prompt)
                return response.content
        except Exception as e:
            logger.error(f"Error in location entity query: {e}")
        
        return None
    except Exception as e:
        logger.error(f"Error in try_entity_specific_queries: {e}")
        return None 
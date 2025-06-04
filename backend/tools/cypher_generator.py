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
    """Generate a Cypher query based on user input and database schema"""
    try:
        logger.info(f"Generating Cypher query for: '{user_input}'")
        
        # Get the database schema
        schema = get_schema()
        logger.info(f"Retrieved schema for query generation")
        
        # Format context for LLM
        context_str = ""
        if context:
            context_items = {k: v for k, v in context.items() if v and k.startswith('last_')}
            if context_items:
                context_str = "The user previously mentioned the following entities in the conversation:\n"
                for key, value in context_items.items():
                    entity_type = key.replace('last_', '')
                    context_str += f"- {entity_type.capitalize()}: {value}\n"
        
        # Create a prompt for the LLM to generate a Cypher query
        prompt = f"""
        You are an expert Neo4j Cypher query generator for a road defect and sensor management database. 
        Based on the database schema below, generate the most appropriate Cypher query to answer the user's question.
        
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
        
        # Generate the Cypher query using LLM
        response = llm.invoke(prompt)
        cypher_query = response.content.strip()
        
        # Clean up the query (remove markdown code blocks if present)
        if "```" in cypher_query:
            # Extract the query from code blocks
            matches = re.findall(r"```(?:cypher)?(.*?)```", cypher_query, re.DOTALL)
            if matches:
                cypher_query = matches[0].strip()
            else:
                # Fallback if regex doesn't match
                cypher_query = cypher_query.replace("```cypher", "").replace("```", "").strip()
        
        # Log the generated query with clear formatting for terminal visibility
        logger.info("════════════════════ GENERATED CYPHER QUERY ════════════════════")
        for line in cypher_query.split('\n'):
            logger.info(line)
        logger.info("══════════════════════════════════════════════════════════════")
        
        # Validate the query before returning
        validate_result = validate_cypher_query(cypher_query)
        if validate_result:
            logger.info("Query validation passed")
            return cypher_query
        else:
            logger.warning("Query validation failed, attempting to fix query")
            fixed_query = fix_cypher_query(cypher_query, user_input, schema)
            if fixed_query:
                logger.info("════════════════════ FIXED CYPHER QUERY ════════════════════")
                for line in fixed_query.split('\n'):
                    logger.info(line)
                logger.info("══════════════════════════════════════════════════════════")
                return fixed_query
            else:
                logger.error("Failed to fix query, returning original query")
                return cypher_query
    except Exception as e:
        logger.error(f"Error generating Cypher query: {e}")
        # Return a simple fallback query based on the user input
        return generate_fallback_query(user_input, context)

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

def execute_dynamic_query(user_input, context=None):
    """Generate and execute a dynamic Cypher query based on user input and context, retrying up to 3 different queries if needed."""
    try:
        logger.info(f"═══════════════ DYNAMIC QUERY EXECUTION ═══════════════")
        logger.info(f"User input: '{user_input}'")
        if context:
            context_str = ", ".join([f"{k}: {v}" for k, v in context.items() if v and k.startswith('last_')])
            logger.info(f"Context available - {context_str}")

        previous_queries = set()
        last_query = None
        for attempt in range(3):
            if attempt == 0:
                cypher_query = generate_cypher_query(user_input, context)
            else:
                # Prompt LLM to generate a different query than previous attempts
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
                8. Is different in structure or approach from the following previous attempts (do NOT repeat them):
                {chr(10).join(previous_queries)}
                
                Return ONLY the Cypher query with no explanations or additional text. The query should be ready to execute.
                """
                response = llm.invoke(prompt)
                cypher_query = response.content.strip()
                if "```" in cypher_query:
                    matches = re.findall(r"```(?:cypher)?(.*?)```", cypher_query, re.DOTALL)
                    if matches:
                        cypher_query = matches[0].strip()
                    else:
                        cypher_query = cypher_query.replace("```cypher", "").replace("```", "").strip()
            if not cypher_query:
                logger.error("Query generation failed")
                continue
            if cypher_query in previous_queries:
                logger.warning("LLM repeated a previous query, skipping this attempt.")
                continue
            previous_queries.add(cypher_query)
            last_query = cypher_query
            params = extract_parameters(cypher_query, user_input, context)
            try:
                logger.info(f"Executing generated query (attempt {attempt+1})...")
                result = graph.query(cypher_query, params)
                result_count = len(result) if result else 0
                logger.info(f"Dynamic query returned {result_count} results")
                if result and result_count > 0:
                    logger.info("════════════════════ SAMPLE RESULTS ════════════════════")
                    for i, item in enumerate(result[:3]):
                        logger.info(f"Result {i+1}: {item}")
                    if result_count > 3:
                        logger.info(f"... and {result_count-3} more results")
                    logger.info("══════════════════════════════════════════════════════")
                    formatted_context = format_query_results(result, user_input)
                    prompt = f"""
                    Based on the following database query results, answer the user's question: "{user_input}"
                    
                    {formatted_context}
                    
                    Respond in a friendly, conversational way. Use HTML formatting (such as <b>, <i>, <ul>, <table>, etc.) to clearly present the information. Clearly state that this information comes from the database. If the results don't fully answer the question, say so, but provide what information you can from these results. Your response should be factual, professional, and concise, focusing only on the information provided in the database results.
                    """
                    response = llm.invoke(prompt)
                    logger.info("Successfully formatted dynamic query results")
                    logger.info("═════════════════════════════════════════════════════════")
                    return {"result": response.content}
            except Exception as query_error:
                logger.error(f"Error executing dynamic query: {query_error}")
                error_message = str(query_error)
                error_type = "unknown"
                if "SyntaxError" in error_message:
                    error_type = "syntax"
                elif "SemanticError" in error_message:
                    error_type = "semantic"
                elif "ConstraintValidationFailed" in error_message:
                    error_type = "constraint"
                elif "PropertyNotFound" in error_message or "NoSuchProperty" in error_message:
                    error_type = "property"
                elif "NotFound" in error_message:
                    error_type = "notfound"
                logger.warning(f"Query error type: {error_type}")
                logger.info("Attempting to fix query based on error message")
                fixed_query = repair_query_from_error(cypher_query, error_message, error_type)
                if fixed_query and fixed_query not in previous_queries:
                    previous_queries.add(fixed_query)
                    try:
                        repair_result = graph.query(fixed_query, params)
                        repair_count = len(repair_result) if repair_result else 0
                        logger.info(f"Repaired query returned {repair_count} results")
                        if repair_result and repair_count > 0:
                            formatted_context = format_query_results(repair_result, user_input)
                            prompt = f"""
                            Based on the following database query results, answer the user's question: "{user_input}"
                            
                            {formatted_context}
                            
                            Respond in a friendly, conversational way. Use HTML formatting (such as <b>, <i>, <ul>, <table>, etc.) to clearly present the information. Clearly state that this information comes from the database. If the results don't fully answer the question, say so, but provide what information you can from these results. Your response should be factual, professional, and concise, focusing only on the information provided in the database results.
                            """
                            response = llm.invoke(prompt)
                            logger.info("Successfully formatted repaired query results")
                            return {"result": response.content}
                    except Exception as repair_error:
                        logger.error(f"Error executing repaired query: {repair_error}")
        # If all attempts failed, try entity-specific queries as fallback
        logger.info("All dynamic query attempts failed, trying entity-specific queries as fallback")
        if last_query:
            params = extract_parameters(last_query, user_input, context)
        entity_result = try_entity_specific_queries(user_input, params)
        if entity_result:
            return {"result": entity_result}
        return {"result": None}
    except Exception as e:
        logger.error(f"Error in execute_dynamic_query: {e}")
        return {"result": None}

def format_query_results(results, user_input):
    """Format query results as an HTML table for the LLM"""
    try:
        if not results or len(results) == 0:
            return "<i>No results found in the database.</i>"
        # Get all possible keys from all results
        all_keys = set()
        for item in results:
            all_keys.update(item.keys())
        all_keys = list(all_keys)
        # Create HTML table header
        table = '<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;">'
        table += '<thead><tr>' + ''.join(f'<th>{key}</th>' for key in all_keys) + '</tr></thead><tbody>'
        # Add each result as a row
        for item in results:
            row = '<tr>'
            for key in all_keys:
                value = item.get(key, "")
                if isinstance(value, list):
                    value = ', '.join(str(v) for v in value) if value else 'none'
                elif value is None:
                    value = 'null'
                row += f'<td>{value}</td>'
            row += '</tr>'
            table += row
        table += '</tbody></table>'
        return table
    except Exception as e:
        logger.error(f"Error formatting query results: {e}")
        # Fallback to simple HTML formatting
        simple_text = "<ul>"
        for i, item in enumerate(results):
            simple_text += f"<li>Result {i+1}: {item}</li>"
        simple_text += "</ul>"
        return simple_text

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
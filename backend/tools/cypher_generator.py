from llm import llm
from graph import graph
import logging
import re
import json

logger = logging.getLogger(__name__)

def get_schema():
    """Return the hardcoded POLE schema for Cypher query generation."""
    return '''
## 🕵️‍♂️ POLE (Person, Object, Location, Event) Graph Schema – Neo4j Crime Investigation

### Overview
The POLE schema represents crime investigation data using a graph model. It captures entities like people, objects, locations, and events, along with their complex relationships.

---

### Node Types (Labels)

#### 1. Person
Represents individuals involved in the investigation.

**Attributes:**
- name
- surname
- nhs_no
- Subtypes: Person, Officer

#### 2. Object
Represents physical or digital items.

**Types:**
- Object
- Email
- Phone

**Attributes:**
- type
- description
- serial_number

#### 2.1 Vehicle
Represents mode of transport.

**Types:**
- Car
- Vehicle
- Bike
- Truck

**Attributes:**
- reg
- year
- model
- make

#### 3. Location
Geographical places tied to events or people.

**Attributes:**
- address
- postcode
- latitude
- longitude

**Related Nodes:**
- PostCode 
  attribute: code
- Area 
  attribute: areaCode

#### 4. Event
Incidents or interactions relevant to the investigation.

**Types:**
- Crime
- PhoneCall

**Attributes:**
- type
- date
- last_outcome

---

### Relationship Types

#### Between Persons
- KNOWS: General acquaintance
- FAMILY_REL: Family relationship
- KNOWS_LW: Lives with
- KNOWS_PHONE: Phone call connection
- KNOWS_SN: Social network connection

#### Person to Event
- PARTY_TO: Person involved in an event
- INVESTIGATED_BY: Officer investigating an event

#### Event to Location
- OCCURRED_AT: Event occurred at a location

#### Object Associations
- INVOLVED_IN: Object linked to an event
- OWNER_OF: Person owns the object
- DRIVER_OF: Person drives the vehicle

#### Location Hierarchies
- HAS_POSTCODE: Location includes a postcode
- LOCATION_IN_AREA: Location is in a defined area

---

### Useful Query Example

Find all crimes at a given address:
```cypher
MATCH (l:Location {address: $address})<-[:OCCURRED_AT]-(c:Crime)
RETURN c.date AS crimeDate
```

Replace `$address` with the actual address to retrieve relevant crime events.

---

### Schema Visualization

To visualize schema structure in Neo4j:
```cypher
CALL db.schema.visualization()
```
'''

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
        You are an expert Neo4j Cypher query generator for a crime investigation database. 
        Based on the database schema below, generate the most appropriate Cypher query to answer the user's question.
        
        {schema}
        
        USER QUESTION: {user_input}
        
        STEP 1: ANALYZE THE QUESTION
        First, analyze the user's question to identify:
        1. Key entities (people, locations, crimes, vehicles, etc.) mentioned
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
    
    # Simple person search
    if "person" in input_lower or "name" in input_lower or "who is" in input_lower:
        name_match = re.search(r'(?:about|for|on|who is|find)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', user_input)
        search_term = name_match.group(1) if name_match else ""
        
        return """
        MATCH (p:Person)
        WHERE toLower(p.name + ' ' + p.surname) CONTAINS toLower($search)
        OPTIONAL MATCH (p)-[:INVOLVED_IN]->(c:Crime)
        OPTIONAL MATCH (p)-[:HAS_PHONE]->(ph:Phone)
        RETURN p.name AS name, p.surname AS surname, p.age AS age,
               collect(distinct c.type) AS crimes,
               collect(distinct ph.phoneNo) AS phone_numbers
        LIMIT 5
        """
    
    # Simple location search
    elif "location" in input_lower or "address" in input_lower or "where" in input_lower:
        return """
        MATCH (l:Location)
        WHERE toLower(l.address) CONTAINS toLower($search)
        OPTIONAL MATCH (c:Crime)-[:OCCURRED_AT]->(l)
        RETURN l.address AS address, count(c) AS crime_count, 
               collect(distinct c.type) AS crime_types
        LIMIT 5
        """
    
    # Simple vehicle search
    elif "vehicle" in input_lower or "car" in input_lower or "registration" in input_lower:
        return """
        MATCH (v:Vehicle)
        WHERE toLower(v.make) CONTAINS toLower($search)
           OR toLower(v.model) CONTAINS toLower($search)
           OR toLower(v.reg) CONTAINS toLower($search)
        OPTIONAL MATCH (v)-[:INVOLVED_IN]->(c:Crime)
        RETURN v.make AS make, v.model AS model, v.reg AS registration,
               collect(distinct c.type) AS crimes
        LIMIT 5
        """
    
    # Default crime search
    else:
        return """
        MATCH (c:Crime)
        WHERE toLower(c.type) CONTAINS toLower($search)
           OR toLower(c.description) CONTAINS toLower($search)
        OPTIONAL MATCH (c)-[:OCCURRED_AT]->(l:Location)
        RETURN c.type AS type, c.date AS date, c.description AS description,
               l.address AS location
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
                You are an expert Neo4j Cypher query generator for a crime investigation database. 
                Based on the database schema below, generate a Cypher query to answer the user's question.
                
                {schema}
                
                USER QUESTION: {user_input}
                
                STEP 1: ANALYZE THE QUESTION
                First, analyze the user's question to identify:
                1. Key entities (people, locations, crimes, vehicles, etc.) mentioned
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
                    
                    Respond in a friendly, conversational way. Include specific details from the query results.
                    Clearly state that this information comes from the database.
                    If the results don't fully answer the question, say so, but provide what information you can from these results.
                    
                    Your response should be factual, professional, and concise, focusing only on the information provided in the database results.
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
                            
                            Respond in a friendly, conversational way. Include specific details from the query results.
                            Clearly state that this information comes from the database.
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
    """Format query results in a readable way for the LLM"""
    try:
        if not results or len(results) == 0:
            return "No results found in the database."
        
        # Format the results as a readable table
        formatted_text = "Query Results from Database:\n\n"
        
        # Get all possible keys from all results
        all_keys = set()
        for item in results:
            all_keys.update(item.keys())
        
        # Create a table header
        header = " | ".join(all_keys)
        separator = "-" * len(header)
        formatted_text += f"{header}\n{separator}\n"
        
        # Add each result as a row
        for item in results:
            row_values = []
            for key in all_keys:
                value = item.get(key, "")
                if isinstance(value, list):
                    if value:
                        value = ", ".join(str(v) for v in value)
                    else:
                        value = "none"
                elif value is None:
                    value = "null"
                row_values.append(str(value))
            formatted_text += " | ".join(row_values) + "\n"
        
        return formatted_text
    except Exception as e:
        logger.error(f"Error formatting query results: {e}")
        
        # Fallback to simple formatting
        simple_text = "Query Results from Database:\n\n"
        for i, item in enumerate(results):
            simple_text += f"Result {i+1}: {item}\n"
        
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
        
        # Try person search
        person_query = """
        MATCH (p:Person)
        WHERE toLower(p.name + ' ' + COALESCE(p.surname, '')) CONTAINS toLower($search)
        OPTIONAL MATCH (p)-[:INVOLVED_IN]->(c:Crime)
        RETURN p.name AS name, p.surname AS surname, COUNT(c) AS crime_count
        LIMIT 5
        """
        
        try:
            person_result = graph.query(person_query, {"search": search_term})
            if person_result and len(person_result) > 0:
                logger.info(f"Person entity query returned {len(person_result)} results")
                formatted_result = format_query_results(person_result, user_input)
                prompt = f"Based on these person records from the database, answer: '{user_input}'\n\n{formatted_result}\n\nMake it clear this information comes from the database."
                response = llm.invoke(prompt)
                return response.content
        except Exception as e:
            logger.error(f"Error in person entity query: {e}")
        
        # Try location search
        location_query = """
        MATCH (l:Location)
        WHERE toLower(l.address) CONTAINS toLower($search)
        OPTIONAL MATCH (c:Crime)-[:OCCURRED_AT]->(l)
        RETURN l.address AS address, COUNT(c) AS crime_count
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
        
        # Try crime search
        crime_query = """
        MATCH (c:Crime)
        WHERE toLower(c.type) CONTAINS toLower($search) OR 
              toLower(COALESCE(c.description, '')) CONTAINS toLower($search)
        RETURN c.type AS type, c.date AS date, c.description AS description
        LIMIT 5
        """
        
        try:
            crime_result = graph.query(crime_query, {"search": search_term})
            if crime_result and len(crime_result) > 0:
                logger.info(f"Crime entity query returned {len(crime_result)} results")
                formatted_result = format_query_results(crime_result, user_input)
                prompt = f"Based on these crime records from the database, answer: '{user_input}'\n\n{formatted_result}\n\nMake it clear this information comes from the database."
                response = llm.invoke(prompt)
                return response.content
        except Exception as e:
            logger.error(f"Error in crime entity query: {e}")
        
        return None
    except Exception as e:
        logger.error(f"Error in try_entity_specific_queries: {e}")
        return None 
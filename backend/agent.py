from llm import llm
from graph import graph
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create a crime investigation chat chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser

# Create a set of tools
from langchain.tools import Tool
from tools.vector import get_defect_location
from tools.cypher import cypher_qa
from tools.cypher_generator import execute_dynamic_query
from tools.general_conversation import is_general_conversation, handle_general_chat

# --- BEGIN NEW SCHEMA HARDCODE ---
graph_schema = {
    "nodes": {
        "Defect": {
            "label": "Defect",
            "properties": {
                "defect_id": "String",
                "category": "String",
                "description": "String",
                "detectedAt": "DateTime",
                "severity": "String",
                "timesDetected": "Integer",
                "location_id": "String"
            }
        },
        "Sensor": {
            "label": "Sensor",
            "properties": {
                "sensor_id": "String",
                "category": "String",
                "type": "String",
                "location_lat": "Float",
                "location_lon": "Float",
                "accuracy": "Float",
                "status": "String",
                "controlledProperty": "String"
            }
        },
        "DetectionEvent": {
            "label": "DetectionEvent",
            "properties": {
                "event_id": "String",
                "observedAt": "DateTime",
                "image_url": "String",
                "result": "String"
            }
        },
        "CRMCase": {
            "label": "CRMCase",
            "properties": {
                "case_id": "String",
                "status": "String",
                "createdAt": "DateTime",
                "severity": "String",
                "description": "String"
            }
        },
        "Location": {
            "label": "Location",
            "properties": {
                "location_id": "String",
                "location_lat": "Float",
                "location_lon": "Float"
            }
        }
    },
    "relationships": [
        {
            "type": "REPORTED_BY",
            "from": "DetectionEvent",
            "to": "Defect"
        },
        {
            "type": "DETECTED_BY_SENSOR",
            "from": "DetectionEvent",
            "to": "Sensor"
        },
        {
            "type": "ASSOCIATED_WITH",
            "from": "CRMCase",
            "to": "Defect"
        },
        {
            "type": "HAS_LOCATION",
            "from": "Defect",
            "to": "Location"
        }
    ],
    "rules": {
        "CRMCaseCreation": "Create CRMCase only if defect is detected by 4 or more detection events (any sensors)."
    }
}

# --- END NEW SCHEMA HARDCODE ---

# Create the agent
try:
    def get_system_prompt():
        # Format the schema for the LLM
        schema_str = "Nodes and Properties:\n"
        for node, node_info in graph_schema["nodes"].items():
            schema_str += f"- {node}: {', '.join([f'{k} ({v})' for k, v in node_info['properties'].items()])}\n"
        schema_str += "Relationships:\n"
        for rel in graph_schema["relationships"]:
            schema_str += f"- {rel['type']}: {rel['from']} -> {rel['to']}\n"
        schema_str += "Rules:\n"
        for rule, desc in graph_schema["rules"].items():
            schema_str += f"- {rule}: {desc}\n"
        return f"""You are a helpful assistant for a Neo4j graph database about road defects, sensors, detection events, CRM cases, and road segments.\n\nUse only the information in the following schema to answer questions. If you don't know the answer from the database, say so.\n\nDatabase Schema:\n{schema_str}\n"""

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", get_system_prompt()),
        ("human", "{input}"),
    ])

    general_chat = chat_prompt | llm | StrOutputParser()

    def generate_response(user_input, recent_messages=None, context=None):
        try:
            logger.info(f"Received user input: {user_input}")
            # 1. General conversation check
            if is_general_conversation(user_input):
                general_result = handle_general_chat(user_input)
                if general_result and "output" in general_result and general_result["output"]:
                    return {"response": general_result["output"]}
                
            # 2. Try LLM/dynamic Cypher generator for all database queries
            dynamic_result = execute_dynamic_query(user_input, context)
            if dynamic_result:
                # Return the result directly from execute_dynamic_query
                return dynamic_result
            
            # 3. If we get here, no results were found
            return {
                "response": "No results found matching your query.",
                "location": None,
                "locations": []
            }
        except Exception as e:
            logger.error(f"Error in generate_response: {e}")
            return {
                "response": f"An error occurred while processing your query: {str(e)}",
                "location": None,
                "locations": []
            }
except Exception as e:
    logger.error(f"Error setting up crime investigation agent: {e}")
    
    # Ultra-simple fallback
    def generate_response(user_input, recent_messages=None, context=None):
        try:
            logger.info(f"TOOL USED: ultra-simple fallback - Agent setup failed, using direct database request for: '{user_input}'")
            
            # Try to extract key terms
            search_term = user_input.lower()
            
            # Try a direct, simple query for Crime
            try:
                simple_crime_query = """
                MATCH (c:Crime)
                WHERE toLower(c.type) CONTAINS toLower($search) OR toLower(c.description) CONTAINS toLower($search)
                RETURN c.type, c.date, c.description
                LIMIT 3
                """
                crime_result = graph.query(simple_crime_query, {"search": search_term})
                
                if crime_result and len(crime_result) > 0:
                    crime_data = "\n".join([
                        f"Type: {item['c.type']}, Date: {item['c.date']}, Description: {item['c.description']}"
                        for item in crime_result
                    ])
                    
                    return f"Found the following information in the crime database:\n\n{crime_data}"
            except:
                pass
            
            # No information was found, provide a structured response
            no_data_prompt = f"""
            I need to generate a response for a crime investigation chatbot. The user asked:
            
            "{user_input}"
            
            But the system couldn't find any relevant information in the criminal records database.
            
            Create a brief, professional response explaining that no matching records were found.
            Suggest the user try being more specific or provide some examples of what they could ask about.
            """
            
            response = llm.invoke(no_data_prompt)
            return response.content
        except:
            logger.error(f"COMPLETE FAILURE: Could not generate any response even with ultra-simple fallback for: '{user_input}'")
            return "I apologize, but I'm unable to find any relevant information in the criminal records database. Please try a different query." 
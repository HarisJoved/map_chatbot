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
            user_lower = user_input.lower()
            # 1. General conversation check
            if is_general_conversation(user_input):
                general_result = handle_general_chat(user_input)
                if general_result and "output" in general_result and general_result["output"]:
                    return general_result["output"]
            # 2. Try LLM/dynamic Cypher generator for all database questions
            dynamic_result = execute_dynamic_query(user_input, context)
            if dynamic_result and "result" in dynamic_result and dynamic_result["result"]:
                return dynamic_result["result"]
            # 3. Fallback: use hardcoded Cypher queries for simple entity types
            # Defect queries
            if any(word in user_lower for word in ["defect", "issue", "problem", "fault"]):
                cypher = """
                MATCH (d:Defect)
                WHERE toLower(d.description) CONTAINS toLower($search)
                   OR toLower(d.category) CONTAINS toLower($search)
                OPTIONAL MATCH (e:DetectionEvent)-[:REPORTED_BY]->(d)
                OPTIONAL MATCH (c:CRMCase)-[:ASSOCIATED_WITH]->(d)
                RETURN d.defect_id AS defect_id, d.category AS category, d.description AS description, d.severity AS severity, d.timesDetected AS timesDetected, collect(DISTINCT e.event_id) AS detection_events, collect(DISTINCT c.case_id) AS crm_cases
                LIMIT 5
                """
                params = {"search": user_input}
                result = graph.query(cypher, params)
                if result:
                    response = "<b>Defect Results:</b><ul>"
                    for r in result:
                        response += f"<li>ID: {r['defect_id']}, Category: {r['category']}, Desc: {r['description']}, Severity: {r['severity']}, Times Detected: {r['timesDetected']}, Detection Events: {', '.join(r['detection_events'])}, CRM Cases: {', '.join(r['crm_cases'])}</li>"
                    response += "</ul>"
                    return response
                else:
                    return "No defects found matching your query."
            # Sensor queries
            if "sensor" in user_lower:
                cypher = """
                MATCH (s:Sensor)
                WHERE toLower(s.sensor_id) CONTAINS toLower($search)
                   OR toLower(s.category) CONTAINS toLower($search)
                   OR toLower(s.type) CONTAINS toLower($search)
                RETURN s.sensor_id AS sensor_id, s.category AS category, s.type AS type, s.status AS status, s.accuracy AS accuracy, s.controlledProperty AS controlledProperty
                LIMIT 5
                """
                params = {"search": user_input}
                result = graph.query(cypher, params)
                if result:
                    response = "<b>Sensor Results:</b><ul>"
                    for r in result:
                        response += f"<li>ID: {r['sensor_id']}, Category: {r['category']}, Type: {r['type']}, Status: {r['status']}, Accuracy: {r['accuracy']}, Controlled Property: {r['controlledProperty']}</li>"
                    response += "</ul>"
                    return response
                else:
                    return "No sensors found matching your query."
            # DetectionEvent queries
            if "event" in user_lower or "detection" in user_lower:
                cypher = """
                MATCH (e:DetectionEvent)
                WHERE toLower(e.event_id) CONTAINS toLower($search)
                   OR toLower(e.result) CONTAINS toLower($search)
                RETURN e.event_id AS event_id, e.observedAt AS observedAt, e.result AS result, e.image_url AS image_url
                LIMIT 5
                """
                params = {"search": user_input}
                result = graph.query(cypher, params)
                if result:
                    response = "<b>Detection Events:</b><ul>"
                    for r in result:
                        response += f"<li>ID: {r['event_id']}, Observed At: {r['observedAt']}, Result: {r['result']}, Image: {r['image_url']}</li>"
                    response += "</ul>"
                    return response
                else:
                    return "No detection events found matching your query."
            # CRMCase queries
            if "crmcase" in user_lower or "case" in user_lower:
                cypher = """
                MATCH (c:CRMCase)
                WHERE toLower(c.case_id) CONTAINS toLower($search)
                   OR toLower(c.status) CONTAINS toLower($search)
                RETURN c.case_id AS case_id, c.status AS status, c.createdAt AS createdAt, c.severity AS severity, c.description AS description
                LIMIT 5
                """
                params = {"search": user_input}
                result = graph.query(cypher, params)
                if result:
                    response = "<b>CRM Cases:</b><ul>"
                    for r in result:
                        response += f"<li>ID: {r['case_id']}, Status: {r['status']}, Created At: {r['createdAt']}, Severity: {r['severity']}, Desc: {r['description']}</li>"
                    response += "</ul>"
                    return response
                else:
                    return "No CRM cases found matching your query."
            # RoadSegment queries
            if "roadsegment" in user_lower or "road segment" in user_lower or "road" in user_lower:
                cypher = """
                MATCH (r:RoadSegment)
                WHERE toLower(r.name) CONTAINS toLower($search)
                   OR toLower(r.refRoad) CONTAINS toLower($search)
                RETURN r.segment_id AS segment_id, r.name AS name, r.refRoad AS refRoad, r.startKm AS startKm, r.endKm AS endKm, r.roadType AS roadType
                LIMIT 5
                """
                params = {"search": user_input}
                result = graph.query(cypher, params)
                if result:
                    response = "<b>Road Segments:</b><ul>"
                    for r in result:
                        response += f"<li>ID: {r['segment_id']}, Name: {r['name']}, Ref Road: {r['refRoad']}, Start Km: {r['startKm']}, End Km: {r['endKm']}, Type: {r['roadType']}</li>"
                    response += "</ul>"
                    return response
                else:
                    return "No road segments found matching your query."
            # Location queries
            if "location" in user_lower:
                cypher = """
                MATCH (l:Location)
                RETURN l.location_lat AS latitude, l.location_lon AS longitude
                LIMIT 5
                """
                result = graph.query(cypher)
                if result:
                    response = "<b>Locations:</b><ul>"
                    for r in result:
                        response += f"<li>Lat: {r['latitude']}, Lon: {r['longitude']}</li>"
                    response += "</ul>"
                    return response
                else:
                    return "No locations found."
            # General chat fallback
            response = general_chat.invoke({"input": user_input})
            return response
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I'm having trouble processing your request. Please try again later."
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
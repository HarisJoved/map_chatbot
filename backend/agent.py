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
from tools.vector import get_crime_location
from tools.cypher import cypher_qa
from tools.cypher_generator import execute_dynamic_query
from tools.general_conversation import is_general_conversation, handle_general_chat

# Create the agent
try:
    # Create a more versatile chat prompt that handles both crime questions and general conversation
    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a friendly and knowledgeable assistant specializing in crime investigation data using the POLE model (Person, Object, Location, Event).
When asked about crimes, provide detailed information about incidents, locations, people involved, and related evidence or objects.
When engaged in general conversation, respond in a warm, professional manner as if speaking to an investigator.
Always maintain a helpful, factual tone regardless of the topic."""),
        ("human", "{input}"),
    ])

    general_chat = chat_prompt | llm | StrOutputParser()

    def generate_response(user_input, recent_messages=None, context=None):
        """Generate a response based on user input and conversation context"""
        try:
            # Check if the input is general conversation
            if is_general_conversation(user_input):
                logger.info(f"TOOL USED: general_conversation.handle_general_chat - User input: '{user_input}'")
                general_result = handle_general_chat(user_input)
                if general_result and "output" in general_result and general_result["output"]:
                    logger.info("RESPONSE FROM: general_conversation.handle_general_chat - Using general conversation response")
                    return general_result["output"]
            
            # First try to get information about specific crime locations
            logger.info(f"TOOL USED: vector.get_crime_location - Attempting to find location info for: '{user_input}'")
            location_info = get_crime_location(user_input)
            if location_info and "output" in location_info and location_info["output"]:
                logger.info("RESPONSE FROM: vector.get_crime_location - Using crime location information")
                return location_info["output"]
            
            # If no specific location info, try standard cypher query
            logger.info(f"TOOL USED: cypher.cypher_qa - Attempting standard cypher query for: '{user_input}'")
            cypher_result = cypher_qa(user_input)
            
            # If standard cypher returned valid database results, use them
            if cypher_result and "result" in cypher_result and cypher_result["result"]:
                logger.info("RESPONSE FROM: cypher.cypher_qa - Using crime information from database")
                return cypher_result["result"]
            else:
                logger.info("Standard cypher query returned no results, trying dynamic query")
            
            # Try dynamic query generation for all crime-related queries
            logger.info(f"TOOL USED: cypher_generator.execute_dynamic_query - Attempting dynamic cypher query for: '{user_input}'")
            dynamic_result = execute_dynamic_query(user_input, context)
            if dynamic_result and "result" in dynamic_result and dynamic_result["result"]:
                logger.info("RESPONSE FROM: cypher_generator.execute_dynamic_query - Using dynamically generated query results")
                return dynamic_result["result"]
            
            # If all database approaches fail, try specific entity searches
            logger.info("All standard database approaches failed, trying direct entity searches")
            
            # Extract potential person names from query
            import re
            name_match = re.search(r'(?:about|for|on|who is|find)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)', user_input)
            if name_match or "name" in user_input.lower():
                person_name = name_match.group(1) if name_match else user_input.split()[-2:]
                logger.info(f"Attempting direct Person search for: {person_name}")
                
                # Direct query for Person entity
                person_query = """
                MATCH (p:Person)
                WHERE toLower(p.name + ' ' + p.surname) CONTAINS toLower($name)
                OPTIONAL MATCH (p)-[:INVOLVED_IN]->(c:Crime)
                OPTIONAL MATCH (p)-[:HAS_PHONE]->(ph:Phone)
                OPTIONAL MATCH (p)-[:CURRENT_ADDRESS]->(l:Location)
                RETURN p.name AS name, p.surname AS surname, p.age AS age,
                       collect(distinct c.type) AS crimes,
                       collect(distinct l.address) AS addresses,
                       collect(distinct ph.phoneNo) AS phone_numbers
                LIMIT 5
                """
                
                try:
                    search_name = name_match.group(1) if name_match else " ".join(user_input.split()[-2:])
                    person_result = graph.query(person_query, {"name": search_name})
                    
                    if person_result and len(person_result) > 0:
                        logger.info(f"Found {len(person_result)} person records")
                        
                        # Format person results
                        person_info = "\n\n".join([
                            f"Name: {item['name']} {item['surname']}\n" +
                            f"Age: {item['age'] if item['age'] else 'Unknown'}\n" +
                            f"Involved in crimes: {', '.join(item['crimes']) if item['crimes'] else 'None on record'}\n" +
                            f"Addresses: {', '.join(item['addresses']) if item['addresses'] else 'Unknown'}\n" +
                            f"Phone: {', '.join(item['phone_numbers']) if item['phone_numbers'] else 'Unknown'}"
                            for item in person_result
                        ])
                        
                        prompt = f"""
                        Based on the crime database information about this person:
                        
                        {person_info}
                        
                        Answer the user's question: "{user_input}"
                        
                        Only use the information provided above from the database. Make it clear this information is from the criminal records database.
                        """
                        
                        response = llm.invoke(prompt)
                        logger.info("RESPONSE FROM: direct person search - Using person information")
                        return response.content
                except Exception as e:
                    logger.error(f"Error in direct person search: {e}")
            
            # Try vehicle search for car-related queries
            vehicle_indicators = ["car", "vehicle", "truck", "van", "motorcycle", "registration", "reg"]
            if any(indicator in user_input.lower() for indicator in vehicle_indicators):
                logger.info(f"Attempting direct Vehicle search for: {user_input}")
                
                # Direct query for Vehicle entity
                vehicle_query = """
                MATCH (v:Vehicle)
                WHERE toLower(v.make) CONTAINS toLower($search) OR 
                      toLower(v.model) CONTAINS toLower($search) OR
                      toLower(v.reg) CONTAINS toLower($search)
                OPTIONAL MATCH (v)-[:INVOLVED_IN]->(c:Crime)
                RETURN v.make AS make, v.model AS model, v.reg AS registration,
                       v.year AS year, v.style AS style,
                       collect(distinct c.type) AS crimes
                LIMIT 5
                """
                
                try:
                    vehicle_result = graph.query(vehicle_query, {"search": user_input.lower()})
                    
                    if vehicle_result and len(vehicle_result) > 0:
                        logger.info(f"Found {len(vehicle_result)} vehicle records")
                        
                        # Format vehicle results
                        vehicle_info = "\n\n".join([
                            f"Vehicle: {item['make']} {item['model']} ({item['year'] if item['year'] else 'Unknown year'})\n" +
                            f"Registration: {item['registration']}\n" +
                            f"Style: {item['style'] if item['style'] else 'Unknown'}\n" +
                            f"Involved in crimes: {', '.join(item['crimes']) if item['crimes'] else 'None on record'}"
                            for item in vehicle_result
                        ])
                        
                        prompt = f"""
                        Based on the crime database information about these vehicles:
                        
                        {vehicle_info}
                        
                        Answer the user's question: "{user_input}"
                        
                        Only use the information provided above from the database. Make it clear this information is from the criminal records database.
                        """
                        
                        response = llm.invoke(prompt)
                        logger.info("RESPONSE FROM: direct vehicle search - Using vehicle information")
                        return response.content
                except Exception as e:
                    logger.error(f"Error in direct vehicle search: {e}")

            # Try location search for address/area queries
            location_indicators = ["location", "address", "street", "road", "avenue", "place", "area", "district", "where"]
            if any(indicator in user_input.lower() for indicator in location_indicators):
                logger.info(f"Attempting direct Location search for: {user_input}")
                
                # Direct query for Location entity
                location_query = """
                MATCH (l:Location)
                WHERE toLower(l.address) CONTAINS toLower($search)
                OPTIONAL MATCH (l)<-[:OCCURRED_AT]-(c:Crime)
                OPTIONAL MATCH (l)-[:LOCATION_IN_AREA]->(a:Area)
                RETURN l.address AS address, l.latitude AS lat, l.longitude AS lng,
                       a.name AS area_name, a.areaCode AS area_code,
                       count(c) AS crime_count,
                       collect(distinct c.type) AS crime_types
                LIMIT 5
                """
                
                try:
                    location_result = graph.query(location_query, {"search": user_input.lower()})
                    
                    if location_result and len(location_result) > 0:
                        logger.info(f"Found {len(location_result)} location records")
                        
                        # Format location results
                        location_info = "\n\n".join([
                            f"Address: {item['address']}\n" +
                            f"Area: {item['area_name'] if item['area_name'] else 'Unknown'}\n" +
                            f"Area Code: {item['area_code'] if item['area_code'] else 'Unknown'}\n" +
                            f"Total Crimes: {item['crime_count']}\n" +
                            f"Crime Types: {', '.join(item['crime_types']) if item['crime_types'] else 'None reported'}"
                            for item in location_result
                        ])
                        
                        prompt = f"""
                        Based on the crime database information about these locations:
                        
                        {location_info}
                        
                        Answer the user's question: "{user_input}"
                        
                        Only use the information provided above from the database. Make it clear this information is from the criminal records database.
                        """
                        
                        response = llm.invoke(prompt)
                        logger.info("RESPONSE FROM: direct location search - Using location information")
                        return response.content
                except Exception as e:
                    logger.error(f"Error in direct location search: {e}")

            # Try direct crime search for crime-related queries
            crime_indicators = ["crime", "theft", "burglary", "robbery", "assault", "murder", "homicide", "incident", "case"]
            if any(indicator in user_input.lower() for indicator in crime_indicators):
                logger.info(f"Attempting direct Crime search for: {user_input}")
                
                # Direct query for Crime entity
                crime_query = """
                MATCH (c:Crime)
                WHERE toLower(c.type) CONTAINS toLower($search)
                   OR toLower(c.description) CONTAINS toLower($search)
                OPTIONAL MATCH (c)-[:OCCURRED_AT]->(l:Location)
                OPTIONAL MATCH (c)<-[:INVESTIGATED_BY]-(o:Officer)
                OPTIONAL MATCH (c)<-[:INVOLVED_IN]-(p:Person)
                RETURN c.type AS type, c.date AS date, c.description AS description,
                       c.last_outcome AS outcome, c.charge AS charge,
                       l.address AS location,
                       collect(distinct o.badge_no + ' (' + o.rank + ')') AS officers,
                       collect(distinct p.name + ' ' + p.surname) AS people
                LIMIT 5
                """
                
                try:
                    crime_result = graph.query(crime_query, {"search": user_input.lower()})
                    
                    if crime_result and len(crime_result) > 0:
                        logger.info(f"Found {len(crime_result)} crime records")
                        
                        # Format crime results
                        crime_info = "\n\n".join([
                            f"Crime: {item['type']}\n" +
                            f"Date: {item['date'] if item['date'] else 'Unknown'}\n" +
                            f"Description: {item['description'] if item['description'] else 'No description available'}\n" +
                            f"Outcome: {item['outcome'] if item['outcome'] else 'Unknown'}\n" +
                            f"Charge: {item['charge'] if item['charge'] else 'None'}\n" +
                            f"Location: {item['location'] if item['location'] else 'Unknown'}\n" +
                            f"Investigating Officers: {', '.join(item['officers']) if item['officers'] else 'Unknown'}\n" +
                            f"People Involved: {', '.join(item['people']) if item['people'] else 'Unknown'}"
                            for item in crime_result
                        ])
                        
                        prompt = f"""
                        Based on the crime database information about these crimes:
                        
                        {crime_info}
                        
                        Answer the user's question: "{user_input}"
                        
                        Only use the information provided above from the database. Make it clear this information is from the criminal records database.
                        """
                        
                        response = llm.invoke(prompt)
                        logger.info("RESPONSE FROM: direct crime search - Using crime information")
                        return response.content
                except Exception as e:
                    logger.error(f"Error in direct crime search: {e}")
                
            # If no entity information can be found, provide a response about lack of information
            logger.info("No information found in the database, providing a 'no information' response")
            no_info_prompt = f"""
            The crime database does not contain any relevant information to answer: "{user_input}"
            
            Create a brief, professional response explaining that no information was found in the criminal records database. 
            Suggest the user try a different query, and offer some examples of what they could ask about 
            (crimes in a location, information about a specific person, vehicle details, etc.).
            """
            
            response = llm.invoke(no_info_prompt)
            return response.content
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            # Final fallback
            try:
                logger.info(f"TOOL USED: final llm fallback - All other methods failed for: '{user_input}'")
                return llm.invoke(f"As a friendly assistant who knows about crime investigation data but can also chat about other topics, respond to this: {user_input}").content
            except:
                logger.error(f"COMPLETE FAILURE: Could not generate any response for: '{user_input}'")
                return "I'm having trouble right now. Please try again later."
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
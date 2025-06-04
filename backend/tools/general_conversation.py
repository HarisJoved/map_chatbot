from llm import llm
import logging

logger = logging.getLogger(__name__)

def is_general_conversation(text):
    """Determine if the input is general conversation rather than a domain-specific question"""
    general_phrases = [
        "how are you", "what's up", "hello", "hi there", "good morning", 
        "good afternoon", "good evening", "how's it going", "nice to meet", 
        "tell me about yourself", "who are you", "what can you do",
        "thank you", "thanks", "bye", "goodbye", "see you"
    ]
    
    text_lower = text.lower()
    
    # Check if the input contains general conversation phrases
    for phrase in general_phrases:
        if phrase in text_lower:
            logger.info(f"Detected general conversation phrase: '{phrase}' in input: '{text}'")
            return True
    
    # If the text is very short, it's likely general conversation
    if len(text.split()) < 4:
        logger.info(f"Detected short message (likely general conversation): '{text}'")
        return True
    
    logger.info(f"Input not detected as general conversation: '{text}'")
    return False

def handle_general_chat(input):
    """Handle general conversation not specific to defects, sensors, events, CRM cases, or road segments"""
    try:
        logger.info(f"Handling general conversation: '{input}'")
        prompt = """You are a friendly assistant for a Neo4j graph database about road defects, sensors, detection events, CRM cases, and road segments.\nRespond to the user's message in a warm, professional way as if you're having a conversation with a user interested in this data.\nKeep your response concise but helpful.\n\nUser: {input}"""
        response = llm.invoke(prompt.format(input=input))
        logger.info("Successfully generated general conversation response")
        return {"output": response.content}
    except Exception as e:
        logger.error(f"Error in handle_general_chat: {e}")
        return {"output": "I'm sorry, I'm having trouble with my conversation abilities right now."} 
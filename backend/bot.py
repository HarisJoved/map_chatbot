from utils import write_message
from agent import generate_response

# Page Config
st.set_page_config("POLE Investigator", page_icon=":mag:")

# Set up Session State
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm your Crime Investigation Assistant. I can help you explore crime data using the POLE model (Person, Object, Location, Event). Ask me about crimes, locations, people involved, vehicles, officers, and evidence related to cases."},
    ]

# Keep track of context
if "context" not in st.session_state:
    st.session_state.context = {
        "last_crime": None,
        "last_location": None,
        "last_person": None,
        "last_vehicle": None,
        "last_area": None,
        "last_officer": None,
        "discussed_topics": []
    }

# Submit handler
def handle_submit(message):
    """
    Submit handler:

    You will modify this method to talk with an LLM and provide
    context using data from Neo4j.
    """

    # Handle the response
    with st.spinner('Investigating...'):
        # Get last few messages for context
        recent_messages = []
        for msg in st.session_state.messages[-5:]:  # Last 5 messages for context
            recent_messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Call the agent with message and context
        response = generate_response(message, recent_messages, st.session_state.context)
        
        # Update context based on response (simple keyword extraction)
        update_context(message, response)
        
        write_message('assistant', response)

def update_context(user_message, response):
    """Update conversation context based on messages"""
    # Extract potential mentions
    lower_msg = user_message.lower()
    lower_resp = response.lower()
    
    # Check for crime mentions
    crime_indicators = ["crime", "case", "incident", "investigation", "offense", "theft", "burglary", "robbery", "assault"]
    
    # Simple crime extraction (this is basic, could be improved)
    if any(indicator in lower_msg for indicator in crime_indicators):
        # Extract potential crime information
        import re
        crime_match = re.search(r'"([^"]+)"', user_message)
        if crime_match:
            st.session_state.context["last_crime"] = crime_match.group(1)
        elif "about" in lower_msg:
            # Extract crime info after "about"
            about_parts = user_message.split("about")
            if len(about_parts) > 1 and len(about_parts[1].strip()) > 0:
                potential_crime = about_parts[1].strip().strip('?!.,')
                st.session_state.context["last_crime"] = potential_crime
    
    # Check for location mentions
    location_indicators = ["location", "place", "area", "address", "street", "where"]
    if any(indicator in lower_msg for indicator in location_indicators):
        import re
        location_match = re.search(r'"([^"]+)"', user_message)
        if location_match:
            st.session_state.context["last_location"] = location_match.group(1)
    
    # Check for person mentions
    person_indicators = ["person", "suspect", "victim", "witness", "who", "individual", "civilian"]
    if any(indicator in lower_msg for indicator in person_indicators):
        import re
        person_match = re.search(r'"([^"]+)"', user_message)
        if person_match:
            st.session_state.context["last_person"] = person_match.group(1)
    
    # Check for vehicle mentions
    vehicle_indicators = ["car", "vehicle", "truck", "van", "motorcycle", "bike", "registration", "plate", "reg"]
    if any(indicator in lower_msg for indicator in vehicle_indicators):
        import re
        vehicle_match = re.search(r'"([^"]+)"', user_message)
        if vehicle_match:
            st.session_state.context["last_vehicle"] = vehicle_match.group(1)
    
    # Check for area mentions
    area_indicators = ["district", "area", "neighborhood", "zone", "region", "sector"]
    if any(indicator in lower_msg for indicator in area_indicators):
        import re
        area_match = re.search(r'"([^"]+)"', user_message)
        if area_match:
            st.session_state.context["last_area"] = area_match.group(1)
            
    # Check for officer mentions
    officer_indicators = ["officer", "detective", "inspector", "police", "investigator", "badge"]
    if any(indicator in lower_msg for indicator in officer_indicators):
        import re
        officer_match = re.search(r'"([^"]+)"', user_message)
        if officer_match:
            st.session_state.context["last_officer"] = officer_match.group(1)
    
    # Track discussed topics
    if any(word in lower_msg for word in crime_indicators):
        st.session_state.context["discussed_topics"].append("crimes")
    if any(word in lower_msg for word in location_indicators):
        st.session_state.context["discussed_topics"].append("locations")
    if any(word in lower_msg for word in person_indicators):
        st.session_state.context["discussed_topics"].append("people")
    if "object" in lower_msg or "evidence" in lower_msg or "item" in lower_msg:
        st.session_state.context["discussed_topics"].append("objects")
    if any(word in lower_msg for word in vehicle_indicators):
        st.session_state.context["discussed_topics"].append("vehicles")
    if any(word in lower_msg for word in area_indicators):
        st.session_state.context["discussed_topics"].append("areas")
    if any(word in lower_msg for word in officer_indicators):
        st.session_state.context["discussed_topics"].append("officers")


# Display messages in Session State
for message in st.session_state.messages:
    write_message(message['role'], message['content'], save=False)

# Handle any user input
if prompt := st.chat_input("Ask about crimes, people, locations, vehicles, officers, or evidence..."):
    # Display user message in chat message container
    write_message('user', prompt)

    # Generate a response
    handle_submit(prompt)
"""
LangGraph-based Certification Credit Points Agent

This agent processes Credly certification URLs and calculates credit points
based on certification type and validity.
"""

import os
import json
import sqlite3
import re
from datetime import datetime
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
import subprocess

# State definition for the graph
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "The messages in the conversation"]
    cert_data: dict | None
    credit_points: float | None
    cert_name: str | None
    is_valid: bool | None


@tool
def extract_certification_data(url: str) -> dict:
    """
    Extract certification data from a Credly URL using the webscrap_cred_v2.py script.
    
    Args:
        url: The Credly certification URL to scrape
        
    Returns:
        Dictionary containing certification details including name, user, issue date, and expiry date
    """
    try:
        # Import and call the scraper directly
        import sys
        import importlib.util
        
        # Load the scraper module
        spec = importlib.util.spec_from_file_location("webscrap_cred_v2", "webscrap_cred_v2.py")
        scraper_module = importlib.util.module_from_spec(spec)
        sys.modules["webscrap_cred_v2"] = scraper_module
        spec.loader.exec_module(scraper_module)
        
        # Call the scraping function with the URL
        data = scraper_module.scrape_credly_alternative(url)
        return data
    except AttributeError:
        # If scrape_credly_alternative doesn't exist, try other function names
        try:
            data = scraper_module.scrape_credly(url)
            return data
        except:
            return {"error": "Could not find scraping function in webscrap_cred_v2.py"}
    except Exception as e:
        return {"error": f"Error calling scraper: {str(e)}"}


@tool
def get_certification_points(cert_name: str) -> dict:
    """
    Query the SQLite database to determine credit points for a certification.
    
    Args:
        cert_name: Name of the certification to lookup
        
    Returns:
        Dictionary with matched category and points
    """
    try:
        conn = sqlite3.connect('certifications_data.db')
        cursor = conn.cursor()
        
        # Get all certification categories
        cursor.execute("SELECT cert_name, points FROM certifications_data")
        categories = cursor.fetchall()
        conn.close()
        
        # Normalize cert name for matching
        cert_name_lower = cert_name.lower()
        
        # Match logic based on certification name
        if 'professional' in cert_name_lower or 'specialty' in cert_name_lower:
            return {"category": "Any Professional or Specialty", "points": 10}
        elif 'associate' in cert_name_lower or 'hashicorp' in cert_name_lower:
            return {"category": "Any Associate or Hashicorp", "points": 5}
        else:
            return {"category": "Anything Else", "points": 2.5}
            
    except Exception as e:
        return {"error": f"Database error: {str(e)}"}


def check_certification_validity(cert_data: dict) -> bool:
    """
    Check if a certification is still valid based on expiry date.
    
    Args:
        cert_data: Dictionary containing certification information
        
    Returns:
        Boolean indicating if certification is valid
    """
    try:
        if "Certifications" not in cert_data or len(cert_data["Certifications"]) == 0:
            return False
        
        cert = cert_data["Certifications"][0]
        expiry_str = cert.get("Certification Expiry Date", "")
        
        # Extract date from string like "Expires: September 26, 2027"
        date_match = re.search(r'(\w+\s+\d+,\s+\d{4})', expiry_str)
        if date_match:
            expiry_date_str = date_match.group(1)
            expiry_date = datetime.strptime(expiry_date_str, "%B %d, %Y")
            current_date = datetime.now()
            return current_date < expiry_date
        
        # If no expiry date found, check for "No Expiration Date"
        if "no expiration" in expiry_str.lower():
            return True
            
        return False
    except Exception as e:
        print(f"Error checking validity: {e}")
        return False


# Define the agent node
def agent_node(state: AgentState):
    """
    Main agent logic node that processes user queries about certifications.
    """
    # messages = state["messages"] # This was not working for langgraph studio
    messages = state.get("messages", [])
    if not messages:
        return state
    
    #last_message = messages[-1].content # This alone was giving error in langgraph studio

    # Handle both dict and BaseMessage formats
    last_message = messages[-1]
    if isinstance(last_message, dict):
        last_message_content = last_message.get("content", "")
    else:
        last_message_content = last_message.content
    
    # Initialize LLM with Groq
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY")
    )
    
    # Check if this is a URL query
    url_pattern = r'https?://(?:www\.)?credly\.com/badges/[a-zA-Z0-9\-]+'
    urls = re.findall(url_pattern, last_message_content)
    
    if urls:
        # Extract data from URL
        url = urls[0]
        cert_data = extract_certification_data.invoke({"url": url})
        
        if "error" in cert_data:
            return {
                "messages": messages + [AIMessage(content=f"I encountered an error: {cert_data['error']}")]
            }
        
        # Check validity
        is_valid = check_certification_validity(cert_data)
        
        # Get certification name
        cert_name = cert_data.get("Name", "Unknown")
        
        # Get points
        points_data = get_certification_points.invoke({"cert_name": cert_name})
        points = points_data.get("points", 0)
        category = points_data.get("category", "Unknown")
        
        # Generate response
        if not is_valid:
            response = f"Sorry, your cert has expired. So you won't get any credit points. But otherwise you would have stood to obtain {points} credit points for your {cert_name}"
        else:
            response = f"I see that this is a {cert_name}. And it is still valid. So you can be granted {points} credit points for it."
        
        return {
            "messages": messages + [AIMessage(content=response)],
            "cert_data": cert_data,
            "credit_points": points if is_valid else 0,
            "cert_name": cert_name,
            "is_valid": is_valid
        }
    else:
        # Handle hypothetical questions like "If I clear AWS Solution Architect Professional"
        # Use LLM to extract certification name and query database
        prompt = f"""
        Based on this user question: "{last_message}"
        
        Extract the certification name mentioned. If the user is asking about a hypothetical certification
        (like "if I clear" or "how many points will I get"), identify the certification name and respond
        with just the certification name.
        """
        
        response = llm.invoke([SystemMessage(content=prompt)])
        extracted_cert = response.content.strip()
        
        # Get points for the certification
        points_data = get_certification_points.invoke({"cert_name": extracted_cert})
        points = points_data.get("points", 0)
        
        response_text = f"You will get {points} credit points for that cert."
        
        return {
            "messages": messages + [AIMessage(content=response_text)],
            "cert_data": {},
            "credit_points": points,
            "cert_name": extracted_cert,
            "is_valid": True
        }


def should_continue(state: AgentState):
    """Determine if we should continue or end the conversation."""
    return END


# Build the graph
def create_certification_agent():
    """Create and compile the LangGraph agent."""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("agent", agent_node)
    
    # Add edges
    workflow.set_entry_point("agent")
    workflow.add_edge("agent", END)
    
    # Compile
    app = workflow.compile()
    return app

# Create the app instance for LangGraph Studio
app = create_certification_agent()

# Main execution function
def run_agent(user_input: str):
    """
    Run the certification credit agent with a user input.
    
    Args:
        user_input: User's question or Credly URL
        
    Returns:
        Agent's response
    """
    # app = create_certification_agent() # Should not be done here else langgraph studio won't open
    
    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "cert_data": {},
        "credit_points": 0.0,
        "cert_name": "",
        "is_valid": False
    }
    
    result = app.invoke(initial_state)
    return result["messages"][-1].content


# Example usage
if __name__ == "__main__":
    print("Certification Credit Points Agent")
    print("=" * 50)
    
    # Example queries
    queries = [
        "How many credit points can I get for https://www.credly.com/badges/e192db17-f8c5-46aa-8f99-8a565223f1d6?",
        "What about https://www.credly.com/badges/90ee2ee9-f6cf-4d9b-8a52-f631d8644d58 ?",
        "If I clear AWS Solution Architect Professional how many points will I get?"
    ]
    
    for query in queries:
        print(f"\nUser: {query}")
        response = run_agent(query)
        print(f"System: {response}")
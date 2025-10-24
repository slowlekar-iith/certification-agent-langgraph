"""
LangGraph-based Certification Credit Points Agent using ReAct Pattern

This agent uses create_react_agent to autonomously process Credly certification URLs 
and calculate credit points based on certification type and validity.
"""

import os
import json
import sqlite3
import re
from datetime import datetime
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool


@tool
def extract_certification_data(url: str) -> str:
    """
    Extract certification data from a Credly URL. ALWAYS call this FIRST when user provides a URL.
    
    This tool scrapes the Credly badge page and returns certification details including:
    - Name: The full certification name (e.g., "HashiCorp Terraform Associate")
    - Certification Expiry Date: The expiry date string (e.g., "Expires: January 15, 2023")
    - Issue Date: When the certification was issued
    - User names: The badge holders
    
    Args:
        url: The Credly certification URL (format: https://www.credly.com/badges/...)
        
    Returns:
        JSON string with structure: {"Name": "...", "Certifications": [{"Certification Expiry Date": "..."}]}
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
        
        # Return as JSON string for the LLM
        return json.dumps(data, indent=2)
    except AttributeError:
        # If scrape_credly_alternative doesn't exist, try other function names
        try:
            data = scraper_module.scrape_credly(url)
            return json.dumps(data, indent=2)
        except:
            return json.dumps({"error": "Could not find scraping function in webscrap_cred_v2.py"})
    except Exception as e:
        return json.dumps({"error": f"Error calling scraper: {str(e)}"})


@tool
def get_certification_points(cert_name: str) -> str:
    """
    Get credit points for a certification by looking it up in the database.
    
    The database has these categories with point values:
    - "Any Professional or Specialty" = 10 points (matches: professional, specialty)
    - "Any Associate or Hashicorp" = 5 points (matches: associate, hashicorp, terraform)
    - "Anything Else" = 2.5 points (default for all others)
    
    Args:
        cert_name: Full certification name (e.g., "AWS Solutions Architect Professional", 
                   "HashiCorp Terraform Associate", "AWS AI Practitioner")
        
    Returns:
        JSON with: {"category": "...", "points": number, "cert_name": "..."}
        Use the "points" value in your response to the user.
    """
    try:
        conn = sqlite3.connect('certifications_data.db')
        cursor = conn.cursor()
        
        # Get all certification categories from database
        cursor.execute("SELECT cert_name, points FROM certifications_data ORDER BY points DESC")
        categories = cursor.fetchall()
        conn.close()
        
        # Normalize cert name for matching
        cert_name_lower = cert_name.lower()
        
        # Try to match against each category in database
        for category_name, points in categories:
            category_lower = category_name.lower()
            
            # Extract keywords from category name
            keywords = []
            for word in category_lower.replace(' or ', ' ').replace(' and ', ' ').split():
                if len(word) > 2:
                    keywords.append(word)
            
            # Check if any keyword matches the certification name
            for keyword in keywords:
                if keyword in cert_name_lower:
                    return json.dumps({
                        "category": category_name,
                        "points": points,
                        "cert_name": cert_name
                    })
        
        # If no match found, return the last category (lowest points)
        if categories:
            default_category, default_points = categories[-1]
            return json.dumps({
                "category": default_category,
                "points": default_points,
                "cert_name": cert_name
            })
        else:
            return json.dumps({"error": "No categories found in database"})
            
    except Exception as e:
        return json.dumps({"error": f"Database error: {str(e)}"})


@tool
def check_certification_validity(expiry_date_str: str) -> str:
    """
    Check if a certification is still valid. Call this AFTER extracting certification data.
    
    Pass the "Certification Expiry Date" field value from the extracted data.
    
    Args:
        expiry_date_str: The expiry date string from certification data 
                        (e.g., "Expires: September 26, 2027" or "No Expiration Date")
        
    Returns:
        JSON with: {"is_valid": true/false, "message": "Valid" or "Expired", "days_remaining": number}
        - is_valid: true means cert is still active, false means expired
        - Use this to determine if user gets points (expired = 0 points)
    """
    try:
        # Check for "No Expiration Date" first
        if "no expiration" in expiry_date_str.lower() or "does not expire" in expiry_date_str.lower():
            return json.dumps({
                "is_valid": True,
                "message": "Valid - Does not expire",
                "days_remaining": "N/A"
            })
        
        # Extract date from string
        date_patterns = [
            r'expires?:?\s*(\w+\s+\d+,\s+\d{4})',
            r'expir[y|ation]*\s*date:?\s*(\w+\s+\d+,\s+\d{4})',
            r'(\w+\s+\d+,\s+\d{4})',
        ]
        
        expiry_date = None
        for pattern in date_patterns:
            date_match = re.search(pattern, expiry_date_str, re.IGNORECASE)
            if date_match:
                expiry_date_str_clean = date_match.group(1)
                try:
                    expiry_date = datetime.strptime(expiry_date_str_clean, "%B %d, %Y")
                    break
                except ValueError:
                    continue
        
        if expiry_date:
            current_date = datetime.now()
            is_valid = current_date < expiry_date
            days_remaining = (expiry_date - current_date).days
            
            return json.dumps({
                "is_valid": is_valid,
                "expiry_date": expiry_date.strftime("%Y-%m-%d"),
                "days_remaining": days_remaining if is_valid else 0,
                "message": "Valid" if is_valid else "Expired"
            })
        
        return json.dumps({
            "is_valid": False,
            "message": "Expired - Could not parse date",
            "days_remaining": 0
        })
        
    except Exception as e:
        return json.dumps({
            "error": f"Error checking validity: {str(e)}",
            "is_valid": False,
            "message": "Error"
        })


# System prompt for the agent
SYSTEM_PROMPT = """You are a certification credit points calculator agent. Your job is to help users determine how many credit points they can earn for their professional certifications.

**CRITICAL WORKFLOW INSTRUCTIONS:**

For Credly URL queries:
1. ALWAYS call extract_certification_data first to get the certification details
2. Then call check_certification_validity with the expiry date string from the data
3. Then call get_certification_points with the certification name
4. Finally, format your response based on validity status

For hypothetical certification queries (e.g., "If I clear AWS..."):
1. Call get_certification_points with the certification name
2. Respond with the simple format

**EXACT RESPONSE FORMATS (FOLLOW THESE PRECISELY):**

For EXPIRED certifications:
"Sorry, your cert has expired. So you won't get any credit points. But otherwise you would have stood to obtain [POINTS] credit points for your [CERT_NAME]"

For VALID certifications:
"I see that this is a [CERT_NAME]. And it is still valid. So you can be granted [POINTS] credit points for it."

For HYPOTHETICAL queries:
"You will get [POINTS] credit points for that cert."

**IMPORTANT RULES:**
- Use the EXACT wording from the formats above
- For expired certs, award 0 points but mention what they would have gotten
- Extract the certification name from the scraped data (look for "Name" field)
- Always use the points value from the database tool
- Don't add extra explanations or details
- Follow the capitalization and punctuation exactly

**Example Tool Usage Flow:**
User: "How many points for https://credly.com/badges/abc123?"
1. Call extract_certification_data("https://credly.com/badges/abc123")
   Result: {"Name": "HashiCorp Terraform Associate", "Certifications": [{"Certification Expiry Date": "Expires: January 15, 2023"}]}
2. Call check_certification_validity("Expires: January 15, 2023")
   Result: {"is_valid": false, "message": "Expired"}
3. Call get_certification_points("HashiCorp Terraform Associate")
   Result: {"category": "Any Associate or Hashicorp", "points": 5}
4. Response: "Sorry, your cert has expired. So you won't get any credit points. But otherwise you would have stood to obtain 5 credit points for your HashiCorp Terraform Associate"

Be precise and follow the formats exactly!"""


def create_certification_agent():
    """Create and compile the LangGraph ReAct agent."""
    
    # Initialize LLM
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY")
    )
    
    # Define tools
    tools = [
        extract_certification_data,
        check_certification_validity,
        get_certification_points
    ]
    
    # Create ReAct agent (no state_modifier in this version)
    agent = create_react_agent(llm, tools)
    
    return agent


# Create the app instance for LangGraph Studio
app = create_certification_agent()


def run_agent(user_input: str):
    """
    Run the certification credit agent with a user input.
    
    Args:
        user_input: User's question or Credly URL
        
    Returns:
        Agent's response
    """
    # Prepend system message to the conversation
    initial_state = {
        "messages": [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_input)
        ]
    }
    
    result = app.invoke(initial_state)
    
    # Get the last message (agent's final response)
    last_message = result["messages"][-1]
    return last_message.content


# Example usage
if __name__ == "__main__":
    print("Certification Credit Points Agent (ReAct)")
    print("=" * 50)
    
    # Example queries
    queries = [
        "How many credit points can I get for https://www.credly.com/badges/e192db17-f8c5-46aa-8f99-8a565223f1d6?",
        "What about https://www.credly.com/badges/90ee2ee9-f6cf-4d9b-8a52-f631d8644d58?",
        "If I clear AWS Solution Architect Professional how many points will I get?"
    ]
    
    for query in queries:
        print(f"\nUser: {query}")
        try:
            response = run_agent(query)
            print(f"System: {response}")
        except Exception as e:
            print(f"Error: {e}")

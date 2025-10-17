# LangGraph Certification Credit Points Agent

# Goal 
An intelligent agent built with LangGraph that processes Credly certification URLs and calculates credit points based on certification type and validity.

## User Interaction 
How Users Interact with the Agent

# Step 1: Launch the Agent
Users can interact with the agent through two methods:

Method A: LangGraph Studio (Visual Interface)
(bash) langgraph dev

Method B: Python Script (Programmatic)
(python) from langgraph_cred_agent import run_agent
response = run_agent("your query here")

# Step 2: Submit a Query
Users can ask following types of questions:
Query Type 1: Check Credit Points for a Specific Badge (Expired)
User: "How many credit points can I get for https://www.credly.com/badges/e192db17-f8c5-46aa-8f99-8a565223f1d6?"
Agent Response: "Sorry, your cert has expired. So you won't get any credit points. 
But otherwise you would have stood to obtain 5 credit points for your Hashicorp Terraform Cert"

Query Type 2: Check Credit Points for a Valid Badge
User: "What about https://www.credly.com/badges/90ee2ee9-f6cf-4d9b-8a52-f631d8644d58?"
Agent Response: "I see that this is an AWS AI Practitioner cert. And it is still valid. 
So you can be granted 2.5 credit points for it."

Query Type 3: Hypothetical Certification Query
User: "If I clear AWS Solution Architect Professional how many points will I get?"
Agent Response: "You will get 10 credit points for that cert."

# Step 3: View Results
The agent provides:

Credit Points: Numerical value based on certification tier
Certification Name: Extracted from the badge or query
Validity Status: Whether the certification is currently valid
Reasoning: Clear explanation of the decision

# Step 4: Continue Conversation
Users can ask follow-up questions in the same session:
User: "What if I get both AWS Solutions Architect and Terraform Associate?"
Agent: [Calculates cumulative points]

## Agent Specification Overview

1. Architecture Overview

System Components
┌─────────────────────────────────────────────────────────────┐
│                    User Input Layer                         │
│         (LangGraph Studio / Python Interface)               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  LangGraph Agent Core                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Agent Node (Main Logic)                  │  │
│  │  • Query Classification                               │  │
│  │  • URL Pattern Matching                               │  │
│  │  │  Orchestration Logic                               │  │
│  └──┬────────────────────────────────────────────────────┘  │
│     │                                                       │
│     ├──► Tool 1: Web Scraper (webscrap_cred_v2.py)          │
│     │    • Extracts cert data from Credly                   │
│     │    • Returns: Name, Issue Date, Expiry Date           │
│     │                                                       │
│     └──► Tool 2: Database Query (SQLite)                    │
│          • Matches cert name to point category              │
│          • Returns: Category and Points                     │
└─────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   Response Generation                       │
│    • Validity Check Logic                                   │
│    • Point Calculation                                      │
│    • Natural Language Response                              │
└─────────────────────────────────────────────────────────────┘

2. State Management

AgentState Schema
python{
    "messages": List[Message],      # Conversation history
    "cert_data": Dict | None,       # Extracted certification data
    "credit_points": float | None,  # Calculated points
    "cert_name": str | None,        # Certification name
    "is_valid": bool | None         # Validity status
}


3. Decision Flow

Query Classification Logic

User Input
    │
    ▼
┌─────────────────┐
│ URL Detection?  │
└────┬────────────┘
     │
     ├─ YES ──► Extract URL ──► Call Web Scraper Tool
     │                              │
     │                              ▼
     │                         Parse Response
     │                              │
     │                              ▼
     │                         Check Expiry Date
     │                              │
     │                              ├─ Valid ──► Query DB ──► Award Points
     │                              │
     │                              └─ Expired ──► Query DB ──► 0 Points (with message)
     │
     └─ NO ──► Extract Cert Name
                    │
                    ▼
               Query DB for Points
                    │
                    ▼
               Return Hypothetical Response

4. Extensibility Points
- Adding New Certification Tiers
- Adding New Data Sources
- Enhancing NLP


## Features

- Extracts certification data from Credly URLs
- Validates certification expiry dates
- Calculates credit points based on certification tier
- Handles both URL queries and hypothetical questions
- Powered by Groq's  model

## Setup

### Prerequisites
- Python 3.8+
- Groq API Key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/slowlekar-iith/certification-agent-langgraph.git
cd YOUR_REPO
```

2. Install dependencies:
```bash
pip install langgraph langchain langchain-groq langchain-core groq
```

3. Set up environment variables:
```bash
export GROQ_API_KEY="your_groq_api_key_here"
```

4. Create the database:
```bash
python sqlite_cert.py
```

## Usage

### With LangGraph Studio
```bash
langgraph dev
```

### Programmatically
```python
from langgraph_cred_agent import run_agent

response = run_agent("How many credit points can I get for https://www.credly.com/badges/...")
print(response)
```

## Project Structure
```
.
├── langgraph_cred_agent.py      # Main LangGraph agent
├── webscrap_cred_v2.py          # Web scraper for Credly
├── certifications_data.db       # SQLite database
├── langgraph.json               # LangGraph configuration
└── README.md                    # This file
```

## Query & Traces (Reference Screenshots)

![image alt](https://github.com/slowlekar-iith/certification-agent-langgraph/blob/eb2ac8ae632577e3b7ba39ec966df549d92e8e32/img/Credly_Query1_Screenshot.png)

![image alt](https://github.com/slowlekar-iith/certification-agent-langgraph/blob/eb2ac8ae632577e3b7ba39ec966df549d92e8e32/img/Credly_Query2_Screenshot.png)

![image alt](https://github.com/slowlekar-iith/certification-agent-langgraph/blob/eb2ac8ae632577e3b7ba39ec966df549d92e8e32/img/Credly_Query3_Screenshot.png)

![image alt](https://github.com/slowlekar-iith/certification-agent-langgraph/blob/eb2ac8ae632577e3b7ba39ec966df549d92e8e32/img/Credly_Trace_Screenshot.png)

## Database/Table Records View

![image alt](https://github.com/slowlekar-iith/certification-agent-langgraph/blob/eb2ac8ae632577e3b7ba39ec966df549d92e8e32/img/Credly_DB_Screenshot.png)

## Credit Point System

| Certification Type | Points |
|-------------------|--------|
| Professional or Specialty | 10 |
| Associate or Hashicorp | 5 |
| Anything Else | 2.5 |



# LangGraph Certification Credit Points Agent

An intelligent agent built with LangGraph that processes Credly certification URLs and calculates credit points based on certification type and validity.

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

## Credit Point System

| Certification Type | Points |
|-------------------|--------|
| Professional or Specialty | 10 |
| Associate or Hashicorp | 5 |
| Anything Else | 2.5 |



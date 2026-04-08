# AI-Powered Subscription Manager
​An intelligent full-stack application designed to help users track, manage, and optimize their software subscriptions. This system features an AI Agent built with LangGraph to provide financial insights and automated email alerts to prevent missed renewals.

​# Key Features
**​Intelligent AI Assistant: Interact with a chatbot that understands your spending habits, suggests cheaper alternatives using web search, and analyzes your subscription data.

**​Proactive Renewal Alerts: Automated background scheduler that sends email notifications 2 days before a subscription is due.

**​Secure Authentication: Implements OAuth2 with JWT (JSON Web Tokens) for secure user login and strict data isolation.

**​Dynamic Dashboard: A clean Streamlit interface to visualize total spending and monitor upcoming obligations.
​
**Automated Logic: Automatically calculates renewal dates based on weekly, monthly, or yearly billing cycles.
​
**Tech Stack
​Backend: FastAPI (Python)
​AI Orchestration: LangGraph, LangChain
​LLM: OpenAI GPT-4o-mini
​Database: SQLAlchemy (SQLite)
​Frontend: Streamlit
​Task Scheduling: APScheduler
​Security: JOSE (JWT), Passlib (Bcrypt)
​
**Getting Started
​1. Prerequisites
​Python 3.10+
​OpenAI API Key
​Tavily API Key (for web search)
​Gmail App Password (for email alerts)

​2. Installation
**Clone the repository
git clone <your-repo-link>
cd AI_Subscription_Manager

#Install dependencies
pip install -r requirements.txt
or manually install the bellow commands
pip install fastapi uvicorn sqlalchemy passlib bcrypt python-jose pip install langchain langgraph langchain-openai langchain-community

3. Environment Setup
​Create a .env file in the root directory:
OPENAI_API_KEY=your_openai_key
TAVILY_API_KEY=your_tavily_key
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_16_character_app_password

4. Running the Application
Start the Backend:
uvicorn main:app --reload

Start the Frontend:
streamlit run frontend.py

API Endpoints (Swagger)
Once the backend is running, visit http://127.0.0.1:8000/docs to explore:
POST /signup/ & POST /login/: User management.
POST /subscriptions/: Create new tools with purchase and renewal dates.
GET /dashboard/: Retrieve spending analytics.
POST /chat/: Converse with the AI Agent.

**AI Agent Logic
The agent uses a StateGraph to:
Retrieve: Fetch the user's current subscriptions from the database.
Search: Use Tavily to find real-time pricing and alternatives.
Analyze: Compare internal costs with market data to provide actionable optimization advice.

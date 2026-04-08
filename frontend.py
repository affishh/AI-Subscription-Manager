import streamlit as st
import requests
from datetime import date

# --- CONFIGURATION ---
API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="AI Subscription Manager", layout="wide")

# --- SESSION STATE FOR AUTH ---
if "token" not in st.session_state:
    st.session_state.token = None

# --- SIDEBAR: LOGIN & SIGNUP ---
with st.sidebar:
    st.title("🔐 Authentication")
    auth_mode = st.radio("Choose Mode", ["Login", "Signup"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    if auth_mode == "Signup":
        name = st.text_input("Full Name")
        if st.button("Create Account"):
            res = requests.post(f"{API_URL}/signup/", json={"email": email, "full_name": name, "password": password})
            st.success("Account created! Please login.")
    else:
        if st.button("Login"):
            # Using the OAuth2 form data format
            res = requests.post(f"{API_URL}/login/", data={"username": email, "password": password})
            if res.status_code == 200:
                st.session_state.token = res.json()["access_token"]
                st.success("Logged in!")
            else:
                st.error("Invalid credentials")

# --- MAIN DASHBOARD ---
if st.session_state.token:
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    
    st.title(" AI Subscription Dashboard")
    
    # 1. ADD NEW SUBSCRIPTION (Form)
    with st.expander("➕ Add New Tool Subscription"):
        with st.form("sub_form"):
            col1, col2 = st.columns(2)
            tool = col1.text_input("Tool Name")
            cost = col2.number_input("Cost ($)", min_value=0.0)
            cycle = col1.selectbox("Billing Cycle", ["weekly", "monthly", "yearly"])
            p_date = col2.date_input("Purchase Date", value=date.today())
            
            if st.form_submit_button("Save Subscription"):
                data = {"tool_name": tool, "cost": cost, "billing_cycle": cycle, "purchase_date": str(p_date)}
                requests.post(f"{API_URL}/subscriptions/", json=data, headers=headers)
                st.rerun()

    # 2. VIEW ALL & MONITOR RENEWALS (Dashboard)
    dash_res = requests.get(f"{API_URL}/dashboard/", headers=headers).json()
    
    col_a, col_b = st.columns([2, 1])
    
    with col_a:
        st.subheader("📊 Your Active Subscriptions")
        if dash_res.get("subscriptions"):
            st.table(dash_res["subscriptions"])
        else:
            st.info("No subscriptions found. Add one above!")

    with col_b:
        st.metric("Total Monthly Spend", f"${dash_res.get('total_spending', 0)}")
        st.subheader("🔔 Upcoming Renewals")
        # Logic to highlight items within 7 days
        for sub in dash_res.get("subscriptions", []):
            st.write(f"**{sub['tool_name']}** due on {sub['renewal_date']}")

    # 3. INTERACT WITH CHATBOT (Interface)
    st.divider()
    st.subheader(" AI Assistant")
    user_query = st.text_input("Ask about your spending, alternatives, or optimizations:")
    if st.button("Send to AI"):
        with st.spinner("Thinking..."):
            chat_res = requests.post(f"{API_URL}/chat/", json={"query": user_query}, headers=headers).json()
            st.chat_message("assistant").write(chat_res.get("response"))

else:
    st.warning("Please login from the sidebar to access your dashboard.")
import streamlit as st
import os
import time

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        user = st.session_state["username"]
        password = st.session_state["password"]
        
        def get_remote_ip():
            """Extracts the client IP from Streamlit headers."""
            try:
                from streamlit.web.server.websocket_headers import _get_websocket_headers
                headers = _get_websocket_headers()
                if headers and "X-Forwarded-For" in headers:
                    return headers["X-Forwarded-For"].split(",")[0]
                return "Unknown"
            except Exception:
                return "Unknown"

        def get_secret(key, default):
            # 1. Try Environment Variable
            val = os.getenv(key)
            if val: return val
            
            # 2. Try Streamlit Secrets (Safely)
            try:
                if key in st.secrets:
                    return st.secrets[key]
            except Exception:
                pass
            
            # 3. Fallback
            return default

        # Get secrets with fallback to defaults
        admin_user = get_secret("ADMIN_USER", "admin@admin.com")
        admin_pass = get_secret("ADMIN_PASSWORD", "Admin@123")
        
        guest_user = get_secret("GUEST_USER", "demo@agentic.ai")
        guest_pass = get_secret("GUEST_PASSWORD", "DemoAccess!2025")
        
        client_ip = get_remote_ip()

        if user == admin_user and password == admin_pass:
            st.session_state["password_correct"] = True
            st.session_state["user_role"] = "admin"
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 🔐 LOGIN SUCCESS: Admin user '{user}' logged in from IP: {client_ip}")
            del st.session_state["password"]
            del st.session_state["username"]
        elif user == guest_user and password == guest_pass:
            st.session_state["password_correct"] = True
            st.session_state["user_role"] = "guest"
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 👤 LOGIN SUCCESS: Guest user '{user}' logged in from IP: {client_ip}")
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ❌ LOGIN FAILED: User '{user}' attempted login from IP: {client_ip}")
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input
        st.markdown(
            """
            <style>
            /* Nuclear Option: Hide ALL Streamlit Cloud UI Elements */
            .stApp > header {visibility: hidden !important; display: none !important;}
            header {visibility: hidden !important; display: none !important;}
            footer {visibility: hidden !important; display: none !important;}
            
            #MainMenu {visibility: hidden !important; display: none !important;}
            div[data-testid="stToolbar"] {visibility: hidden !important; display: none !important;}
            div[data-testid="stHeader"] {visibility: hidden !important; display: none !important;}
            div[data-testid="stStatusWidget"] {visibility: hidden !important; display: none !important;}
            div[data-testid="stFooter"] {visibility: hidden !important; display: none !important;}
            div[data-testid="stDecoration"] {visibility: hidden !important; display: none !important;}
            
            /* Wildcard hide for Viewer Badge (Bottom Right) */
            div[class*="viewerBadge"] {visibility: hidden !important; display: none !important;}
            .viewerBadge_container__1QSob {display: none !important;}
            
            .stTextInput > div > div > input { background-color: #f0f2f6; }
            .auth-container { max_width: 400px; margin: 100px auto; padding: 2rem; border-radius: 10px; background: white; }
            </style>
            """, unsafe_allow_html=True
        )
        with st.container():
            st.markdown("## 🔐 Login Required")
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.button("Login", on_click=password_entered)
        return False
    
    elif not st.session_state["password_correct"]:
        with st.container():
            st.markdown("## 🔐 Login Required")
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.button("Login", on_click=password_entered)
            st.error("😕 User not known or password incorrect")
        return False
    
    else:
        return True

def logout():
    """Logs the user out."""
    st.session_state["password_correct"] = False
    st.rerun()

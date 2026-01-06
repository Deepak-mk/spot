import streamlit as st
import os
import time

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        user = st.session_state["username"]
        password = st.session_state["password"]
        
        # Get secrets with fallback to defaults
        correct_user = os.getenv("ADMIN_USER", "") or st.secrets.get("ADMIN_USER", "admin@admin.com")
        correct_password = os.getenv("ADMIN_PASSWORD", "") or st.secrets.get("ADMIN_PASSWORD", "Admin@123")

        if user == correct_user and password == correct_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for username and password
        st.markdown(
            """
            <style>
            .stTextInput > div > div > input {
                background-color: #f0f2f6;
            }
            .auth-container {
                max_width: 400px;
                margin: 100px auto;
                padding: 2rem;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                background-color: white;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        with st.container():
            st.markdown("## 🔐 Login Required")
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.button("Login", on_click=password_entered)
            
        return False
    
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error
        with st.container():
            st.markdown("## 🔐 Login Required")
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.button("Login", on_click=password_entered)
            st.error("😕 User not known or password incorrect")
        return False
    
    else:
        # Password correct
        return True

def logout():
    """Logs the user out."""
    st.session_state["password_correct"] = False
    st.rerun()

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
        
        def send_email_alert(user_email, ip_address):
            """Sends an email alert for guest logins."""
            sender_email = get_secret("SMTP_EMAIL", "")
            sender_password = get_secret("SMTP_PASSWORD", "")
            admin_ip = get_secret("ADMIN_IP", "")
            
            # 1. Skip if no credentials
            if not sender_email or not sender_password:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ Email alert skipped: SMTP credentials not found.")
                return

            # 2. Skip if IP matches Admin IP (User's IP)
            if admin_ip and ip_address == admin_ip:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ℹ️ Email alert skipped: Known Admin IP ({ip_address}).")
                return

            # 3. Persistence & Alerting (Webhook + SMTP)
            alert_sent = False
            
            # 3. Persistence & Alerting
            alert_sent = False
            
            # Option A: ntfy.sh (Open Source) - PREFERRED
            # Just set NTFY_TOPIC in secrets (e.g., "spot-alerts-deepak")
            ntfy_topic = get_secret("NTFY_TOPIC", "")
            if ntfy_topic:
                try:
                    import requests
                    requests.post(f"https://ntfy.sh/{ntfy_topic}", 
                        data=f"🚨 Guest Login: {user} from IP {client_ip}".encode("utf-8"),
                        headers={"Title": "Spot Security Alert", "Priority": "high"}
                    )
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 🔔 ntfy.sh alert sent to topic '{ntfy_topic}'")
                    alert_sent = True
                except Exception as e:
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ❌ ntfy.sh failed: {e}")

            # Option B: Slack/Discord Webhook
            webhook_url = get_secret("ALERT_WEBHOOK_URL", "")
            if not alert_sent and webhook_url:
                try:
                    import requests
                    import json
                    payload = {"text": f"🚨 *Spot Security Alert*\n*User:* `{user}`\n*IP:* `{client_ip}`"}
                    requests.post(webhook_url, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
                    alert_sent = True
                except Exception:
                    pass

            # Option C: SMTP (Fallback)
            if not alert_sent and sender_email and sender_password:
                try:
                    import smtplib
                    from email.mime.text import MIMEText
                    
                    recipient = "deepak09b@gmail.com"
                    subject = f"🚨 Spot Alert: Guest Login from {ip_address}"
                    body = f"""
                    Spot Agentic Platform Alert
                    ---------------------------
                    User: {user_email}
                    Role: Guest
                    IP: {ip_address}
                    Time: {time.strftime('%Y-%m-%d %H:%M:%S')}
                    """
                    
                    msg = MIMEText(body)
                    msg['Subject'] = subject
                    msg['From'] = sender_email
                    msg['To'] = recipient
                    
                    # Gmail SMTP Default
                    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                        server.login(sender_email, sender_password)
                        server.sendmail(sender_email, recipient, msg.as_string())
                    
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 📧 Email alert sent to {recipient}")
                except Exception as e:
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ❌ Email alert failed: {e}")

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
            
            # Trigger Alert
            send_email_alert(user, client_ip)
            
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

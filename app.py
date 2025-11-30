# app.py
from database import init_db
init_db()   # This creates the missing "users" table
import streamlit as st
import sqlite3
import hashlib

# -------------------------------
# Page Config + Hide Sidebar Completely
# -------------------------------
st.set_page_config(
    page_title="AI-Integrated Financial Management Web Application",
    page_icon="logo_circle.png",  # Ensure this file exists in your app root
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Hide sidebar using CSS
hide_sidebar = """
<style>
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    .css-1d391kg, .css-fblp2m {
        display: none !important;
    }
</style>
"""
st.markdown(hide_sidebar, unsafe_allow_html=True)

# -------------------------------
# Initialize Session State
# -------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "user_role" not in st.session_state:
    st.session_state.user_role = "user"
if "email" not in st.session_state:
    st.session_state.email = None
if "show_signup" not in st.session_state:
    st.session_state.show_signup = False

# -------------------------------
# Database & Hashing
# -------------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username: str, password: str):
    try:
        conn = sqlite3.connect("finance.db")
        c = conn.cursor()
        c.execute("""
            SELECT username, role, email FROM users 
            WHERE LOWER(username)=? AND password_hash=?
        """, (username.lower(), hash_password(password)))
        result = c.fetchone()
        conn.close()
        return result
    except Exception as e:
        print(e)
        return None

def create_user(username: str, email: str, password: str):
    try:
        conn = sqlite3.connect("finance.db")
        c = conn.cursor()
        c.execute("SELECT 1 FROM users WHERE LOWER(username)=? OR email=?", 
                  (username.lower(), email))
        if c.fetchone():
            conn.close()
            return False, "Username or email already taken"
        
        c.execute("""
            INSERT INTO users (username, email, password_hash, role) 
            VALUES (?, ?, ?, 'user')
        """, (username, email, hash_password(password)))
        conn.commit()
        conn.close()
        return True, "Account created successfully!"
    except Exception as e:
        return False, f"Error: {str(e)}"

# -------------------------------
# Main Login / Signup UI
# -------------------------------
if not st.session_state.logged_in:

    # Custom CSS (includes link-style secondary buttons)
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;600&display=swap');
        body { font-family: 'Poppins', sans-serif; }
        .login-container {
            max-width: 440px; margin: 8vh auto; padding: 40px;
            background: rgba(255, 255, 255, 0.97); border-radius: 24px;
            box-shadow: 0 15px 40px rgba(216, 27, 96, 0.25);
            backdrop-filter: blur(12px); border: 2px solid #f06292;
            text-align: center;
        }
        .title {
            color: black;
            font-size: 2em;
            font-weight: 600;
            margin-bottom: 10px;
        }
        .stTextInput > div > div > input {
            border-radius: 14px !important;
            border: 2px solid #f06292 !important;
            padding: 14px !important;
            font-size: 16px;
        }
        .stButton > button {
            background: linear-gradient(145deg, #ec407a, #d81b60) !important;
            color: white !important;
            width: 100% !important;
            padding: 14px !important;
            border-radius: 16px !important;
            font-weight: 600 !important;
            font-size: 17px;
            border: none !important;
            box-shadow: 0 8px 20px rgba(216,27,96,0.4) !important;
        }
        .stButton > button:hover {
            transform: translateY(-3px) !important;
            box-shadow: 0 12px 25px rgba(216,27,96,0.5) !important;
        }
        /* Style secondary buttons as links */
        .stButton > button[kind="secondary"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            color: #d81b60 !important;
            font-weight: 600 !important;
            text-decoration: underline !important;
            text-decoration-color: #f06292 !important;
            text-underline-offset: 3px !important;
            font-size: 15px !important;
            display: inline-block !important;
            width: auto !important;
            margin: 0 auto !important;
            transform: none !important;
        }
        .stButton > button[kind="secondary"]:hover {
            background: transparent !important;
            color: #ec407a !important;
            text-decoration-thickness: 2px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Logo
    st.markdown("""
        <div style="text-align: center; margin-bottom: 12px;">
            <img src="https://raw.githubusercontent.com/ymteoh/fyp-finance/main/logo_circle.png" width="170" style="
                border-radius: 26px; padding: 12px;
                background: white; box-shadow: 0 10px 35px rgba(216, 27, 96, 0.35);
            ">
        </div>
        <div style="text-align: center; margin-bottom: 24px;">
            <h2 style="color: black; font-family: 'Poppins', sans-serif; font-weight: 600; font-size: 1.4em; margin: 0;">
                AI-Integrated Financial Management Web Application
            </h2>
        </div>
    """, unsafe_allow_html=True)

    # Title
    if st.session_state.show_signup:
        st.markdown("<h1 class='title'>📝 Create Account</h1>", unsafe_allow_html=True)
    else:
        st.markdown("<h1 class='title'>🔐 Sign in</h1>", unsafe_allow_html=True)

    if st.session_state.show_signup:
        # ============= SIGN UP FORM =============
        with st.form("signup_form", clear_on_submit=True):
            username = st.text_input("👤 Username", placeholder="Choose a unique username")
            email = st.text_input("📧 Email", placeholder="you@example.com")
            password = st.text_input("🔒 Password", type="password", placeholder="Minimum 6 characters")
            confirm = st.text_input("🔒 Confirm Password", type="password")
            submitted = st.form_submit_button("Create Account")

            if submitted:
                if not all([username, email, password, confirm]):
                    st.error("⚠️ Please fill all fields")
                elif len(username) < 3:
                    st.error("Username too short")
                elif len(password) < 6:
                    st.error("Password must be 6+ characters")
                elif password != confirm:
                    st.error("Passwords don't match")
                else:
                    success, msg = create_user(username.strip(), email.strip(), password)
                    if success:
                        st.success("✅ Account created! Please log in.")
                        st.session_state.show_signup = False
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")

        # Back to Login (Styled as Link)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button(
                "Already have an account? Sign in",
                key="login_link_button",
                type="secondary",
                use_container_width=True
            ):
                st.session_state.show_signup = False
                st.rerun()

    else:
        # ============= LOGIN FORM =============
        with st.form("login_form", clear_on_submit=True):
            username = st.text_input("👤 Username", placeholder="Enter your username")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
            login_btn = st.form_submit_button("Login")

            if login_btn:
                if not username or not password:
                    st.error("Please enter both username and password")
                else:
                    user_data = authenticate_user(username, password)
                    if user_data:
                        st.session_state.logged_in = True
                        st.session_state.username = user_data[0]
                        st.session_state.user_role = user_data[1]
                        st.session_state.email = user_data[2]
                        st.success(f"Welcome back, {user_data[0].title()}! 🎉")
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password")

        # Sign Up (Styled as Link)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button(
                "Don’t have an account? Sign up",
                key="signup_link_button",
                type="secondary",
                use_container_width=True
            ):
                st.session_state.show_signup = True
                st.rerun()

else:
    # Logged in → redirect
    st.switch_page("pages/dashboard.py")
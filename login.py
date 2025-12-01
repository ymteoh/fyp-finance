import streamlit as st

# -------------------------------
# Page Configuration
# -------------------------------
st.set_page_config(
    page_title="Login",
    page_icon="🔐",
    layout="centered"
)

# -------------------------------
# Custom CSS: Dreamy Pink Login
# -------------------------------
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;600&family=Quicksand:wght@500&display=swap');

    .main {
        background: linear-gradient(135deg, #fdf2f8, #f8bbd0, #fce4ec);
        background-size: 400% 400%;
        animation: gradientShift 12s ease infinite;
        padding: 0;
        margin: 0;
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        font-family: 'Poppins', sans-serif;
    }

    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    .login-box {
        width: 100%;
        max-width: 440px;
        padding: 40px;
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(10px);
        border-radius: 24px;
        box-shadow:
            0 10px 30px rgba(216, 27, 96, 0.25),
            0 6px 12px rgba(236, 64, 122, 0.18);
        border: 1px solid rgba(255, 182, 193, 0.3);
        text-align: center;
        animation: float 6s ease-in-out infinite;
    }

    @keyframes float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }

    .title {
        font-size: 1.9em;
        color: #d81b60;
        margin-bottom: 24px;
        font-weight: 600;
    }

    .stTextInput > div > div > input {
        padding: 14px;
        font-size: 1em;
        border-radius: 12px;
        border: 2px solid #f06292;
        background: white;
        transition: all 0.3s;
    }
    .stTextInput > div > div > input:focus {
        border-color: #d81b60;
        box-shadow: 0 0 0 2px rgba(216, 27, 96, 0.2);
        transform: scale(1.02);
    }

    .login-btn {
        background: linear-gradient(145deg, #ec407a, #d81b60);
        color: white;
        padding: 14px;
        width: 100%;
        border: none;
        border-radius: 14px;
        font-size: 1.1em;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 6px 12px rgba(216, 27, 96, 0.3);
        margin-top: 20px;
        transition: all 0.3s ease;
    }
    .login-btn:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 20px rgba(216, 27, 96, 0.4);
    }
    .login-btn:active {
        transform: translateY(1px);
    }
    </style>
    """, unsafe_allow_html=True)

# -------------------------------
# Login Form
# -------------------------------
st.markdown("<div class='login-box'>", unsafe_allow_html=True)
st.markdown("<h1 class='title'>🔐 Login</h1>", unsafe_allow_html=True)

with st.form(key="login_form"):
    username = st.text_input("👤 Username", placeholder="Enter your username")
    password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
    submit = st.form_submit_button("Login")

    if submit:
        if username.strip() == "" or password == "":
            st.error("Please fill in all fields.")
        else:
            # Simulate login success
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"Welcome, {username}! Redirecting...")
            st.balloons()
            # Use meta refresh to redirect
            st.markdown("""
                <meta http-equiv="refresh" content="2;url=http://localhost:8501/dashboard" />
                """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
import streamlit as st

# -------------------------------
# Page Configuration
# -------------------------------
st.set_page_config(
    page_title="My Pink Portfolio",
    page_icon="💖",
    layout="centered",
    initial_sidebar_state="expanded"
)

# -------------------------------
# Custom CSS for Pink Theme
# -------------------------------
st.markdown("""
    <style>
    .main {
        background-color: #fdf2f8;
        color: #333;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .css-1d391kg { /* Sidebar title */
        color: #c2185b;
        font-weight: bold;
    }
    .css-1v3fvcr a {
        color: #d81b60;
        font-size: 1.1em;
    }
    .css-1v3fvcr a:hover {
        color: #ad1457;
        background-color: #fce4ec;
        border-radius: 8px;
    }
    .title {
        color: #d81b60;
        text-align: center;
        font-weight: 600;
    }
    .card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        border-left: 4px solid #ec407a;
    }
    </style>
    """, unsafe_allow_html=True)

# -------------------------------
# Sidebar Navigation (Auto-magically includes pages/)
# -------------------------------
st.sidebar.markdown("<h3 style='color:#d81b60; text-align:center;'>💖 Menu</h3>", unsafe_allow_html=True)

# Streamlit automatically detects pages/ folder and adds them to navigation
# You don't need to manually add links if using the pages/ system!

# Optional: Add custom title or info
st.sidebar.write("Navigate using the pages above!")

# -------------------------------
# Home Page Content
# -------------------------------
st.markdown("<h1 class='title'>🌸 Welcome to My Homepage</h1>", unsafe_allow_html=True)

st.markdown("""
<div class='card'>
    <h3>✨ About Me</h3>
    <p>
        Hi there! I'm a passionate creator who loves all things pink and sparkly.
        This site is my little corner of the internet. Check out the <strong>Gallery</strong> page!
    </p>
</div>
""", unsafe_allow_html=True)

# Feature cards
col1, col2 = st.columns(2)
with col1:
    st.markdown("""
    <div class='card'>
        <h4>🎨 Creative</h4>
        <p>Designing beautiful and meaningful experiences.</p>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown("""
    <div class='card'>
        <h4>💻 Tech-Savvy</h4>
        <p>Building apps with Python and Streamlit!</p>
    </div>
    """, unsafe_allow_html=True)

# -------------------------------
# Footer
# -------------------------------
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
    <div style="position: fixed; left: 0; bottom: 0; width: 100%; background-color: #f8bbd0; color: #c2185b; text-align: center; padding: 10px; font-size: 0.9em; border-top: 1px solid #e91e6333;">
        © 2024 My Pink Website | Designed with ❤️ using Streamlit
    </div>
    """, unsafe_allow_html=True)

# Hide default footer and menu
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)
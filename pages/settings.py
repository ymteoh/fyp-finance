import streamlit as st
import pandas as pd
import sqlite3
import subprocess
import sys
import io
import os
import zipfile
import requests
import time
from datetime import datetime, timedelta

# -------------------------------
# Shared Currency Configuration (SAME AS TREND PAGE)
# -------------------------------
currency_options = [
    "MYR", "USD", "EUR", "JPY", "GBP", "AUD", "CAD", "CHF", "CNY", "SEK",
    "NZD", "KRW", "SGD", "NOK", "MXN", "BRL", "ZAR", "RUB", "TRY", "AED",
    "INR", "PHP", "IDR", "THB", "VND", "PKR", "BDT", "LKR", "MMK", "EGP"
]

currency_symbol_map = {
    "MYR": "RM", "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥",
    "INR": "₹", "SGD": "S$", "AUD": "A$", "CAD": "C$", "CHF": "Fr",
    "CNY": "¥", "KRW": "₩", "AED": "د.إ", "THB": "฿", "IDR": "Rp",
    "PHP": "₱", "ZAR": "R", "BRL": "R$", "MXN": "$", "TRY": "₺",
    "SEK": "kr", "NOK": "kr", "NZD": "NZ$"
}

def get_exchange_rate(base="MYR", target="MYR"):
    if base == target:
        return 1.0
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{base}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data['rates'].get(target, 1.0)
    except Exception as e:
        st.warning(f"⚠️ Using MYR (API error: {str(e)[:50]}...)")
    return 1.0

# -------------------------------
# CRITICAL: Read currency from session state FIRST (SAME AS TREND PAGE)
# -------------------------------
selected_currency = st.session_state.get("selected_currency", "MYR")
exchange_rate = get_exchange_rate("MYR", selected_currency)
currency_symbol = currency_symbol_map.get(selected_currency, selected_currency + " ")

# -------------------------------
# Ensure login
# -------------------------------
if not st.session_state.get("logged_in"):
    st.error("Please log in first.")
    if st.button("Go to Login"):
        st.session_state.clear()
        st.switch_page("app.py")
    st.stop()

# -------------------------------
# Check user role (assuming you store this in session)
# -------------------------------
user_role = st.session_state.get("user_role", "user")  # Default to 'user'

# -------------------------------
# Page Configuration
# -------------------------------
st.set_page_config(
    page_title="Settings",
    page_icon="⚙️",
    layout="wide"
)

# -------------------------------
# Custom CSS (EXACT SAME AS TREND PAGE)
# -------------------------------
st.markdown("""
<style>
    .stApp {
        background-color: white !important;
    }
    .main {
        background-color: white !important;
        padding: 20px;
        font-family: 'Segoe UI', sans-serif;
    }
    h1 { 
        color: black; 
        text-align: center; 
        font-weight: 700; 
    }
    .original-subtitle {
        text-align: center; 
        color: #c2185b; 
        font-size: 0.9em;
    }
    hr { border-color: #e2e8f0; margin: 1.5rem 0; }
    
    /* Expander styling to match your theme */
    .streamlit-expanderHeader {
        background: linear-gradient(145deg, #ec407a, #d81b60) !important;
        color: white !important;
        border-radius: 12px !important;
        padding: 12px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(216,27,96,0.3) !important;
    }
    .streamlit-expanderContent {
        background: white !important;
        padding: 20px !important;
        border-radius: 0 0 12px 12px !important;
        border: 1px solid #f06292 !important;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# Database Functions for User Management
# -------------------------------
def get_all_users():
    """Get all users from database"""
    try:
        conn = sqlite3.connect("finance.db")
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email, role, created_at FROM users ORDER BY created_at DESC')
        users = cursor.fetchall()
        conn.close()
        return users
    except Exception as e:
        st.error(f"Error fetching users: {e}")
        return []

def delete_user_by_email(email):
    """Delete user by email (transactions remain in database)"""
    try:
        conn = sqlite3.connect("finance.db")
        cursor = conn.cursor()
        
        # Just delete the user - leave transactions as-is
        cursor.execute('DELETE FROM users WHERE email = ?', (email,))
        user_deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        if user_deleted:
            return True, "User deleted successfully! (Transactions preserved)"
        else:
            return False, "User not found"
            
    except Exception as e:
        return False, f"Error deleting user: {e}"

def create_user(username, email, password, role='user'):
    """Create a new user (admin only)"""
    try:
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = sqlite3.connect("finance.db")
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, role)
            VALUES (?, ?, ?, ?)
        ''', (username, email, password_hash, role))
        conn.commit()
        conn.close()
        return True, "User created successfully!"
    except sqlite3.IntegrityError as e:
        if "username" in str(e).lower():
            return False, "Username already exists"
        elif "email" in str(e).lower():
            return False, "Email already exists"
        else:
            return False, f"Database error: {e}"
    except Exception as e:
        return False, f"Error creating user: {e}"

# -------------------------------
# HEADER: Back + Title (EXACT SAME AS TREND PAGE)
# -------------------------------
header_container = st.container()
with header_container:
    col_back, col_title, col_spacer = st.columns([0.5, 4, 0.5])
    with col_back:
        if st.button("← ", key="back_to_dashboard", help="Return to Dashboard", type="secondary"):
            st.switch_page("pages/dashboard.py")
    with col_title:
        st.markdown("<h1>⚙️ Settings</h1>", unsafe_allow_html=True)
        st.markdown('<p class="original-subtitle">Customize your financial management experience</p>', unsafe_allow_html=True)
    with col_spacer:
        st.write("")

# -------------------------------
# Load Data Function (Currency-Aware)
# -------------------------------
@st.cache_data(ttl=300)
def load_data_with_currency(exchange_rate, user_id=None):
    try:
        conn = sqlite3.connect("finance.db")
        if user_id:
            df = pd.read_sql_query("SELECT * FROM transactions WHERE user_id = ?", conn, params=(user_id,))
        else:
            df = pd.read_sql_query("SELECT * FROM transactions", conn)
        conn.close()
        # Convert to display currency
        df['Amount_Display'] = pd.to_numeric(df['amount'], errors='coerce') * exchange_rate
        return df
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()

# Load data for current user
user_id = st.session_state.get("user_id")
df = load_data_with_currency(exchange_rate, user_id)

# -------------------------------
# SIDEBAR NAVIGATION (Role-based)
# -------------------------------
st.sidebar.markdown("### 🔧 Settings Sections")

# Admin gets extra sections
if user_role == "admin":
    section = st.sidebar.radio(
        "Go to:",
        ["Display", "Data", "Account", "Admin"],
        label_visibility="collapsed"
    )
else:
    section = st.sidebar.radio(
        "Go to:",
        ["Display", "Data", "Account"],
        label_visibility="collapsed"
    )
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.switch_page("app.py")

# -------------------------------
# DISPLAY SETTINGS (Currency Sync)
# -------------------------------
if section == "Display":
    st.subheader("🎨 Display Preferences")
    
    # Currency selector (SYNCED WITH DASHBOARD)
    current_currency = st.session_state.get("selected_currency", "MYR")
    selected_currency_input = st.selectbox(
        "Default Display Currency",
        options=currency_options,
        index=currency_options.index(current_currency) if current_currency in currency_options else 0,
        help="All amounts will be shown in this currency"
    )
    
    if st.button("Save Display Settings", type="primary"):
        # Update session state (SYNC WITH DASHBOARD)
        st.session_state["selected_currency"] = selected_currency_input
        st.success(f"✅ Display settings saved! Currency: {selected_currency_input}")
        st.rerun()  # Refresh to show new currency

# -------------------------------
# DATA SETTINGS (Currency-Aware Exports) - NO IMPORT SECTION
# -------------------------------
elif section == "Data":
    st.subheader("💾 Data Management")
    
    # Only show export options (removed import section)
    st.markdown("#### Export Data")
    
    # Export transactions in DISPLAY CURRENCY
    if st.button("Export All Transactions (CSV)", type="primary"):
        if not df.empty:
            # Make a copy to avoid side effects
            export_df = df.copy()
            
            # Replace the 'amount' column with the currency-converted values
            export_df['amount'] = export_df['Amount_Display']

            # Update the 'currency' column to reflect the display currency
            export_df['currency'] = selected_currency
            
            # Remove the helper column 'Amount_Display' (not needed in export)
            export_df = export_df.drop(columns=['Amount_Display'], errors='ignore')
            
            # Export ALL columns (no selection — full DataFrame)
            csv = export_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download CSV",
                csv,
                f"financial_data_{selected_currency}_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv",
                key='download-csv'
            )
        else:
            st.warning("No data to export.")
    
    # Export forecasts 
    if st.button("Export All Forecasts (ZIP)", type="primary"):

        forecast_dir = "income_expense_forecast"
        os.makedirs(forecast_dir, exist_ok=True)

        # Helper: Get files for currency
        def get_currency_files(currency):
            files = []
            for f in os.listdir(forecast_dir):
                if f.endswith((".csv", ".png", ".md")):
                    if currency == "MYR":
                        if not any(f"_{c}." in f for c in currency_options if c != "MYR"):
                            files.append(f)
                    else:
                        if f"_{currency}." in f:
                            files.append(f)
            return files

        if selected_currency == "MYR":
            myr_files = get_currency_files("MYR")
            
            first_time_marker = os.path.join(forecast_dir, ".myr_exported")
            if not os.path.exists(first_time_marker) and myr_files:
                st.info("✅ Exporting MYR forecasts.")
                existing_files = myr_files
                
                # Create marker so next time we check freshness
                with open(first_time_marker, "w") as f:
                    f.write("MYR forecasts have been exported at least once.")
            else:
                # Not first time → treat like other currencies (use 10-min rule)
                existing_files = myr_files
                fresh_files = False
                if existing_files:
                    latest = max((os.path.join(forecast_dir, f) for f in existing_files), key=os.path.getmtime)
                    if datetime.now() - datetime.fromtimestamp(os.path.getmtime(latest)) < timedelta(minutes=10):
                        fresh_files = True
                
                if not fresh_files:
                    existing_files = []  # Trigger regeneration below
                else:
                    st.info("✅ Using recent MYR forecasts.")
        else:
            # Consider files "fresh" if created in last 10 minutes
            existing_files = get_currency_files(selected_currency)
            fresh_files = False
            if existing_files:
                latest = max((os.path.join(forecast_dir, f) for f in existing_files), key=os.path.getmtime)
                if datetime.now() - datetime.fromtimestamp(os.path.getmtime(latest)) < timedelta(minutes=10):
                    fresh_files = True
            
            if not fresh_files:
                existing_files = []  # Trigger regeneration
            else:
                st.info(f"✅ Using recent {selected_currency} forecasts.")

        # Regenerate if needed
        if not existing_files:
            with st.spinner(f"🧠 Generating {selected_currency} forecasts... (up to 90 seconds)"):
                # Clean old files for this currency
                old_files = get_currency_files(selected_currency)
                for f in old_files:
                    try:
                        os.remove(os.path.join(forecast_dir, f))
                    except:
                        pass

                env = os.environ.copy()
                env["FORECAST_CURRENCY"] = selected_currency

                try:
                    result = subprocess.run(
                        [sys.executable, "financial_income_category_forecast.py"],
                        env=env,
                        cwd=os.getcwd(),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=90
                    )

                    if result.returncode != 0:
                        st.error("❌ Forecast generation failed.")
                        stderr_lines = result.stderr.strip().split('\n')[-5:]
                        st.code('\n'.join(stderr_lines))
                        st.stop()

                    time.sleep(1)
                    existing_files = get_currency_files(selected_currency)

                    if not existing_files:
                        st.error(f"❌ No {selected_currency} files created.")
                        st.stop()

                    st.success(f"✅ Fresh {selected_currency} forecasts ready!")

                except subprocess.TimeoutExpired:
                    st.error("⏱️ Timed out. Try again or reduce data.")
                    st.stop()
                except Exception as e:
                    st.error(f"💥 Error: {str(e)}")
                    st.stop()

        # Create zip
        if not existing_files:
            st.error("❌ No forecast files to export.")
            st.stop()

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in existing_files:
                zf.write(os.path.join(forecast_dir, f), f)

        buffer.seek(0)
        st.download_button(
            "📥 Download Forecasts",
            buffer,
            f"forecasts_{selected_currency}_{datetime.now().strftime('%Y%m%d')}.zip",
            "application/zip",
            key=f"dl_forecast_{selected_currency}_{int(time.time())}"
        )

# -------------------------------
# ACCOUNT SETTINGS
# -------------------------------
elif section == "Account":
    st.subheader("🔐 Account & Security")
    
    # Profile section
    st.markdown("#### 👤 Profile Information")

    # Auto-fetch real email if session lost it
    if "email" not in st.session_state or st.session_state.email in ["user@example.com", "", None]:
        try:
            conn = sqlite3.connect("finance.db")
            c = conn.cursor()
            c.execute("SELECT email FROM users WHERE username = ?", (st.session_state.username,))
            result = c.fetchone()
            conn.close()
            if result and result[0]:
                st.session_state.email = result[0]
        except:
            pass  # Silent fail — never breaks the app

    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("Username", value=st.session_state.get("username", "user123"), disabled=True)
    with col2:
        st.text_input("Email", value=st.session_state.get("email", "user@example.com"), disabled=True)
    with col3:
        st.text_input("Account Type", value=st.session_state.get("user_role", "user").title(), disabled=True)

    # Security section
    st.markdown("#### 🔒 Security Settings")
    
    # Change Password - NOW WORKS USING USERNAME ONLY!
    with st.expander("🔑 Change Password", expanded=False):
        st.markdown("Update your account password securely")
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password", help="Minimum 8 characters")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            submitted = st.form_submit_button("Update Password", type="primary")
            
            if submitted:
                if not all([current_password, new_password, confirm_password]):
                    st.error("❌ Please fill in all fields")
                elif new_password != confirm_password:
                    st.error("❌ New passwords do not match")
                elif len(new_password) < 8:
                    st.error("❌ Password must be at least 8 characters")
                else:
                    try:
                        import hashlib
                        conn = sqlite3.connect("finance.db")
                        c = conn.cursor()
                        
                        # Use username instead of user_id — 100% safe & working
                        current_hash = hashlib.sha256(current_password.encode()).hexdigest()
                        c.execute("SELECT password_hash FROM users WHERE username = ?", 
                                (st.session_state.username,))
                        stored = c.fetchone()
                        
                        if stored and stored[0] == current_hash:
                            new_hash = hashlib.sha256(new_password.encode()).hexdigest()
                            c.execute("UPDATE users SET password_hash = ? WHERE username = ?", 
                                    (new_hash, st.session_state.username))
                            conn.commit()
                            conn.close()
                            st.success("✅ Password changed successfully!")
                            st.balloons()
                        else:
                            st.error("❌ Current password is incorrect")
                            conn.close()
                    except Exception as e:
                        st.error(f"Error: {e}")
    
# -------------------------------
# ADMIN SETTINGS (Admin-only section)
# -------------------------------
elif section == "Admin" and user_role == "admin":
    st.subheader("👑 Admin Settings")
    
    # User management
    st.markdown("#### 👥 User Management")

    # Toggle button: Show/Hide Users
    if 'show_users' not in st.session_state:
        st.session_state.show_users = False

    if st.button("View All Users", type="secondary"):
        st.session_state.show_users = not st.session_state.show_users  # Toggle!

    if st.session_state.show_users:
        users_raw = get_all_users()
        current_user_email = st.session_state.get("email")

        if not users_raw:
            st.info("📭 No users found in the database.")
        else:
            # Prepare clean DataFrame
            df_users = pd.DataFrame(users_raw, columns=["ID", "Username", "Email", "Role", "Created At"])
            df_users = df_users[["Username", "Email", "Role", "Created At"]]
            df_users.rename(columns={"Created At": "Created"}, inplace=True)

            # Display as clean table
            st.dataframe(
                df_users,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Username": st.column_config.TextColumn("Username", width="medium"),
                    "Email": st.column_config.TextColumn("Email", width="medium"),
                    "Role": st.column_config.TextColumn("Role", width="small"),
                    "Created": st.column_config.TextColumn("Created", width="small"),
                }
            )
    
    # Create New User - EXPANDABLE SECTION
    with st.expander("➕ Create New User", expanded=False):
        st.markdown("#### Create a new user account")
        with st.form("create_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username*", help="Unique username (3-20 characters)")
                new_email = st.text_input("Email*", help="Valid email address")
            with col2:
                new_password = st.text_input("Password*", type="password", help="At least 6 characters")
                new_role = st.selectbox("Role", ["user", "admin"], help="User permissions level")
            
            st.markdown("<small>* Required fields</small>", unsafe_allow_html=True)
            create_submitted = st.form_submit_button("Create User", type="primary")
            
            if create_submitted:
                if not all([new_username, new_email, new_password]):
                    st.error("❌ Please fill in all required fields")
                elif len(new_username) < 3:
                    st.error("❌ Username must be at least 3 characters")
                elif len(new_password) < 6:
                    st.error("❌ Password must be at least 6 characters")
                else:
                    success, message = create_user(new_username, new_email, new_password, new_role)
                    if success:
                        st.success(f"✅ {message}")
                        st.balloons()
                    else:
                        st.error(f"❌ {message}")
    
    # Account Deletion (Admin-only) - REDESIGNED
    st.markdown("#### 🗑️ Account Deletion")
    
    # Warning card
    st.warning("⚠️ **Delete User Account**")
    # Two-step deletion process
    col1, col2 = st.columns([3, 1])
    
    with col1:
        admin_delete_email = st.text_input(
            "Enter user email to delete", 
            placeholder="user@example.com",
            help="Enter the exact email address of the user you want to delete"
        )
    
    with col2:
        st.write("")  # Spacer
        st.write("")  # Spacer
        delete_disabled = not admin_delete_email or admin_delete_email == st.session_state.get("email")
        if st.button("🔍 Verify", type="secondary", disabled=delete_disabled, key="verify_delete"):
            st.session_state.delete_verified = admin_delete_email
            st.session_state.delete_confirmed = False
    
    # Show verification and confirmation
    if "delete_verified" in st.session_state and st.session_state.delete_verified == admin_delete_email:
        # Verify user exists
        try:
            conn = sqlite3.connect("finance.db")
            cursor = conn.cursor()
            cursor.execute('SELECT username, role FROM users WHERE email = ?', (admin_delete_email,))
            user_info = cursor.fetchone()
            conn.close()
            
            if user_info:
                username, role = user_info
                if username == "admin":
                    st.error("❌ Cannot delete admin account")
                    if "delete_verified" in st.session_state:
                        del st.session_state.delete_verified
                else:
                    st.success(f"✅ User found: **{username}** ({role.title()})")
                    st.info(f"Email: {admin_delete_email}")
                    
                    # Confirmation button
                    if st.button("⚠️ CONFIRM DELETION", type="primary", key="confirm_delete"):
                        st.session_state.delete_confirmed = True
                    
                    # Final deletion
                    if st.session_state.get("delete_confirmed"):
                        if st.button("🗑️ FINAL DELETE - CANNOT BE UNDONE", type="primary", key="final_delete"):
                            success, message = delete_user_by_email(admin_delete_email)
                            if success:
                                st.success(f"✅ {message}")
                                # Clear session state
                                if "delete_verified" in st.session_state:
                                    del st.session_state.delete_verified
                                if "delete_confirmed" in st.session_state:
                                    del st.session_state.delete_confirmed
                                st.rerun()
                            else:
                                st.error(f"❌ {message}")
            else:
                st.error("❌ User not found with this email address")
                if "delete_verified" in st.session_state:
                    del st.session_state.delete_verified
                    
        except Exception as e:
            st.error(f"❌ Database error: {e}")
            if "delete_verified" in st.session_state:
                del st.session_state.delete_verified

# -------------------------------
# FOOTER (SAME AS TREND PAGE)
# -------------------------------
st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown(
    f"<p style='text-align:center; font-size:0.9em; color:#c2185b;'>"
    f" © 2025 AI-Integrated Financial Management Web Application • Currency: {selected_currency} • Role: {user_role.title()}"
    "</p>",
    unsafe_allow_html=True
)
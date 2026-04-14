import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import hashlib
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import io
import base64
from PIL import Image
import matplotlib.pyplot as plt
from fpdf import FPDF
import json
import random

# ---------- Database Setup ----------
def init_db():
    conn = sqlite3.connect('gym_portal.db')
    c = conn.cursor()
    
    # Members table with new fields
    c.execute('''CREATE TABLE IF NOT EXISTS members
                 (username TEXT PRIMARY KEY,
                  password TEXT,
                  name TEXT,
                  email TEXT,
                  diet_plan TEXT,
                  role TEXT,
                  profile_pic BLOB,
                  weight REAL,
                  height REAL,
                  goal TEXT,
                  join_date TEXT)''')
    
    # Activity logs
    c.execute('''CREATE TABLE IF NOT EXISTS activity
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT,
                  date TEXT,
                  exercise TEXT,
                  duration_minutes INTEGER,
                  calories_burned INTEGER,
                  workout_type TEXT)''')
    
    # Attendance tracking
    c.execute('''CREATE TABLE IF NOT EXISTS attendance
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT,
                  check_in TEXT,
                  check_out TEXT,
                  date TEXT)''')
    
    # Goals table
    c.execute('''CREATE TABLE IF NOT EXISTS goals
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT,
                  goal_type TEXT,
                  target_value REAL,
                  current_value REAL,
                  start_date TEXT,
                  target_date TEXT,
                  status TEXT)''')
    
    # Trainer assignments
    c.execute('''CREATE TABLE IF NOT EXISTS trainer_assignments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  trainer_username TEXT,
                  member_username TEXT,
                  assignment_date TEXT)''')
    
    # Workout library
    c.execute('''CREATE TABLE IF NOT EXISTS workout_library
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  exercise_name TEXT,
                  category TEXT,
                  default_calories_per_minute REAL,
                  instructions TEXT)''')
    
    # Insert demo data
    c.execute("SELECT * FROM members WHERE username='john'")
    if not c.fetchone():
        # Members
        c.execute("INSERT INTO members VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                  ('john', hashlib.sha256('pass123'.encode()).hexdigest(),
                   'John Doe', 'john@email.com', 'High protein, low carb - 2000 kcal', 'member', None, 85.5, 180, 'Weight Loss', '2024-01-15'))
        c.execute("INSERT INTO members VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                  ('jane', hashlib.sha256('pass456'.encode()).hexdigest(),
                   'Jane Smith', 'jane@email.com', 'Vegetarian high protein - 1800 kcal', 'member', None, 65.2, 165, 'Muscle Gain', '2024-02-01'))
        
        # Trainer
        c.execute("INSERT INTO members VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                  ('trainer1', hashlib.sha256('train123'.encode()).hexdigest(),
                   'Mike Johnson', 'mike@gym.com', '', 'trainer', None, 90.0, 185, '', '2024-01-01'))
        
        # Admin
        c.execute("INSERT INTO members VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                  ('admin', hashlib.sha256('admin123'.encode()).hexdigest(),
                   'Admin User', 'admin@gym.com', '', 'admin', None, None, None, '', '2024-01-01'))
        
        # Trainer assignments
        c.execute("INSERT INTO trainer_assignments (trainer_username, member_username, assignment_date) VALUES (?,?,?)",
                  ('trainer1', 'john', '2024-02-01'))
        c.execute("INSERT INTO trainer_assignments (trainer_username, member_username, assignment_date) VALUES (?,?,?)",
                  ('trainer1', 'jane', '2024-02-01'))
        
        # Workout library
        workouts = [
            ('Running', 'Cardio', 10, 'Treadmill or outdoor running'),
            ('Cycling', 'Cardio', 8, 'Stationary bike or outdoor cycling'),
            ('Swimming', 'Cardio', 12, 'Lap swimming'),
            ('Bench Press', 'Strength', 5, 'Chest exercise with barbell'),
            ('Squats', 'Strength', 6, 'Leg exercise with barbell'),
            ('Deadlifts', 'Strength', 7, 'Full body compound exercise'),
            ('Yoga', 'Flexibility', 4, 'Various yoga poses'),
            ('HIIT', 'Cardio', 15, 'High Intensity Interval Training')
        ]
        for w in workouts:
            c.execute("INSERT INTO workout_library (exercise_name, category, default_calories_per_minute, instructions) VALUES (?,?,?,?)", w)
    
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect('gym_portal.db')

# ---------- Helper Functions ----------
def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def verify_password(pwd, hashed):
    return hash_password(pwd) == hashed

def authenticate(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT password, role FROM members WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    if row and verify_password(password, row[0]):
        return row[1]
    return None

def send_email(to_email, subject, body, attachment=None):
    """Send email (configure with your SMTP settings)"""
    try:
        # For demo, we'll just show a preview
        st.info(f"📧 Email would be sent to {to_email}\nSubject: {subject}\nBody: {body[:200]}...")
        return True
    except Exception as e:
        st.error(f"Email error: {e}")
        return False

def create_pdf_report(username, data_type):
    """Generate PDF report"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Gym Report for {username}", ln=1, align='C')
    
    if data_type == "activity":
        pdf.cell(200, 10, txt="Activity Log", ln=1)
        df = get_member_activity(username)
        if not df.empty:
            for idx, row in df.iterrows():
                pdf.cell(200, 10, txt=f"{row['date']}: {row['exercise']} - {row['calories_burned']} cal", ln=1)
    
    return pdf.output(dest='S').encode('latin1')

def get_workout_library():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM workout_library", conn)
    conn.close()
    return df

# ---------- Member Functions ----------
def get_member_diet(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT diet_plan FROM members WHERE username=?", (username,))
    diet = c.fetchone()[0]
    conn.close()
    return diet

def add_activity(username, exercise, duration, calories, workout_type):
    conn = get_db_connection()
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("INSERT INTO activity (username, date, exercise, duration_minutes, calories_burned, workout_type) VALUES (?,?,?,?,?,?)",
              (username, today, exercise, duration, calories, workout_type))
    conn.commit()
    conn.close()

def get_member_activity(username):
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT date, exercise, duration_minutes, calories_burned, workout_type FROM activity WHERE username=? ORDER BY date DESC", conn, params=(username,))
    conn.close()
    return df

def check_in_out(username, action):
    conn = get_db_connection()
    c = conn.cursor()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    
    if action == "check_in":
        c.execute("INSERT INTO attendance (username, check_in, date) VALUES (?,?,?)", (username, time_str, today))
        st.success(f"✅ Checked in at {time_str}")
    else:
        c.execute("UPDATE attendance SET check_out=? WHERE username=? AND date=? AND check_out IS NULL", 
                  (time_str, username, today))
        st.success(f"✅ Checked out at {time_str}")
    
    conn.commit()
    conn.close()

def get_attendance(username):
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT date, check_in, check_out FROM attendance WHERE username=? ORDER BY date DESC", conn, params=(username,))
    conn.close()
    return df

def set_goal(username, goal_type, target, target_date):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT weight FROM members WHERE username=?", (username,))
    current_weight = c.fetchone()[0]
    
    current_value = current_weight if goal_type == "Weight Loss" or goal_type == "Weight Gain" else 0
    
    c.execute('''INSERT INTO goals (username, goal_type, target_value, current_value, start_date, target_date, status)
                 VALUES (?,?,?,?,?,?,?)''',
              (username, goal_type, target, current_value, datetime.now().strftime("%Y-%m-%d"), target_date, 'Active'))
    conn.commit()
    conn.close()

def get_goals(username):
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM goals WHERE username=? ORDER BY start_date DESC", conn, params=(username,))
    conn.close()
    return df

def update_goal_progress(username, goal_id, current_value):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE goals SET current_value=? WHERE id=? AND username=?", (current_value, goal_id, username))
    conn.commit()
    conn.close()

def get_member_info(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, email, weight, height, goal, join_date FROM members WHERE username=?", (username,))
    info = c.fetchone()
    conn.close()
    return info

def update_profile(username, weight=None, height=None, diet_plan=None):
    conn = get_db_connection()
    c = conn.cursor()
    updates = []
    params = []
    if weight:
        updates.append("weight=?")
        params.append(weight)
    if height:
        updates.append("height=?")
        params.append(height)
    if diet_plan:
        updates.append("diet_plan=?")
        params.append(diet_plan)
    
    if updates:
        params.append(username)
        c.execute(f"UPDATE members SET {', '.join(updates)} WHERE username=?", params)
        conn.commit()
    conn.close()

def save_profile_pic(username, image_file):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE members SET profile_pic=? WHERE username=?", (image_file.read(), username))
    conn.commit()
    conn.close()

def get_profile_pic(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT profile_pic FROM members WHERE username=?", (username,))
    pic = c.fetchone()[0]
    conn.close()
    return pic

# ---------- Trainer Functions ----------
def get_trainer_members(trainer_username):
    conn = get_db_connection()
    df = pd.read_sql_query('''SELECT m.username, m.name, m.email, m.weight, m.height, m.goal 
                              FROM members m 
                              JOIN trainer_assignments t ON m.username=t.member_username 
                              WHERE t.trainer_username=?''', conn, params=(trainer_username,))
    conn.close()
    return df

def update_member_diet(trainer_username, member_username, diet_plan):
    conn = get_db_connection()
    c = conn.cursor()
    # Verify trainer has access to this member
    c.execute("SELECT * FROM trainer_assignments WHERE trainer_username=? AND member_username=?", 
              (trainer_username, member_username))
    if c.fetchone():
        c.execute("UPDATE members SET diet_plan=? WHERE username=?", (diet_plan, member_username))
        conn.commit()
        st.success(f"Diet plan updated for {member_username}")
    else:
        st.error("You don't have access to this member")
    conn.close()

# ---------- Admin Functions ----------
def get_all_members():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT username, name, email, role, join_date FROM members", conn)
    conn.close()
    return df

def get_all_activity():
    conn = get_db_connection()
    df = pd.read_sql_query('''SELECT a.username, m.name, a.date, a.exercise, a.duration_minutes, a.calories_burned 
                              FROM activity a JOIN members m ON a.username=m.username ORDER BY a.date DESC''', conn)
    conn.close()
    return df

def reset_member_password(username, new_password):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE members SET password=? WHERE username=?", (hash_password(new_password), username))
    conn.commit()
    conn.close()

def register_member(username, password, name, email, role='member'):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO members (username, password, name, email, role, join_date) VALUES (?,?,?,?,?,?)",
                  (username, hash_password(password), name, email, role, datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def assign_trainer(member_username, trainer_username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO trainer_assignments (trainer_username, member_username, assignment_date) VALUES (?,?,?)",
              (trainer_username, member_username, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()

def get_gym_stats():
    conn = get_db_connection()
    
    # Total members
    members = pd.read_sql_query("SELECT COUNT(*) as count FROM members WHERE role='member'", conn).iloc[0]['count']
    
    # Today's attendance
    today = datetime.now().strftime("%Y-%m-%d")
    attendance_today = pd.read_sql_query("SELECT COUNT(DISTINCT username) as count FROM attendance WHERE date=?", conn, params=(today,)).iloc[0]['count']
    
    # Active goals
    active_goals = pd.read_sql_query("SELECT COUNT(*) as count FROM goals WHERE status='Active'", conn).iloc[0]['count']
    
    conn.close()
    return members, attendance_today, active_goals

# ---------- Streamlit App ----------
st.set_page_config(page_title="Complete Gym Management System", layout="wide")

# Custom CSS
st.markdown("""
    <style>
    .stButton > button {
        width: 100%;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# Session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

# Login / Signup
if not st.session_state.logged_in:
    st.title("💪 Complete Gym Management System")
    
    tab_login, tab_signup = st.tabs(["Login", "Sign Up"])
    
    with tab_login:
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                role = authenticate(username, password)
                if role:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.role = role
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        with col2:
            st.markdown("**Demo Credentials:**")
            st.write("Member: `john` / `pass123`")
            st.write("Trainer: `trainer1` / `train123`")
            st.write("Admin: `admin` / `admin123`")
    
    with tab_signup:
        st.subheader("New Member Registration")
        new_username = st.text_input("Choose Username")
        new_password = st.text_input("Choose Password", type="password")
        new_name = st.text_input("Full Name")
        new_email = st.text_input("Email")
        
        if st.button("Register"):
            if register_member(new_username, new_password, new_name, new_email):
                st.success("Registration successful! Please login.")
            else:
                st.error("Username already exists")

else:
    # Sidebar
    with st.sidebar:
        st.image("https://img.icons8.com/ios-filled/100/000000/gym.png", width=80)
        st.write(f"**{st.session_state.username}**")
        st.write(f"Role: {st.session_state.role.upper()}")
        st.markdown("---")
        
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.rerun()
    
    # ---------- MEMBER DASHBOARD ----------
    if st.session_state.role == "member":
        st.title(f"Welcome Back, {st.session_state.username}! 🏋️")
        
        # Stats Row
        col1, col2, col3, col4 = st.columns(4)
        member_info = get_member_info(st.session_state.username)
        df_activity = get_member_activity(st.session_state.username)
        
        with col1:
            total_calories = df_activity['calories_burned'].sum() if not df_activity.empty else 0
            st.metric("Total Calories Burned", f"{total_calories:,}")
        with col2:
            workouts = len(df_activity) if not df_activity.empty else 0
            st.metric("Total Workouts", workouts)
        with col3:
            attendance = get_attendance(st.session_state.username)
            days = len(attendance) if not attendance.empty else 0
            st.metric("Days Visited", days)
        with col4:
            if member_info[2]:
                st.metric("Current Weight", f"{member_info[2]} kg")
        
        # Main Tabs
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "📋 Profile", "🍽️ Diet Plan", "📝 Log Workout", "📊 Progress", 
            "✅ Attendance", "🎯 Goals", "📧 Reports"
        ])
        
        with tab1:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.subheader("Profile Picture")
                uploaded_file = st.file_uploader("Upload photo", type=['jpg', 'png', 'jpeg'])
                if uploaded_file:
                    save_profile_pic(st.session_state.username, uploaded_file)
                    st.success("Profile picture updated!")
                
                # Display profile pic
                pic = get_profile_pic(st.session_state.username)
                if pic:
                    st.image(pic, width=200)
                else:
                    st.info("No profile picture")
            
            with col2:
                st.subheader("Personal Information")
                name, email, weight, height, goal, join_date = member_info
                st.write(f"**Name:** {name}")
                st.write(f"**Email:** {email}")
                st.write(f"**Height:** {height} cm" if height else "**Height:** Not set")
                st.write(f"**Goal:** {goal}" if goal else "**Goal:** Not set")
                st.write(f"**Member Since:** {join_date}")
                
                st.subheader("Update Information")
                new_weight = st.number_input("Weight (kg)", value=float(weight) if weight else 0.0, step=0.5)
                new_height = st.number_input("Height (cm)", value=float(height) if height else 0.0, step=1.0)
                if st.button("Update Profile"):
                    update_profile(st.session_state.username, new_weight, new_height)
                    st.success("Profile updated!")
        
        with tab2:
            diet = get_member_diet(st.session_state.username)
            st.info(diet)
            
            # Diet suggestions based on goal
            if member_info[4] == "Weight Loss":
                st.markdown("""
                ### 💡 Weight Loss Tips:
                - Eat protein with every meal
                - Reduce processed carbs
                - Drink 2-3L water daily
                - Sleep 7-8 hours
                """)
            elif member_info[4] == "Muscle Gain":
                st.markdown("""
                ### 💪 Muscle Gain Tips:
                - Increase protein intake to 1.6-2.2g/kg body weight
                - Eat in calorie surplus (+300-500 calories)
                - Focus on compound exercises
                - Get adequate rest between workouts
                """)
        
        with tab3:
            st.subheader("Log Your Workout")
            workout_lib = get_workout_library()
            
            col1, col2 = st.columns(2)
            with col1:
                exercise_type = st.selectbox("Workout Category", workout_lib['category'].unique())
                exercises = workout_lib[workout_lib['category'] == exercise_type]['exercise_name'].tolist()
                exercise = st.selectbox("Exercise", exercises)
                
                # Get default calories
                default_cal = workout_lib[workout_lib['exercise_name'] == exercise]['default_calories_per_minute'].values[0]
                
            with col2:
                duration = st.number_input("Duration (minutes)", min_value=1, step=5)
                calories = st.number_input("Calories Burned", value=int(duration * default_cal), step=10)
                workout_type = st.selectbox("Workout Intensity", ["Light", "Moderate", "Intense"])
            
            if st.button("Save Workout", use_container_width=True):
                add_activity(st.session_state.username, exercise, duration, calories, workout_type)
                st.balloons()
                st.success(f"Great workout! You burned {calories} calories!")
                
                # Check and update goals
                goals_df = get_goals(st.session_state.username)
                if not goals_df.empty:
                    st.info("Keep going towards your goals! 🎯")
        
        with tab4:
            st.subheader("Your Progress Charts")
            df_activity = get_member_activity(st.session_state.username)
            
            if not df_activity.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Calories trend
                    fig1 = px.line(df_activity, x="date", y="calories_burned", 
                                   title="Calories Burned Over Time", markers=True)
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    # Workout distribution
                    workout_counts = df_activity['exercise'].value_counts()
                    fig2 = px.pie(values=workout_counts.values, names=workout_counts.index, 
                                  title="Workout Distribution")
                    st.plotly_chart(fig2, use_container_width=True)
                
                # Weekly summary
                df_activity['date'] = pd.to_datetime(df_activity['date'])
                weekly = df_activity.groupby(df_activity['date'].dt.isocalendar().week)['calories_burned'].sum().reset_index()
                fig3 = px.bar(weekly, x='date', y='calories_burned', title="Weekly Calories Burned")
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("No activity data yet. Start logging workouts to see your progress!")
        
        with tab5:
            st.subheader("Attendance Tracking")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ Check In", use_container_width=True):
                    check_in_out(st.session_state.username, "check_in")
            
            with col2:
                if st.button("❌ Check Out", use_container_width=True):
                    check_in_out(st.session_state.username, "check_out")
            
            # Attendance history
            attendance_df = get_attendance(st.session_state.username)
            if not attendance_df.empty:
                st.subheader("Attendance History")
                st.dataframe(attendance_df, use_container_width=True)
                
                # Attendance calendar view
                attendance_df['date'] = pd.to_datetime(attendance_df['date'])
                attendance_by_month = attendance_df.groupby(attendance_df['date'].dt.strftime('%B'))['date'].count()
                fig = px.bar(x=attendance_by_month.index, y=attendance_by_month.values, 
                            title="Monthly Attendance")
                st.plotly_chart(fig, use_container_width=True)
        
        with tab6:
            st.subheader("Your Fitness Goals")
            goals_df = get_goals(st.session_state.username)
            
            # Set new goal
            with st.expander("Set New Goal"):
                goal_type = st.selectbox("Goal Type", ["Weight Loss", "Muscle Gain", "Workout Frequency", "Strength Target"])
                target = st.number_input("Target Value", min_value=0.0, step=1.0)
                if goal_type == "Weight Loss":
                    st.write("Target: kg to lose")
                elif goal_type == "Muscle Gain":
                    st.write("Target: kg to gain")
                target_date = st.date_input("Target Date")
                
                if st.button("Set Goal"):
                    set_goal(st.session_state.username, goal_type, target, target_date.strftime("%Y-%m-%d"))
                    st.success("Goal set successfully!")
            
            # Display existing goals
            if not goals_df.empty:
                for idx, goal in goals_df.iterrows():
                    with st.container():
                        col1, col2, col3 = st.columns([2, 2, 1])
                        with col1:
                            st.metric(goal['goal_type'], f"{goal['current_value']} / {goal['target_value']}")
                        with col2:
                            progress = (goal['current_value'] / goal['target_value']) * 100 if goal['target_value'] > 0 else 0
                            st.progress(min(progress/100, 1.0))
                        with col3:
                            if st.button(f"Update", key=f"update_{idx}"):
                                new_value = st.number_input("Current value", value=float(goal['current_value']))
                                if st.button("Save Update"):
                                    update_goal_progress(st.session_state.username, goal['id'], new_value)
                                    st.rerun()
                        st.markdown("---")
        
        with tab7:
            st.subheader("Generate Reports")
            report_type = st.selectbox("Report Type", ["Activity Summary", "Progress Report", "Attendance Report"])
            
            if st.button("Generate PDF Report"):
                pdf_data = create_pdf_report(st.session_state.username, "activity")
                st.download_button(
                    label="Download PDF Report",
                    data=pdf_data,
                    file_name=f"{st.session_state.username}_report.pdf",
                    mime="application/pdf"
                )
            
            # Email report
            if st.button("Email Report to Myself"):
                member_email = get_member_info(st.session_state.username)[1]
                if member_email:
                    send_email(member_email, "Your Gym Progress Report", 
                              f"Here's your progress report for {st.session_state.username}")
                    st.success("Report sent to your email!")
                else:
                    st.error("No email address found in profile")
    
    # ---------- TRAINER DASHBOARD ----------
    elif st.session_state.role == "trainer":
        st.title(f"Trainer Dashboard - {st.session_state.username} 👨‍🏫")
        
        tab1, tab2, tab3 = st.tabs(["👥 My Members", "📋 Assign Diet Plans", "📊 Member Progress"])
        
        with tab1:
            st.subheader("Assigned Members")
            members_df = get_trainer_members(st.session_state.username)
            if not members_df.empty:
                st.dataframe(members_df, use_container_width=True)
                
                for _, member in members_df.iterrows():
                    with st.expander(f"{member['name']} ({member['username']})"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Email:** {member['email']}")
                            st.write(f"**Weight:** {member['weight']} kg" if member['weight'] else "Weight: Not set")
                        with col2:
                            st.write(f"**Height:** {member['height']} cm" if member['height'] else "Height: Not set")
                            st.write(f"**Goal:** {member['goal']}" if member['goal'] else "Goal: Not set")
            else:
                st.info("No members assigned yet")
        
        with tab2:
            st.subheader("Update Member Diet Plans")
            members_df = get_trainer_members(st.session_state.username)
            if not members_df.empty:
                selected_member = st.selectbox("Select Member", members_df['username'].tolist())
                current_diet = get_member_diet(selected_member)
                st.text_area("Current Diet Plan", current_diet, height=100)
                
                new_diet = st.text_area("New Diet Plan", height=200,
                                       placeholder="Example:\nBreakfast: ...\nLunch: ...\nDinner: ...\nSnacks: ...")
                
                if st.button("Update Diet Plan"):
                    update_member_diet(st.session_state.username, selected_member, new_diet)
                    st.success(f"Diet plan updated for {selected_member}")
        
        with tab3:
            st.subheader("Member Progress Tracking")
            members_df = get_trainer_members(st.session_state.username)
            if not members_df.empty:
                selected_member = st.selectbox("Select Member to View Progress", members_df['username'].tolist(), key="progress_select")
                
                member_activity = get_member_activity(selected_member)
                if not member_activity.empty:
                    fig = px.line(member_activity, x="date", y="calories_burned", 
                                 title=f"{selected_member} - Calories Burned Over Time", markers=True)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Weekly summary
                    member_activity['date'] = pd.to_datetime(member_activity['date'])
                    weekly_stats = member_activity.groupby(member_activity['date'].dt.isocalendar().week).agg({
                        'calories_burned': 'sum',
                        'duration_minutes': 'sum'
                    }).reset_index()
                    st.dataframe(weekly_stats, use_container_width=True)
                else:
                    st.info("No activity data for this member")
    
    # ---------- ADMIN DASHBOARD ----------
    elif st.session_state.role == "admin":
        st.title("Admin Dashboard - Complete Gym Overview 👑")
        
        # KPI Metrics
        total_members, today_attendance, active_goals = get_gym_stats()
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Members", total_members)
        with col2:
            st.metric("Today's Attendance", today_attendance)
        with col3:
            st.metric("Active Goals", active_goals)
        with col4:
            all_activity = get_all_activity()
            total_calories = all_activity['calories_burned'].sum() if not all_activity.empty else 0
            st.metric("Total Gym Calories", f"{total_calories:,}")
        
        # Main Tabs
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "👥 Members", "📊 Analytics", "🔐 User Management", 
            "👨‍🏫 Trainer Assignment", "📧 Bulk Actions", "⚙️ Settings"
        ])
        
        with tab1:
            st.subheader("All Members")
            members_df = get_all_members()
            st.dataframe(members_df, use_container_width=True)
            
            st.subheader("Recent Activity Log")
            all_activity = get_all_activity()
            if not all_activity.empty:
                st.dataframe(all_activity.head(20), use_container_width=True)
            else:
                st.info("No activity data")
        
        with tab2:
            st.subheader("Gym Analytics")
            all_activity = get_all_activity()
            
            if not all_activity.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Total calories per member
                    member_calories = all_activity.groupby("name")["calories_burned"].sum().reset_index()
                    fig = px.bar(member_calories, x="name", y="calories_burned", 
                                title="Total Calories Burned by Member",
                                color="name", text_auto=True)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Daily gym total
                    daily_total = all_activity.groupby("date")["calories_burned"].sum().reset_index()
                    fig2 = px.line(daily_total, x="date", y="calories_burned", 
                                  title="Gym Total Calories per Day", markers=True)
                    st.plotly_chart(fig2, use_container_width=True)
                
                # Most popular exercises
                exercise_counts = all_activity['exercise'].value_counts().head(10)
                fig3 = px.bar(x=exercise_counts.index, y=exercise_counts.values, 
                             title="Most Popular Exercises")
                st.plotly_chart(fig3, use_container_width=True)
                
                # Member comparison
                st.subheader("Member Comparison")
                selected_members = st.multiselect("Select members to compare", members_df['username'].tolist())
                if selected_members:
                    member_data = all_activity[all_activity['username'].isin(selected_members)]
                    member_summary = member_data.groupby('username').agg({
                        'calories_burned': 'sum',
                        'duration_minutes': 'sum'
                    }).reset_index()
                    st.dataframe(member_summary, use_container_width=True)
            else:
                st.info("No activity data available")
        
        with tab3:
            st.subheader("User Management")
            
            # Add new member
            with st.expander("➕ Add New Member"):
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
                new_name = st.text_input("Full Name")
                new_email = st.text_input("Email")
                new_role = st.selectbox("Role", ["member", "trainer"])
                
                if st.button("Add Member"):
                    if register_member(new_username, new_password, new_name, new_email, new_role):
                        st.success(f"Member {new_username} added successfully!")
                    else:
                        st.error("Username already exists")
            
            # Reset password
            with st.expander("🔑 Reset Member Password"):
                members_list = get_all_members()['username'].tolist()
                if members_list:
                    selected_member = st.selectbox("Select Member", members_list)
                    new_pass = st.text_input("New Password", type="password")
                    if st.button("Reset Password"):
                        if new_pass:
                            reset_member_password(selected_member, new_pass)
                            st.success(f"Password for {selected_member} reset successfully")
        
        with tab4:
            st.subheader("Trainer Assignment")
            
            col1, col2 = st.columns(2)
            with col1:
                trainers = get_all_members()[get_all_members()['role'] == 'trainer']['username'].tolist()
                if trainers:
                    selected_trainer = st.selectbox("Select Trainer", trainers)
                else:
                    st.warning("No trainers available")
                    selected_trainer = None
            
            with col2:
                members_without_trainer = get_all_members()[
                    (get_all_members()['role'] == 'member') & 
                    (~get_all_members()['username'].isin(pd.read_sql_query("SELECT member_username FROM trainer_assignments", get_db_connection())['member_username'].tolist() if not pd.read_sql_query("SELECT member_username FROM trainer_assignments", get_db_connection()).empty else []))
                ]['username'].tolist()
                
                if members_without_trainer:
                    selected_member = st.selectbox("Select Member", members_without_trainer)
                else:
                    st.info("All members have trainers assigned")
                    selected_member = None
            
            if selected_trainer and selected_member and st.button("Assign Trainer"):
                assign_trainer(selected_member, selected_trainer)
                st.success(f"Assigned {selected_member} to trainer {selected_trainer}")
            
            # View current assignments
            st.subheader("Current Assignments")
            assignments = pd.read_sql_query('''SELECT t.trainer_username, m1.name as trainer_name, 
                                                     t.member_username, m2.name as member_name
                                              FROM trainer_assignments t
                                              JOIN members m1 ON t.trainer_username = m1.username
                                              JOIN members m2 ON t.member_username = m2.username''', 
                                           get_db_connection())
            if not assignments.empty:
                st.dataframe(assignments, use_container_width=True)
        
        with tab5:
            st.subheader("Bulk Actions")
            
            # Send email to all members
            if st.button("📧 Send Newsletter to All Members"):
                all_members = get_all_members()[get_all_members()['role'] == 'member']
                for _, member in all_members.iterrows():
                    if member['email']:
                        send_email(member['email'], "Gym Newsletter", 
                                  "Check out our new classes and offers!")
                st.success(f"Newsletter sent to {len(all_members)} members!")
            
            # Export data
            st.subheader("Export Data")
            export_type = st.selectbox("Select Data to Export", ["All Members", "Activity Logs", "Attendance Records"])
            
            if st.button("Export to CSV"):
                if export_type == "All Members":
                    data = get_all_members()
                elif export_type == "Activity Logs":
                    data = get_all_activity()
                else:
                    data = pd.read_sql_query("SELECT * FROM attendance", get_db_connection())
                
                csv = data.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"{export_type.lower().replace(' ', '_')}.csv",
                    mime="text/csv"
                )
        
        with tab6:
            st.subheader("System Settings")
            
            # Workout library management
            st.write("### Workout Library")
            workout_lib = get_workout_library()
            st.dataframe(workout_lib, use_container_width=True)
            
            # Add new workout
            with st.expander("➕ Add New Workout"):
                new_exercise = st.text_input("Exercise Name")
                new_category = st.selectbox("Category", ["Cardio", "Strength", "Flexibility", "HIIT"])
                new_calories = st.number_input("Calories per minute", min_value=1.0, step=0.5)
                new_instructions = st.text_area("Instructions")
                
                if st.button("Add Workout"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO workout_library (exercise_name, category, default_calories_per_minute, instructions) VALUES (?,?,?,?)",
                             (new_exercise, new_category, new_calories, new_instructions))
                    conn.commit()
                    conn.close()
                    st.success("Workout added to library!")
                    st.rerun()

st.markdown("---")
st.markdown("💪 *Complete Gym Management System - Track, Train, Transform!*")

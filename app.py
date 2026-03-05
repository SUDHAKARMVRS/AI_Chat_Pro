import streamlit as st
import psycopg2
import bcrypt
import requests
import json
import re
import time
from datetime import datetime

st.set_page_config(page_title="AI Chat Pro", page_icon="🤖", layout="wide")

# ---------------- STYLE ----------------

st.markdown("""
<style>

.stApp{
background: linear-gradient(135deg,#0f2027,#203a43,#2c5364);
color:white;
}

[data-testid="stChatMessage"]:has([aria-label="user"]){
background: linear-gradient(90deg,#0072ff,#00c6ff);
border-radius:15px;
padding:10px;
}

[data-testid="stChatMessage"]:has([aria-label="assistant"]){
background: rgba(255,255,255,0.08);
border-radius:15px;
padding:10px;
}

code{
background:#0d1117;
color:#00ffcc;
}

</style>
""", unsafe_allow_html=True)

# ---------------- TITLE ----------------

st.title("🤖 AI Chat Pro")

# ---------------- DATABASE ----------------

def get_connection():
    return psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="Nadhi@2508",
        host="localhost",
        port="5432"
    )

# ---------------- PASSWORD ----------------

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------------- USER AUTH ----------------

def register_user(username,password):

    conn=get_connection()
    cur=conn.cursor()

    try:
        cur.execute(
        "INSERT INTO users(username,password) VALUES(%s,%s)",
        (username,hash_password(password))
        )
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def login_user(username,password):

    conn=get_connection()
    cur=conn.cursor()

    cur.execute(
    "SELECT id,username,password FROM users WHERE username=%s",
    (username,)
    )

    user=cur.fetchone()
    conn.close()

    if user and verify_password(password,user[2]):
        return user[0],user[1]

    return None

# ---------------- CHAT ----------------

def create_chat(user_id):

    conn=get_connection()
    cur=conn.cursor()

    cur.execute(
    "INSERT INTO chat_sessions(user_id,title) VALUES(%s,%s) RETURNING id",
    (user_id,"New Chat")
    )

    session_id=cur.fetchone()[0]

    conn.commit()
    conn.close()

    return session_id

def get_sessions(user_id):

    conn=get_connection()
    cur=conn.cursor()

    cur.execute("""
    SELECT id,title
    FROM chat_sessions
    WHERE user_id=%s
    ORDER BY created_at DESC
    """,(user_id,))

    sessions=cur.fetchall()
    conn.close()

    return sessions

def load_chat_session(session_id):

    conn=get_connection()
    cur=conn.cursor()

    cur.execute("""
    SELECT role,content
    FROM chats
    WHERE session_id=%s
    ORDER BY timestamp
    """,(session_id,))

    messages=cur.fetchall()
    conn.close()

    return messages

def save_message(session_id,role,content):

    conn=get_connection()
    cur=conn.cursor()

    cur.execute("""
    INSERT INTO chats(session_id,role,content)
    VALUES(%s,%s,%s)
    """,(session_id,role,content))

    conn.commit()
    conn.close()

def delete_chat(session_id):

    conn=get_connection()
    cur=conn.cursor()

    cur.execute("DELETE FROM chats WHERE session_id=%s",(session_id,))
    cur.execute("DELETE FROM chat_sessions WHERE id=%s",(session_id,))

    conn.commit()
    conn.close()

# ---------------- AI ----------------

def generate_title(prompt):

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": f"Create short 3 word title: {prompt}",
                "stream": False
            }
        )

        data = json.loads(response.text.split("\n")[0])
        return data["response"].strip()

    except:
        return "New Chat"

# ---------------- CODE RENDER ----------------

def render_message(content):

    code_blocks=re.findall(r"```(.*?)```",content,re.DOTALL)

    if code_blocks:

        parts=re.split(r"```.*?```",content)

        for i,part in enumerate(parts):

            st.markdown(part)

            if i < len(code_blocks):
                st.code(code_blocks[i])

    else:
        st.markdown(content)

# ---------------- SESSION ----------------

if "user_id" not in st.session_state:
    st.session_state.user_id=None

if "username" not in st.session_state:
    st.session_state.username=None

if "session_id" not in st.session_state:
    st.session_state.session_id=None

if "messages" not in st.session_state:
    st.session_state.messages=[]

# ---------------- LOGIN ----------------

if st.session_state.user_id is None:

    menu=st.sidebar.selectbox("Menu",["Login","Register"])

    username=st.text_input("Username")
    password=st.text_input("Password",type="password")

    if menu=="Register":

        if st.button("Register"):

            if register_user(username,password):
                st.success("User Registered")
            else:
                st.error("Username exists")

    if menu=="Login":

        if st.button("Login"):

            result=login_user(username,password)

            if result:

                user_id,username=result

                st.session_state.user_id=user_id
                st.session_state.username=username

                st.session_state.session_id=create_chat(user_id)
                st.session_state.messages=[]

                st.success("Login successful")
                st.rerun()

            else:
                st.error("Invalid credentials")

# ---------------- CHAT APP ----------------

else:

    st.sidebar.markdown(f"👤 **{st.session_state.username}**")

    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    st.sidebar.title("💬 Chats")

    if st.sidebar.button("➕ New Chat"):

        st.session_state.session_id=create_chat(
        st.session_state.user_id)

        st.session_state.messages=[]
        st.rerun()

    sessions=get_sessions(st.session_state.user_id)

    for s in sessions:

        col1,col2=st.sidebar.columns([4,1])

        with col1:

            if st.button(s[1],key=f"chat_{s[0]}"):

                st.session_state.session_id=s[0]

                history=load_chat_session(s[0])

                st.session_state.messages=[
                {"role":r,"content":c} for r,c in history
                ]

                st.rerun()

        with col2:

            if st.button("🗑️",key=f"del_{s[0]}"):

                delete_chat(s[0])
                st.rerun()


    st.markdown("""
<div id="timer-box">
⏳ Generating... <span id="timer">0.0</span>s
</div>

<style>
#timer-box{
position:fixed;
bottom:20px;
right:20px;
background:linear-gradient(135deg,#00c6ff,#0072ff);
color:white;
padding:12px 20px;
border-radius:12px;
font-weight:bold;
font-size:16px;
box-shadow:0 0 20px rgba(0,198,255,0.8);
animation: pulse 1.5s infinite;
z-index:9999;
}

@keyframes pulse{
0%{box-shadow:0 0 10px rgba(0,198,255,0.6);}
50%{box-shadow:0 0 25px rgba(0,198,255,1);}
100%{box-shadow:0 0 10px rgba(0,198,255,0.6);}
}
</style>

<script>
let start = Date.now();
let timer = document.getElementById("timer");

setInterval(()=>{
    let now = Date.now();
    let seconds = ((now-start)/1000).toFixed(1);
    if(timer){
        timer.innerText = seconds;
    }
},100);
</script>
""", unsafe_allow_html=True)

    # -------- CHAT DISPLAY --------

    for msg in st.session_state.messages:

        with st.chat_message(msg["role"]):

            render_message(msg["content"])

    prompt=st.chat_input("Ask anything...")

    if prompt:

        st.session_state.messages.append(
        {"role":"user","content":prompt})

        save_message(
        st.session_state.session_id,
        "user",
        prompt)

        if len(st.session_state.messages)==1:

            title = " ".join(prompt.split()[:4])

            conn=get_connection()
            cur=conn.cursor()

            cur.execute(
            "UPDATE chat_sessions SET title=%s WHERE id=%s",
            (title,st.session_state.session_id))

            conn.commit()
            conn.close()

        with st.chat_message("assistant"):

            placeholder=st.empty()

            start_timestamp = datetime.now()
            start_time = time.time()

            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "mistral",
                    "prompt": prompt,
                    "stream": True
                },
                stream=True
            )

            reply=""

            for line in response.iter_lines():

                if line:

                    data=json.loads(line.decode("utf-8"))

                    if "response" in data:

                        reply+=data["response"]
                        placeholder.markdown(reply)

                    if data.get("done"):
                        break
            end_timestamp = datetime.now()
            end_time = time.time()
            elapsed = round(end_time - start_time, 2)

        st.session_state.messages.append(
        {"role":"assistant","content":reply})

        save_message(
        st.session_state.session_id,
        "assistant",
        reply)
        st.markdown(f"""
<div style="
position:fixed;
bottom:20px;
right:20px;
background:linear-gradient(135deg,#00c6ff,#0072ff);
color:white;
padding:15px 22px;
border-radius:12px;
font-weight:bold;
font-size:14px;
box-shadow:0 0 20px rgba(0,198,255,0.9);
animation: glow 1.5s infinite;
z-index:9999;
">

⏱ Start : {start_timestamp.strftime("%H:%M:%S")} <br>
🏁 End : {end_timestamp.strftime("%H:%M:%S")} <br>
⚡ Duration : {elapsed} sec

</div>

<style>
@keyframes glow {{
0% {{box-shadow:0 0 10px #00c6ff}}
50% {{box-shadow:0 0 25px #00c6ff}}
100% {{box-shadow:0 0 10px #00c6ff}}
}}
</style>
""", unsafe_allow_html=True)
# ---------------- FOOTER ----------------

st.markdown("""
<hr>
<center>Built with ❤️ using Streamlit + Ollama</center>
""",unsafe_allow_html=True)
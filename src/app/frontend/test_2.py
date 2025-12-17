import streamlit as st
import time
import re

st.set_page_config(
    page_title="Echo Chatbot",
    page_icon="🤖",
    layout="wide"
)

st.markdown("""
<style>
/* giới hạn chiều rộng */
.stChatMessage {
    max-width: 900px;
    margin-left: auto;
    margin-right: auto;
}

/* ===== USER (bên phải) ===== */
.stChatMessage.user {
    justify-content: flex-end;
}

.stChatMessage.user [data-testid="stChatMessageContent"] {
    background-color: #1f2937;
    padding: 0.75rem 1rem;
    border-radius: 12px 12px 0 12px;
    max-width: 70%;
    margin-left: auto;
}

/* ===== ASSISTANT (bên trái) ===== */
.stChatMessage.assistant {
    justify-content: flex-start;
}

.stChatMessage.assistant [data-testid="stChatMessageContent"] {
    background-color: #111827;
    padding: 0.75rem 1rem;
    border-radius: 12px 12px 12px 0;
    max-width: 70%;
    margin-right: auto;
}
</style>
""", unsafe_allow_html=True)


# -----------------------------
# Helpers
# -----------------------------
def slugify(text, max_words=5):
    words = re.findall(r"\w+", text.lower())
    return "_".join(words[:max_words]) if words else "chat"

def unique_chat_id(base, existing_ids):
    if base not in existing_ids:
        return base
    i = 2
    while f"{base}_{i}" in existing_ids:
        i += 1
    return f"{base}_{i}"

# -----------------------------
# Session state
# -----------------------------
if "chats" not in st.session_state:
    st.session_state.chats = {}   # chat_id -> messages

if "current_chat" not in st.session_state:
    st.session_state.current_chat = None

# -----------------------------
# Feedback callback
# -----------------------------
def save_feedback(chat_id, msg_index):
    st.session_state.chats[chat_id][msg_index]["feedback"] = \
        st.session_state[f"feedback_{chat_id}_{msg_index}"]

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.markdown("## 🧠 Echo Chatbot")

    if st.button("➕ New chat", use_container_width=True):
        st.session_state.current_chat = None
        st.rerun()

    st.divider()
    st.markdown("### 💬 Your chats")

    for cid in reversed(st.session_state.chats.keys()):
        if st.button(cid.replace("_", " "), key=cid, use_container_width=True):
            st.session_state.current_chat = cid
            st.rerun()

# -----------------------------
# Main area
# -----------------------------
st.title("Echo Chatbot")

# Rename chat
if st.session_state.current_chat:
    with st.expander("✏️ Rename chat"):
        new_name = st.text_input(
            "New chat name",
            value=st.session_state.current_chat.replace("_", " ")
        )
        if st.button("Save name"):
            base = slugify(new_name)
            new_id = unique_chat_id(base, st.session_state.chats.keys())

            st.session_state.chats[new_id] = st.session_state.chats.pop(
                st.session_state.current_chat
            )
            st.session_state.current_chat = new_id
            st.rerun()

# -----------------------------
# Messages
# -----------------------------
messages = []
chat_id = st.session_state.current_chat

if chat_id:
    messages = st.session_state.chats[chat_id]

for i, msg in enumerate(messages):
    with st.chat_message(
        msg["role"],
        avatar="🧑‍💻" if msg["role"] == "user" else "🤖"
    ):
        st.markdown(msg["content"])

        # 👇 Feedback chỉ cho assistant
        if msg["role"] == "assistant":
            feedback = msg.get("feedback", None)

            key = f"feedback_{chat_id}_{i}"
            st.session_state[key] = feedback

            st.feedback(
                "thumbs",
                key=key,
                disabled=feedback is not None,
                on_change=save_feedback,
                args=[chat_id, i],
            )

# -----------------------------
# Input
# -----------------------------
if prompt := st.chat_input("Let's chat"):
    # First message → create chat ID
    if st.session_state.current_chat is None:
        base_id = slugify(prompt)
        chat_id = unique_chat_id(base_id, st.session_state.chats.keys())
        st.session_state.current_chat = chat_id
        st.session_state.chats[chat_id] = []

    messages = st.session_state.chats[st.session_state.current_chat]

    messages.append({
        "role": "user",
        "content": prompt
    })

    time.sleep(0.3)
    response = f"echo {prompt}"
    messages.append({
        "role": "assistant",
        "content": response,
        "feedback": None
    })

    st.rerun()

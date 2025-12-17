import streamlit as st
import time

st.markdown("""
<style>
.chat-container {
    max-width: 900px;
    margin: auto;
}
</style>
""", unsafe_allow_html=True)

st.title("Echo Chatbot")

if "messages" not in st.session_state:
    st.session_state.messages = []

st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="🧑‍💻" if message["role"]=="user" else "🤖"):
        st.markdown(message["content"])


if prompt := st.chat_input("Let's chat"):

    st.chat_message("user", avatar="🧑‍💻").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    response = f"echo {prompt}"
    st.chat_message("assistant", avatar="🤖").markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})

st.markdown("</div>", unsafe_allow_html=True)
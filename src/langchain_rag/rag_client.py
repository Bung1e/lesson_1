import streamlit as st
import requests

AZURE_FUNCTION_ENDPOINT = "http://localhost:7071/api/ask"

def ask_rag_endpoint(question: str):
    params = {"question": question}
    response = requests.get(AZURE_FUNCTION_ENDPOINT, params=params)
    response_data = response.json()
    return response_data.get("answer")

st.set_page_config(page_title="RAG Chat")

st.title("RAG Chat")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask something"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        answer = ask_rag_endpoint(prompt)
        st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
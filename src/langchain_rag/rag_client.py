import streamlit as st
import requests
import tempfile
import os
from pathlib import Path
import json

AZURE_FUNCTION_ENDPOINT = "http://localhost:7071/api/ask"
UPLOAD_ENDPOINT = "http://localhost:7071/api/upload" 

def ask_rag_endpoint(question: str):
    try:
        params = {"question": question}
        response = requests.get(AZURE_FUNCTION_ENDPOINT, params=params)
        response.raise_for_status()
        response_data = response.json()
        return response_data.get("answer", "No answer received")
    except requests.exceptions.RequestException as e:
        return f"Error connecting to RAG service: {str(e)}"

def upload_pdf_files(uploaded_files):
    """Upload PDF files to the server for processing"""
    try:
        files_data = []
        
        for uploaded_file in uploaded_files:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_file_path = tmp_file.name
            
            with open(tmp_file_path, 'rb') as f:
                files_data.append(('files', (uploaded_file.name, f.read(), 'application/pdf')))
            
            os.unlink(tmp_file_path)
        
        response = requests.post(UPLOAD_ENDPOINT, files=files_data)
        response.raise_for_status()
        
        return response.json()
    
    except requests.exceptions.RequestException as e:
        return {"error": f"Upload failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Processing error: {str(e)}"}

st.set_page_config(
    page_title="RAG Chat",
    layout="wide"
)


st.title("RAG Chat")

with st.sidebar:
    st.header("Upload Documents")
    st.markdown("Upload PDF files")
    
    uploaded_files = st.file_uploader(
        "Choose PDF files",
        type=['pdf'],
        accept_multiple_files=True,
        help="Select one or more PDF files to upload"
    )
    
    if uploaded_files:
        st.write(f"Selected {len(uploaded_files)} file(s):")
        for file in uploaded_files:
            st.write(f"• {file.name} ({file.size} bytes)")
        
        if st.button("Upload Files", type="primary"):
            with st.spinner("Uploading and processing files..."):
                result = upload_pdf_files(uploaded_files)
                
            if "error" in result:
                st.error(f"{result['error']}")
            else:
                st.success("Files uploaded successfully!")
                if "processed_count" in result:
                    st.info(f"Processed {result['processed_count']} documents")
                st.rerun()  # Refresh the app

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize upload status
if "upload_status" not in st.session_state:
    st.session_state.upload_status = None

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get and display assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            answer = ask_rag_endpoint(prompt)
        
        st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})

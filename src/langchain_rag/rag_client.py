import streamlit as st
import requests
import tempfile
import os
from pathlib import Path
import json
import logging
import sys
import uuid 

from opencensus.ext.azure.log_exporter import AzureLogHandler

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

if os.environ.get('APPLICATIONINSIGHTS_CONNECTION_STRING'):
    azure_handler = AzureLogHandler()
    logger.addHandler(azure_handler)

AZURE_FUNCTION_ENDPOINT = "http://localhost:7071/api/ask"
UPLOAD_ENDPOINT = "http://localhost:7071/api/upload" 

def trigger_test_error():
    trace_id = str(uuid.uuid4())
    logger.info(f"trace_id={trace_id} Triggering test error")
    try:
        response = requests.get(AZURE_FUNCTION_ENDPOINT + "?test_error=true")
        response.raise_for_status() 
    except requests.exceptions.RequestException as e:
        logger.exception(f"trace_id={trace_id} Error triggering test error endpoint")
        st.error(f"Error triggering test error: {str(e)}")
        return 
    
    try:
        response_data = response.json()
        if response_data.get("status") == "error":
             logger.error(f"trace_id={trace_id} Backend reported an error: {response_data.get("error", "Unknown error")}")
             st.error(f"Backend reported an error: {response_data.get("error", "Unknown error")}")
        else:
            st.info("Test error endpoint called, check backend logs for details.")
    except json.JSONDecodeError:
         logger.error(f"trace_id={trace_id} Received non-JSON response from error endpoint")
         st.error(f"Received non-JSON response from error endpoint: {response.text}")

def ask_rag_endpoint(question: str):
    trace_id = str(uuid.uuid4())
    try:
        logger.info(f"trace_id={trace_id} Sending question to backend: {question}")
        params = {"question": question}
        response = requests.get(AZURE_FUNCTION_ENDPOINT, params=params)
        response.raise_for_status()
        response_data = response.json()
        logger.info(f"trace_id={trace_id} Received response from backend")
        return response_data.get("answer", "No answer received")
    except requests.exceptions.RequestException as e:
        logger.exception(f"trace_id={trace_id} Error connecting to RAG service: {str(e)}")
        return f"Error connecting to RAG service: {str(e)}"

def upload_pdf_files(uploaded_files):
    "Upload PDF files to the server for processing"
    trace_id = str(uuid.uuid4())
    try:
        logger.info(f"trace_id={trace_id} Attempting to upload {len(uploaded_files)} files")
        files_data = []
        
        for uploaded_file in uploaded_files:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_file_path = tmp_file.name
            
            with open(tmp_file_path, 'rb') as f:
                files_data.append(('files', (uploaded_file.name, f.read(), 'application/pdf')))
            
            os.unlink(tmp_file_path)
        
        logger.info(f"trace_id={trace_id} Sending upload request to backend")
        response = requests.post(UPLOAD_ENDPOINT, files=files_data)
        response.raise_for_status()
        
        logger.info(f"trace_id={trace_id} Upload successful")
        return response.json()
    
    except requests.exceptions.RequestException as e:
        logger.exception(f"trace_id={trace_id} Upload failed: {str(e)}")
        return {"error": f"Upload failed: {str(e)}"}
    except Exception as e:
        logger.exception(f"trace_id={trace_id} Processing error: {str(e)}")
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
                st.rerun() 
                
    st.divider()
    if st.button("🔥 Test Error", help="Click to test error monitoring"):
        trigger_test_error()

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
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            answer = ask_rag_endpoint(prompt)
        
        st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})

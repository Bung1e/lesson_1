import azure.functions as func
import json
import logging
import tempfile
import os
from datetime import datetime
from pathlib import Path
from main import SimpleTravelRAG
from docs_to_storage import DocumentUploader

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

rag_system = None
document_uploader = None

def get_rag_system():
    """Get or create RAG system instance"""
    global rag_system
    if rag_system is None:
        rag_system = SimpleTravelRAG()
    return rag_system

def get_document_uploader():
    """Get or create document uploader instance"""
    global document_uploader
    if document_uploader is None:
        document_uploader = DocumentUploader()
    return document_uploader

@app.function_name(name="ask_rag")
@app.route(route="ask", methods=["POST", "GET"])
def ask_rag(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP trigger function for travel questions using RAG system.
    
    Usage:
    POST: {"question": "What hotels are available in Paris?"}
    GET: ?question=What hotels are available in Paris?
    
    Returns:
    JSON response with answer and metadata
    """
    try:
        question = None
        
        if req.method == "POST":
            try:
                req_body = req.get_json()
                question = req_body.get("question") if req_body else None
            except ValueError:
                return func.HttpResponse(
                    json.dumps({"error": "Invalid JSON", "status": "error"}),
                    status_code=400,
                    mimetype="application/json"
                )
        else: 
            question = req.params.get("question")
        
        rag = get_rag_system()
        result = rag.ask(question.strip())
        
        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error in ask_rag: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "error": f"Internal error: {str(e)}",
                "status": "error",
                "timestamp": datetime.now().isoformat()
            }),
            status_code=500,
            mimetype="application/json"
        )

@app.function_name(name="upload_documents")
@app.route(route="upload", methods=["POST"])
def upload_documents(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP trigger function for uploading PDF documents.
    
    Usage:
    POST with multipart/form-data containing PDF files
    
    Returns:
    JSON response with upload status and processing results
    """
    try:
        files = []
        for key, value in req.form.items():
            if key == 'files':
                files.append(value)
        
        if hasattr(req, 'files'):
            for file_key in req.files:
                files.extend(req.files.getlist(file_key))
        
        if not files:
            return func.HttpResponse(
                json.dumps({
                    "error": "No files uploaded", 
                    "status": "error"
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        temp_dir = tempfile.mkdtemp()
        saved_files = []
        
        try:
            for i, file_data in enumerate(files):
                if hasattr(file_data, 'filename') and hasattr(file_data, 'stream'):
                    filename = file_data.filename or f"uploaded_file_{i}.pdf"
                    file_path = os.path.join(temp_dir, filename)
                    
                    with open(file_path, 'wb') as f:
                        f.write(file_data.stream.read())
                    
                    saved_files.append(file_path)
                    logger.info(f"Saved file: {filename}")
                
                elif isinstance(file_data, bytes):
                    filename = f"uploaded_file_{i}.pdf"
                    file_path = os.path.join(temp_dir, filename)
                    
                    with open(file_path, 'wb') as f:
                        f.write(file_data)
                    
                    saved_files.append(file_path)
                    logger.info(f"Saved file: {filename}")
            
            if not saved_files:
                return func.HttpResponse(
                    json.dumps({
                        "error": "No valid PDF files found", 
                        "status": "error"
                    }),
                    status_code=400,
                    mimetype="application/json"
                )
            
            uploader = get_document_uploader()
            uploader.process_documents(temp_dir)
            
            global rag_system
            rag_system = None
            
            response_data = {
                "status": "success",
                "message": "Files uploaded and processed successfully",
                "processed_count": len(saved_files),
                "files": [os.path.basename(f) for f in saved_files],
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Successfully processed {len(saved_files)} files")
            
            return func.HttpResponse(
                json.dumps(response_data, ensure_ascii=False),
                status_code=200,
                mimetype="application/json"
            )
            
        finally:
            import shutil
            try:
                shutil.rmtree(temp_dir)
                logger.info("Temporary files cleaned up")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temp directory: {cleanup_error}")
        
    except Exception as e:
        logger.error(f"Error in upload_documents: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "error": f"Upload processing failed: {str(e)}",
                "status": "error",
                "timestamp": datetime.now().isoformat()
            }),
            status_code=500,
            mimetype="application/json"
        )
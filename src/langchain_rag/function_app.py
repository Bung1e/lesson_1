import azure.functions as func
import json
import logging
from datetime import datetime
from main import SimpleTravelRAG

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = func.FunctionApp()

# Singleton RAG system
rag_system = None

def get_rag_system():
    """Get or create RAG system instance"""
    global rag_system
    if rag_system is None:
        rag_system = SimpleTravelRAG()
    return rag_system

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
        # Get question from request
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
        else:  # GET request
            question = req.params.get("question")
        
        # Validate question
        if not question or not question.strip():
            return func.HttpResponse(
                json.dumps({"error": "Question is required", "status": "error"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Process question using RAG system
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
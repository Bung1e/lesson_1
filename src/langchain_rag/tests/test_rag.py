import pytest
import json
from unittest.mock import Mock, patch
import azure.functions as func
from src.langchain_rag.function_app import ask_rag, get_rag_system


def test_ask_rag_post_request():
    with patch('src.langchain_rag.function_app.get_rag_system') as mock_get_rag:
        mock_rag = Mock()
        mock_rag.ask.return_value = {
            "timestamp": "2024-01-01T12:00:00",
            "question": "Where can I travel?",
            "answer": "You can travel to Paris, London, and Rome",
            "status": "success"
        }
        mock_get_rag.return_value = mock_rag

        req_body = json.dumps({"question": "Where can I travel?"})
        req = func.HttpRequest(
            method='POST',
            body=req_body.encode('utf-8'),
            url='http://localhost/api/ask',
            headers={'content-type': 'application/json'}
        )
        
        response = ask_rag(req)
        
        assert response.status_code == 200
        response_data = json.loads(response.get_body().decode())
        assert response_data["status"] == "success"
        assert "travel" in response_data["answer"]

def test_ask_rag_missing_question():

    req_body = json.dumps({})
    req = func.HttpRequest(
        method='POST',
        body=req_body.encode('utf-8'),
        url='http://localhost/api/ask',
        headers={'content-type': 'application/json'}
    )
    
    response = ask_rag(req)
    
    assert response.status_code == 400
    response_data = json.loads(response.get_body().decode())
    assert response_data["status"] == "error"
    assert "required" in response_data["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
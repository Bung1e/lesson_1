import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_community.retrievers import AzureAISearchRetriever
from langchain_core.prompts import PromptTemplate
from langchain.chains import RetrievalQA

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/travel_assistant_rag.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SimpleTravelRAG:
    def __init__(self):
        load_dotenv()
        self._setup_components()
        
    def _setup_components(self):
        # Setup LLM
        self.llm = AzureChatOpenAI(
            azure_deployment=os.getenv("CHAT_MODEL"),
            api_version="2024-02-01",
            azure_endpoint=os.getenv("OPENAI_ENDPOINT"),
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.7
        )
        
        # Setup search retriever
        self.retriever = AzureAISearchRetriever(
            service_name=os.getenv("SEARCH_ENDPOINT"),
            index_name=os.getenv("INDEX_NAME"),
            api_key=os.getenv("SEARCH_KEY"),
            content_key=os.getenv("CONTENT_KEY", "content"),
            top_k=3
        )
        
        self.prompt = PromptTemplate(
            input_variables=["context", "question"],
            template="""
You are a travel assistant. Based on the provided information from Margie's Travel brochures, 
provide helpful information about travel destinations, accommodations, and services.

Context from search results:
{context}

User question: {question}

Answer (use only information from the context):
"""
        )
        
        # Create QA chain
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.retriever,
            chain_type_kwargs={"prompt": self.prompt}
        )
    
    def ask(self, question):
        result = self.qa_chain.invoke({"query": question})
        response_data = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "answer": result["result"]
        }
        
        logger.info(f"Question: {question}")
        logger.info(f"Answer: {result['result']}")
        
        self._save_to_json(response_data)
        
        return response_data
    
    def _save_to_json(self, data):
        filename = "results/answers.json"
        
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                responses = json.load(f)
        else:
            responses = []
        
        responses.append(data)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(responses, f, ensure_ascii=False, indent=2)

def main(): 
    assistant = SimpleTravelRAG()
    
    while True:
        question = input("\nYour question: ").strip()
        
        if question.lower() == "quit":
            break
            
        if not question:
            continue
        
        result = assistant.ask(question)

if __name__ == "__main__":
    main()
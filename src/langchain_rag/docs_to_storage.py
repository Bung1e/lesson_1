import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from langchain_community.document_loaders import (
    PyPDFLoader, 
    TextLoader, 
    Docx2txtLoader,
    UnstructuredMarkdownLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    VectorSearchAlgorithmKind,
    SearchField,
    SearchFieldDataType
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/document_uploader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DocumentUploader:
    def __init__(self):
        load_dotenv()
        self._setup_components()
        
    def _setup_components(self):
        self.embeddings = AzureOpenAIEmbeddings(
            azure_deployment=os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002"),
            api_version="2024-02-01",
            azure_endpoint=os.getenv("OPENAI_ENDPOINT"),
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.search_endpoint = os.getenv("SEARCH_ENDPOINT")
        self.search_key = os.getenv("SEARCH_KEY")
        self.index_name = os.getenv("NEW_INDEX_NAME")
        
        credential = AzureKeyCredential(self.search_key)
        self.search_client = SearchClient(
            endpoint=self.search_endpoint,
            index_name=self.index_name,
            credential=credential
        )
        self.index_client = SearchIndexClient(
            endpoint=self.search_endpoint,
            credential=credential
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
    def create_search_index(self):
        try:
            existing_indexes = [idx.name for idx in self.index_client.list_indexes()]
            if self.index_name in existing_indexes:
                logger.info(f"Индекс {self.index_name} уже существует")
                return
            
            fields = [
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="content", type=SearchFieldDataType.String),
                SearchableField(name="title", type=SearchFieldDataType.String),
                SimpleField(name="source", type=SearchFieldDataType.String),
                SimpleField(name="chunk_id", type=SearchFieldDataType.Int32),
                SearchField(
                    name="content_vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=1536,  # for text-embedding-ada-002
                    vector_search_profile_name="my-vector-config"
                )
            ]
            
            vector_search = VectorSearch(
                profiles=[
                    VectorSearchProfile(
                        name="my-vector-config",
                        algorithm_configuration_name="my-hnsw"
                    )
                ],
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="my-hnsw",
                        kind=VectorSearchAlgorithmKind.HNSW
                    )
                ]
            )
            
            index = SearchIndex(
                name=self.index_name,
                fields=fields,
                vector_search=vector_search
            )
            
            self.index_client.create_index(index)
            logger.info(f"Index {self.index_name} created")
            
        except Exception as e:
            logger.error(f"Error when creating the index: {e}")
            raise
    
    def load_documents(self, documents_path: str) -> List[Dict[str, Any]]:
        documents = []
        documents_path = Path(documents_path)
        
        if not documents_path.exists():
            raise FileNotFoundError(f"Folder {documents_path} not found")
        
        file_loaders = {
            '.pdf': PyPDFLoader,
            '.txt': TextLoader,
            '.docx': Docx2txtLoader,
            '.md': UnstructuredMarkdownLoader
        }
        
        for file_path in documents_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in file_loaders:
                try:
                    loader_class = file_loaders[file_path.suffix.lower()]
                    loader = loader_class(str(file_path))
                    docs = loader.load()
                    
                    for doc in docs:
                        documents.append({
                            'content': doc.page_content,
                            'metadata': doc.metadata,
                            'source': str(file_path),
                            'title': file_path.stem
                        })
                    
                    logger.info(f"File uploaded: {file_path}")
                    
                except Exception as e:
                    logger.error(f"Error when uploading a file {file_path}: {e}")
        
        logger.info(f"Total documents uploaded: {len(documents)}")
        return documents
    
    def split_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        chunks = []
        
        for doc_idx, doc in enumerate(documents):
            text_chunks = self.text_splitter.split_text(doc['content'])
            
            for chunk_idx, chunk_text in enumerate(text_chunks):
                chunks.append({
                    'content': chunk_text,
                    'title': doc['title'],
                    'source': doc['source'],
                    'chunk_id': chunk_idx,
                    'id': f"{doc_idx}_{chunk_idx}"
                })
        
        logger.info(f"Created chunks: {len(chunks)}")
        return chunks
    
    def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]: 
        texts = [chunk['content'] for chunk in chunks]
        
        batch_size = 50
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = self.embeddings.embed_documents(batch_texts)
            
            for j, embedding in enumerate(batch_embeddings):
                chunks[i + j]['content_vector'] = embedding
            
            logger.info(f"Processed embeddings: {min(i + batch_size, len(texts))}/{len(texts)}")
        
        return chunks
    
    def upload_to_azure_search(self, chunks: List[Dict[str, Any]]):
       
        try:
            batch_size = 100
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                result = self.search_client.upload_documents(documents=batch)
                
                success_count = sum(1 for r in result if r.succeeded)
                logger.info(f"Uploaded documents in the batch: {success_count}/{len(batch)}")
            
            logger.info(f"All documents have been successfully uploaded to the index {self.index_name}")
            
        except Exception as e:
            logger.error(f"Error when uploading to Azure Search: {e}")
            raise
    
    def process_documents(self, documents_path: str):
        try:
            
            self.create_search_index()
            
            documents = self.load_documents(documents_path)
            if not documents:
                logger.warning("No documents found")
                return
            
            chunks = self.split_documents(documents)
            
            chunks_with_embeddings = self.embed_chunks(chunks)
            
            self.upload_to_azure_search(chunks_with_embeddings)
            
            self._save_processing_stats(len(documents), len(chunks))
            
        except Exception as e:
            logger.error(f"Document processing error: {e}")
            raise
    
    def _save_processing_stats(self, doc_count: int, chunk_count: int):
        stats = {
            "processed_at": str(Path().cwd()),
            "documents_count": doc_count,
            "chunks_count": chunk_count,
            "index_name": self.index_name
        }
        
        os.makedirs("results", exist_ok=True)
        with open("results/processing_stats.json", "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

def main():
    documents_folder = "src\langchain_rag\docs"
    
    try:
        uploader = DocumentUploader()
        uploader.process_documents(documents_folder)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
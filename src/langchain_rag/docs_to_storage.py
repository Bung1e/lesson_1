import os
import json
import logging
import tempfile
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
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedDocumentUploader:
    def __init__(self):
        load_dotenv()
        self._setup_components()
        
    def _setup_components(self):
        """Initialize Azure components and configurations"""
        try:
            self.embeddings = AzureOpenAIEmbeddings(
                azure_deployment=os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002"),
                api_version="2024-02-01",
                azure_endpoint=os.getenv("OPENAI_ENDPOINT"),
                api_key=os.getenv("OPENAI_API_KEY")
            )
            
            self.search_endpoint = os.getenv("SEARCH_ENDPOINT")
            self.search_key = os.getenv("SEARCH_KEY")
            self.index_name = os.getenv("NEW_INDEX_NAME")
            
            if not all([self.search_endpoint, self.search_key, self.index_name]):
                raise ValueError("Missing Azure Search configuration")
            
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
            
            logger.info("Document uploader components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
        
    def create_search_index(self):
        try:
            existing_indexes = [idx.name for idx in self.index_client.list_indexes()]
            if self.index_name in existing_indexes:
                logger.info(f"Index {self.index_name} already exists")
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
            logger.info(f"Index {self.index_name} created successfully")
            
        except Exception as e:
            logger.error(f"Error creating index: {e}")
            raise
    
    def load_documents(self, documents_path: str) -> List[Dict[str, Any]]:
        documents = []
        documents_path = Path(documents_path)
        
        if not documents_path.exists():
            raise FileNotFoundError(f"Path {documents_path} not found")
        
        file_loaders = {
            '.pdf': PyPDFLoader,
            '.txt': TextLoader,
            '.docx': Docx2txtLoader,
            '.md': UnstructuredMarkdownLoader
        }
        

        processed_files = 0
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
                    
                    processed_files += 1
                    logger.info(f"Loaded file: {file_path.name}")
                    
                except Exception as e:
                    logger.error(f"Error loading file {file_path}: {e}")
        
        logger.info(f"Loaded {len(documents)} documents from {processed_files} files")
        return documents
    
    def split_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        chunks = []
        
        for doc_idx, doc in enumerate(documents):
            try:
                text_chunks = self.text_splitter.split_text(doc['content'])
                
                for chunk_idx, chunk_text in enumerate(text_chunks):
                    chunk_id = f"{doc_idx}_{chunk_idx}_{len(chunks)}"
                    chunks.append({
                        'content': chunk_text,
                        'title': doc['title'],
                        'source': doc['source'],
                        'chunk_id': chunk_idx,
                        'id': chunk_id
                    })
            except Exception as e:
                logger.error(f"Error splitting document {doc_idx}: {e}")
        
        logger.info(f"Created {len(chunks)} chunks from {len(documents)} documents")
        return chunks
    
    def embed_chunks(self, chunks): 
        if not chunks:
            return chunks
        
        texts = [chunk['content'] for chunk in chunks]
        batch_size = 50
        
        try:
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_embeddings = self.embeddings.embed_documents(batch_texts)
                
                for j, embedding in enumerate(batch_embeddings):
                    chunks[i + j]['content_vector'] = embedding
                
                logger.info(f"Generated embeddings: {min(i + batch_size, len(texts))}/{len(texts)}")
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
        
        return chunks
    
    def upload_to_azure_search(self, chunks: List[Dict[str, Any]]):
        try:
            batch_size = 100
            total_uploaded = 0
            
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                result = self.search_client.upload_documents(documents=batch)
                
                success_count = sum(1 for r in result if r.succeeded)
                total_uploaded += success_count
                
                if success_count < len(batch):
                    failed_count = len(batch) - success_count
                    logger.warning(f"Batch {i//batch_size + 1}: {failed_count} documents failed to upload")
                
                logger.info(f"Uploaded batch {i//batch_size + 1}: {success_count}/{len(batch)} documents")
            
            logger.info(f"Total documents uploaded: {total_uploaded}/{len(chunks)}")
            
        except Exception as e:
            logger.error(f"Error uploading to Azure Search: {e}")
            raise
    
    def process_documents(self, documents_path: str):
        try:
            logger.info(f"Starting document processing for path: {documents_path}")
            
            self.create_search_index()
            
            documents = self.load_documents(documents_path)
            if not documents:
                logger.warning("No documents found to process")
                return {"documents_count": 0, "chunks_count": 0}
            
            chunks = self.split_documents(documents)
            if not chunks:
                logger.warning("No chunks created from documents")
                return {"documents_count": len(documents), "chunks_count": 0}
            
            chunks_with_embeddings = self.embed_chunks(chunks)
            
            self.upload_to_azure_search(chunks_with_embeddings)
            
            logger.info("Document processing completed successfully")
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            raise
    
DocumentUploader = EnhancedDocumentUploader

def main():
    """Main function for testing"""
    documents_folder = r"src\langchain_rag\docs"
    
    try:
        uploader = EnhancedDocumentUploader()
        result = uploader.process_documents(documents_folder)
        print(f"Processing completed: {result}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
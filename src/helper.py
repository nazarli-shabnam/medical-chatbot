from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from typing import List, Optional
from langchain_core.documents import Document
import os


#Extract Data From the PDF File
def load_pdf_file(data):
    loader= DirectoryLoader(data,
                            glob="*.pdf",
                            loader_cls=PyPDFLoader)

    documents=loader.load()

    return documents


def load_single_pdf(file_path: str):
    """Load a single PDF file"""
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    return documents


def filter_to_minimal_docs(docs: List[Document]) -> List[Document]:
    """
    Given a list of Document objects, return a new list of Document objects
    containing only 'source' in metadata and the original page_content.
    """
    minimal_docs: List[Document] = []
    for doc in docs:
        src = doc.metadata.get("source")
        page = doc.metadata.get("page", 0)
        minimal_docs.append(
            Document(
                page_content=doc.page_content,
                metadata={"source": src, "page": page}
            )
        )
    return minimal_docs


#Split the Data into Text Chunks
def text_split(extracted_data, chunk_size=500, chunk_overlap=20):
    text_splitter=RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    text_chunks=text_splitter.split_documents(extracted_data)
    return text_chunks


#Download the Embeddings from HuggingFace 
def download_hugging_face_embeddings():
    embeddings=HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')  #this model return 384 dimensions
    return embeddings


#Download Gemini Embeddings (alternative)
def get_gemini_embeddings():
    """Get Google Gemini embeddings"""
    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
    return embeddings
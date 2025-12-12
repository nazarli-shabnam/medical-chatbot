"""Tests for helper functions"""
import pytest
from langchain_core.documents import Document
from src.helper import filter_to_minimal_docs, text_split, download_hugging_face_embeddings


class TestDocumentFiltering:
    """Tests for document filtering"""
    
    def test_filter_to_minimal_docs(self):
        """Test filtering documents to minimal metadata"""
        docs = [
            Document(page_content="Content 1", metadata={"source": "file1.pdf", "page": 1, "extra": "data"}),
            Document(page_content="Content 2", metadata={"source": "file2.pdf", "page": 2, "extra": "data"})
        ]
        
        filtered = filter_to_minimal_docs(docs)
        
        assert len(filtered) == 2
        assert filtered[0].metadata == {"source": "file1.pdf", "page": 1}
        assert "extra" not in filtered[0].metadata


class TestTextSplitting:
    """Tests for text splitting"""
    
    def test_text_split_default(self):
        """Test text splitting with default parameters"""
        docs = [Document(
            page_content="This is a long text that should be split into chunks. " * 20,
            metadata={"source": "test.pdf", "page": 1}
        )]
        
        chunks = text_split(docs)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, Document) for chunk in chunks)
    
    def test_text_split_preserves_metadata(self):
        """Test that text splitting preserves metadata"""
        docs = [Document(
            page_content="Text to split " * 50,
            metadata={"source": "test.pdf", "page": 5}
        )]
        
        chunks = text_split(docs)
        
        assert all(chunk.metadata.get("source") == "test.pdf" for chunk in chunks)
        assert all(chunk.metadata.get("page") == 5 for chunk in chunks)


class TestEmbeddings:
    """Tests for embedding functions"""
    
    def test_download_hugging_face_embeddings(self, mock_embeddings):
        """Test downloading HuggingFace embeddings"""
        embeddings = download_hugging_face_embeddings()
        
        assert embeddings is not None
        result = embeddings.embed_query("test query")
        assert isinstance(result, list)
        assert len(result) == 384
    
    def test_embeddings_embed_documents(self, mock_embeddings):
        """Test embedding multiple documents"""
        embeddings = download_hugging_face_embeddings()
        
        texts = ["First document", "Second document"]
        results = embeddings.embed_documents(texts)
        assert len(results) == len(texts)
        assert all(len(embedding) == 384 for embedding in results)

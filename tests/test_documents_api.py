"""Tests for document management API"""
import pytest
import json
from io import BytesIO
from src.database import db, Document, DocumentChunk


class TestDocumentUpload:
    """Tests for document upload"""
    
    def test_upload_requires_auth(self, client):
        """Test upload requires authentication"""
        response = client.post('/api/upload')
        assert response.status_code in [401, 403, 302]
    
    def test_upload_no_file(self, authenticated_client):
        """Test upload without file fails"""
        response = authenticated_client.post('/api/upload')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_upload_non_pdf(self, authenticated_client):
        """Test upload of non-PDF file fails"""
        data = {'file': (BytesIO(b'not a pdf'), 'test.txt')}
        response = authenticated_client.post('/api/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 400


class TestDocumentDeletion:
    """Tests for document deletion"""
    
    def test_delete_requires_auth(self, client):
        """Test delete requires authentication"""
        response = client.delete('/api/documents/1')
        assert response.status_code in [401, 403, 302]
    
    def test_delete_nonexistent(self, authenticated_client):
        """Test delete nonexistent document fails"""
        response = authenticated_client.delete('/api/documents/99999')
        assert response.status_code == 404
    
    def test_delete_success(self, authenticated_client, app, test_document):
        """Test successful document deletion"""
        with app.app_context():
            test_document = db.session.merge(test_document)
            db.session.commit()
            doc_id = test_document.id
        
        response = authenticated_client.delete(f'/api/documents/{doc_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get('success') == True
        
        with app.app_context():
            assert Document.query.get(doc_id) is None
    
    def test_delete_removes_chunks(self, authenticated_client, app, test_document):
        """Test deleting document removes associated chunks"""
        with app.app_context():
            test_document = db.session.merge(test_document)
            db.session.commit()
            db.session.refresh(test_document)
            
            # Clear existing chunks first
            DocumentChunk.query.filter_by(document_id=test_document.id).delete()
            db.session.commit()
            
            # Create a new chunk
            chunk = DocumentChunk(
                document_id=test_document.id,
                chunk_index=0,
                page_number=1,
                content_preview="Test"
            )
            db.session.add(chunk)
            db.session.commit()
            db.session.refresh(chunk)
            chunk_id = chunk.id
            
            # Load the relationship to ensure cascade works
            _ = test_document.chunks
            db.session.refresh(test_document)
            
            # Verify chunk exists before deletion
            assert DocumentChunk.query.get(chunk_id) is not None
            assert len(test_document.chunks) == 1
        
        response = authenticated_client.delete(f'/api/documents/{test_document.id}')
        assert response.status_code == 200
        
        with app.app_context():
            # Document should be deleted
            doc_check = Document.query.get(test_document.id)
            assert doc_check is None, f"Document {test_document.id} should be deleted but still exists"
            
            # Chunk should be deleted via cascade
            deleted_chunk = DocumentChunk.query.get(chunk_id)
            assert deleted_chunk is None, f"Chunk {chunk_id} should be deleted via cascade but still exists"

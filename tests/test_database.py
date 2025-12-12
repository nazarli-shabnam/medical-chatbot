"""Tests for database models"""
import pytest
from src.database import db, User, Document, Conversation, Message, Citation, Feedback, DocumentChunk


class TestUser:
    """Tests for User model"""
    
    def test_create_user(self, app):
        """Test creating a user"""
        with app.app_context():
            User.query.filter_by(email='newuser@example.com').delete()
            db.session.commit()
            
            user = User(username='newuser', email='newuser@example.com')
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            
            assert user.id is not None
            assert user.check_password('password123')
            assert not user.check_password('wrong')
    
    def test_user_relationships(self, app, test_user):
        """Test user relationships"""
        with app.app_context():
            test_user = db.session.merge(test_user)
            Conversation.query.filter_by(user_id=test_user.id).delete()
            Document.query.filter_by(user_id=test_user.id).delete()
            db.session.commit()
            
            conv = Conversation(user_id=test_user.id)
            doc = Document(
                user_id=test_user.id,
                filename='test.pdf',
                original_filename='test.pdf',
                file_path='/test/test.pdf',
                file_size=1024
            )
            db.session.add(conv)
            db.session.add(doc)
            db.session.commit()
            db.session.refresh(test_user)
            
            assert len(test_user.conversations) == 1
            assert len(test_user.documents) == 1


class TestDocument:
    """Tests for Document model"""
    
    def test_create_document(self, app, test_user):
        """Test creating a document"""
        with app.app_context():
            test_user = db.session.merge(test_user)
            db.session.commit()
            
            doc = Document(
                user_id=test_user.id,
                filename='doc.pdf',
                original_filename='My Document.pdf',
                file_path='/uploads/doc.pdf',
                file_size=2048
            )
            db.session.add(doc)
            db.session.commit()
            
            assert doc.id is not None
            assert doc.user_id == test_user.id


class TestConversation:
    """Tests for Conversation model"""
    
    def test_create_conversation(self, app, test_user):
        """Test creating a conversation"""
        with app.app_context():
            test_user = db.session.merge(test_user)
            db.session.commit()
            
            conv = Conversation(user_id=test_user.id)
            db.session.add(conv)
            db.session.commit()
            
            assert conv.id is not None
            assert conv.user_id == test_user.id
    
    def test_conversation_messages(self, app, test_conversation):
        """Test conversation messages relationship"""
        with app.app_context():
            test_conversation = db.session.merge(test_conversation)
            Message.query.filter_by(conversation_id=test_conversation.id).delete()
            db.session.commit()
            
            msg1 = Message(conversation_id=test_conversation.id, role='user', content='Hello')
            msg2 = Message(conversation_id=test_conversation.id, role='assistant', content='Hi')
            db.session.add(msg1)
            db.session.add(msg2)
            db.session.commit()
            db.session.refresh(test_conversation)
            
            assert len(test_conversation.messages) == 2


class TestMessage:
    """Tests for Message model"""
    
    def test_create_message(self, app, test_conversation):
        """Test creating a message"""
        with app.app_context():
            test_conversation = db.session.merge(test_conversation)
            db.session.commit()
            
            msg = Message(
                conversation_id=test_conversation.id,
                role='user',
                content='Test message'
            )
            db.session.add(msg)
            db.session.commit()
            
            assert msg.id is not None
            assert msg.conversation_id == test_conversation.id
    
    def test_message_citations(self, app, test_message, test_document):
        """Test message citations relationship"""
        with app.app_context():
            test_message = db.session.merge(test_message)
            test_document = db.session.merge(test_document)
            db.session.commit()
            
            citation = Citation(
                message_id=test_message.id,
                document_id=test_document.id,
                page_number=1,
                content_snippet="Relevant content"
            )
            db.session.add(citation)
            db.session.commit()
            db.session.refresh(test_message)
            
            assert len(test_message.citations) == 1

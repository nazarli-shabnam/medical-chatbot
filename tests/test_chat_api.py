"""Tests for chat API endpoints"""
import pytest
import json
from src.database import db, Conversation, Message
from tests.test_utils import consume_stream


class TestChatStream:
    """Tests for chat streaming endpoint"""
    
    def test_chat_stream_creates_conversation(self, authenticated_client, app, test_user, mock_pinecone, mock_gemini):
        """Test chat stream creates new conversation"""
        with app.app_context():
            test_user = db.session.merge(test_user)
            initial_count = Conversation.query.filter_by(user_id=test_user.id).count()
        
        response = authenticated_client.post('/api/chat/stream', json={'message': 'Hello'})
        assert response.status_code == 200
        assert 'text/event-stream' in response.content_type
        
        consume_stream(response)
        
        with app.app_context():
            final_count = Conversation.query.filter_by(user_id=test_user.id).count()
            assert final_count == initial_count + 1
    
    def test_chat_stream_saves_messages(self, authenticated_client, app, test_user, mock_pinecone, mock_gemini):
        """Test chat stream saves messages"""
        with app.app_context():
            test_user = db.session.merge(test_user)
        
        response = authenticated_client.post('/api/chat/stream', json={'message': 'Test question'})
        assert response.status_code == 200
        consume_stream(response)
        
        with app.app_context():
            conversation = Conversation.query.filter_by(
                user_id=test_user.id).order_by(Conversation.created_at.desc()).first()
            assert conversation is not None
            messages = Message.query.filter_by(conversation_id=conversation.id).all()
            assert len(messages) >= 1
            assert any(msg.role == 'user' for msg in messages)


class TestConversationsAPI:
    """Tests for conversations API endpoints"""
    
    def test_get_conversations_requires_auth(self, client):
        """Test get conversations requires authentication"""
        response = client.get('/api/conversations')
        assert response.status_code in [401, 403, 302]
    
    def test_get_conversations_empty(self, authenticated_client, app, test_user):
        """Test get conversations when user has none"""
        with app.app_context():
            test_user = db.session.merge(test_user)
            Conversation.query.filter_by(user_id=test_user.id).delete()
            db.session.commit()
        
        response = authenticated_client.get('/api/conversations')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_get_conversations_with_data(self, authenticated_client, app, test_user, test_conversation):
        """Test get conversations returns user's conversations"""
        with app.app_context():
            test_user = db.session.merge(test_user)
            test_conversation = db.session.merge(test_conversation)
            Message.query.filter_by(conversation_id=test_conversation.id).delete()
            db.session.commit()
            
            msg = Message(conversation_id=test_conversation.id, role='user', content='Test')
            db.session.add(msg)
            db.session.commit()
        
        response = authenticated_client.get('/api/conversations')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) > 0
        assert 'id' in data[0]
        assert 'message_count' in data[0]
    
    def test_get_messages_success(self, authenticated_client, app, test_conversation, test_message):
        """Test get messages returns conversation messages"""
        with app.app_context():
            test_conversation = db.session.merge(test_conversation)
            test_message = db.session.merge(test_message)
            db.session.commit()
            db.session.refresh(test_conversation)
            db.session.refresh(test_message)
            
            # Clear other messages to ensure clean state
            Message.query.filter_by(conversation_id=test_conversation.id).filter(Message.id != test_message.id).delete()
            db.session.commit()
            
            # Verify message exists and is attached to conversation
            msg_check = Message.query.get(test_message.id)
            assert msg_check is not None
            assert msg_check.conversation_id == test_conversation.id
        
        response = authenticated_client.get(f'/api/conversations/{test_conversation.id}/messages')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) > 0
        assert any(msg['id'] == test_message.id for msg in data)

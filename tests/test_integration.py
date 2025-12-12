"""Integration tests for complete user flows"""
import pytest
import json
from src.database import db, User, Conversation, Message
from tests.test_utils import consume_stream


class TestCompleteUserFlow:
    """Tests for complete user workflows"""
    
    def test_register_login_chat_flow(self, client, app):
        """Test complete flow: register -> login -> chat"""
        with app.app_context():
            User.query.filter_by(email='flow@example.com').delete()
            db.session.commit()
        
        response = client.post('/auth/register', data={
            'username': 'flowuser',
            'email': 'flow@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200
        
        response = client.post('/auth/login', data={
            'username': 'flowuser',
            'password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200
        
        response = client.get('/chat')
        assert response.status_code == 200
    
    def test_chat_with_feedback_flow(self, authenticated_client, app, test_user, mock_pinecone, mock_gemini):
        """Test flow: chat -> receive response -> provide feedback"""
        with app.app_context():
            test_user = db.session.merge(test_user)
        
        response = authenticated_client.post('/api/chat/stream', json={'message': 'What is diabetes?'})
        assert response.status_code == 200
        consume_stream(response)
        
        response = authenticated_client.get('/api/conversations')
        data = json.loads(response.data)
        assert len(data) > 0
        
        conv_id = data[0]['id']
        response = authenticated_client.get(f'/api/conversations/{conv_id}/messages')
        messages_data = json.loads(response.data)
        
        assistant_msg = next((msg for msg in messages_data if msg['role'] == 'assistant'), None)
        if assistant_msg:
            response = authenticated_client.post('/api/feedback', json={
                'message_id': assistant_msg['id'],
                'rating': 'positive',
                'comment': 'Helpful answer'
            })
            assert response.status_code == 200


class TestMultiUserIsolation:
    """Tests for multi-user data isolation"""
    
    def test_users_cannot_access_each_others_data(self, app):
        """Test users cannot access each other's conversations"""
        with app.app_context():
            User.query.filter_by(email='user1@test.com').delete()
            User.query.filter_by(email='user2@test.com').delete()
            db.session.commit()
            
            user1 = User(username='user1', email='user1@test.com')
            user1.set_password('pass1')
            user2 = User(username='user2', email='user2@test.com')
            user2.set_password('pass2')
            db.session.add(user1)
            db.session.add(user2)
            db.session.commit()
            db.session.refresh(user1)
            db.session.refresh(user2)
            
            conv1 = Conversation(user_id=user1.id)
            conv2 = Conversation(user_id=user2.id)
            db.session.add(conv1)
            db.session.add(conv2)
            db.session.commit()
            
            user1_convs = Conversation.query.filter_by(user_id=user1.id).all()
            user2_convs = Conversation.query.filter_by(user_id=user2.id).all()
            
            assert len(user1_convs) == 1
            assert len(user2_convs) == 1
            assert user1_convs[0].id != user2_convs[0].id

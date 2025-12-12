"""Tests for feedback API"""
import pytest
import json
from src.database import db, Feedback, Message, Conversation


class TestFeedbackSubmission:
    """Tests for feedback submission"""
    
    def test_feedback_requires_auth(self, client):
        """Test feedback requires authentication"""
        response = client.post('/api/feedback', json={'message_id': 1, 'rating': 'positive'})
        assert response.status_code in [401, 403, 302]
    
    def test_feedback_missing_fields(self, authenticated_client):
        """Test feedback with missing fields fails"""
        response = authenticated_client.post('/api/feedback', json={})
        assert response.status_code == 400
    
    def test_feedback_positive_rating(self, authenticated_client, app, test_user, test_message):
        """Test submitting positive feedback"""
        with app.app_context():
            test_user = db.session.merge(test_user)
            test_message = db.session.merge(test_message)
            db.session.commit()
            db.session.refresh(test_user)
            db.session.refresh(test_message)
            
            # Ensure conversation relationship is loaded
            conv = Conversation.query.get(test_message.conversation_id)
            assert conv is not None
            assert conv.user_id == test_user.id
            
            # Refresh message to ensure conversation relationship is accessible
            db.session.refresh(test_message)
            # Access the relationship to ensure it's loaded
            _ = test_message.conversation.user_id
        
        response = authenticated_client.post('/api/feedback', json={
            'message_id': test_message.id,
            'rating': 'positive',
            'comment': 'Great answer!'
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get('success') == True
        
        with app.app_context():
            feedback = Feedback.query.filter_by(
                message_id=test_message.id,
                user_id=test_user.id
            ).first()
            assert feedback is not None
            assert feedback.rating == 'positive'
    
    def test_feedback_nonexistent_message(self, authenticated_client):
        """Test feedback for nonexistent message fails"""
        response = authenticated_client.post('/api/feedback', json={
            'message_id': 99999,
            'rating': 'positive'
        })
        assert response.status_code == 404
    
    def test_feedback_updates_existing(self, authenticated_client, app, test_user, test_message):
        """Test feedback updates existing feedback"""
        with app.app_context():
            test_user = db.session.merge(test_user)
            test_message = db.session.merge(test_message)
            db.session.commit()
            db.session.refresh(test_user)
            db.session.refresh(test_message)
            
            # Ensure conversation relationship is loaded
            conv = Conversation.query.get(test_message.conversation_id)
            assert conv is not None
            assert conv.user_id == test_user.id
            
            # Refresh message to ensure conversation relationship is accessible
            db.session.refresh(test_message)
            # Access the relationship to ensure it's loaded
            _ = test_message.conversation.user_id
            
            # Clean up any existing feedback
            Feedback.query.filter_by(message_id=test_message.id, user_id=test_user.id).delete()
            db.session.commit()
            
            # Create initial feedback
            feedback1 = Feedback(user_id=test_user.id, message_id=test_message.id, rating='positive')
            db.session.add(feedback1)
            db.session.commit()
            db.session.refresh(feedback1)
            
            # Verify initial feedback exists
            assert Feedback.query.filter_by(message_id=test_message.id, user_id=test_user.id).count() == 1
        
        response = authenticated_client.post('/api/feedback', json={
            'message_id': test_message.id,
            'rating': 'negative',
            'comment': 'Changed my mind'
        })
        
        assert response.status_code == 200
        
        with app.app_context():
            feedbacks = Feedback.query.filter_by(message_id=test_message.id, user_id=test_user.id).all()
            assert len(feedbacks) == 1
            assert feedbacks[0].rating == 'negative'

"""Tests for authentication"""
import pytest
from src.database import db, User


class TestRegistration:
    """Tests for user registration"""
    
    def test_register_success(self, client, app):
        """Test successful user registration"""
        with app.app_context():
            User.query.filter_by(email='newuser@example.com').delete()
            db.session.commit()
        
        response = client.post('/auth/register', data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        with app.app_context():
            user = User.query.filter_by(username='newuser').first()
            assert user is not None
            assert user.check_password('password123')
    
    def test_register_duplicate_email(self, client, app, test_user):
        """Test registration with duplicate email fails"""
        with app.app_context():
            db.session.merge(test_user)
            db.session.commit()
        
        response = client.post('/auth/register', data={
            'username': 'different',
            'email': 'test@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        
        assert response.status_code == 200
        assert b'Email already registered' in response.data or b'already exists' in response.data.lower()
    
    def test_register_password_mismatch(self, client):
        """Test registration with mismatched passwords fails"""
        response = client.post('/auth/register', data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'password123',
            'confirm_password': 'different'
        })
        
        assert response.status_code == 200
        assert b'Passwords do not match' in response.data or b'do not match' in response.data.lower()


class TestLogin:
    """Tests for user login"""
    
    def test_login_success(self, client, app, test_user):
        """Test successful login"""
        with app.app_context():
            db.session.merge(test_user)
            db.session.commit()
        
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_login_wrong_password(self, client, app, test_user):
        """Test login with wrong password fails"""
        with app.app_context():
            db.session.merge(test_user)
            db.session.commit()
        
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'wrong'
        })
        
        assert response.status_code == 200
        assert b'Invalid' in response.data or b'invalid' in response.data.lower()


class TestProtectedRoutes:
    """Tests for route protection"""
    
    def test_chat_requires_login(self, client):
        """Test chat page requires authentication"""
        response = client.get('/chat', follow_redirects=True)
        assert b'Login' in response.data or response.status_code == 401

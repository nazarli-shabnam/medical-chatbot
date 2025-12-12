"""
Pytest configuration and fixtures
"""
import pytest
import os
import tempfile
import shutil
import threading
import gc
from src.database import db, User, Document, Conversation, Message, Citation, Feedback, DocumentChunk

# Set testing environment BEFORE importing app to prevent global resource creation
os.environ["TESTING"] = "1"
os.environ["PYTEST_CURRENT_TEST"] = "1"

from app import app as flask_app
from werkzeug.security import generate_password_hash


@pytest.fixture(scope='session')
def app():
    """Create application for testing"""
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['SECRET_KEY'] = 'test-secret-key'
    flask_app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
    flask_app.config['WTF_CSRF_ENABLED'] = False
    
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        try:
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        except Exception:
            pass
    
    if os.path.exists(flask_app.config['UPLOAD_FOLDER']):
        shutil.rmtree(flask_app.config['UPLOAD_FOLDER'])


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def test_user(app):
    """Create a test user"""
    with app.app_context():
        User.query.filter_by(email='test@example.com').delete()
        db.session.commit()
        
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


@pytest.fixture
def authenticated_client(client, app, test_user):
    """Create authenticated test client"""
    with app.app_context():
        db.session.merge(test_user)
        db.session.commit()
    
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'testpass123'
    }, follow_redirects=True)
    return client


@pytest.fixture
def test_document(app, test_user):
    """Create a test document"""
    with app.app_context():
        test_user = db.session.merge(test_user)
        db.session.commit()
        
        doc = Document(
            user_id=test_user.id,
            filename='test.pdf',
            original_filename='test.pdf',
            file_path='/test/test.pdf',
            file_size=1024
        )
        db.session.add(doc)
        db.session.commit()
        db.session.refresh(doc)
        return doc


@pytest.fixture
def test_conversation(app, test_user):
    """Create a test conversation"""
    with app.app_context():
        test_user = db.session.merge(test_user)
        db.session.commit()
        
        conv = Conversation(user_id=test_user.id)
        db.session.add(conv)
        db.session.commit()
        db.session.refresh(conv)
        return conv


@pytest.fixture
def test_message(app, test_conversation):
    """Create a test message"""
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
        db.session.refresh(msg)
        return msg


@pytest.fixture(autouse=True)
def mock_embeddings(monkeypatch):
    """Mock embeddings to prevent loading real PyTorch models"""
    class MockEmbeddings:
        def embed_query(self, text):
            return [0.1] * 384
        def embed_documents(self, texts):
            return [[0.1] * 384] * len(texts)
    
    monkeypatch.setattr('src.helper.download_hugging_face_embeddings', lambda: MockEmbeddings())


@pytest.fixture
def mock_pinecone(monkeypatch):
    """Mock Pinecone vector store"""
    class MockVectorStore:
        def as_retriever(self, **kwargs):
            class MockRetriever:
                def invoke(self, query):
                    return []
            return MockRetriever()
    
    monkeypatch.setattr('langchain_pinecone.PineconeVectorStore.from_existing_index', 
                       lambda *args, **kwargs: MockVectorStore())


@pytest.fixture
def mock_gemini(monkeypatch):
    """Mock Gemini LLM"""
    from langchain_core.runnables import Runnable
    from typing import Any
    
    class MockLLM(Runnable):
        def invoke(self, input, config=None, **kwargs):
            if isinstance(input, dict):
                if "original_query" in input:
                    return f"Rewritten: {input['original_query']}"
                elif "question" in input and "context" in input:
                    return "DIRECT: Mocked answer"
                elif "original_query" in input and "sub_questions" in input:
                    return "Mocked comprehensive answer"
            return "Mocked response from Gemini"
        
        def __or__(self, other):
            from langchain_core.runnables import RunnableSequence
            return RunnableSequence(self, other)
        
        def __ror__(self, other):
            from langchain_core.runnables import RunnableSequence
            return RunnableSequence(other, self)
    
    monkeypatch.setattr('langchain_google_genai.ChatGoogleGenerativeAI', lambda *args, **kwargs: MockLLM())


@pytest.fixture(autouse=True)
def cleanup_after_test(app):
    """Clean up database after each test"""
    yield
    with app.app_context():
        try:
            db.session.expire_all()
            db.session.remove()
        except Exception:
            pass


def pytest_sessionfinish(session, exitstatus):
    """Force exit after all tests complete"""
    import time
    
    print("\n" + "="*70)
    print("CLEANUP: Starting test session cleanup...")
    print("="*70)
    
    try:
        with flask_app.app_context():
            try:
                db.session.remove()
                print("✓ Database session removed")
            except Exception as e:
                print(f"✗ Error removing session: {e}")
            try:
                db.engine.dispose()
                print("✓ Database engine disposed")
            except Exception as e:
                print(f"✗ Error disposing engine: {e}")
    except Exception as e:
        print(f"✗ Error in database cleanup: {e}")
    
    try:
        for i in range(3):
            collected = gc.collect()
            if i == 0:
                print(f"✓ Garbage collection: {collected} objects collected")
    except Exception as e:
        print(f"✗ Error in resource cleanup: {e}")
    
    time.sleep(0.2)
    
    active_threads = [t for t in threading.enumerate() 
                     if t.is_alive() and not t.daemon and t != threading.current_thread()]
    
    if active_threads:
        print(f"\n⚠️  WARNING: {len(active_threads)} non-daemon threads still active")
        time.sleep(1)
    else:
        print("✓ No lingering non-daemon threads")
    
    print("="*70)
    print(f"FORCING EXIT with status: {exitstatus if exitstatus is not None else 0}")
    print("="*70 + "\n")
    
    import os
    os._exit(exitstatus if exitstatus is not None else 0)


import atexit
def cleanup_on_exit():
    import os
    try:
        with flask_app.app_context():
            db.session.remove()
            db.engine.dispose()
    except:
        pass
    for _ in range(3):
        gc.collect()
    os._exit(0)

atexit.register(cleanup_on_exit)

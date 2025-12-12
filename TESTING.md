# Testing Guide

## Quick Start

**Normal usage** - Just run tests directly (tests directory is mounted, changes sync automatically):

```bash
docker-compose exec app pytest
```

Run with verbose output:

```bash
docker-compose exec app pytest -v
```

**When to restart the container:**

Only run `.\restart_tests.ps1` (or restart manually) if:
- Tests are hanging/not exiting
- Tests are running old cached files
- You see errors about missing test files that should exist
- Python bytecode cache is causing issues

For normal test runs after making changes, just run `docker-compose exec app pytest` directly.

## Test Structure

The test suite is organized into focused test files:

- `tests/conftest.py` - Pytest fixtures and configuration
- `tests/test_auth.py` - Authentication tests (registration, login, protected routes)
- `tests/test_database.py` - Database model tests (User, Document, Conversation, Message, etc.)
- `tests/test_chat_api.py` - Chat API tests (streaming, conversations, messages)
- `tests/test_documents_api.py` - Document management tests (upload, deletion)
- `tests/test_feedback_api.py` - Feedback system tests
- `tests/test_helpers.py` - Helper function tests (filtering, text splitting, embeddings)
- `tests/test_integration.py` - Integration tests (complete user flows, multi-user isolation)
- `tests/test_utils.py` - Test utility functions

## Running Specific Tests

```bash
# Run specific test file
docker-compose exec app pytest tests/test_auth.py

# Run specific test class
docker-compose exec app pytest tests/test_auth.py::TestRegistration

# Run specific test function
docker-compose exec app pytest tests/test_auth.py::TestRegistration::test_register_success

# Run tests matching a pattern
docker-compose exec app pytest -k "login"

# Run with short traceback
docker-compose exec app pytest --tb=short

# Run quietly (minimal output)
docker-compose exec app pytest -q
```

## Test Configuration

- **Database**: Uses in-memory SQLite (`sqlite:///:memory:`) for fast, isolated tests
- **Mocks**: External services (Pinecone, Gemini, embeddings) are automatically mocked
- **Isolation**: Each test runs in isolation with clean database state
- **Cleanup**: Automatic cleanup after each test and forced exit after all tests

## Test Fixtures

Available fixtures (defined in `conftest.py`):

- `app` - Flask application instance with test database
- `client` - Test client for making HTTP requests
- `test_user` - Creates a test user (username: `testuser`, email: `test@example.com`)
- `authenticated_client` - Test client with logged-in user
- `test_document` - Creates a test document
- `test_conversation` - Creates a test conversation
- `test_message` - Creates a test message
- `mock_pinecone` - Mocks Pinecone vector store
- `mock_gemini` - Mocks Gemini LLM
- `mock_embeddings` - Automatically mocks embeddings (autouse fixture)

## Writing Tests

### Example: Testing an API Endpoint

```python
def test_chat_stream_requires_auth(client):
    """Test chat stream requires authentication"""
    response = client.post('/api/chat/stream', json={'message': 'test'})
    assert response.status_code in [401, 403, 302]
```

### Example: Testing with Authentication

```python
def test_get_conversations(authenticated_client, app, test_user):
    """Test getting user's conversations"""
    with app.app_context():
        test_user = db.session.merge(test_user)
        # Setup test data
    
    response = authenticated_client.get('/api/conversations')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
```

### Example: Testing Database Models

```python
def test_create_user(app):
    """Test creating a user"""
    with app.app_context():
        user = User(username='newuser', email='newuser@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        assert user.id is not None
        assert user.check_password('password123')
```

## Best Practices

1. **Use fixtures** for common setup (test_user, authenticated_client, etc.)
2. **Merge fixtures** when accessing in app context: `db.session.merge(test_user)`
3. **Clean up data** before creating new test data to avoid conflicts
4. **Consume streams** when testing streaming endpoints to prevent hanging
5. **Use descriptive test names** that explain what is being tested
6. **Keep tests isolated** - each test should be independent
7. **Test edge cases** - not just happy paths

## Troubleshooting

### Tests Fail with Database Errors

- Ensure fixtures are properly merging objects: `db.session.merge(test_user)`
- Check that test data is cleaned up before creating new data
- Verify database session is properly managed

### Tests Hang/Don't Exit

- The test suite includes forced exit mechanism - if tests hang, check for:
  - Unconsumed streaming responses (use `consume_stream()` helper)
  - Background threads from third-party libraries
  - Database connections not being closed

### Import Errors

- Make sure all dependencies are installed in the container
- Check that test files are in the `tests/` directory
- Verify Python path includes the project root

## Test Coverage

Generate coverage report:

```bash
# Generate HTML coverage report
docker-compose exec app pytest --cov=src --cov=app --cov-report=html

# Coverage report will be in htmlcov/index.html
```

View coverage in terminal:

```bash
docker-compose exec app pytest --cov=src --cov=app --cov-report=term
```

## Notes

- Tests use mocked external services to avoid API costs and ensure fast execution
- The test suite automatically forces exit after completion to prevent hanging
- All tests run in isolation with a fresh in-memory database

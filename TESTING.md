# Testing Guide

## Running Tests in Docker

### Option 1: Run tests inside the app container (Recommended)

```bash
# Start the database first
docker-compose up -d db

# Run all tests
docker-compose exec app pytest

# Run with verbose output
docker-compose exec app pytest -v

# Run specific test file
docker-compose exec app pytest tests/test_auth.py

# Run with coverage
docker-compose exec app pytest --cov=src --cov=app

# Run with HTML coverage report
docker-compose exec app pytest --cov=src --cov=app --cov-report=html
```

### Option 2: Use the test service (if configured)

```bash
docker-compose --profile test up test
```

### Option 3: Run tests locally (without Docker)

```bash
# Make sure you have PostgreSQL running locally
# Set environment variables
export DATABASE_URL=postgresql://user:pass@localhost:5432/test_db
export PINECONE_API_KEY=your_key
export GOOGLE_API_KEY=your_key
export SECRET_KEY=test-secret-key

# Run tests
pytest
```

## Test Structure

- `tests/conftest.py` - Pytest fixtures and configuration
- `tests/test_auth.py` - Authentication tests
- `tests/test_chat_api.py` - Chat API tests
- `tests/test_database.py` - Database model tests
- `tests/test_documents_api.py` - Document management tests
- `tests/test_feedback_api.py` - Feedback system tests
- `tests/test_helpers.py` - Helper function tests
- `tests/test_integration.py` - Integration tests
- `tests/test_rag_advanced.py` - Advanced RAG tests

## Test Configuration

Tests use an in-memory SQLite database by default (configured in `conftest.py`).
This ensures tests run quickly and don't require a real database.

## Running Specific Tests

```bash
# Run only unit tests
docker-compose exec app pytest -m unit

# Run only integration tests
docker-compose exec app pytest -m integration

# Run tests matching a pattern
docker-compose exec app pytest -k "test_login"

# Run with coverage report
docker-compose exec app pytest --cov=src --cov=app --cov-report=html

# Run with short traceback
docker-compose exec app pytest --tb=short

# Run with line traceback
docker-compose exec app pytest --tb=line
```

## Test Coverage

### Generate Coverage Report

```bash
# Generate HTML coverage report
docker-compose exec app pytest --cov=src --cov=app --cov-report=html

# Coverage report will be in htmlcov/index.html
# View it by opening the file in a browser
```

### View Coverage in Terminal

```bash
docker-compose exec app pytest --cov=src --cov=app --cov-report=term
```

## Test Fixtures

The test suite includes several useful fixtures (defined in `conftest.py`):

- `app` - Flask application instance with test database
- `client` - Test client for making requests
- `runner` - CLI test runner
- `test_user` - Creates a test user
- `authenticated_client` - Test client with logged-in user
- `test_document` - Creates a test document
- `test_conversation` - Creates a test conversation
- `test_message` - Creates a test message
- `mock_pinecone` - Mocks Pinecone vector store
- `mock_gemini` - Mocks Gemini LLM
- `mock_embeddings` - Mocks embeddings

## Writing Tests

### Example: Testing an API Endpoint

```python
def test_upload_document(authenticated_client, mock_pinecone, mock_gemini, mock_embeddings):
    """Test document upload"""
    with open('test.pdf', 'rb') as f:
        response = authenticated_client.post(
            '/api/upload',
            data={'file': (f, 'test.pdf')},
            content_type='multipart/form-data'
        )
    assert response.status_code == 200
    assert response.json['success'] == True
```

### Example: Testing Database Models

```python
def test_user_creation(app):
    """Test user creation"""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        assert user.id is not None
        assert user.check_password('password123')
```

## Troubleshooting

### Tests Fail with Database Errors
- Ensure test database is properly configured
- Check that `conftest.py` is using in-memory SQLite
- Verify fixtures are working correctly

### Tests Fail with Import Errors
- Make sure all dependencies are installed in the container
- Check that the test files are in the correct location
- Verify Python path includes the project root

### Tests Timeout
- Check if database container is running
- Verify network connectivity between containers
- Increase timeout values if needed

### Coverage Report Not Generated
- Make sure `pytest-cov` is installed
- Check that `--cov` flags are correct
- Verify output directory permissions

## CI/CD Integration

Tests are automatically run in CI/CD pipeline (`.github/workflows/ci.yml`):

- Runs on every push and pull request
- Uses PostgreSQL service in GitHub Actions
- Generates coverage reports
- Uploads coverage to Codecov

## Best Practices

1. **Use fixtures** for common setup/teardown
2. **Mock external services** (Pinecone, Gemini) in tests
3. **Use descriptive test names** that explain what is being tested
4. **Keep tests isolated** - each test should be independent
5. **Clean up after tests** - use fixtures for cleanup
6. **Test edge cases** - not just happy paths
7. **Use assertions** that provide clear error messages

## Running Tests During Development

```bash
# Watch mode (requires pytest-watch)
docker-compose exec app ptw

# Run only failed tests from last run
docker-compose exec app pytest --lf

# Run tests in parallel (requires pytest-xdist)
docker-compose exec app pytest -n auto
```


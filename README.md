# Medical Chatbot

A comprehensive medical chatbot application built with Flask, Gemini AI, Pinecone, and PostgreSQL. Features real-time chat with document-based RAG (Retrieval-Augmented Generation), source citations, conversation history, and advanced query processing.

## 🚀 Quick Start

### Prerequisites

- **Docker Desktop** installed ([Download here](https://www.docker.com/products/docker-desktop))
- **Pinecone API Key** ([Get one here](https://www.pinecone.io/))
- **Google Gemini API Key** ([Get one here](https://makersuite.google.com/app/apikey))

### First Time Setup

1. **Create `.env` file** in the project root:

   ```ini
   PINECONE_API_KEY=your_pinecone_key_here
   GOOGLE_API_KEY=your_gemini_key_here
   SECRET_KEY=change-this-to-random-string-in-production
   GEMINI_MODEL=gemini-2.5-flash
   ```

2. **Start the application**:

   ```bash
   docker-compose up --build
   ```

3. **Open browser**: http://localhost:8080

4. **Register an account** and start chatting!

For detailed Docker setup and running instructions, see [DOCKER_SETUP.md](DOCKER_SETUP.md).

## ✨ Features

- ✅ **User Authentication** - Secure registration and login system
- ✅ **Multi-Document Upload** - Upload and manage multiple PDF documents
- ✅ **Real-time Chat** - Streaming responses with immediate feedback
- ✅ **Source Citations** - Transparent source attribution with clickable citations
- ✅ **Conversation History** - Persistent chat history per user
- ✅ **User Feedback** - Thumbs up/down feedback system
- ✅ **Advanced RAG** - Query rewriting and multi-hop reasoning
- ✅ **Document Management** - View, manage, and delete uploaded documents

## 🏗️ Architecture

- **Backend**: Flask (Python 3.10)
- **Database**: PostgreSQL 15 (Docker container)
- **Vector Store**: Pinecone (384-dimensional embeddings)
- **LLM**: Google Gemini (configurable model)
- **Embeddings**: HuggingFace sentence-transformers (all-MiniLM-L6-v2)
- **Frontend**: HTML/CSS/JavaScript with Bootstrap

## 📁 Project Structure

```
medical-chatbot/
├── app.py                  # Main Flask application
├── docker-compose.yml      # Docker Compose configuration
├── Dockerfile              # Application container definition
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create this)
├── src/                    # Source code
│   ├── database.py        # Database models (User, Document, Conversation, etc.)
│   ├── auth.py            # Authentication routes
│   ├── helper.py          # Helper functions (PDF loading, text splitting)
│   ├── prompt.py          # System prompts
│   └── rag_advanced.py    # Advanced RAG features (query rewriting, multi-hop)
├── tests/                  # Test suite
│   ├── conftest.py        # Pytest fixtures
│   ├── test_auth.py       # Authentication tests
│   ├── test_chat_api.py   # Chat API tests
│   ├── test_database.py   # Database model tests
│   ├── test_documents_api.py  # Document management tests
│   ├── test_feedback_api.py      # Feedback system tests
│   ├── test_integration.py       # Integration tests
│   └── test_rag_advanced.py      # Advanced RAG tests
├── templates/              # HTML templates
│   ├── base.html          # Base template with navbar
│   ├── chat.html          # Chat interface
│   ├── documents.html     # Document management page
│   ├── login.html         # Login page
│   └── register.html      # Registration page
├── static/                 # CSS/JS files
│   └── style.css          # Custom styles
└── data/
    └── uploads/           # Uploaded PDFs (persisted via Docker volume)
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root with:

```ini
# Required
PINECONE_API_KEY=your_pinecone_api_key
GOOGLE_API_KEY=your_gemini_api_key
SECRET_KEY=your-random-secret-key-change-in-production

# Optional (with defaults)
GEMINI_MODEL=gemini-2.5-flash  # Default: gemini-2.5-flash
DATABASE_URL=postgresql://medicalbot:medicalbot_password@db:5432/medical_chatbot  # Auto-set by docker-compose
```

For detailed Docker setup instructions, see [DOCKER_SETUP.md](DOCKER_SETUP.md).

## 🧪 Testing

For comprehensive testing instructions, see [TESTING.md](TESTING.md).

Quick start:

```bash
# Run all tests
docker-compose exec app pytest

# Run with coverage
docker-compose exec app pytest --cov=src --cov=app
```

## 🔌 API Endpoints

### Authentication

- `GET /auth/login` - Login page
- `POST /auth/login` - Login
- `GET /auth/register` - Registration page
- `POST /auth/register` - Register new user
- `GET /auth/logout` - Logout

### Chat

- `GET /chat` - Chat interface
- `POST /api/chat/stream` - Stream chat response (Server-Sent Events)
  - Body: `{ "message": "...", "conversation_id": 123, "use_advanced_rag": false }`

### Documents

- `GET /documents` - Document management page
- `POST /api/upload` - Upload new PDF document (multipart/form-data)
- `DELETE /api/documents/<id>` - Delete document

### Conversations

- `GET /api/conversations` - Get user's conversations
- `GET /api/conversations/<id>/messages` - Get messages for conversation

### Feedback

- `POST /api/feedback` - Submit feedback for a message
  - Body: `{ "message_id": 123, "rating": "positive|negative", "comment": "..." }`

## 🗄️ Database Schema

- **User** - User accounts with authentication
- **Document** - Uploaded PDF documents metadata
- **DocumentChunk** - Chunk metadata for citations
- **Conversation** - Chat conversations
- **Message** - Individual messages in conversations
- **Citation** - Source citations for messages
- **Feedback** - User feedback on messages

## 🚀 Advanced Features

### Query Rewriting

Automatically improves user queries for better document retrieval. Enabled by default in standard RAG mode.

### Multi-hop Reasoning

Breaks down complex questions into sub-questions and retrieves information iteratively. Enable via the "Advanced RAG" toggle in the chat interface.

### Source Citations

Every response includes citations to source documents with:

- Document name
- Page number
- Content preview
- Clickable badges for easy navigation

## 🐛 Troubleshooting

### Gemini Model Not Found Error

If you see `404 models/gemini-pro is not found`:

1. **Check available models**:

   ```bash
   docker-compose exec app python -c "
   from google import generativeai as genai
   import os
   genai.configure(api_key=os.environ.get('GOOGLE_API_KEY'))
   for model in genai.list_models():
       if 'generateContent' in model.supported_generation_methods:
           print(f'{model.name}')
   "
   ```

2. **Update `.env` file** with a model from the list:

   ```ini
   GEMINI_MODEL=gemini-2.5-flash  # or gemini-2.5-pro, gemini-pro-latest, etc.
   ```

3. **Restart the app**:
   ```bash
   docker-compose restart app
   ```

### File Upload Not Working

- Check that the upload folder exists and is writable
- Verify file size is under 16MB
- Check browser console for errors
- Ensure you're logged in (authentication required)

For more troubleshooting tips, see [DOCKER_SETUP.md](DOCKER_SETUP.md).

## 🧪 Testing

Run tests with:

```bash
docker-compose exec app pytest
```

**Note:** The tests directory is mounted, so you can edit tests and run them immediately without restarting. Only restart the container if tests are hanging or using cached files.

For more details, see [TESTING.md](TESTING.md).

## 🔄 CI/CD

This project uses **GitHub Actions** for continuous integration and continuous delivery. Both workflows are automatically triggered on pushes to the `main` branch.

### Continuous Integration (CI)

#### What the CI Does

1. **Build & Test**: Sets up Python 3.10 and PostgreSQL 15
2. **Install Dependencies**: Installs all requirements and removes deprecated packages
3. **Run Tests**: Executes the full test suite with pytest
4. **Generate Coverage**: Creates code coverage reports
5. **Upload Coverage**: Uploads coverage to Codecov (optional)

#### CI Workflow

The workflow file is located at `.github/workflows/ci.yml`. It:

- **Triggers**: Runs on pushes and pull requests to `main` branch
- **Database**: Uses PostgreSQL 15 as a service container
- **Tests**: Runs full pytest test suite with coverage reporting
- **Output**: Generates coverage reports in XML and HTML formats

### Continuous Delivery (CD)

#### What the CD Does

1. **Build Docker Image**: Creates a production-ready Docker image
2. **Push to Registry**: Uploads the image to GitHub Container Registry (ghcr.io)
3. **Tag Images**: Tags with `latest` and the commit SHA for versioning

#### CD Workflow

The workflow file is located at `.github/workflows/cd.yml`. It:

- **Triggers**: Runs only on pushes to `main` branch (after CI passes)
- **Registry**: Pushes to GitHub Container Registry (`ghcr.io`)
- **Image Tags**:
  - `ghcr.io/[owner]/medical-chatbot:latest` - Always points to latest
  - `ghcr.io/[owner]/medical-chatbot:[commit-sha]` - Specific version
- **Caching**: Uses Docker layer caching for faster builds

#### Pulling the CD Image

After CD runs, you can pull the image:

```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Pull the latest image
docker pull ghcr.io/[your-username]/medical-chatbot:latest

# Or pull a specific version
docker pull ghcr.io/[your-username]/medical-chatbot:[commit-sha]
```

### Setting Up GitHub Secrets

**Required Secrets** (must be set manually):

1. Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add these secrets:

   - **`PINECONE_API_KEY`**

     - **Purpose**: Required for CI tests (mocked in tests, but still needed)
     - **Where to get**: [Pinecone Console](https://app.pinecone.io/)
     - **Required for**: CI workflow

   - **`GOOGLE_API_KEY`**
     - **Purpose**: Required for CI tests (mocked in tests, but still needed)
     - **Where to get**: [Google AI Studio](https://makersuite.google.com/app/apikey)
     - **Required for**: CI workflow

**Automatic Secrets** (no action needed):

- **`GITHUB_TOKEN`**: Automatically provided by GitHub Actions
  - **Purpose**: Used by CD workflow to push to GitHub Container Registry
  - **No setup required**: GitHub automatically provides this token

### Workflow Summary

| Workflow | Trigger           | Purpose                       | Secrets Needed                       |
| -------- | ----------------- | ----------------------------- | ------------------------------------ |
| **CI**   | Push/PR to `main` | Run tests & generate coverage | `PINECONE_API_KEY`, `GOOGLE_API_KEY` |
| **CD**   | Push to `main`    | Build & push Docker image     | `GITHUB_TOKEN` (automatic)           |

### Viewing Workflow Results

- **Check Status**: Go to the **Actions** tab in your GitHub repository
- **CI Results**: View test results, coverage reports, and any failures
- **CD Results**: See Docker image build logs and registry push status
- **Coverage**: Reports are uploaded to Codecov (if configured)

### Troubleshooting

**CI fails with "secret not found"**:

- Ensure `PINECONE_API_KEY` and `GOOGLE_API_KEY` are set in repository secrets
- Check that secrets are spelled exactly as shown (case-sensitive)

**CD fails with authentication error**:

- `GITHUB_TOKEN` is automatic - no setup needed
- If issues persist, check repository permissions in Settings → Actions → General

**CD image not accessible**:

- Make sure the repository is public, OR
- Set package visibility: Go to repository → Packages → medical-chatbot → Package settings → Change visibility

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `docker-compose exec app pytest`
5. Submit a pull request (CI will automatically run tests)

## 📞 Support

For issues and questions, please open an issue on GitHub.

## 📄 License

See LICENSE file

---

**Note**: This application uses Google Gemini AI for generating responses. Make sure you have a valid API key and that billing is enabled on your Google Cloud project if required for your chosen model.

**Documentation**:

- [DOCKER_SETUP.md](DOCKER_SETUP.md) - Detailed Docker setup and running instructions
- [TESTING.md](TESTING.md) - Comprehensive testing guide

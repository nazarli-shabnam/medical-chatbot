from src.auth import auth_bp
from flask import Flask, render_template, jsonify, request, stream_with_context, Response, redirect, session
from flask_login import LoginManager, login_required, current_user
from src.database import db, User, Conversation, Message, Document, DocumentChunk, Citation, Feedback
from src.helper import download_hugging_face_embeddings, load_single_pdf, filter_to_minimal_docs, text_split
from langchain_pinecone import PineconeVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
from src.prompt import system_prompt_with_citations
from src.rag_advanced import rewrite_query, multi_hop_reasoning
import os
import json
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
import tempfile

IS_TESTING = os.environ.get("TESTING") == "1" or os.environ.get(
    "PYTEST_CURRENT_TEST") is not None

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY', 'dev-secret-key-change-in-production')

database_url = os.environ.get('DATABASE_URL')
if IS_TESTING:
    database_url = 'sqlite:///:memory:'
if not database_url:
    database_url = 'postgresql://medicalbot:medicalbot_password@db:5432/medical_chatbot'

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp(
) if IS_TESTING else 'data/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

load_dotenv()

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


app.register_blueprint(auth_bp, url_prefix='/auth')

if IS_TESTING:
    # Lightweight stubs for tests to avoid external services
    from langchain_core.runnables import Runnable
    from langchain_core.runnables.utils import Input, Output
    from typing import Any

    class _DummyLLM(Runnable[Input, Output]):
        """Dummy LLM for testing that implements Runnable interface"""

        def invoke(self, input: Input, config: Any = None, **kwargs: Any) -> Output:
            if isinstance(input, dict):
                return "Test response"
            elif isinstance(input, str):
                return "Test response"
            return "Test response"

        def __or__(self, other):
            from langchain_core.runnables import RunnableSequence
            return RunnableSequence(self, other)

        def __ror__(self, other):
            from langchain_core.runnables import RunnableSequence
            return RunnableSequence(other, self)

    class _DummyRetriever:
        def invoke(self, query):
            return []
    llm = _DummyLLM()
    embeddings = None
    docsearch = None
    retriever = _DummyRetriever()
    index_name = "test-index"
    print("Running in TESTING mode: using in-memory DB and dummy LLM/retriever.")
else:
    PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

    if not PINECONE_API_KEY:
        raise ValueError("PINECONE_API_KEY not found in environment variables")
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")

    os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

    print("Initializing embeddings model...")
    try:
        embeddings = download_hugging_face_embeddings()
        print("✓ Embeddings model loaded successfully")
    except Exception as e:
        print(f"✗ Failed to load embeddings model: {e}")
        raise

    index_name = "medical-chatbot"

    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')
    print(f"Initializing Gemini LLM (model: {GEMINI_MODEL})...")
    try:
        llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            temperature=0.7,
            google_api_key=GOOGLE_API_KEY
        )
        print(f"✓ Gemini LLM initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize Gemini LLM: {e}")
        raise

    print("Connecting to Pinecone vector store...")
    try:
        docsearch = PineconeVectorStore.from_existing_index(
            index_name=index_name,
            embedding=embeddings
        )
        retriever = docsearch.as_retriever(
            search_type="similarity", search_kwargs={"k": 5})
        print("✓ Pinecone connection established successfully")
    except Exception as e:
        print(f"✗ Failed to connect to Pinecone: {e}")
        print("  Make sure your PINECONE_API_KEY is valid and the index 'medical-chatbot' exists")
        raise


@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect('/chat')
    return redirect('/auth/login')


@app.route("/chat")
@login_required
def chat():
    if not session.get('_user_id') or not current_user.is_authenticated:
        return redirect('/auth/login')
    return render_template('chat.html')


@app.route("/documents")
@login_required
def documents():
    """Show only documents that actually exist on the filesystem"""
    if not session.get('_user_id') or not current_user.is_authenticated:
        return redirect('/auth/login')
    user_docs = Document.query.filter_by(user_id=current_user.id).order_by(
        Document.uploaded_at.desc()).all()
    if IS_TESTING:
        existing_docs = user_docs
    else:
        existing_docs = []
        for doc in user_docs:
            if os.path.exists(doc.file_path):
                existing_docs.append(doc)
            else:
                print(
                    f"Document {doc.id} ({doc.original_filename}) file not found at {doc.file_path}, cleaning up database")
                try:
                    from src.database import Citation

                    doc_citations = Citation.query.filter_by(
                        document_id=doc.id).all()

                    chunk_ids = [
                        chunk.id for chunk in doc.chunks] if doc.chunks else []

                    chunk_citations = []
                    if chunk_ids:
                        chunk_citations = Citation.query.filter(
                            Citation.chunk_id.in_(chunk_ids)).all()

                    all_citations = list(set(doc_citations + chunk_citations))

                    for citation in all_citations:
                        if citation.document_id == doc.id:
                            citation.document_id = None
                        if citation.chunk_id in chunk_ids:
                            citation.chunk_id = None
                        db.session.add(citation)

                    db.session.commit()

                    db.session.delete(doc)
                    db.session.commit()
                    print(f"Successfully cleaned up document {doc.id}")
                except Exception as e:
                    import traceback
                    print(f"Error cleaning up missing document {doc.id}: {e}")
                    print(traceback.format_exc())
                    db.session.rollback()
                    continue

    return render_template('documents.html', documents=existing_docs)


@app.route("/api/chat/stream", methods=["POST", "GET", "OPTIONS"])
@login_required
def chat_stream():
    """Stream chat response with citations"""
    if request.method == "OPTIONS":
        return Response(status=200)
    if request.method == "GET":
        return jsonify({"error": "Method not allowed. Use POST."}), 405

    print(f"INFO: /api/chat/stream called method={request.method}")
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    user_message = data.get('message', '')
    conversation_id = data.get('conversation_id')
    use_advanced_rag = data.get('use_advanced_rag', False)

    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    if conversation_id:
        conversation = Conversation.query.filter_by(
            id=conversation_id, user_id=current_user.id).first()
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404
    else:
        conversation = Conversation(user_id=current_user.id)
        db.session.add(conversation)
        db.session.commit()
        conversation_id = conversation.id

    user_msg = Message(
        conversation_id=conversation_id,
        role='user',
        content=user_message
    )
    db.session.add(user_msg)
    db.session.commit()

    user_id = current_user.id

    def generate():
        try:
            yield "data: {\"type\": \"heartbeat\"}\n\n"

            allowed_user_ids = {str(user_id), "global", None}

            user_docs = Document.query.filter_by(
                user_id=user_id, is_indexed=True).all()
            user_retriever = docsearch.as_retriever(
                search_type="similarity",
                search_kwargs={
                    "k": 8,
                    "filter": {"user_id": str(user_id)}
                }
            ) if user_docs else None

            base_retriever = retriever

            print(
                f"Retrievers ready. User docs: {len(user_docs)}. Using global + user-specific retrieval.")

            def filter_allowed(docs):
                filtered = [
                    d for d in docs
                    if d.metadata.get('user_id') in allowed_user_ids
                ]
                return filtered

            if use_advanced_rag:
                def filtered_retrieve(query):
                    docs = []
                    base_docs = base_retriever.invoke(query)
                    docs.extend(filter_allowed(base_docs))
                    if user_retriever:
                        user_docs_res = user_retriever.invoke(query)
                        docs.extend(filter_allowed(user_docs_res))

                    print(
                        f"Advanced RAG: Retrieved {len(docs)} combined docs (global + user) for user {user_id}")
                    return docs

                result = multi_hop_reasoning(
                    llm, filtered_retrieve, user_message, max_hops=2)
                retrieved_docs = result["context_used"]
                answer = result["answer"]
            else:
                rewritten_query = rewrite_query(llm, user_message)

                retrieved_docs = []

                base_docs = base_retriever.invoke(rewritten_query)
                base_docs = filter_allowed(base_docs)
                retrieved_docs.extend(base_docs)

                if user_retriever:
                    user_docs_res = user_retriever.invoke(rewritten_query)
                    user_docs_res = filter_allowed(user_docs_res)
                    retrieved_docs.extend(user_docs_res)

                print(
                    f"Retrieved {len(retrieved_docs)} documents total (global + user). Global: {len(base_docs)}, User: {len(user_docs_res) if user_retriever else 0}")

                for i, doc in enumerate(retrieved_docs[:3]):
                    print(f"  Doc {i+1}: source={doc.metadata.get('source', 'Unknown')}, user_id={doc.metadata.get('user_id', 'Unknown')}, document_id={doc.metadata.get('document_id', 'Unknown')}")

                if retrieved_docs:
                    formatted_context = "\n\n".join([
                        f"[Source {i+1}] {doc.page_content}\n(Source: {doc.metadata.get('source', 'Unknown')}, Page: {doc.metadata.get('page', 'N/A')})"
                        for i, doc in enumerate(retrieved_docs)
                    ])
                    print(
                        f"Formatted context length: {len(formatted_context)} characters from {len(retrieved_docs)} documents")
                else:
                    formatted_context = "No relevant documents found in the uploaded files."
                    print(
                        f"WARNING: No documents retrieved for user {user_id}")

                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt_with_citations),
                    ("human", "{input}"),
                ])
                chain = prompt | llm | StrOutputParser()
                answer = chain.invoke(
                    {"input": user_message, "context": formatted_context})
                print(f"Generated answer length: {len(answer)} characters")

            words = answer.split()
            full_answer = ""
            for word in words:
                full_answer += word + " "
                yield f"data: {json.dumps({'type': 'token', 'content': word + ' '})}\n\n"

            assistant_msg = Message(
                conversation_id=conversation_id,
                role='assistant',
                content=full_answer.strip()
            )
            db.session.add(assistant_msg)
            db.session.flush()

            for i, doc in enumerate(retrieved_docs):
                source = doc.metadata.get('source', 'Unknown')
                page = doc.metadata.get('page')

                doc_id = None
                chunk_id = None

                doc_obj = Document.query.filter_by(file_path=source).first()
                if doc_obj:
                    doc_id = doc_obj.id
                    chunk_obj = DocumentChunk.query.filter_by(
                        document_id=doc_id,
                        page_number=page
                    ).first()
                    if chunk_obj:
                        chunk_id = chunk_obj.id

                citation = Citation(
                    message_id=assistant_msg.id,
                    document_id=doc_id,
                    chunk_id=chunk_id,
                    page_number=page,
                    relevance_score=0.8,
                    content_snippet=doc.page_content[:200]
                )
                db.session.add(citation)

            db.session.commit()

            citations_data = []
            for i, doc in enumerate(retrieved_docs):
                source_path = doc.metadata.get('source', 'Unknown')
                source_name = os.path.basename(
                    source_path) if source_path != 'Unknown' else 'Unknown'
                citations_data.append({
                    'id': i+1,
                    'source': source_name,
                    'page': doc.metadata.get('page', 'N/A'),
                    'preview': doc.page_content[:150] + '...' if len(doc.page_content) > 150 else doc.page_content
                })

            yield f"data: {json.dumps({'type': 'citations', 'citations': citations_data, 'conversation_id': conversation_id})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'message_id': assistant_msg.id})}\n\n"

        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"Error in chat_stream: {error_msg}")
            print(traceback.format_exc())
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no'
    })


@app.route("/api/conversations", methods=["GET"])
@login_required
def get_conversations():
    """Get user's conversations"""
    if not session.get('_user_id') or not current_user.is_authenticated:
        return jsonify({"error": "Unauthorized"}), 401
    conversations = Conversation.query.filter_by(user_id=current_user.id)\
        .order_by(Conversation.updated_at.desc()).limit(20).all()

    result = []
    for conv in conversations:
        messages = Message.query.filter_by(
            conversation_id=conv.id).order_by(Message.created_at).all()
        result.append({
            'id': conv.id,
            'created_at': conv.created_at.isoformat(),
            'message_count': len(messages),
            'preview': messages[0].content[:100] if messages else ''
        })

    return jsonify(result)


@app.route("/api/conversations/<int:conversation_id>/messages", methods=["GET"])
@login_required
def get_messages(conversation_id):
    """Get messages for a conversation"""
    if not session.get('_user_id') or not current_user.is_authenticated:
        return jsonify({"error": "Unauthorized"}), 401
    conversation = Conversation.query.filter_by(
        id=conversation_id, user_id=current_user.id).first()
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404

    messages = Message.query.filter_by(conversation_id=conversation_id)\
        .order_by(Message.created_at).all()

    result = []
    for msg in messages:
        msg_data = {
            'id': msg.id,
            'role': msg.role,
            'content': msg.content,
            'created_at': msg.created_at.isoformat()
        }

        if msg.role == 'assistant':
            citations = Citation.query.filter_by(message_id=msg.id).all()
            msg_data['citations'] = []
            for cit in citations:
                source_name = 'Unknown'
                if cit.document_id:
                    doc = Document.query.get(cit.document_id)
                    if doc:
                        source_name = doc.original_filename
                msg_data['citations'].append({
                    'id': cit.id,
                    'source': source_name,
                    'page': cit.page_number,
                    'preview': cit.content_snippet
                })

            feedback = Feedback.query.filter_by(message_id=msg.id).first()
            if feedback:
                msg_data['feedback'] = feedback.rating

        result.append(msg_data)

    return jsonify(result)


@app.route("/api/upload", methods=["POST"])
@login_required
def upload_document():
    """Upload and index a new PDF document"""
    if not session.get('_user_id') or not current_user.is_authenticated:
        return jsonify({"error": "Unauthorized"}), 401
    print(f"Upload request received from user {current_user.id}")
    print(f"Request method: {request.method}")
    print(f"Request content type: {request.content_type}")
    print(f"Files in request: {list(request.files.keys())}")

    if 'file' not in request.files:
        print("Upload error: No file in request.files")
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    print(f"File received: {file.filename}, Content type: {file.content_type}")

    if file.filename == '':
        print("Upload error: Empty filename")
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.lower().endswith('.pdf'):
        print(f"Upload error: Invalid file type - {file.filename}")
        return jsonify({"error": "Only PDF files are supported"}), 400

    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

    print(f"Uploading file: {filename} -> {file_path}")
    file.save(file_path)
    print(f"File saved successfully: {os.path.exists(file_path)}")

    try:
        print(f"Loading PDF from: {file_path}")
        documents = load_single_pdf(file_path)
        print(f"Loaded {len(documents)} documents from PDF")
        if documents:
            print(
                f"First document preview: {documents[0].page_content[:200]}...")

        filtered_docs = filter_to_minimal_docs(documents)
        print(f"After filtering: {len(filtered_docs)} documents")

        text_chunks = text_split(filtered_docs)
        print(f"After text splitting: {len(text_chunks)} chunks")

        if len(text_chunks) == 0:
            print(f"ERROR: No text chunks created! PDF might be empty or corrupted.")
            return jsonify({"error": "PDF appears to be empty or could not be processed. Please check the file."}), 400

        doc = Document(
            user_id=current_user.id,
            filename=unique_filename,
            original_filename=filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            is_indexed=False
        )
        db.session.add(doc)
        db.session.flush()

        chunk_objects = []
        for i, chunk in enumerate(text_chunks):
            chunk_obj = DocumentChunk(
                document_id=doc.id,
                chunk_index=i,
                page_number=chunk.metadata.get('page', 0),
                content_preview=chunk.page_content[:200]
            )
            chunk_objects.append(chunk_obj)
            db.session.add(chunk_obj)

        db.session.flush()

        for chunk_obj in chunk_objects:
            if chunk_obj.id is None:
                print(f"Warning: chunk_obj.id is None after flush!")
                db.session.refresh(chunk_obj)
                print(f"After refresh: chunk_obj.id = {chunk_obj.id}")

        from langchain_pinecone import PineconeVectorStore
        vector_store = PineconeVectorStore.from_existing_index(
            index_name=index_name,
            embedding=embeddings
        )

        for chunk, chunk_obj in zip(text_chunks, chunk_objects):
            clean_metadata = {}

            original_source = chunk.metadata.get('source', file_path)
            clean_metadata['source'] = str(
                original_source) if original_source else str(file_path)

            for key, value in chunk.metadata.items():
                if key == 'source':
                    continue
                if value is not None:
                    if isinstance(value, (str, int, float, bool)):
                        clean_metadata[key] = value
                    elif isinstance(value, list):
                        clean_metadata[key] = [str(v)
                                               for v in value if v is not None]

            clean_metadata['document_id'] = str(doc.id)
            if chunk_obj.id is not None:
                clean_metadata['chunk_id'] = str(chunk_obj.id)
            clean_metadata['user_id'] = str(current_user.id)

            page = clean_metadata.get('page', chunk.metadata.get('page', 0))
            clean_metadata['page'] = int(page) if isinstance(
                page, (int, float)) else 0

            chunk.metadata = clean_metadata

            print(
                f"Chunk metadata: source={clean_metadata.get('source')}, document_id={clean_metadata.get('document_id')}, user_id={clean_metadata.get('user_id')}, page={clean_metadata.get('page')}")

        print(
            f"Adding {len(text_chunks)} chunks to Pinecone for user {current_user.id}")
        vector_store.add_documents(text_chunks)
        print(f"Successfully added documents to Pinecone")

        doc.is_indexed = True
        db.session.commit()

        return jsonify({
            "success": True,
            "document": {
                "id": doc.id,
                "filename": filename,
                "chunks": len(text_chunks)
            }
        })

    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Upload error: {error_msg}")
        print(traceback.format_exc())
        db.session.rollback()
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({"error": f"Error processing file: {error_msg}"}), 500


@app.route("/api/documents/<int:doc_id>", methods=["DELETE"])
@login_required
def delete_document(doc_id):
    """Delete a document"""
    if not session.get('_user_id') or not current_user.is_authenticated:
        return jsonify({"error": "Unauthorized"}), 401
    doc = Document.query.filter_by(id=doc_id, user_id=current_user.id).first()
    if not doc:
        return jsonify({"error": "Document not found"}), 404

    try:
        from src.database import Citation

        citations = Citation.query.filter_by(document_id=doc.id).all()

        chunk_ids = [chunk.id for chunk in doc.chunks]

        if chunk_ids:
            chunk_citations = Citation.query.filter(
                Citation.chunk_id.in_(chunk_ids)).all()
            all_citations = list(set(citations + chunk_citations))
        else:
            all_citations = citations

        for citation in all_citations:
            if citation.chunk_id in chunk_ids:
                citation.chunk_id = None
            if citation.document_id == doc.id:
                citation.document_id = None
            db.session.add(citation)

        db.session.flush()

        try:
            from pinecone import Pinecone
            pc = Pinecone(api_key=PINECONE_API_KEY)
            index = pc.Index(index_name)

            delete_filter = {
                "document_id": str(doc.id)
            }
            print(f"Deleting vectors from Pinecone for document_id={doc.id}")
            index.delete(filter=delete_filter)
            print(
                f"Successfully deleted vectors from Pinecone for document {doc.id}")
        except Exception as e:
            print(f"Warning: Could not delete vectors from Pinecone: {e}")
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
            print(f"Deleted file: {doc.file_path}")

        db.session.delete(doc)
        db.session.commit()

        return jsonify({"success": True})
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Delete error: {error_msg}")
        print(traceback.format_exc())
        db.session.rollback()
        return jsonify({"error": f"Error deleting document: {error_msg}"}), 500


@app.route("/api/cleanup-pinecone", methods=["POST"])
@login_required
def cleanup_pinecone():
    """Clean up orphaned vectors in Pinecone (vectors without corresponding documents in DB)"""
    try:
        from pinecone import Pinecone

        user_docs = Document.query.filter_by(user_id=current_user.id).all()
        valid_document_ids = {str(doc.id) for doc in user_docs}

        print(f"Cleaning up Pinecone for user {current_user.id}")
        print(
            f"Found {len(user_docs)} documents to delete (all user documents)")

        pc = Pinecone(api_key=PINECONE_API_KEY)
        index = pc.Index(index_name)

        user_filter = {"user_id": str(current_user.id)}

        deleted_count = 0

        print(f"Deleting all vectors for user {current_user.id} from Pinecone")
        index.delete(filter=user_filter)
        print(f"Deleted all vectors for user {current_user.id}")

        from src.database import Citation

        deleted_count = 0
        for doc in user_docs:
            citations = Citation.query.filter_by(document_id=doc.id).all()

            chunk_ids = [
                chunk.id for chunk in doc.chunks] if doc.chunks else []

            if chunk_ids:
                chunk_citations = Citation.query.filter(
                    Citation.chunk_id.in_(chunk_ids)).all()
                all_citations = list(set(citations + chunk_citations))
            else:
                all_citations = citations

            for citation in all_citations:
                if citation.document_id == doc.id:
                    citation.document_id = None
                if citation.chunk_id in chunk_ids:
                    citation.chunk_id = None
                db.session.add(citation)

            if os.path.exists(doc.file_path):
                try:
                    os.remove(doc.file_path)
                    print(f"Deleted file: {doc.file_path}")
                except Exception as e:
                    print(
                        f"Warning: Could not delete file {doc.file_path}: {e}")

            db.session.delete(doc)
            deleted_count += 1

        db.session.commit()
        print(f"Deleted {deleted_count} documents from database")

        return jsonify({
            "success": True,
            "message": f"Cleaned up Pinecone and deleted {deleted_count} document(s) from your account.",
            "deleted_count": deleted_count
        })

    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Cleanup error: {error_msg}")
        print(traceback.format_exc())
        db.session.rollback()
        return jsonify({"error": f"Error cleaning up Pinecone: {error_msg}"}), 500


@app.route("/api/feedback", methods=["POST"])
@login_required
def submit_feedback():
    """Submit feedback for a message"""
    if not session.get('_user_id') or not current_user.is_authenticated:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    message_id = data.get('message_id')
    rating = data.get('rating')
    comment = data.get('comment', '')

    if not message_id or rating not in ['positive', 'negative']:
        return jsonify({"error": "Invalid request"}), 400

    message = Message.query.get(message_id)
    if not message:
        return jsonify({"error": "Message not found"}), 404
    if message.conversation.user_id != current_user.id:
        return jsonify({"error": "Message not found"}), 404

    existing = Feedback.query.filter_by(
        message_id=message_id, user_id=current_user.id).first()
    if existing:
        existing.rating = rating
        existing.comment = comment
    else:
        feedback = Feedback(
            user_id=current_user.id,
            message_id=message_id,
            rating=rating,
            comment=comment
        )
        db.session.add(feedback)

    db.session.commit()
    return jsonify({"success": True})


# Initialize database tables
with app.app_context():
    try:
        print("Initializing database...")
        db.create_all()
        print("✓ Database initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize database: {e}")
        print("  Make sure DATABASE_URL is set correctly and the database is accessible")
        raise

if __name__ == '__main__':
    # Use PORT environment variable if available (for Render, Heroku, etc.), otherwise default to 8080
    port = int(os.environ.get('PORT', 8080))
    # Only use debug mode if explicitly set (not in production)
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host="0.0.0.0", port=port, debug=debug)

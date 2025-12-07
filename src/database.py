from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    conversations = db.relationship('Conversation', backref='user', lazy=True, cascade='all, delete-orphan')
    feedbacks = db.relationship('Feedback', backref='user', lazy=True, cascade='all, delete-orphan')
    documents = db.relationship('Document', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Document(db.Model):
    """Document model for storing uploaded PDFs metadata"""
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)  # in bytes
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_indexed = db.Column(db.Boolean, default=False)
    
    chunks = db.relationship('DocumentChunk', backref='document', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Document {self.original_filename}>'


class DocumentChunk(db.Model):
    """Store metadata about document chunks for citation"""
    __tablename__ = 'document_chunks'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    chunk_index = db.Column(db.Integer, nullable=False)  # Order in document
    page_number = db.Column(db.Integer)
    content_preview = db.Column(db.Text)
    pinecone_id = db.Column(db.String(255))
    
    def __repr__(self):
        return f'<DocumentChunk {self.document_id}-{self.chunk_index}>'


class Conversation(db.Model):
    """Conversation model for storing chat history"""
    __tablename__ = 'conversations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade='all, delete-orphan', order_by='Message.created_at')
    
    def __repr__(self):
        return f'<Conversation {self.id}>'


class Message(db.Model):
    """Message model for storing individual chat messages"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    citations = db.relationship('Citation', backref='message', lazy=True, cascade='all, delete-orphan')
    feedback = db.relationship('Feedback', backref='message', uselist=False, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Message {self.id}>'


class Citation(db.Model):
    """Citation model for storing source references"""
    __tablename__ = 'citations'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True)
    chunk_id = db.Column(db.Integer, db.ForeignKey('document_chunks.id'), nullable=True)
    page_number = db.Column(db.Integer)
    relevance_score = db.Column(db.Float)
    content_snippet = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Citation {self.id}>'


class Feedback(db.Model):
    """Feedback model for user ratings"""
    __tablename__ = 'feedbacks'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False)
    rating = db.Column(db.String(10), nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Feedback {self.id}>'


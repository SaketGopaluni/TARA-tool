from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize SQLAlchemy
db = SQLAlchemy()

class Script(db.Model):
    """Model for storing scripts generated or modified by the application."""
    __tablename__ = 'scripts'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(50), default='python')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with script versions
    versions = db.relationship('ScriptVersion', backref='script', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Script {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'language': self.language,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class ScriptVersion(db.Model):
    """Model for storing versions of scripts for comparison."""
    __tablename__ = 'script_versions'
    
    id = db.Column(db.Integer, primary_key=True)
    script_id = db.Column(db.Integer, db.ForeignKey('scripts.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    version = db.Column(db.Integer, nullable=False)
    changes = db.Column(db.Text)  # Description of changes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ScriptVersion {self.script_id}-{self.version}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'script_id': self.script_id,
            'content': self.content,
            'version': self.version,
            'changes': self.changes,
            'created_at': self.created_at.isoformat()
        }

class TestCase(db.Model):
    """Model for storing test cases created by users."""
    __tablename__ = 'test_cases'
    
    id = db.Column(db.Integer, primary_key=True)
    script_id = db.Column(db.Integer, db.ForeignKey('scripts.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with test results
    results = db.relationship('TestResult', backref='test_case', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<TestCase {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'script_id': self.script_id,
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class TestResult(db.Model):
    """Model for storing results of test case executions."""
    __tablename__ = 'test_results'
    
    id = db.Column(db.Integer, primary_key=True)
    test_case_id = db.Column(db.Integer, db.ForeignKey('test_cases.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'passed', 'failed', 'error'
    output = db.Column(db.Text)
    execution_time = db.Column(db.Float)  # in seconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<TestResult {self.test_case_id}-{self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'test_case_id': self.test_case_id,
            'status': self.status,
            'output': self.output,
            'execution_time': self.execution_time,
            'created_at': self.created_at.isoformat()
        }

class ChatSession(db.Model):
    """Model for storing chat sessions."""
    __tablename__ = 'chat_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with chat messages
    messages = db.relationship('ChatMessage', backref='session', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<ChatSession {self.session_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class ChatMessage(db.Model):
    """Model for storing messages within chat sessions."""
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_sessions.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ChatMessage {self.session_id}-{self.role}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'role': self.role,
            'content': self.content,
            'created_at': self.created_at.isoformat()
        }

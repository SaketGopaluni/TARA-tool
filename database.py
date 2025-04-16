from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize SQLAlchemy
db = SQLAlchemy()

class Script(db.Model):
    """Model for storing scripts generated or modified by the application."""
    __tablename__ = 'scripts'
    
    id = db.Column(db.BigInteger, primary_key=True)
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
    script_id = db.Column(db.BigInteger, db.ForeignKey('scripts.id'), nullable=False)
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
    script_id = db.Column(db.BigInteger, db.ForeignKey('scripts.id'), nullable=False)
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

# New models for FA Transcriber module
class Image(db.Model):
    """Model for storing uploaded FA diagram images."""
    __tablename__ = 'images'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    data = db.Column(db.LargeBinary, nullable=False)
    content_type = db.Column(db.String(100), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with transcriptions
    transcriptions = db.relationship('FATranscription', backref='image', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Image {self.filename}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'content_type': self.content_type,
            'uploaded_at': self.uploaded_at.isoformat()
        }

class FATranscription(db.Model):
    """Model for storing FA transcription sessions."""
    __tablename__ = 'fa_transcriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=False)
    processed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with transcription items
    items = db.relationship('FATranscriptionItem', backref='transcription', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<FATranscription {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'image_id': self.image_id,
            'processed_at': self.processed_at.isoformat()
        }

class FATranscriptionItem(db.Model):
    """Model for storing individual FA transcription items."""
    __tablename__ = 'fa_transcription_items'
    
    id = db.Column(db.Integer, primary_key=True)
    transcription_id = db.Column(db.Integer, db.ForeignKey('fa_transcriptions.id'), nullable=False)
    sheet_name = db.Column(db.String(255))
    message = db.Column(db.Text)
    start_ecu = db.Column(db.String(255))
    end_ecu = db.Column(db.String(255))
    sending_ecu = db.Column(db.String(255))
    receiving_ecu = db.Column(db.String(255))
    dashed_line = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<FATranscriptionItem {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'transcription_id': self.transcription_id,
            'sheet_name': self.sheet_name,
            'message': self.message,
            'start_ecu': self.start_ecu,
            'end_ecu': self.end_ecu,
            'sending_ecu': self.sending_ecu,
            'receiving_ecu': self.receiving_ecu,
            'dashed_line': self.dashed_line,
            'created_at': self.created_at.isoformat()
        }

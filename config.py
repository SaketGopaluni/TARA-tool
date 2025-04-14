import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base configuration class
class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    DEBUG = False
    TESTING = False
    
    # OpenRouter configuration
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
    YOUR_SITE_URL = os.environ.get('YOUR_SITE_URL', '') 
    YOUR_SITE_NAME = os.environ.get('YOUR_SITE_NAME', 'TARA Assistant')
    OPENROUTER_MODEL = os.environ.get('OPENROUTER_MODEL', 'meta-llama/llama-4-maverick:free')
    
    # Database configuration
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///tara_assistant.db'
    SQLALCHEMY_DATABASE_URI = DATABASE_URL 
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Application configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  

# Development configuration
class DevelopmentConfig(Config):
    DEBUG = True

# Testing configuration
class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Production configuration
class ProductionConfig(Config):
    DEBUG = False
    
    # Use environment variable in production
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Make sure these values exist in production
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Check for required environment variables
        assert os.environ.get('SECRET_KEY'), "SECRET_KEY environment variable not set"
        assert os.environ.get('OPENROUTER_API_KEY'), "OPENROUTER_API_KEY environment variable not set"

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    
    # Default configuration
    'default': DevelopmentConfig
}

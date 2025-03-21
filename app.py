import os
import tempfile
import uuid
import json
from flask import Flask, render_template, request, jsonify, session, Response
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()

# Import OpenAI
from openai import OpenAI

# Create Flask app
app = Flask(__name__, static_folder="static", template_folder="templates")

# Configure the app
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-testing')
app.config['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY')
app.config['OPENAI_MODEL'] = os.environ.get('OPENAI_MODEL', 'gpt-4o')
app.config['DEBUG'] = os.environ.get('DEBUG', 'False').lower() == 'true'

# Setup CSRF protection
csrf = CSRFProtect(app)

# Setup proxy fix for Vercel
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Initialize OpenAI client
openai_client = OpenAI(api_key=app.config['OPENAI_API_KEY'], base_url="https://api.openai.com/v1")

# Home route
@app.route('/')
def index():
    return render_template('index.html')

# Coding route
@app.route('/coding')
def coding():
    return render_template('coding.html')

# Testing route
@app.route('/testing')
def testing():
    return render_template('testing.html')

# Chat route
@app.route('/chat')
def chat():
    # Initialize session ID if not present
    if 'chat_session_id' not in session:
        session['chat_session_id'] = str(uuid.uuid4())
    
    return render_template('chat.html')

# API Routes

# Coding API - Generate Script
@app.route('/api/coding/generate', methods=['POST'])
def generate_script():
    try:
        data = request.json
        prompt = data.get('prompt')
        language = data.get('language', 'python')
        
        if not prompt:
            return jsonify({"success": False, "message": "Prompt is required"}), 400
        
        # Generate the script using OpenAI
        system_message = f"""You are an expert {language} developer specializing in cybersecurity and
        automotive systems. Generate a well-commented, production-ready script based on the user's requirements.
        Focus on security best practices, error handling, and maintainability."""
        
        response = openai_client.chat.completions.create(
            model=app.config['OPENAI_MODEL'],
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=4000
        )
        
        script_content = response.choices[0].message.content.strip()
        
        # Extract code from markdown code blocks if present
        if "```" in script_content:
            script_content = extract_code_from_markdown(script_content)
        
        # Create a simple title from the prompt
        title = prompt.split('\n')[0].strip() if '\n' in prompt else prompt[:50] + "..."
        
        # Return the script
        return jsonify({
            "success": True,
            "script": {
                "id": str(uuid.uuid4()),  # Generate a fake ID for the script
                "title": title,
                "content": script_content,
                "language": language
            },
            "message": "Script generated successfully"
        })
        
    except Exception as e:
        app.logger.error(f"Error generating script: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to generate script"
        }), 500

# Testing API - Generate Test Case
@app.route('/api/testing/generate', methods=['POST'])
def generate_test_case():
    try:
        data = request.json
        script_id = data.get('script_id')
        script_content = data.get('script_content')
        test_requirements = data.get('test_requirements')
        
        if not script_content or not test_requirements:
            return jsonify({
                "success": False, 
                "message": "Script content and test requirements are required"
            }), 400
        
        # Generate the test case using OpenAI
        system_message = """You are an expert in writing Python unit tests. Your task is to create
        comprehensive test cases for the provided code, following best practices for testing.
        Include setup, assertions, and error handling in your tests."""
        
        response = openai_client.chat.completions.create(
            model=app.config['OPENAI_MODEL'],
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"Write unit tests for the following code, according to these requirements: '{test_requirements}'\n\n{script_content}"}
            ],
            temperature=0.2,
            max_tokens=4000
        )
        
        test_content = response.choices[0].message.content.strip()
        
        # Extract code from markdown code blocks if present
        if "```" in test_content:
            test_content = extract_code_from_markdown(test_content)
        
        # Create a simple title from the test requirements
        title = test_requirements.split('\n')[0].strip() if '\n' in test_requirements else test_requirements[:50] + "..."
        
        # Return the test case
        return jsonify({
            "success": True,
            "test_case": {
                "id": str(uuid.uuid4()),  # Generate a fake ID for the test case
                "script_id": script_id,
                "title": title,
                "content": test_content
            },
            "message": "Test case generated successfully"
        })
        
    except Exception as e:
        app.logger.error(f"Error generating test case: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to generate test case"
        }), 500

# Chat API - Send Message
@app.route('/api/chat/send', methods=['POST'])
def send_chat_message():
    try:
        data = request.json
        message = data.get('message')
        query_type = data.get('query_type', 'general')
        
        if not message:
            return jsonify({"success": False, "message": "Message is required"}), 400
        
        # Get or create chat session ID
        chat_session_id = session.get('chat_session_id')
        if not chat_session_id:
            chat_session_id = str(uuid.uuid4())
            session['chat_session_id'] = chat_session_id
        
        # Initialize or get chat history
        if 'chat_history' not in session:
            session['chat_history'] = []
        
        chat_history = session.get('chat_history', [])
        
        # Add user message to history
        chat_history.append({"role": "user", "content": message})
        
        # Select system prompt based on query type
        system_prompts = {
            "general": """You are an expert in automotive cybersecurity, specializing in Threat Analysis and Risk Assessment (TARA).
            Provide helpful, accurate information related to automotive cybersecurity, ECUs, threat modeling, and risk assessment.
            When appropriate, reference industry standards such as ISO 21434, SAE J3061, and related best practices."""
        }
        
        system_prompt = system_prompts.get(query_type, system_prompts["general"])
        
        # Prepare messages for API call
        openai_messages = [{"role": "system", "content": system_prompt}]
        for msg in chat_history:
            openai_messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model=app.config['OPENAI_MODEL'],
            messages=openai_messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        assistant_response = response.choices[0].message.content.strip()
        
        # Add assistant response to history
        chat_history.append({"role": "assistant", "content": assistant_response})
        
        # Update session
        session['chat_history'] = chat_history
        
        return jsonify({
            "success": True,
            "response": assistant_response,
            "message": "Message sent successfully"
        })
        
    except Exception as e:
        app.logger.error(f"Error sending chat message: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to send message"
        }), 500

# Chat API - Get History
@app.route('/api/chat/history', methods=['GET'])
def get_chat_history():
    try:
        chat_history = session.get('chat_history', [])
        
        return jsonify({
            "success": True,
            "messages": chat_history,
            "message": f"Retrieved {len(chat_history)} messages successfully"
        })
        
    except Exception as e:
        app.logger.error(f"Error getting chat history: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to get chat history"
        }), 500

# Chat API - Clear History
@app.route('/api/chat/clear', methods=['POST'])
def clear_chat_history():
    try:
        # Clear chat history
        session['chat_history'] = []
        
        return jsonify({
            "success": True,
            "message": "Chat history cleared successfully"
        })
        
    except Exception as e:
        app.logger.error(f"Error clearing chat history: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to clear chat history"
        }), 500

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error="Internal server error"), 500

# Helper functions
def extract_code_from_markdown(markdown_content):
    """Extract code from markdown code blocks."""
    # Check if the content is wrapped in markdown code blocks
    if "```" not in markdown_content:
        return markdown_content
        
    # Split by code blocks
    parts = markdown_content.split('```')
    
    # If there are at least 3 parts (before, code, after)
    if len(parts) >= 3:
        # Get the code part (should be at index 1)
        code = parts[1]
        
        # Remove the language identifier if present
        if code.find('\n') > 0:
            code = code[code.find('\n')+1:]
            
        return code.strip()
    
    return markdown_content

# For local development
if __name__ == '__main__':
    app.run(debug=True)

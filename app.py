import os
import tempfile
import uuid
import json
import re
from flask import Flask, render_template, request, jsonify, session, Response, make_response
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
import traceback
from functools import wraps

# Load environment variables
load_dotenv()

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
try:
    from openai import OpenAI
    openai_client = OpenAI(api_key=app.config['OPENAI_API_KEY'], base_url="https://api.openai.com/v1")
except ImportError:
    app.logger.error("OpenAI package not installed. Please run 'pip install openai'")
    openai_client = None

# Simple diff implementation (since we're not using the database anymore)
def generate_diff_html(old_text, new_text):
    """Generate HTML diff between two texts."""
    import difflib
    d = difflib.Differ()
    diff = list(d.compare(old_text.splitlines(), new_text.splitlines()))
    
    html = []
    for line in diff:
        if line.startswith('+ '):
            html.append(f'<div class="diff-line-added">{line[2:]}</div>')
        elif line.startswith('- '):
            html.append(f'<div class="diff-line-removed">{line[2:]}</div>')
        elif line.startswith('  '):
            html.append(f'<div>{line[2:]}</div>')
    
    return ''.join(html)

# Response time decorator for debugging
def timed_response(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        import time
        start_time = time.time()
        response = f(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        
        # Log duration for debugging
        app.logger.info(f"Route {request.path} took {duration:.2f} seconds")
        
        # Add timing header
        if isinstance(response, Response):
            response.headers["X-Response-Time"] = f"{duration:.2f}s"
        return response
    return decorated_function

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
@timed_response
def generate_script():
    try:
        # Validate input data
        if not request.is_json:
            return jsonify({"success": False, "message": "Invalid request: JSON required"}), 400
        
        data = request.json
        prompt = data.get('prompt')
        language = data.get('language', 'python')
        
        if not prompt:
            return jsonify({"success": False, "message": "Prompt is required"}), 400
        
        # Check if OpenAI client is initialized
        if not openai_client:
            return jsonify({"success": False, "message": "OpenAI client not initialized"}), 500
        
        # Generate the script using OpenAI
        system_message = f"""You are an expert {language} developer specializing in cybersecurity and
        automotive systems. Generate a well-commented, production-ready script based on the user's requirements.
        Focus on security best practices, error handling, and maintainability. Return ONLY the code without any explanations or markdown."""
        
        # Log request for debugging
        app.logger.info(f"Sending request to OpenAI for script generation: {prompt[:50]}...")
        
        try:
            response = openai_client.chat.completions.create(
                model=app.config['OPENAI_MODEL'],
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=3000
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
            app.logger.error(f"OpenAI API error: {str(e)}")
            return jsonify({
                "success": False,
                "error": str(e),
                "message": "Error calling OpenAI API. Please try again later."
            }), 500
            
    except Exception as e:
        app.logger.error(f"Error generating script: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to generate script"
        }), 500

# Debug Script API
@app.route('/api/coding/debug', methods=['POST'])
@timed_response
def debug_script():
    try:
        # Validate input data
        if not request.is_json:
            return jsonify({"success": False, "message": "Invalid request: JSON required"}), 400
        
        data = request.json
        script_content = data.get('script_content')
        
        if not script_content:
            return jsonify({"success": False, "message": "Script content is required"}), 400
        
        # Check if OpenAI client is initialized
        if not openai_client:
            return jsonify({"success": False, "message": "OpenAI client not initialized"}), 500
        
        # Debug script using OpenAI
        system_message = """You are an expert code debugger. Analyze the provided code, identify bugs, errors, 
        or potential issues, and provide a fixed version along with an explanation of your changes. 
        Format your response in two parts: first the explanation, then the fixed code. 
        Start the code section with '### FIXED CODE ###' on its own line."""
        
        try:
            response = openai_client.chat.completions.create(
                model=app.config['OPENAI_MODEL'],
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Debug this code:\n\n{script_content}"}
                ],
                temperature=0.2,
                max_tokens=3000
            )
            
            response_content = response.choices[0].message.content.strip()
            
            # Split explanation and code
            if "### FIXED CODE ###" in response_content:
                parts = response_content.split("### FIXED CODE ###", 1)
                explanation = parts[0].strip()
                fixed_script = parts[1].strip()
            else:
                # Fallback if the model didn't follow the format
                explanation, fixed_script = extract_explanation_and_code(response_content)
            
            # Generate HTML diff
            diff_html = generate_diff_html(script_content, fixed_script)
            
            return jsonify({
                "success": True,
                "explanation": explanation,
                "fixed_script": fixed_script,
                "diff_html": diff_html,
                "message": "Script debugged successfully"
            })
            
        except Exception as e:
            app.logger.error(f"OpenAI API error: {str(e)}")
            return jsonify({
                "success": False,
                "error": str(e),
                "message": "Error calling OpenAI API. Please try again later."
            }), 500
            
    except Exception as e:
        app.logger.error(f"Error debugging script: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to debug script"
        }), 500

# Modify Script API
@app.route('/api/coding/modify', methods=['POST'])
@timed_response
def modify_script():
    try:
        # Validate input data
        if not request.is_json:
            return jsonify({"success": False, "message": "Invalid request: JSON required"}), 400
        
        data = request.json
        script_content = data.get('script_content')
        modification_request = data.get('modification_request')
        
        if not script_content:
            return jsonify({"success": False, "message": "Script content is required"}), 400
        
        if not modification_request:
            return jsonify({"success": False, "message": "Modification request is required"}), 400
        
        # Check if OpenAI client is initialized
        if not openai_client:
            return jsonify({"success": False, "message": "OpenAI client not initialized"}), 500
        
        # Modify script using OpenAI
        system_message = """You are an expert code modifier. Modify the provided code according to the user's request.
        Format your response in two parts: first explain your changes, then provide the complete modified code.
        Start the code section with '### MODIFIED CODE ###' on its own line."""
        
        try:
            response = openai_client.chat.completions.create(
                model=app.config['OPENAI_MODEL'],
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Modify this code according to this request: '{modification_request}'\n\n{script_content}"}
                ],
                temperature=0.2,
                max_tokens=3000
            )
            
            response_content = response.choices[0].message.content.strip()
            
            # Split explanation and code
            if "### MODIFIED CODE ###" in response_content:
                parts = response_content.split("### MODIFIED CODE ###", 1)
                explanation = parts[0].strip()
                modified_script = parts[1].strip()
            else:
                # Fallback if the model didn't follow the format
                explanation, modified_script = extract_explanation_and_code(response_content)
            
            # Generate HTML diff
            diff_html = generate_diff_html(script_content, modified_script)
            
            return jsonify({
                "success": True,
                "explanation": explanation,
                "modified_script": modified_script,
                "diff_html": diff_html,
                "message": "Script modified successfully"
            })
            
        except Exception as e:
            app.logger.error(f"OpenAI API error: {str(e)}")
            return jsonify({
                "success": False,
                "error": str(e),
                "message": "Error calling OpenAI API. Please try again later."
            }), 500
            
    except Exception as e:
        app.logger.error(f"Error modifying script: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to modify script"
        }), 500

# Diff Checker API
@app.route('/api/coding/diffcheck', methods=['POST'])
@timed_response
def diffcheck():
    try:
        # Validate input data
        if not request.is_json:
            return jsonify({"success": False, "message": "Invalid request: JSON required"}), 400
        
        data = request.json
        original_content = data.get('original_content')
        new_content = data.get('new_content')
        
        if not original_content or not new_content:
            return jsonify({"success": False, "message": "Both original and new content are required"}), 400
        
        # Check if OpenAI client is initialized
        if not openai_client:
            return jsonify({"success": False, "message": "OpenAI client not initialized"}), 500
        
        # Generate diff HTML
        diff_html = generate_diff_html(original_content, new_content)
        
        # Get explanation of changes using OpenAI
        system_message = """You are an expert code analyzer. Explain the differences between two versions of code.
        Provide a clear, concise explanation of what has changed and why these changes might have been made."""
        
        try:
            # Create a simple text representation of the diff for OpenAI
            diff_lines = []
            for line in original_content.splitlines():
                if line not in new_content.splitlines():
                    diff_lines.append(f"- {line}")
            
            for line in new_content.splitlines():
                if line not in original_content.splitlines():
                    diff_lines.append(f"+ {line}")
            
            diff_text = "\n".join(diff_lines)
            
            response = openai_client.chat.completions.create(
                model=app.config['OPENAI_MODEL'],
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Explain these code changes:\n\n{diff_text}"}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            
            explanation = response.choices[0].message.content.strip()
            
            return jsonify({
                "success": True,
                "explanation": explanation,
                "diff_html": diff_html,
                "message": "Scripts compared successfully"
            })
            
        except Exception as e:
            app.logger.error(f"OpenAI API error: {str(e)}")
            return make_simple_diff_response(original_content, new_content)
            
    except Exception as e:
        app.logger.error(f"Error checking diff: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to compare scripts"
        }), 500

# Fallback for diff checker if OpenAI fails
def make_simple_diff_response(original_content, new_content):
    """Create a diff response without OpenAI explanation."""
    diff_html = generate_diff_html(original_content, new_content)
    return jsonify({
        "success": True,
        "explanation": "Comparison completed. Lines in green were added, lines in red were removed.",
        "diff_html": diff_html,
        "message": "Scripts compared (without AI explanation)"
    })

# Testing API - Generate Test Case
@app.route('/api/testing/generate', methods=['POST'])
@timed_response
def generate_test_case():
    try:
        # Validate input data
        if not request.is_json:
            return jsonify({"success": False, "message": "Invalid request: JSON required"}), 400
        
        data = request.json
        script_id = data.get('script_id')  # This might be empty for file uploads
        script_content = data.get('script_content')
        test_requirements = data.get('test_requirements')
        
        if not script_content or not test_requirements:
            return jsonify({"success": False, "message": "Script content and test requirements are required"}), 400
        
        # Check if OpenAI client is initialized
        if not openai_client:
            return jsonify({"success": False, "message": "OpenAI client not initialized"}), 500
        
        # Generate the test case using OpenAI
        system_message = """You are an expert in writing Python unit tests. Create comprehensive test cases 
        for the provided code, following best practices for testing. Include setup, assertions, and error handling.
        Return ONLY the Python test code without any explanations or markdown."""
        
        try:
            response = openai_client.chat.completions.create(
                model=app.config['OPENAI_MODEL'],
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Write unit tests for this code, according to these requirements: '{test_requirements}'\n\n{script_content}"}
                ],
                temperature=0.2,
                max_tokens=3000
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
            app.logger.error(f"OpenAI API error: {str(e)}")
            return jsonify({
                "success": False,
                "error": str(e),
                "message": "Error calling OpenAI API. Please try again later."
            }), 500
            
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
@timed_response
def send_chat_message():
    try:
        # Validate input data
        if not request.is_json:
            return jsonify({"success": False, "message": "Invalid request: JSON required"}), 400
        
        data = request.json
        message = data.get('message')
        
        if not message:
            return jsonify({"success": False, "message": "Message is required"}), 400
        
        # Check if OpenAI client is initialized
        if not openai_client:
            return jsonify({"success": False, "message": "OpenAI client not initialized"}), 500
        
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
        
        # Limit history length to avoid token limits
        if len(chat_history) > 20:
            # Keep the first message (system context) and the 19 most recent messages
            chat_history = chat_history[-20:]
        
        # System prompt for automotive cybersecurity
        system_prompt = """You are an expert in automotive cybersecurity, specializing in Threat Analysis and Risk Assessment (TARA).
        Provide helpful, accurate information related to automotive cybersecurity, ECUs, threat modeling, and risk assessment.
        When appropriate, reference industry standards such as ISO 21434, SAE J3061, and related best practices."""
        
        # Prepare messages for API call
        openai_messages = [{"role": "system", "content": system_prompt}]
        for msg in chat_history:
            openai_messages.append({"role": msg["role"], "content": msg["content"]})
        
        try:
            # Call OpenAI API
            response = openai_client.chat.completions.create(
                model=app.config['OPENAI_MODEL'],
                messages=openai_messages,
                temperature=0.7,
                max_tokens=1500  # Reduced token count to avoid timeouts
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
            app.logger.error(f"OpenAI API error: {str(e)}")
            return jsonify({
                "success": False,
                "error": str(e),
                "message": "Error calling OpenAI API. Please try again later."
            }), 500
            
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

# API Status route
@app.route('/api/status', methods=['GET'])
def api_status():
    """Simple endpoint to check if API is working and has OpenAI access."""
    try:
        status = {
            "api": "online",
            "openai": "ready" if openai_client else "not_configured",
            "environment": "production" if not app.config['DEBUG'] else "development"
        }
        
        # Add OpenAI connectivity check if client exists
        if openai_client:
            try:
                # Simple model list call to check connectivity
                openai_client.models.list()
                status["openai_connection"] = "connected"
            except Exception as e:
                status["openai_connection"] = "error"
                status["openai_error"] = str(e)
        
        return jsonify({"success": True, "status": status})
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": str(e),
            "message": "API status check failed"
        }), 500

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    app.logger.error(f"Server error: {str(e)}")
    app.logger.error(traceback.format_exc())
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

def extract_explanation_and_code(content):
    """Extract explanation and code from a mixed response."""
    # If no code blocks, try to find natural division
    if "```" in content:
        # Find code blocks
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', content, re.DOTALL)
        if code_blocks:
            # Join multiple code blocks if present
            code = '\n\n'.join(code_blocks)
            
            # Remove code blocks from content to get explanation
            explanation = re.sub(r'```(?:\w+)?\n.*?```', '', content, flags=re.DOTALL).strip()
            return explanation, code
    
    # Fallback: assume the first part is explanation, rest is code
    # Look for indicators like "Here's the code:"
    indicators = ["Here's the code:", "Here is the code:", "Fixed code:", "Modified code:"]
    for indicator in indicators:
        if indicator in content:
            parts = content.split(indicator, 1)
            return parts[0].strip(), parts[1].strip()
    
    # If no clear indicators, try to find the first code-like line
    lines = content.splitlines()
    for i, line in enumerate(lines):
        # Check for common code indicators
        if (line.strip().startswith('def ') or 
            line.strip().startswith('class ') or 
            line.strip().startswith('import ') or 
            line.strip().startswith('from ') or
            line.strip() == ''):
            # Found potential code start - split here
            return '\n'.join(lines[:i]).strip(), '\n'.join(lines[i:]).strip()
    
    # If can't clearly separate, return the whole thing as code with empty explanation
    return "Here's the fixed/modified code:", content

# For local development
if __name__ == '__main__':
    app.run(debug=True)

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
from modules.chat import ChatModule
from modules.testing import TestingModule
from modules.coding import CodingModule

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__, static_folder="static", template_folder="templates")

# Configure the app
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-testing')
app.config['DEEPSEEK_API_KEY'] = os.environ.get('DEEPSEEK_API_KEY')
app.config['DEEPSEEK_MODEL'] = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')
app.config['DEBUG'] = os.environ.get('DEBUG', 'False').lower() == 'true'

# Setup CSRF protection
csrf = CSRFProtect(app)

# Setup proxy fix for Vercel
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Initialize OpenAI client for DeepSeek
try:
    from openai import OpenAI
    openai_client = OpenAI(api_key=app.config['DEEPSEEK_API_KEY'], base_url="https://api.deepseek.com")
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

# Helper function for faster diff generation
def generate_simple_diff_html(old_text, new_text):
    """Generate a simpler HTML diff that's faster to compute."""
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    
    # Use set operations for a faster (though less precise) diff
    old_set = set(old_lines)
    new_set = set(new_lines)
    
    removed = old_set - new_set
    added = new_set - old_set
    
    html = []
    for line in old_lines:
        if line in removed:
            html.append(f'<div class="diff-line-removed">{line}</div>')
        elif line in old_set.intersection(new_set):
            html.append(f'<div>{line}</div>')
    
    # Add lines that are in new but not in the output above
    for line in new_lines:
        if line in added and f'<div>{line}</div>' not in html:
            html.append(f'<div class="diff-line-added">{line}</div>')
    
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

# Streaming response helper
def stream_deepseek_response(response_stream):
    """Stream the DeepSeek response to the client."""
    try:
        full_content = ""
        
        # Stream each chunk
        for chunk in response_stream:
            if chunk.choices:
                content = chunk.choices[0].delta.content or ""
                full_content += content
                
                # Yield the chunk as a JSON object with a data prefix for EventSource
                yield f"data: {json.dumps({'chunk': content, 'full': full_content})}\n\n"
                
        # Send a completion message
        yield f"data: {json.dumps({'done': True, 'full': full_content})}\n\n"
            
    except Exception as e:
        app.logger.error(f"Error in stream: {str(e)}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

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

# Coding API - Wolves of Wall Street
@app.route('/api/coding/generate', methods=['POST'])
@csrf.exempt
@timed_response
def generate_script():
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        language = data.get('language', 'python')
        
        # Input validation
        if not prompt:
            return jsonify({
                "success": False,
                "error": "Prompt is required",
                "message": "Please provide a prompt for the script generation"
            }), 400
            
        # Check if DeepSeek client is initialized
        if not openai_client:
            return jsonify({"success": False, "message": "DeepSeek client not initialized"}), 500
        
        # Generate the script using DeepSeek
        system_message = f"""You are an expert {language} developer specializing in cybersecurity and
        automotive systems. Generate a well-commented, production-ready script based on the user's requirements.
        Focus on security best practices, error handling, and maintainability. Return ONLY the code without any explanations or markdown."""
        
        try:
            response = openai_client.chat.completions.create(
                model=app.config['DEEPSEEK_MODEL'],
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=3000
            )
            
            # Check if streaming is requested
            stream = request.args.get('stream', 'false').lower() == 'true'
            
            if stream:
                # Return a streaming response
                return Response(stream_deepseek_response(response.choices[0].delta.stream()),
                               mimetype='text/event-stream',
                               headers={
                                   'Cache-Control': 'no-cache',
                                   'X-Accel-Buffering': 'no'
                               })
            else:
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
            app.logger.error(f"DeepSeek API error: {str(e)}")
            return jsonify({
                "success": False,
                "error": str(e),
                "message": "Error calling DeepSeek API. Please try again later."
            }), 500
            
    except Exception as e:
        app.logger.error(f"Error generating script: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to generate script"
        }), 500

# Debug Script API - OPTIMIZED VERSION WITH TIMEOUT FIXES
@app.route('/api/coding/debug', methods=['POST'])
@csrf.exempt
@timed_response
def debug_script():
    try:
        data = request.get_json()
        script_content = data.get('script_content', '')
        
        # Input validation
        if not script_content:
            return jsonify({
                "success": False,
                "error": "Script content is required",
                "message": "Please provide the script content"
            }), 400
            
        # Check if DeepSeek client is initialized
        if not openai_client:
            return jsonify({"success": False, "message": "DeepSeek client not initialized"}), 500
        
        # For very long scripts, truncate to reduce processing time
        max_length = 10000  # Character limit to avoid timeouts
        original_length = len(script_content)
        if original_length > max_length:
            script_content = script_content[:max_length] + "\n# Note: Script was truncated due to length"
            app.logger.warning(f"Script truncated from {original_length} to {max_length} characters to avoid timeout")
        
        # Debug script using DeepSeek - shortened prompt and reduced tokens for speed
        system_message = """You are an expert code debugger. Analyze the code briefly, identify key issues, 
        and provide quick fixes. Be concise. Respond with:
        1. A very brief explanation (2-3 sentences max)
        2. The fixed code prefixed with '### FIXED CODE ###'"""
        
        try:
            # Use reduced tokens and temperature to speed up response
            response = openai_client.chat.completions.create(
                model=app.config['DEEPSEEK_MODEL'],
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Fix this code quickly:\n\n{script_content}"}
                ],
                temperature=0.1,
                max_tokens=1500,  # Reduced tokens to avoid timeout
                timeout=8  # Set explicit timeout lower than Vercel's 10s limit
            )
            
            # Check if streaming is requested
            stream = request.args.get('stream', 'false').lower() == 'true'
            
            if stream:
                # Return a streaming response
                return Response(stream_deepseek_response(response.choices[0].delta.stream()),
                               mimetype='text/event-stream',
                               headers={
                                   'Cache-Control': 'no-cache',
                                   'X-Accel-Buffering': 'no'
                               })
            else:
                response_content = response.choices[0].message.content.strip()
                
                # Split explanation and code
                if "### FIXED CODE ###" in response_content:
                    parts = response_content.split("### FIXED CODE ###", 1)
                    explanation = parts[0].strip()
                    fixed_script = parts[1].strip()
                else:
                    # Fallback if the model didn't follow the format
                    explanation, fixed_script = extract_explanation_and_code(response_content)
                
                # Generate simple HTML diff (faster than complex diffing)
                diff_html = generate_simple_diff_html(script_content, fixed_script)
                
                return jsonify({
                    "success": True,
                    "explanation": explanation,
                    "fixed_script": fixed_script,
                    "diff_html": diff_html,
                    "message": "Script debugged successfully"
                })
                
        except Exception as e:
            app.logger.error(f"DeepSeek API error: {str(e)}")
            # Return a simplified response for timeout errors
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                return jsonify({
                    "success": False,
                    "error": "The operation timed out. Please try with a smaller script or simpler requirements.",
                    "message": "Debugging operation timed out"
                }), 504  # Gateway Timeout status
            return jsonify({
                "success": False,
                "error": str(e),
                "message": "Error calling DeepSeek API. Please try again later."
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
@csrf.exempt
@timed_response
def modify_script():
    try:
        data = request.get_json()
        script_content = data.get('script_content', '')
        modification_request = data.get('modification_request', '')
        
        # Input validation
        if not script_content:
            return jsonify({
                "success": False,
                "error": "Script content is required",
                "message": "Please provide the script content"
            }), 400
            
        if not modification_request:
            return jsonify({
                "success": False,
                "error": "Modification request is required",
                "message": "Please provide the modification request"
            }), 400
            
        # Check if DeepSeek client is initialized
        if not openai_client:
            return jsonify({"success": False, "message": "DeepSeek client not initialized"}), 500
        
        # For very long scripts, truncate to reduce processing time
        max_length = 10000  # Character limit to avoid timeouts
        original_length = len(script_content)
        if original_length > max_length:
            script_content = script_content[:max_length] + "\n# Note: Script was truncated due to length"
            app.logger.warning(f"Script truncated from {original_length} to {max_length} characters to avoid timeout")
        
        # Modify script using DeepSeek - with reduced prompt length for speed
        system_message = """You are an expert code modifier. Modify the provided code according to the user's request.
        Format your response in two parts: first explain your changes briefly, then provide the complete modified code.
        Start the code section with '### MODIFIED CODE ###' on its own line."""
        
        try:
            # Use reduced tokens and temperature to speed up response
            response = openai_client.chat.completions.create(
                model=app.config['DEEPSEEK_MODEL'],
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Modify this code according to this request: '{modification_request}'\n\n{script_content}"}
                ],
                temperature=0.1,
                max_tokens=1500,  # Reduced tokens to avoid timeout
                timeout=8  # Set explicit timeout lower than Vercel's 10s limit
            )
            
            # Check if streaming is requested
            stream = request.args.get('stream', 'false').lower() == 'true'
            
            if stream:
                # Return a streaming response
                return Response(stream_deepseek_response(response.choices[0].delta.stream()),
                               mimetype='text/event-stream',
                               headers={
                                   'Cache-Control': 'no-cache',
                                   'X-Accel-Buffering': 'no'
                               })
            else:
                response_content = response.choices[0].message.content.strip()
                
                # Split explanation and code
                if "### MODIFIED CODE ###" in response_content:
                    parts = response_content.split("### MODIFIED CODE ###", 1)
                    explanation = parts[0].strip()
                    modified_script = parts[1].strip()
                else:
                    # Fallback if the model didn't follow the format
                    explanation, modified_script = extract_explanation_and_code(response_content)
                
                # Generate simple HTML diff (faster than complex diffing)
                diff_html = generate_simple_diff_html(script_content, modified_script)
                
                return jsonify({
                    "success": True,
                    "explanation": explanation,
                    "modified_script": modified_script,
                    "diff_html": diff_html,
                    "message": "Script modified successfully"
                })
                
        except Exception as e:
            app.logger.error(f"DeepSeek API error: {str(e)}")
            # Return a simplified response for timeout errors
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                return jsonify({
                    "success": False,
                    "error": "The operation timed out. Please try with a smaller script or simpler requirements.",
                    "message": "Modification operation timed out"
                }), 504  # Gateway Timeout status
            return jsonify({
                "success": False,
                "error": str(e),
                "message": "Error calling DeepSeek API. Please try again later."
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
        
        # Check if DeepSeek client is initialized
        if not openai_client:
            return jsonify({"success": False, "message": "DeepSeek client not initialized"}), 500
        
        # For very long inputs, truncate to reduce processing time
        max_length = 8000  # Character limit to avoid timeouts
        if len(original_content) > max_length or len(new_content) > max_length:
            # If either input is too long, fall back to simple diff
            app.logger.warning("Inputs too long for DeepSeek analysis, falling back to simple diff")
            return make_simple_diff_response(original_content, new_content)
        
        # Generate diff HTML
        diff_html = generate_simple_diff_html(original_content, new_content)
        
        # Get explanation of changes using DeepSeek
        system_message = """You are an expert code analyzer. Explain the differences between two versions of code.
        Provide a clear, concise explanation of what has changed. Be very brief."""
        
        try:
            # Create a simple text representation of the diff for DeepSeek
            diff_lines = []
            for line in original_content.splitlines():
                if line not in new_content.splitlines():
                    diff_lines.append(f"- {line}")
            
            for line in new_content.splitlines():
                if line not in original_content.splitlines():
                    diff_lines.append(f"+ {line}")
            
            # Limit diff text to avoid timeouts
            diff_text = "\n".join(diff_lines[:200])  # Limit to 200 lines
            if len(diff_lines) > 200:
                diff_text += "\n... (additional changes omitted for brevity)"
            
            response = openai_client.chat.completions.create(
                model=app.config['DEEPSEEK_MODEL'],
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Explain these code changes briefly:\n\n{diff_text}"}
                ],
                temperature=0.1,
                max_tokens=500,  # Very limited tokens for speed
                timeout=8  # Set explicit timeout lower than Vercel's 10s limit
            )
            
            explanation = response.choices[0].message.content.strip()
            
            return jsonify({
                "success": True,
                "explanation": explanation,
                "diff_html": diff_html,
                "message": "Scripts compared successfully"
            })
            
        except Exception as e:
            app.logger.error(f"DeepSeek API error: {str(e)}")
            return make_simple_diff_response(original_content, new_content)
            
    except Exception as e:
        app.logger.error(f"Error checking diff: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to compare scripts"
        }), 500

# Fallback for diff checker if DeepSeek fails
def make_simple_diff_response(original_content, new_content):
    """Create a diff response without DeepSeek explanation."""
    diff_html = generate_simple_diff_html(original_content, new_content)
    return jsonify({
        "success": True,
        "explanation": "Comparison completed. Lines in green were added, lines in red were removed.",
        "diff_html": diff_html,
        "message": "Scripts compared (without AI explanation)"
    })

# Testing API - Generate Test Case
@app.route('/api/testing/generate', methods=['POST'])
@csrf.exempt
@timed_response
def generate_test_case():
    try:
        data = request.get_json()
        script_id = data.get('script_id')
        script_content = data.get('script_content', '')
        test_requirements = data.get('test_requirements', '')
        
        # Input validation
        if not script_content:
            return jsonify({
                "success": False,
                "error": "Script content is required",
                "message": "Please provide the script content"
            }), 400
            
        if not test_requirements:
            return jsonify({
                "success": False,
                "error": "Test requirements are required",
                "message": "Please provide the test requirements"
            }), 400
            
        # Initialize the testing module with DeepSeek credentials
        testing_module = TestingModule(
            api_key=app.config['DEEPSEEK_API_KEY'],
            model=app.config['DEEPSEEK_MODEL']
        )
        
        # Generate test case
        result = testing_module.generate_test_case(script_id, script_content, test_requirements)
        
        # Check if streaming is requested
        stream = request.args.get('stream', 'false').lower() == 'true'
        
        if result.get("success"):
            if stream and 'stream' in result:
                # Return a streaming response
                return Response(stream_deepseek_response(result['stream']), 
                               mimetype='text/event-stream',
                               headers={
                                   'Cache-Control': 'no-cache',
                                   'X-Accel-Buffering': 'no'
                               })
            else:
                # Handle the streaming response ourselves and return a normal response
                full_content = ""
                for chunk in result['stream']:
                    if chunk.choices and chunk.choices[0].delta.content:
                        full_content += chunk.choices[0].delta.content
                
                # Extract code from markdown if present
                if full_content.startswith("```") and full_content.endswith("```"):
                    full_content = extract_code_from_markdown(full_content)
                
                # Create database entry
                title = result['title']
                test_case = TestCase(
                    script_id=script_id,
                    title=title,
                    content=full_content
                )
                db.session.add(test_case)
                db.session.commit()
                
                return jsonify({
                    "success": True,
                    "test_case": test_case.to_dict(),
                    "message": "Test case generated successfully"
                })
        else:
            return jsonify(result), 500
            
    except Exception as e:
        app.logger.error(f"Error in generate_test_case: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to generate test case"
        }), 500

# Testing API - Improve Test Case
@app.route('/api/testing/improve', methods=['POST'])
@csrf.exempt
@timed_response
def improve_test_case():
    try:
        data = request.get_json()
        test_case_id = data.get('test_case_id')
        test_content = data.get('test_content', '')
        script_content = data.get('script_content', '')
        test_result_output = data.get('test_result_output', '')
        
        # Input validation
        if not test_case_id:
            return jsonify({
                "success": False,
                "error": "Test case ID is required",
                "message": "Please provide the test case ID"
            }), 400
            
        if not test_content:
            return jsonify({
                "success": False,
                "error": "Test content is required",
                "message": "Please provide the test content"
            }), 400
            
        if not script_content:
            return jsonify({
                "success": False,
                "error": "Script content is required",
                "message": "Please provide the script content"
            }), 400
            
        # Initialize the testing module with DeepSeek credentials
        testing_module = TestingModule(
            api_key=app.config['DEEPSEEK_API_KEY'],
            model=app.config['DEEPSEEK_MODEL']
        )
        
        # Improve test case
        result = testing_module.improve_test_case(test_case_id, test_content, script_content, test_result_output)
        
        # Check if streaming is requested
        stream = request.args.get('stream', 'false').lower() == 'true'
        
        if result.get("success"):
            if stream and 'stream' in result:
                # Return a streaming response
                return Response(stream_deepseek_response(result['stream']), 
                               mimetype='text/event-stream',
                               headers={
                                   'Cache-Control': 'no-cache',
                                   'X-Accel-Buffering': 'no'
                               })
            else:
                # Handle the streaming response ourselves and return a normal response
                full_content = ""
                for chunk in result['stream']:
                    if chunk.choices and chunk.choices[0].delta.content:
                        full_content += chunk.choices[0].delta.content
                
                # Extract code from markdown if present
                if full_content.startswith("```") and full_content.endswith("```"):
                    full_content = extract_code_from_markdown(full_content)
                
                # Update the test case in the database
                test_case = TestCase.query.get(test_case_id)
                
                if not test_case:
                    return jsonify({
                        "success": False,
                        "error": "Test case not found",
                        "message": "Failed to improve test case: Test case not found"
                    }), 404
                
                # Update the test case content
                test_case.content = full_content
                db.session.commit()
                
                return jsonify({
                    "success": True,
                    "test_case": test_case.to_dict(),
                    "message": "Test case improved successfully"
                })
        else:
            return jsonify(result), 500
            
    except Exception as e:
        app.logger.error(f"Error in improve_test_case: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to improve test case"
        }), 500

# Chat API - Send Message
@app.route('/api/chat/send', methods=['POST'])
@csrf.exempt
@timed_response
def send_chat_message():
    try:
        data = request.get_json()
        message = data.get('message', '')
        query_type = data.get('query_type', 'general')
        
        # Input validation
        if not message:
            return jsonify({
                "success": False,
                "error": "Message is required",
                "message": "Please provide a message"
            }), 400
            
        # Get session ID from session or create new
        session_id = session.get('chat_session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            session['chat_session_id'] = session_id
            
        # Initialize the chat module
        chat_module = ChatModule()
        
        # Create session if it doesn't exist
        result = chat_module.create_session()
        if not result['success']:
            # If creation failed but not because it already exists
            if "already exists" not in result.get('message', ''):
                return jsonify(result), 500
                
        # Send the message
        result = chat_module.send_message(session_id, message, query_type)
        
        # Check if streaming is requested
        stream = request.args.get('stream', 'false').lower() == 'true'
        
        if result.get("success"):
            if stream and 'stream' in result:
                # Return a streaming response
                return Response(stream_deepseek_response(result['stream']), 
                               mimetype='text/event-stream',
                               headers={
                                   'Cache-Control': 'no-cache',
                                   'X-Accel-Buffering': 'no'
                               })
            else:
                # Handle the streaming response ourselves and return a normal response
                full_content = ""
                for chunk in result['stream']:
                    if chunk.choices and chunk.choices[0].delta.content:
                        full_content += chunk.choices[0].delta.content
                
                # Save assistant response to database
                chat_session_id = result['chat_session_id']
                assistant_message = ChatMessage(
                    session_id=chat_session_id,
                    role="assistant",
                    content=full_content
                )
                db.session.add(assistant_message)
                db.session.commit()
                
                return jsonify({
                    "success": True,
                    "response": full_content,
                    "message": "Message sent successfully"
                })
        else:
            return jsonify(result), 500
            
    except Exception as e:
        app.logger.error(f"Error in send_chat_message: {str(e)}")
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
    """Simple endpoint to check if API is working and has DeepSeek access."""
    try:
        status = {
            "api": "online",
            "deepseek": "ready" if openai_client else "not_configured",
            "environment": "production" if not app.config['DEBUG'] else "development"
        }
        
        # Add DeepSeek connectivity check if client exists
        if openai_client:
            try:
                # Simple model list call to check connectivity
                openai_client.models.list()
                status["deepseek_connection"] = "connected"
            except Exception as e:
                status["deepseek_connection"] = "error"
                status["deepseek_error"] = str(e)
        
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

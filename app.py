import os
import tempfile
import uuid # Add the missing import
import json
import re
import logging # Add logging import
from datetime import datetime # Add missing datetime import
from flask import Flask, render_template, request, jsonify, session, Response, make_response
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
import traceback
# from functools import wraps # No longer needed for timed_response
import html
import difflib

# Import refactored modules and database models
from modules.chat import ChatModule
from modules.testing import TestingModule
from modules.coding import CodingModule
from database import db, ChatSession, ChatMessage, Script, ScriptVersion, TestCase, TestResult
from config import config # Import the config dictionary

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__, static_folder="static", template_folder="templates")

# Load configuration based on environment variable
config_name = os.environ.get('FLASK_CONFIG') or 'default' # Use 'default' (development) if FLASK_CONFIG not set
app.config.from_object(config[config_name]) # Load config from dictionary

# Configure logging based on Flask debug setting
if app.config['DEBUG']:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup database
# Database URI is now loaded via app.config from get_config()
db.init_app(app)

# Setup CSRF protection
csrf = CSRFProtect(app)

# Setup proxy fix for Vercel
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# REMOVE OLD DeepSeek Client Initialization
# try:
#     from openai import OpenAI
#     openai_client = OpenAI(
#         api_key=app.config['DEEPSEEK_API_KEY'], 
#         base_url="https://api.deepseek.com",
#         timeout=5.0  # Set a 5 second timeout to ensure we don't hit Vercel's 10s limit
#     )
# except ImportError:
#     app.logger.error("OpenAI package not installed. Please run 'pip install openai'")
#     openai_client = None

# Initialize the refactored modules with the app config
# These instances will handle the AI interactions
try:
    # Pass the whole config dictionary (or app.config directly)
    logger.debug(f"Attempting to initialize modules with config: {app.config}") # Log the config object
    logger.info(f"Found OPENROUTER_API_KEY in app.config: {'*' * 5 + app.config.get('OPENROUTER_API_KEY')[-4:] if app.config.get('OPENROUTER_API_KEY') else 'Not Found'}") # Log if key exists (partially masked)
    
    logger.info("Initializing CodingModule...")
    coding_module = CodingModule(app.config)
    logger.info("CodingModule initialized successfully.")
    
    logger.info("Initializing TestingModule...")
    testing_module = TestingModule(app.config)
    logger.info("TestingModule initialized successfully.")
    
    logger.info("Initializing ChatModule...")
    chat_module = ChatModule(app.config)
    logger.info("ChatModule initialized successfully.")
    
except ValueError as e:
    logger.error(f"ValueError during module initialization: {e}. Ensure OPENROUTER_API_KEY is set.", exc_info=True) # Log full traceback
    # Depending on the app's requirements, you might exit or run in a limited mode.
    # For now, we'll log the error and let Flask continue, but API calls will fail.
    coding_module = None
    testing_module = None
    chat_module = None
except Exception as e:
    logger.error(f"Unexpected Exception during module initialization: {e}", exc_info=True) # Log full traceback
    coding_module = None
    testing_module = None
    chat_module = None

# Helper function to generate HTML diff
def generateDiffHtml(original, modified):
    """Generate HTML diff between original and modified text"""
    if original == modified:
        return "<div class='bg-yellow-100 p-2 rounded'>No changes made - code is identical.</div>"
    
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        modified.splitlines(keepends=True),
        n=3
    )
    
    html_diff = []
    for line in diff:
        if line.startswith('+'):
            html_diff.append(f"<div class='bg-green-100 text-green-800'>{html.escape(line)}</div>")
        elif line.startswith('-'):
            html_diff.append(f"<div class='bg-red-100 text-red-800'>{html.escape(line)}</div>")
        elif line.startswith('@@'):
            html_diff.append(f"<div class='bg-blue-100 text-blue-800'>{html.escape(line)}</div>")
        else:
            html_diff.append(f"<div>{html.escape(line)}</div>")
    
    return f"<div class='font-mono text-sm whitespace-pre'>{''.join(html_diff)}</div>"

# Remove old diff functions, use CodingModule.calculate_diff static method
# def generate_diff_html(old_text, new_text): ...
# def generate_simple_diff_html(old_text, new_text): ...

# Remove old Response time decorator
# def timed_response(f): ...

# Remove old streaming helper
# def stream_deepseek_response(response_stream): ...

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
# @csrf.exempt # Typically POST routes should be protected
def generate_script():
    if not coding_module:
        return jsonify({"success": False, "error": "Coding module not initialized. Check API key.", "message": "Internal server error"}), 500
        
    try:
        data = request.json
        logger.info(f"Received data in generate_script: {data}")
        language = data.get('language')
        
        # Accept either 'requirements' or 'prompt' for backward compatibility
        requirements = data.get('requirements')
        if requirements is None:
            requirements = data.get('prompt')  # Fallback to 'prompt' if 'requirements' is not provided
            
        script_name = data.get('script_name', 'Generated Script') # Optional name from frontend
        
        logger.info(f"Parsed parameters - language: {language}, requirements exists: {requirements is not None}, script_name: {script_name}")

        if not language or not requirements:
            logger.error(f"Missing parameters - language: {language}, requirements: {requirements}")
            return jsonify({"success": False, "error": "Missing language or requirements"}), 400

        # Call the refactored module method (non-streaming)
        logger.debug(f"Calling coding_module.generate_script for {language}")
        generated_code = coding_module.generate_script(language, requirements)

        if generated_code.startswith("Error generating script:"):
            logger.error(f"Module Error in generate_script: {generated_code}")
            return jsonify({"success": False, "error": generated_code}), 500

        # --- Database Interaction --- 
        logger.debug("Saving generated script to database.")
        # Use provided name or generate one
        title = script_name if script_name else f"{language.capitalize()} script based on: {requirements[:30]}..."
        
        new_script = Script(title=title, language=language, content=generated_code)
        db.session.add(new_script)
        # Commit here to get the new_script.id
        db.session.commit()
        logger.info(f"Created new Script with ID: {new_script.id}")
        
        # Add initial version
        initial_version = ScriptVersion(script_id=new_script.id, version=1, content=generated_code, changes="Initial generation")
        db.session.add(initial_version)
        db.session.commit()
        logger.info(f"Created initial ScriptVersion ID: {initial_version.id} for Script ID: {new_script.id}")

        return jsonify({
            "success": True, 
            "script": new_script.to_dict(), # Return the saved script data
            "version": initial_version.to_dict()
        }), 201 # Status code for resource created

    except Exception as e:
        logger.error(f"Error in generate_script API: {e}")
        logger.error(traceback.format_exc())
        db.session.rollback() # Rollback DB changes on error
        return jsonify({"success": False, "error": str(e), "message": "Failed to generate script"}), 500

# Coding API - Debug Script
@app.route('/api/coding/debug', methods=['POST'])
# @csrf.exempt
def debug_script():
    logger.info("Entering debug_script route...")
    if not coding_module:
        return jsonify({"success": False, "error": "Coding module not initialized. Check API key.", "message": "Internal server error"}), 500
        
    try:
        data = request.json
        logger.info(f"Received data in debug_script: {data}") 
        
        script_id = data.get('script_id')
        script_content = data.get('script_content') # Get current content from request
        error_log = data.get('error_log', '') # Get error log from request

        if script_content is None:
            return jsonify({"success": False, "error": "Missing script_content"}), 400

        # If script_id is missing but we have content, we can still proceed with debugging
        script = None
        if script_id:
            script = Script.query.get(script_id)
            logger.info(f"Found script in database with ID: {script_id}")
        else:
            logger.warning("No script_id provided, proceeding with content-only debugging")

        logger.debug(f"Calling coding_module.debug_script for script")
        # Call refactored debug method (returns dict with 'analysis' and 'fixed_code')
        debug_result = coding_module.debug_script(script_content, error_log)

        analysis = debug_result.get('analysis', 'No analysis provided.')
        fixed_code = debug_result.get('fixed_code') # Will be None if no fix or error

        if fixed_code is None: # Check if debugging failed or no changes needed
             # Check if the analysis indicates an error from the module
            if analysis.startswith("Error during debugging:"):
                logger.error(f"Module Error in debug_script: {analysis}")
                return jsonify({"success": False, "error": analysis}), 500
            else:
                # No changes needed or analysis only
                logger.info(f"Debug analysis complete, no code changes suggested.")
                return jsonify({
                    "success": True,
                    "analysis": analysis,
                    "explanation": analysis,  # Add this for frontend compatibility
                    "fixed_code": script_content, # Return original content if no changes
                    "diff_html": "<div class='bg-yellow-100 p-2 rounded'>No changes needed - script appears to be functioning correctly.</div>",
                    "script_id": script_id,
                    "new_version": None # No new version created
                })

        # --- Database Interaction (Code Changed) --- 
        version_dict = None
        if script and fixed_code != script_content:
            logger.debug(f"Saving debugged version for script ID: {script_id}")
            latest_version = ScriptVersion.query.filter_by(script_id=script.id).order_by(ScriptVersion.version.desc()).first()
            new_version_num = (latest_version.version + 1) if latest_version else 1
            
            new_version = ScriptVersion(
                script_id=script.id,
                version=new_version_num,
                content=fixed_code,
                changes=f"Debugged: {analysis[:150]}..." # Truncate analysis for changes field
            )
            db.session.add(new_version)
            
            # Update the main script content as well
            script.content = fixed_code 
            script.updated_at = db.func.current_timestamp()
            
            db.session.commit()
            logger.info(f"Created debugged ScriptVersion ID: {new_version.id} for Script ID: {script.id}")
            version_dict = new_version.to_dict()
        else:
            if script:
                logger.info(f"Debug analysis complete for script {script_id}, code was identical.")
            else:
                logger.info("Debug completed without script ID, no version saved to database")
            
        return jsonify({
            "success": True,
            "analysis": analysis,
            "explanation": analysis,  # Add this for frontend compatibility
            "fixed_code": fixed_code,
            "diff_html": generateDiffHtml(script_content, fixed_code),  # Better diff display
            "script_id": script_id if script else None,
            "new_version": version_dict # Include new version info if created
        })

    except Exception as e:
        logger.error(f"Error in debug_script API: {e}")
        logger.error(traceback.format_exc())
        db.session.rollback()
        return jsonify({"success": False, "error": str(e), "message": "Failed to debug script"}), 500

# Coding API - Modify Script
@app.route('/api/coding/modify', methods=['POST'])
# @csrf.exempt
def modify_script():
    if not coding_module:
        return jsonify({"success": False, "error": "Coding module not initialized."}), 500

    try:
        data = request.json
        logger.info(f"Received data in modify_script: {data}")
        
        script_id = data.get('script_id')
        modification_request = data.get('modification_request')
        script_content = data.get('script_content') # Get current content from request

        if not modification_request or script_content is None:
            return jsonify({"success": False, "error": "Missing modification_request or script_content"}), 400

        # If script_id is missing but we have content, we can still proceed with modification
        script = None
        if script_id:
            script = Script.query.get(script_id)
            if not script:
                logger.warning(f"Script ID {script_id} not found in database")
        else:
            logger.warning("No script_id provided, proceeding with content-only modification")

        logger.debug(f"Calling coding_module.modify_script")
        # Call refactored modify method (returns modified code string or error string)
        modify_result = coding_module.modify_script(script_content, modification_request)
        
        # Check if the result is a dictionary or just a string
        if isinstance(modify_result, dict):
            explanation = modify_result.get('explanation', f"Script modified according to request: {modification_request[:100]}...")
            modified_code = modify_result.get('modified_code', '')
        else:
            # Backwards compatibility with older module versions that return just the code string
            explanation = f"Script modified according to request: {modification_request[:100]}..."
            modified_code = modify_result

        if isinstance(modified_code, str) and modified_code.startswith("Error modifying script:"):
            logger.error(f"Module Error in modify_script: {modified_code}")
            return jsonify({"success": False, "error": modified_code}), 500
        
        # --- Database Interaction (Code Changed) --- 
        version_dict = None
        if script and modified_code != script_content:
            logger.debug(f"Saving modified version for script ID: {script_id}")
            latest_version = ScriptVersion.query.filter_by(script_id=script.id).order_by(ScriptVersion.version.desc()).first()
            new_version_num = (latest_version.version + 1) if latest_version else 1
            
            new_version = ScriptVersion(
                script_id=script.id,
                version=new_version_num,
                content=modified_code,
                changes=f"Modified: {modification_request[:150]}..." # Truncate request for changes field
            )
            db.session.add(new_version)
            
            # Update the main script content as well
            script.content = modified_code
            script.updated_at = db.func.current_timestamp()
            
            db.session.commit()
            logger.info(f"Created modified ScriptVersion ID: {new_version.id} for Script ID: {script.id}")
            version_dict = new_version.to_dict()
        else:
            if script:
                logger.info(f"Modification complete for script {script_id}, code was identical or not changed.")
            else:
                logger.info("Modification completed without script ID, no version saved to database")
             
        return jsonify({
            "success": True,
            "modified_code": modified_code,
            "explanation": explanation,
            "diff_html": generateDiffHtml(script_content, modified_code),  # Better diff display
            "script_id": script_id if script else None,
            "new_version": version_dict # Include new version info if created
        })

    except Exception as e:
        logger.error(f"Error in modify_script API: {e}")
        logger.error(traceback.format_exc())
        db.session.rollback()
        return jsonify({"success": False, "error": str(e), "message": "Failed to modify script"}), 500

# Coding API - Diff Checker (Simplified - No AI Explanation)
@app.route('/api/coding/diffcheck', methods=['POST'])
def diffcheck():
    # Note: This route does not use the AI model directly anymore
    try:
        data = request.json
        original_content = data.get('original_content')
        new_content = data.get('new_content')
        version1_id = data.get('version1_id') # Optional, pass-through
        version2_id = data.get('version2_id') # Optional, pass-through

        if original_content is None or new_content is None:
            return jsonify({"success": False, "error": "Missing original_content or new_content"}), 400

        logger.debug("Generating diff between two content versions.")
        # Use the static method from CodingModule
        diff_html = generateDiffHtml(original_content, new_content)
        
        return jsonify({
            "success": True, 
            "diff_html": diff_html,
            # No AI explanation in this simplified version
            "explanation": "Diff generated.", 
            "version1_id": version1_id, # Pass back if provided
            "version2_id": version2_id  # Pass back if provided
        })

    except Exception as e:
        logger.error(f"Error in diffcheck API: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e), "message": "Failed to generate diff"}), 500

# Testing API - Generate Test Case
@app.route('/api/testing/generate', methods=['POST'])
# @csrf.exempt
def generate_test_case():
    if not testing_module:
        return jsonify({"success": False, "error": "Testing module not initialized. Check API key."}), 500
    
    try:
        data = request.json
        
        # Get script ID and content from the request
        script_id = data.get('script_id')
        script_content = data.get('script_content')
        requirements = data.get('requirements', '')
        
        if not script_content:
            return jsonify({"success": False, "error": "Missing script_content"}), 400
        
        # Call the testing module to generate a test case
        try:
            test_case = testing_module.generate_test_case(script_content, requirements)
        except Exception as e:
            logger.error(f"Error in testing module: {str(e)}")
            return jsonify({"success": False, "error": f"Error generating test case: {str(e)}"}), 500
        
        # Save the test case to the database if a script ID was provided
        if script_id:
            script = Script.query.get(script_id)
            if script:
                new_test_case = TestCase(
                    script_id=script.id,
                    title=f"Test for {script.title or 'Untitled Script'}",
                    content=test_case,
                    created_at=datetime.utcnow()
                )
                db.session.add(new_test_case)
                db.session.commit()
                
                return jsonify({
                    "success": True,
                    "test_case": new_test_case.to_dict(),
                    "message": "Test case generated and saved successfully."
                })
            else:
                logger.warning(f"Script ID {script_id} not found, returning generated test case without saving")
                
        # If no script ID or script not found, return the test case without saving
        return jsonify({
            "success": True,
            "test_case": {
                "id": None,
                "title": "Generated Test Case (Not Saved)",
                "content": test_case,
                "created_at": datetime.utcnow().isoformat()
            },
            "message": "Test case generated successfully (not saved to database)."
        })
        
    except Exception as e:
        logger.error(f"Error in generate_test_case API: {e}")
        logger.error(traceback.format_exc())
        db.session.rollback()
        return jsonify({"success": False, "error": str(e), "message": "Failed to generate test case"}), 500

# Testing API - Get Test Cases
@app.route('/api/testing/test-cases', methods=['GET'])
def get_test_cases():
    try:
        script_id = request.args.get('script_id')
        
        if not script_id:
            return jsonify({"success": False, "error": "Missing script_id parameter"}), 400
            
        # Check if script exists
        script = Script.query.get(script_id)
        if not script:
            return jsonify({"success": False, "error": "Script not found"}), 404
            
        # Get test cases for the script
        test_cases = TestCase.query.filter_by(script_id=script_id).order_by(TestCase.created_at.desc()).all()
        
        return jsonify({
            "success": True,
            "test_cases": [test_case.to_dict() for test_case in test_cases],
            "script_id": script_id
        })
        
    except Exception as e:
        logger.error(f"Error in get_test_cases API: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e), "message": "Failed to get test cases"}), 500

# Add missing route for getting a specific test case
@app.route('/api/testing/test-cases/<int:test_case_id>', methods=['GET'])
def get_test_case(test_case_id):
    try:
        test_case = TestCase.query.get(test_case_id)
        
        if not test_case:
            return jsonify({"success": False, "error": "Test case not found"}), 404
            
        return jsonify({
            "success": True,
            "test_case": test_case.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error in get_test_case API: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e), "message": "Failed to get test case"}), 500

# Get all scripts
@app.route('/api/coding/scripts', methods=['GET'])
def get_scripts():
    try:
        # Get all scripts
        scripts = Script.query.order_by(Script.created_at.desc()).all()
        
        return jsonify({
            "success": True,
            "scripts": [script.to_dict() for script in scripts]
        })
        
    except Exception as e:
        logger.error(f"Error in get_scripts API: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e), "message": "Failed to get scripts"}), 500

# Get a specific script
@app.route('/api/coding/scripts/<int:script_id>', methods=['GET'])
def get_script(script_id):
    try:
        script = Script.query.get(script_id)
        
        if not script:
            return jsonify({"success": False, "error": "Script not found"}), 404
            
        return jsonify({
            "success": True,
            "script": script.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error in get_script API: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e), "message": "Failed to get script"}), 500

# Get script versions
@app.route('/api/coding/scripts/<int:script_id>/versions', methods=['GET'])
def get_script_versions(script_id):
    try:
        script = Script.query.get(script_id)
        
        if not script:
            return jsonify({"success": False, "error": "Script not found"}), 404
            
        versions = ScriptVersion.query.filter_by(script_id=script_id).order_by(ScriptVersion.version.desc()).all()
        
        return jsonify({
            "success": True,
            "script_id": script_id,
            "versions": [version.to_dict() for version in versions]
        })
        
    except Exception as e:
        logger.error(f"Error in get_script_versions API: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e), "message": "Failed to get script versions"}), 500

# Chat API - Send Message
@app.route('/api/chat/send', methods=['POST'])
def send_chat_message():
    if not chat_module:
         return jsonify({"success": False, "error": "Chat module not initialized."}), 500

    try:
        data = request.json
        message = data.get('message')
        session_id = session.get('chat_session_id') # Use Flask session ID

        if not message:
            return jsonify({"success": False, "error": "Missing message"}), 400
        if not session_id:
            # Should not happen if chat() route was hit first, but handle defensively
            logger.warning("Chat session ID not found in Flask session for /api/chat/send")
            return jsonify({"success": False, "error": "Chat session not found. Please refresh the chat page."}), 400
            
        # --- Database Interaction: Get/Create Session and History --- 
        logger.debug(f"Processing chat message for session ID: {session_id}")
        # Get or create DB session record linked to the Flask session ID
        chat_db_session = ChatSession.query.filter_by(session_id=session_id).first()
        if not chat_db_session:
            logger.info(f"Creating new DB record for chat session: {session_id}")
            chat_db_session = ChatSession(session_id=session_id)
            db.session.add(chat_db_session)
            # We need the ID, so commit here
            db.session.commit() 
            logger.info(f"Created ChatSession DB ID: {chat_db_session.id}")
        else:
             logger.debug(f"Found existing ChatSession DB ID: {chat_db_session.id}")

        # Save user message to DB *before* calling the model
        user_msg = ChatMessage(session_id=chat_db_session.id, role='user', content=message)
        db.session.add(user_msg)
        db.session.commit()
        logger.debug(f"Saved user ChatMessage ID: {user_msg.id}")

        # Get history from DB for context (make sure it's ordered correctly)
        db_history = ChatMessage.query.filter_by(session_id=chat_db_session.id).order_by(ChatMessage.created_at.asc()).all()
        # Format for the model: list of {'role': str, 'content': str}
        history_for_model = [{'role': msg.role, 'content': msg.content} for msg in db_history]

        # Call refactored chat method (non-streaming)
        logger.debug(f"Calling chat_module.get_response for session ID: {session_id}")
        result = chat_module.get_response(message, chat_history=history_for_model)

        if not result.get('success'):
            logger.error(f"Module Error in send_chat_message: {result.get('error')}")
            # Optionally save an error message to history?
            # error_msg = ChatMessage(session_id=chat_db_session.id, role='assistant', content=f"Error: {result.get('error')}")
            # db.session.add(error_msg)
            # db.session.commit()
            return jsonify({"success": False, "error": result.get('error', 'Unknown chat error')}), 500

        assistant_response = result.get('response')

        # --- Database Interaction: Save Assistant Response --- 
        logger.debug(f"Saving assistant response for session ID: {session_id}")
        assistant_msg = ChatMessage(session_id=chat_db_session.id, role='assistant', content=assistant_response)
        db.session.add(assistant_msg)
        db.session.commit()
        logger.debug(f"Saved assistant ChatMessage ID: {assistant_msg.id}")

        return jsonify({
            "success": True, 
            "response": assistant_response,
            "session_id": session_id # Return session ID used
        })

    except Exception as e:
        logger.error(f"Error in send_chat_message API: {e}")
        logger.error(traceback.format_exc())
        db.session.rollback()
        return jsonify({"success": False, "error": str(e), "message": "Failed to send message"}), 500

# Chat API - Get History
@app.route('/api/chat/history', methods=['GET'])
def get_chat_history():
    session_id = session.get('chat_session_id') # Get Flask session ID
    if not session_id:
        logger.warning("Chat session ID not found in Flask session for /api/chat/history")
        return jsonify({"success": False, "error": "No active chat session found in your browser session."}), 400

    # Find the corresponding ChatSession in the database
    chat_db_session = ChatSession.query.filter_by(session_id=session_id).first()
    if not chat_db_session:
        logger.info(f"No chat history found in DB for session ID: {session_id}")
        # It's not an error if there's no history yet, return empty list
        return jsonify({"success": True, "messages": [], "session_id": session_id}), 200 

    try:
        logger.debug(f"Fetching chat history for DB session ID: {chat_db_session.id}")
        # Fetch associated messages ordered by creation time
        messages = ChatMessage.query.filter_by(session_id=chat_db_session.id).order_by(ChatMessage.created_at.asc()).all()
        return jsonify({
            "success": True,
            "messages": [msg.to_dict() for msg in messages],
            "session_id": session_id # Return the original Flask session ID
        })
    except Exception as e:
        logger.error(f"Error fetching chat history for session {session_id} (DB ID: {chat_db_session.id}): {e}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e), "message": "Failed to get chat history"}), 500

# Chat API - Clear History
@app.route('/api/chat/clear', methods=['POST'])
def clear_chat_history():
    session_id = session.get('chat_session_id') # Get Flask session ID
    if not session_id:
        logger.warning("Chat session ID not found in Flask session for /api/chat/clear")
        return jsonify({"success": False, "error": "No active chat session found in your browser session."}), 400

    # Find the corresponding ChatSession in the database
    chat_db_session = ChatSession.query.filter_by(session_id=session_id).first()
    if not chat_db_session:
        logger.info(f"No chat history to clear in DB for session ID: {session_id}")
        # Nothing to clear, return success
        return jsonify({"success": True, "message": "No history to clear"}), 200 

    try:
        logger.info(f"Clearing chat history for session ID: {session_id} (DB ID: {chat_db_session.id})")
        # Delete associated messages
        num_deleted = ChatMessage.query.filter_by(session_id=chat_db_session.id).delete()
        # Optional: Delete the ChatSession row itself? 
        # db.session.delete(chat_db_session) 
        db.session.commit()
        logger.info(f"Cleared {num_deleted} messages for chat session {session_id}")
        # Optional: Remove from Flask session too? 
        # session.pop('chat_session_id', None)
        return jsonify({"success": True, "message": "Chat history cleared"})
    except Exception as e:
        logger.error(f"Error clearing chat history for session {session_id} (DB ID: {chat_db_session.id}): {e}")
        logger.error(traceback.format_exc())
        db.session.rollback() # Rollback in case of error
        return jsonify({"success": False, "error": str(e), "message": "Failed to clear chat history"}), 500

# API Status route (Updated for OpenRouter)
@app.route('/api/status', methods=['GET'])
def api_status():
    """Simple endpoint to check if API is working and modules are initialized."""
    openrouter_configured = bool(app.config.get('OPENROUTER_API_KEY'))
    # Check if each module instance exists (was not None after init)
    coding_module_ok = bool(coding_module)
    testing_module_ok = bool(testing_module)
    chat_module_ok = bool(chat_module)
    modules_initialized = coding_module_ok and testing_module_ok and chat_module_ok
    
    status = {
        "api": "online",
        "openrouter_key_set": openrouter_configured,
        "modules_initialized": modules_initialized,
        "coding_module_status": "initialized" if coding_module_ok else "failed",
        "testing_module_status": "initialized" if testing_module_ok else "failed",
        "chat_module_status": "initialized" if chat_module_ok else "failed",
        "environment": "production" if not app.config['DEBUG'] else "development"
    }
    
    # Add a more specific error if key is set but modules failed
    if openrouter_configured and not modules_initialized:
        status["initialization_error"] = "One or more modules failed to initialize. Check logs and ensure OPENROUTER_API_KEY is valid."
        
    # Optionally add DB connection check
    try:
        db.session.execute('SELECT 1')
        status["database_connection"] = "connected"
    except Exception as db_err:
        logger.error(f"Database connection check failed: {db_err}")
        status["database_connection"] = "error"
        status["database_error"] = str(db_err)
        
    return jsonify({"success": True, "status": status})

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    # Log the 404 error
    logger.warning(f"404 Not Found: {request.path} (Referer: {request.referrer})")
    return render_template('error.html', error_code=404, error_message="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    # Log the full error and traceback
    logger.error(f"500 Internal Server Error: {request.path} - {e}")
    logger.error(traceback.format_exc())
    # Avoid exposing detailed errors to the user in production
    error_message = "An internal server error occurred." if not app.config['DEBUG'] else str(e)
    # Ensure DB rollback in case the error happened mid-transaction
    try:
        db.session.rollback()
        logger.info("Rolled back database session due to 500 error.")
    except Exception as rollback_err:
         logger.error(f"Error during automatic rollback on 500 error: {rollback_err}")
         
    return render_template('error.html', error_code=500, error_message=error_message), 500

# Command to create database tables
@app.cli.command("init-db")
def init_db_command():
    """Creates the database tables."""
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully.")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")

# For local development
if __name__ == '__main__':
    # Create tables if DB doesn't exist (useful for first run)
    db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
    if not os.path.exists(db_path):
        logger.info(f"Database file not found at {db_path}. Creating tables.")
        with app.app_context():
             try:
                 db.create_all()
                 logger.info("Database tables created successfully.")
             except Exception as e:
                 logger.error(f"Error creating database tables on startup: {e}")
                 
    app.run(debug=app.config['DEBUG']) # Use debug setting from config

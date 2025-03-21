import os
from flask import Flask, render_template, request, jsonify, session
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
import json
import uuid

from config import config
from database import db, Script, TestCase, ChatSession
from modules.coding import CodingModule
from modules.testing import TestingModule
from modules.chat import ChatModule

def create_app(config_name="default"):
    """
    Create and configure the Flask application.
    
    Args:
        config_name (str): Configuration to use
    
    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__, static_folder="static", template_folder="templates")
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Setup CSRF protection
    csrf = CSRFProtect(app)
    
    # Initialize extensions
    db.init_app(app)
    
    # Setup proxy fix for Vercel
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # Initialize modules
    coding_module = CodingModule(app.config["OPENAI_API_KEY"], app.config["OPENAI_MODEL"])
    testing_module = TestingModule(app.config["OPENAI_API_KEY"], app.config["OPENAI_MODEL"])
    chat_module = ChatModule(app.config["OPENAI_API_KEY"], app.config["OPENAI_MODEL"])
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Routes
    @app.route('/')
    def index():
        """Render the landing page."""
        return render_template('index.html')
    
    # Coding Module Routes
    @app.route('/coding')
    def coding():
        """Render the coding module page."""
        scripts = Script.query.order_by(Script.updated_at.desc()).all()
        return render_template('coding.html', scripts=scripts)
    
    @app.route('/api/coding/generate', methods=['POST'])
    def generate_script():
        """Generate a new script."""
        data = request.json
        prompt = data.get('prompt')
        language = data.get('language', 'python')
        
        if not prompt:
            return jsonify({"success": False, "message": "Prompt is required"}), 400
        
        result = coding_module.generate_script(prompt, language)
        return jsonify(result)
    
    @app.route('/api/coding/debug', methods=['POST'])
    def debug_script():
        """Debug an existing script."""
        data = request.json
        script_id = data.get('script_id')
        script_content = data.get('script_content')
        
        if not script_id or not script_content:
            return jsonify({"success": False, "message": "Script ID and content are required"}), 400
        
        result = coding_module.debug_script(script_id, script_content)
        return jsonify(result)
    
    @app.route('/api/coding/modify', methods=['POST'])
    def modify_script():
        """Modify an existing script."""
        data = request.json
        script_id = data.get('script_id')
        script_content = data.get('script_content')
        modification_request = data.get('modification_request')
        
        if not script_id or not script_content or not modification_request:
            return jsonify({"success": False, "message": "Script ID, content, and modification request are required"}), 400
        
        result = coding_module.modify_script(script_id, script_content, modification_request)
        return jsonify(result)
    
    @app.route('/api/coding/explain-changes', methods=['POST'])
    def explain_changes():
        """Explain changes between two versions of a script."""
        data = request.json
        old_content = data.get('old_content')
        new_content = data.get('new_content')
        
        if not old_content or not new_content:
            return jsonify({"success": False, "message": "Old and new content are required"}), 400
        
        result = coding_module.explain_changes(old_content, new_content)
        return jsonify(result)
    
    @app.route('/api/coding/compare-versions', methods=['POST'])
    def compare_versions():
        """Compare two versions of a script."""
        data = request.json
        script_id = data.get('script_id')
        version1_id = data.get('version1_id')
        version2_id = data.get('version2_id')
        
        if not script_id or not version1_id or not version2_id:
            return jsonify({"success": False, "message": "Script ID and version IDs are required"}), 400
        
        result = coding_module.compare_versions(script_id, version1_id, version2_id)
        return jsonify(result)
    
    @app.route('/api/coding/versions/<int:script_id>', methods=['GET'])
    def get_script_versions(script_id):
        """Get all versions of a script."""
        result = coding_module.get_script_versions(script_id)
        return jsonify(result)
    
    @app.route('/api/coding/scripts', methods=['GET'])
    def get_scripts():
        """Get all scripts."""
        scripts = Script.query.order_by(Script.updated_at.desc()).all()
        return jsonify({
            "success": True,
            "scripts": [script.to_dict() for script in scripts],
            "message": f"Retrieved {len(scripts)} scripts successfully"
        })
    
    @app.route('/api/coding/scripts/<int:script_id>', methods=['GET'])
    def get_script(script_id):
        """Get a specific script."""
        script = Script.query.get(script_id)
        
        if not script:
            return jsonify({"success": False, "message": "Script not found"}), 404
        
        return jsonify({
            "success": True,
            "script": script.to_dict(),
            "message": "Script retrieved successfully"
        })
    
    # Testing Module Routes
    @app.route('/testing')
    def testing():
        """Render the testing module page."""
        scripts = Script.query.order_by(Script.updated_at.desc()).all()
        test_cases = TestCase.query.order_by(TestCase.updated_at.desc()).all()
        return render_template('testing.html', scripts=scripts, test_cases=test_cases)
    
    @app.route('/api/testing/generate', methods=['POST'])
    def generate_test_case():
        """Generate a test case for a script."""
        data = request.json
        script_id = data.get('script_id')
        script_content = data.get('script_content')
        test_requirements = data.get('test_requirements')
        
        if not script_id or not script_content or not test_requirements:
            return jsonify({"success": False, "message": "Script ID, content, and test requirements are required"}), 400
        
        result = testing_module.generate_test_case(script_id, script_content, test_requirements)
        return jsonify(result)
    
    @app.route('/api/testing/execute', methods=['POST'])
    def execute_test():
        """Execute a test case."""
        data = request.json
        test_case_id = data.get('test_case_id')
        test_content = data.get('test_content')
        script_content = data.get('script_content')
        
        if not test_case_id or not test_content or not script_content:
            return jsonify({"success": False, "message": "Test case ID, content, and script content are required"}), 400
        
        result = testing_module.execute_test(test_case_id, test_content, script_content)
        return jsonify(result)
    
    @app.route('/api/testing/improve', methods=['POST'])
    def improve_test_case():
        """Improve a test case based on execution results."""
        data = request.json
        test_case_id = data.get('test_case_id')
        test_content = data.get('test_content')
        script_content = data.get('script_content')
        test_result_output = data.get('test_result_output')
        
        if not test_case_id or not test_content or not script_content or not test_result_output:
            return jsonify({"success": False, "message": "Test case ID, content, script content, and test result output are required"}), 400
        
        result = testing_module.improve_test_case(test_case_id, test_content, script_content, test_result_output)
        return jsonify(result)
    
    @app.route('/api/testing/test-cases', methods=['GET'])
    def get_test_cases():
        """Get all test cases."""
        script_id = request.args.get('script_id')
        
        if script_id:
            test_cases = TestCase.query.filter_by(script_id=script_id).order_by(TestCase.updated_at.desc()).all()
        else:
            test_cases = TestCase.query.order_by(TestCase.updated_at.desc()).all()
        
        return jsonify({
            "success": True,
            "test_cases": [test_case.to_dict() for test_case in test_cases],
            "message": f"Retrieved {len(test_cases)} test cases successfully"
        })
    
    @app.route('/api/testing/test-cases/<int:test_case_id>', methods=['GET'])
    def get_test_case(test_case_id):
        """Get a specific test case."""
        test_case = TestCase.query.get(test_case_id)
        
        if not test_case:
            return jsonify({"success": False, "message": "Test case not found"}), 404
        
        return jsonify({
            "success": True,
            "test_case": test_case.to_dict(),
            "message": "Test case retrieved successfully"
        })
    
    # Chat Module Routes
    @app.route('/chat')
    def chat():
        """Render the chat module page."""
        # Create or get chat session
        if 'chat_session_id' not in session:
            result = chat_module.create_session()
            if result["success"]:
                session['chat_session_id'] = result["session"]["session_id"]
            else:
                return render_template('error.html', error=result["error"])
        
        return render_template('chat.html')
    
    @app.route('/api/chat/session', methods=['POST'])
    def create_chat_session():
        """Create a new chat session."""
        result = chat_module.create_session()
        
        if result["success"]:
            session['chat_session_id'] = result["session"]["session_id"]
        
        return jsonify(result)
    
    @app.route('/api/chat/send', methods=['POST'])
    def send_chat_message():
        """Send a message to the chat."""
        data = request.json
        message = data.get('message')
        query_type = data.get('query_type', 'general')
        session_id = session.get('chat_session_id') or data.get('session_id')
        
        if not session_id:
            # Create a new session if one doesn't exist
            result = chat_module.create_session()
            if result["success"]:
                session_id = result["session"]["session_id"]
                session['chat_session_id'] = session_id
            else:
                return jsonify(result), 500
        
        if not message:
            return jsonify({"success": False, "message": "Message is required"}), 400
        
        result = chat_module.send_message(session_id, message, query_type)
        return jsonify(result)
    
    @app.route('/api/chat/history', methods=['GET'])
    def get_chat_history():
        """Get the conversation history for the current session."""
        session_id = session.get('chat_session_id')
        
        if not session_id:
            return jsonify({"success": False, "message": "No active chat session"}), 400
        
        result = chat_module.get_conversation_history(session_id)
        return jsonify(result)
    
    @app.route('/api/chat/clear', methods=['POST'])
    def clear_chat_history():
        """Clear the conversation history for the current session."""
        session_id = session.get('chat_session_id')
        
        if not session_id:
            return jsonify({"success": False, "message": "No active chat session"}), 400
        
        result = chat_module.clear_conversation_history(session_id)
        return jsonify(result)
    
    @app.route('/api/chat/ecu-explanation', methods=['POST'])
    def generate_ecu_explanation():
        """Generate an explanation about a specific type of ECU."""
        data = request.json
        ecu_type = data.get('ecu_type')
        session_id = session.get('chat_session_id') or data.get('session_id')
        
        if not session_id:
            # Create a new session if one doesn't exist
            result = chat_module.create_session()
            if result["success"]:
                session_id = result["session"]["session_id"]
                session['chat_session_id'] = session_id
            else:
                return jsonify(result), 500
        
        if not ecu_type:
            return jsonify({"success": False, "message": "ECU type is required"}), 400
        
        result = chat_module.generate_ecu_explanation(session_id, ecu_type)
        return jsonify(result)
    
    @app.route('/api/chat/damage-scenario', methods=['POST'])
    def generate_damage_scenario():
        """Generate a damage scenario based on CIA triad."""
        data = request.json
        component = data.get('component')
        cia_aspect = data.get('cia_aspect')
        session_id = session.get('chat_session_id') or data.get('session_id')
        
        if not session_id:
            # Create a new session if one doesn't exist
            result = chat_module.create_session()
            if result["success"]:
                session_id = result["session"]["session_id"]
                session['chat_session_id'] = session_id
            else:
                return jsonify(result), 500
        
        if not component or not cia_aspect:
            return jsonify({"success": False, "message": "Component and CIA aspect are required"}), 400
        
        result = chat_module.generate_damage_scenario(session_id, component, cia_aspect)
        return jsonify(result)
    
    @app.route('/api/chat/threat-scenario', methods=['POST'])
    def generate_threat_scenario():
        """Generate a threat scenario based on STRIDE model."""
        data = request.json
        component = data.get('component')
        stride_aspect = data.get('stride_aspect')
        session_id = session.get('chat_session_id') or data.get('session_id')
        
        if not session_id:
            # Create a new session if one doesn't exist
            result = chat_module.create_session()
            if result["success"]:
                session_id = result["session"]["session_id"]
                session['chat_session_id'] = session_id
            else:
                return jsonify(result), 500
        
        if not component or not stride_aspect:
            return jsonify({"success": False, "message": "Component and STRIDE aspect are required"}), 400
        
        result = chat_module.generate_threat_scenario(session_id, component, stride_aspect)
        return jsonify(result)
    
    @app.route('/api/chat/attack-pattern', methods=['POST'])
    def generate_attack_pattern():
        """Generate attack patterns based on dataflow description."""
        data = request.json
        dataflow_description = data.get('dataflow_description')
        session_id = session.get('chat_session_id') or data.get('session_id')
        
        if not session_id:
            # Create a new session if one doesn't exist
            result = chat_module.create_session()
            if result["success"]:
                session_id = result["session"]["session_id"]
                session['chat_session_id'] = session_id
            else:
                return jsonify(result), 500
        
        if not dataflow_description:
            return jsonify({"success": False, "message": "Dataflow description is required"}), 400
        
        result = chat_module.generate_attack_pattern(session_id, dataflow_description)
        return jsonify(result)
    
    @app.errorhandler(404)
    def page_not_found(e):
        """Handle 404 errors."""
        return render_template('error.html', error="Page not found"), 404
    
    @app.errorhandler(500)
    def server_error(e):
        """Handle 500 errors."""
        return render_template('error.html', error="Internal server error"), 500
    
    return app

# Create the application instance
app = create_app(os.getenv('FLASK_CONFIG') or 'default')

if __name__ == '__main__':
    app.run(debug=True)
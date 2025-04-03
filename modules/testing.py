import os
import tempfile
import time
import unittest
import io
import sys
import contextlib
import traceback
from openai import OpenAI
from database import db, Script, TestCase, TestResult
from flask import current_app

class TestingModule:
    def __init__(self, api_key=None, model=None, app=None):
        """Initialize the testing module with API credentials."""
        # Store Flask app reference if provided
        self.app = app
        
        # Get API key and model from app config if available
        if app:
            api_key = api_key or app.config.get('DEEPSEEK_API_KEY')
            model = model or app.config.get('DEEPSEEK_MODEL', 'deepseek-chat')
        else:
            api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
            model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
            
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not set in environment or app config")
            
        # Initialize the OpenAI client with DeepSeek's base URL and API key
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.model = model
    
    def generate_test_case(self, script_id, script_content, test_requirements):
        """
        Generate a test case for a given script based on the requirements.
        
        Args:
            script_id (int): ID of the script to test
            script_content (str): Content of the script to test
            test_requirements (str): Description of test requirements
        
        Returns:
            dict: Generated test case or a generator if streaming is enabled
        """
        system_message = """You are an expert in writing Python unit tests. Your task is to create
        comprehensive test cases for the provided code, following best practices for testing.
        Include setup, assertions, and error handling in your tests."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Write unit tests for the following code, according to these requirements: '{test_requirements}'\n\n{script_content}"}
                ],
                temperature=0.2,
                max_tokens=4000,
                stream=True
            )
            
            # Return the streaming response
            return {
                "success": True,
                "stream": response,
                "script_id": script_id,
                "title": test_requirements.split('\n')[0].strip() if '\n' in test_requirements else test_requirements[:50] + "..."
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to generate test case"
            }
    
    def execute_test(self, test_case_id, test_content, script_content):
        """
        Execute a test case against a script.
        
        Args:
            test_case_id (int): ID of the test case to execute
            test_content (str): Content of the test case
            script_content (str): Content of the script to test
        
        Returns:
            dict: Test results
        """
        try:
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create the script module file
                script_module_name = "script_module.py"
                script_module_path = os.path.join(temp_dir, script_module_name)
                
                with open(script_module_path, 'w') as f:
                    f.write(script_content)
                
                # Create the test file
                test_file_name = "test_script.py"
                test_file_path = os.path.join(temp_dir, test_file_name)
                
                # Modify imports to use the local module
                test_content = test_content.replace("import unittest", "import unittest, sys\nsys.path.append('.')")
                
                # Replace any imports of the original module
                module_name = "script_module"
                if "import " in script_content:
                    for line in script_content.split('\n'):
                        if line.startswith("class "):
                            class_name = line.split('class ')[1].split('(')[0].strip()
                            test_content = test_content.replace(f"from {class_name}", f"from {module_name}")
                            test_content = test_content.replace(f"import {class_name}", f"from {module_name} import {class_name}")
                
                with open(test_file_path, 'w') as f:
                    f.write(test_content)
                
                # Execute the test
                start_time = time.time()
                
                # Capture stdout and stderr
                stdout_buffer = io.StringIO()
                stderr_buffer = io.StringIO()
                
                with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                    try:
                        # Change to the temporary directory
                        original_dir = os.getcwd()
                        os.chdir(temp_dir)
                        
                        # Create a TestLoader and a TestRunner
                        loader = unittest.TestLoader()
                        runner = unittest.TextTestRunner(stream=stdout_buffer, verbosity=2)
                        
                        # Load and run the tests
                        tests = loader.discover('.', pattern=test_file_name)
                        result = runner.run(tests)
                        
                        # Change back to the original directory
                        os.chdir(original_dir)
                        
                        status = "passed" if result.wasSuccessful() else "failed"
                    except Exception as e:
                        status = "error"
                        traceback.print_exc(file=stderr_buffer)
                
                end_time = time.time()
                execution_time = end_time - start_time
                
                # Combine stdout and stderr
                output = stdout_buffer.getvalue() + "\n" + stderr_buffer.getvalue()
                
                # Save the test result
                test_result = TestResult(
                    test_case_id=test_case_id,
                    status=status,
                    output=output,
                    execution_time=execution_time
                )
                db.session.add(test_result)
                db.session.commit()
                
                return {
                    "success": True,
                    "test_result": test_result.to_dict(),
                    "message": f"Test executed with status: {status}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to execute test"
            }
    
    def improve_test_case(self, test_case_id, test_content, script_content, test_result_output):
        """
        Improve a test case based on previous execution results.
        
        Args:
            test_case_id (int): ID of the test case to improve
            test_content (str): Current content of the test case
            script_content (str): Content of the script being tested
            test_result_output (str): Output from the previous test execution
        
        Returns:
            dict: Improved test case or a generator if streaming is enabled
        """
        system_message = """You are an expert in improving Python unit tests. Your task is to analyze
        the provided test case, the script it's testing, and the execution results, and then make
        improvements to fix any issues or enhance test coverage."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"""Improve the following test case:
                    
                    SCRIPT:
                    ```python
                    {script_content}
                    ```
                    
                    TEST CASE:
                    ```python
                    {test_content}
                    ```
                    
                    EXECUTION RESULTS:
                    ```
                    {test_result_output}
                    ```
                    
                    Please provide an improved version of the test case that addresses any issues."""}
                ],
                temperature=0.2,
                max_tokens=4000,
                stream=True
            )
            
            # Return the streaming response
            return {
                "success": True,
                "stream": response,
                "test_case_id": test_case_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to improve test case"
            }
    
    def _extract_code_from_markdown(self, markdown_content):
        """Extract code from markdown code blocks."""
        lines = markdown_content.split('\n')
        
        # If first line contains the language identifier (```python)
        if lines[0].startswith("```"):
            lines = lines[1:]
        
        # If last line is just the closing tag
        if lines[-1] == "```":
            lines = lines[:-1]
        
        return '\n'.join(lines)

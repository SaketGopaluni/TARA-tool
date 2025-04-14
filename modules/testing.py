import logging
import subprocess
import tempfile
import os
import httpx
from openai import OpenAI, OpenAIError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestingModule:
    """Handles test case generation and execution."""

    def __init__(self, config):
        """Initialize the TestingModule with application configuration."""
        if not config.get('OPENROUTER_API_KEY'):
            raise ValueError("OpenRouter API key not found in configuration.")
            
        # Create an httpx client that doesn't trust environment proxy settings
        httpx_client = httpx.Client(trust_env=False)
            
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=config['OPENROUTER_API_KEY'],
            http_client=httpx_client
        )
        self.model = config.get('OPENROUTER_MODEL', 'meta-llama/llama-4-maverick:free')
        self.site_url = config.get('YOUR_SITE_URL')
        self.site_name = config.get('YOUR_SITE_NAME')
        self.extra_headers = {}
        if self.site_url:
            self.extra_headers["HTTP-Referer"] = self.site_url
        if self.site_name:
            self.extra_headers["X-Title"] = self.site_name

    def _call_openrouter(self, system_prompt, user_prompt):
        """Helper method to make calls to the OpenRouter API."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        try:
            logger.info(f"Calling OpenRouter model: {self.model} for testing module with headers: {self.extra_headers}")
            completion = self.client.chat.completions.create(
                extra_headers=self.extra_headers,
                model=self.model,
                messages=messages,
                temperature=0.5, # Slightly lower temperature for tests
                max_tokens=2048 # Adjust max tokens as needed
            )
            response_content = completion.choices[0].message.content
            logger.info("OpenRouter call successful for testing module.")
            return response_content.strip()
        except OpenAIError as e:
            logger.error(f"OpenRouter API call failed in testing module: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during OpenRouter call in testing module: {e}")
            raise

    def generate_test_cases(self, script_content, language, requirements="Generate standard unit tests."):
        """Generates test cases for the given script using OpenRouter."""
        # Determine the testing framework based on language (basic heuristic)
        test_framework = "unittest or pytest" if language.lower() == "python" else "a standard testing framework" 
        if language.lower() == "c++":
            test_framework = "Google Test or Catch2"
        elif language.lower() == "javascript":
             test_framework = "Jest or Mocha"

        system_prompt = f"You are an expert software tester specializing in writing test cases for {language} code, particularly for automotive and cybersecurity contexts. Generate comprehensive test cases using {test_framework} for the following script. Cover edge cases, common vulnerabilities (if applicable), and standard functionality. Output ONLY the raw test code, without any introduction, explanation, or surrounding text."
        
        # Include the specific requirements in the user prompt
        user_prompt = f"Script ({language}):\n```\n{script_content}\n```\n\nGenerate test cases for this script with these requirements: {requirements}"

        try:
            generated_tests = self._call_openrouter(system_prompt, user_prompt)
            # Post-processing: Ensure it looks like code, remove potential ``` markdown
            lang_lower = language.lower()
            if generated_tests.startswith(f"```{lang_lower}"):
                 generated_tests = generated_tests[len(f"```{lang_lower}\n"):]
            elif generated_tests.startswith("```"):
                 generated_tests = generated_tests[3:]
                 
            if generated_tests.endswith("\n```"):
                generated_tests = generated_tests[:-4]
            elif generated_tests.endswith("```"):
                 generated_tests = generated_tests[:-3]

            return {
                "success": True,
                "test_cases": generated_tests
            }
        except Exception as e:
            logger.error(f"Error generating test cases: {e}")
            return {
                "success": False,
                "error": f"Failed to generate test cases: {e}"
            }

    def execute_test(self, script_content, test_content, language):
        """
        Executes the provided test cases against the script.
        Note: This is a basic implementation and might require adjustments based on the specific language and testing framework.
        """
        logger.info(f"Attempting to execute tests for language: {language}")
        results = "Execution environment not set up for this language or framework."
        success = False

        # Basic execution for Python using unittest/pytest (requires file saving)
        if language.lower() == "python":
            try:
                with tempfile.TemporaryDirectory() as tempdir:
                    script_path = os.path.join(tempdir, "script_to_test.py")
                    test_path = os.path.join(tempdir, "test_script.py")

                    with open(script_path, 'w') as f:
                        f.write(script_content)
                    with open(test_path, 'w') as f:
                        f.write(test_content)

                    # Try running with pytest first, then unittest
                    try:
                        # Ensure pytest runs from the tempdir
                        process = subprocess.run(['pytest', test_path], capture_output=True, text=True, check=True, timeout=30, cwd=tempdir)
                        results = process.stdout + "\n" + process.stderr
                        success = process.returncode == 0
                        logger.info(f"Pytest execution successful (return code {process.returncode}).")
                    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as pytest_err:
                        logger.warning(f"Pytest execution failed ({pytest_err}), trying unittest.")
                        try:
                            # Ensure unittest runs from the tempdir and discovers tests in the file
                            process = subprocess.run(['python', '-m', 'unittest', test_path], capture_output=True, text=True, check=True, timeout=30, cwd=tempdir)
                            results = process.stdout + "\n" + process.stderr
                            success = process.returncode == 0
                            logger.info(f"Unittest execution successful (return code {process.returncode}).")
                        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as unittest_err:
                            logger.error(f"Both pytest and unittest execution failed. Pytest error: {pytest_err}, Unittest error: {unittest_err}")
                            results = f"Pytest failed: {pytest_err.stderr if hasattr(pytest_err, 'stderr') else pytest_err}\n\nUnittest failed: {unittest_err.stderr if hasattr(unittest_err, 'stderr') else unittest_err}"
                            success = False
                            
            except Exception as e:
                logger.error(f"Error setting up or running Python tests: {e}")
                results = f"Error during test execution setup: {e}"
                success = False
        else:
            logger.warning(f"Test execution not implemented for language: {language}")
            # Placeholder for other languages (C++, JavaScript, etc.)
            # This would require specific compilers/interpreters and test runners
            # For C++: Compile script and tests, link, run executable
            # For JS: Use Node.js with Jest/Mocha runner

        return {
            "success": success,
            "results": results
        }

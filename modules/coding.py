import logging
from openai import OpenAI, OpenAIError
import httpx
from diff_match_patch import diff_match_patch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CodingModule:
    """Handles script generation, debugging, and modification using an AI model via OpenRouter."""

    def __init__(self, config):
        """Initialize the CodingModule with application configuration."""
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
        
        # Log the prompts and payload before sending
        logger.info(f"_call_openrouter - System Prompt: {system_prompt}")
        logger.info(f"_call_openrouter - User Prompt: {user_prompt}")
        logger.info(f"_call_openrouter - Sending messages payload: {messages}") 
        logger.info(f"Calling OpenRouter model: {self.model} for coding with headers: {self.extra_headers}")
        
        try:
            completion = self.client.chat.completions.create(
                extra_headers=self.extra_headers,
                model=self.model,
                messages=messages,
                temperature=0.7, # Adjust temperature as needed
                max_tokens=2048 # Adjust max tokens as needed
            )
            response_content = completion.choices[0].message.content
            logger.info("OpenRouter call successful.")
            return response_content.strip()
        except OpenAIError as e:
            logger.error(f"OpenRouter API call failed: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during OpenRouter call: {e}")
            raise

    def generate_script(self, language, requirements):
        """Generates a script based on language and requirements using OpenRouter."""
        system_prompt = f"You are an expert programmer specializing in {language} for automotive cybersecurity applications. Generate a complete, well-commented, and functional script based ONLY on the user's requirements. Output ONLY the raw code for the script, without any introduction, explanation, or surrounding text."
        user_prompt = f"Language: {language}\nRequirements: {requirements}"
        
        try:
            generated_code = self._call_openrouter(system_prompt, user_prompt)
            # Post-processing: Ensure it looks like code, remove potential ``` markdown
            if generated_code.startswith(f"```{language}"):
                generated_code = generated_code[len(f"```{language}\n"):]
            if generated_code.startswith("```"):
                lines = generated_code.split('\n', 1)
                if len(lines) > 1:
                    generated_code = lines[1] # Skip the first line like ```python
                else:
                    generated_code = generated_code[3:] # Just remove ```
            if generated_code.endswith("\n```"):
                generated_code = generated_code[:-4]
            elif generated_code.endswith("```"):
                generated_code = generated_code[:-3]

            return generated_code
        except Exception as e:
            logger.error(f"Error in generate_script: {e}")
            return f"Error generating script: {e}"

    def debug_script(self, script_content):
        """Debugs the provided script using OpenRouter, identifying issues and suggesting fixes."""
        system_prompt = "You are an expert code debugger. Analyze the following script, identify any bugs, security vulnerabilities, or potential issues. Provide a concise analysis of the problems found and then provide the corrected version of the script. Format your response clearly with 'Analysis:' section and 'Corrected Script:' section. Output ONLY the analysis and the raw corrected code, without any other introduction or explanation."
        user_prompt = f"Script to debug:\n```\n{script_content}\n```"

        try:
            response = self._call_openrouter(system_prompt, user_prompt)
            
            # Parse the response to separate analysis and fixed code
            analysis = "Could not parse analysis from response."
            fixed_code = "Could not parse corrected script from response."
            
            analysis_marker = "Analysis:"
            code_marker = "Corrected Script:"
            
            analysis_start = response.find(analysis_marker)
            code_start = response.find(code_marker)
            
            if analysis_start != -1 and code_start != -1:
                analysis = response[analysis_start + len(analysis_marker):code_start].strip()
                fixed_code = response[code_start + len(code_marker):].strip()
            elif analysis_start != -1: # Found analysis but not code marker
                analysis = response[analysis_start + len(analysis_marker):].strip()
                fixed_code = "Corrected script not found after analysis."
            elif code_start != -1: # Found code but not analysis marker
                fixed_code = response[code_start + len(code_marker):].strip()
                analysis = "Analysis section not found before corrected script."
            else: # Couldn't find either marker
                # Assume the model might have just outputted the code if the analysis was simple
                # Or maybe it just gave analysis. Let's try to detect if it looks like code.
                # This is a heuristic and might need refinement.
                if 'def ' in response or 'class ' in response or 'function ' in response or 'main(' in response or '{' in response or ';' in response:
                    fixed_code = response # Assume it's mostly code
                    analysis = "Analysis not explicitly found, assuming direct code correction or simple issue."
                else:
                    analysis = response # Assume it's mostly analysis
                    fixed_code = script_content # Return original script if no correction found

            # Clean up potential markdown in fixed_code
            if fixed_code.startswith("```"):
                lines = fixed_code.split('\n', 1)
                if len(lines) > 1:
                    fixed_code = lines[1] # Skip the first line like ```python
                else:
                    fixed_code = fixed_code[3:] # Just remove ```
            if fixed_code.endswith("\n```"):
                fixed_code = fixed_code[:-4]
            elif fixed_code.endswith("```"):
                fixed_code = fixed_code[:-3]

            return {
                "analysis": analysis,
                "fixed_code": fixed_code
            }
        except Exception as e:
            logger.error(f"Error in debug_script: {e}")
            return {
                "analysis": f"Error during debugging: {e}",
                "fixed_code": script_content # Return original script on error
            }

    def modify_script(self, script_content, modification_prompt):
        """Modifies the provided script based on the modification prompt using OpenRouter."""
        system_prompt = "You are an expert programmer. Modify the following script based ONLY on the user's instructions. Output ONLY the raw modified code, without any introduction, explanation, or surrounding text."
        user_prompt = f"Script to modify:\n```\n{script_content}\n```\n\nModification instructions: {modification_prompt}"
        
        try:
            modified_code = self._call_openrouter(system_prompt, user_prompt)
            # Post-processing: Ensure it looks like code, remove potential ``` markdown
            if modified_code.startswith("```"):
                lines = modified_code.split('\n', 1)
                if len(lines) > 1:
                    modified_code = lines[1] # Skip the first line like ```python
                else:
                    modified_code = modified_code[3:] # Just remove ```
            if modified_code.endswith("\n```"):
                modified_code = modified_code[:-4]
            elif modified_code.endswith("```"):
                modified_code = modified_code[:-3]
            
            return modified_code
        except Exception as e:
            logger.error(f"Error in modify_script: {e}")
            return f"Error modifying script: {e}"

    @staticmethod
    def calculate_diff(text1, text2):
        """Calculates the difference between two texts using diff-match-patch."""
        dmp = diff_match_patch()
        diffs = dmp.diff_main(text1, text2)
        dmp.diff_cleanupSemantic(diffs)
        
        # Format diff for HTML display (similar to GitHub diff view)
        html_diff = []
        for (op, data) in diffs:
            text = data.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "&para;\n")
            if op == dmp.DIFF_INSERT:
                html_diff.append(f'<span class="diff-line-added">+{text}</span>')
            elif op == dmp.DIFF_DELETE:
                html_diff.append(f'<span class="diff-line-removed">-{text}</span>')
            elif op == dmp.DIFF_EQUAL:
                html_diff.append(f'<span>{text}</span>')
        return "".join(html_diff)

import os
import json
from openai import OpenAI
from diff_match_patch import diff_match_patch
from database import db, Script, ScriptVersion

class CodingModule:
    def __init__(self):
        """Initialize the coding module with DeepSeek API credentials from environment variable."""
        # Fetch the API key from the environment variable DEEPSEEK_API_KEY
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is not set")
        
        # Initialize the OpenAI client with DeepSeek's base URL and API key
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.model = "deepseek-chat"
        self.dmp = diff_match_patch()

    def generate_script(self, prompt, language="python"):
        """
        Generate a new script based on the provided prompt.
        
        Args:
            prompt (str): Description of the script to generate
            language (str): Programming language for the script
        
        Returns:
            dict: Generated script and metadata or a generator if streaming is enabled
        """
        system_message = f"""You are an expert {language} developer specializing in cybersecurity and
        automotive systems. Generate a well-commented, production-ready script based on the user's requirements.
        Focus on security best practices, error handling, and maintainability."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=4000,
                stream=True
            )
            
            # Return the streaming response
            title = prompt.split('\n')[0].strip() if '\n' in prompt else prompt[:50] + "..."
            return {
                "success": True,
                "stream": response,
                "title": title,
                "language": language
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to generate script"
            }
    
    def debug_script(self, script_id, script_content):
        """
        Debug an existing script and identify/fix errors.
        
        Args:
            script_id (int): ID of the script to debug
            script_content (str): Current content of the script
        
        Returns:
            dict: Debugged script and explanation or a generator if streaming is enabled
        """
        system_message = """You are an expert code debugger specializing in identifying and fixing errors in code.
        Analyze the provided code, identify any bugs, errors, or potential issues, and provide a fixed version
        of the code along with explanations for each fix."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Debug the following code and identify/fix any issues:\n\n{script_content}"}
                ],
                temperature=0.2,
                max_tokens=4000,
                stream=True
            )
            
            # Return the streaming response
            return {
                "success": True,
                "stream": response,
                "script_id": script_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to debug script"
            }
    
    def modify_script(self, script_id, script_content, modification_request):
        """
        Modify an existing script based on the provided request.
        
        Args:
            script_id (int): ID of the script to modify
            script_content (str): Current content of the script
            modification_request (str): Description of the requested modifications
        
        Returns:
            dict: Modified script and explanation or a generator if streaming is enabled
        """
        system_message = """You are an expert code modifier specializing in adapting existing code to new requirements.
        Analyze the provided code and the modification request, and provide a modified version of the code that
        addresses the requested changes. Include explanations for significant changes."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"""Modify the following code according to this request:
                    
                    MODIFICATION REQUEST:
                    {modification_request}
                    
                    CURRENT CODE:
                    {script_content}
                    
                    Please provide the modified code and explain the changes you made."""}
                ],
                temperature=0.2,
                max_tokens=4000,
                stream=True
            )
            
            # Return the streaming response
            return {
                "success": True,
                "stream": response,
                "script_id": script_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to modify script"
            }
    
    def explain_changes(self, old_content, new_content):
        """
        Generate an explanation of the changes between two versions of a script.
        
        Args:
            old_content (str): Previous content of the script
            new_content (str): New content of the script
        
        Returns:
            dict: Explanation of changes and diff visualization or a generator if streaming is enabled
        """
        system_message = """You are an expert code reviewer specializing in analyzing code changes.
        Examine the changes between the old and new versions of the code, and provide a clear,
        concise explanation of the changes, focusing on functionality, performance, and security impacts."""
        
        try:
            # Generate visual diff for display
            self.dmp.Diff_Timeout = 5.0  # Increase timeout for larger files
            diffs = self.dmp.diff_main(old_content, new_content)
            self.dmp.diff_cleanupSemantic(diffs)
            diff_html = self.dmp.diff_prettyHtml(diffs)
            
            # Remove css styling from the output for better display in the app
            diff_html = diff_html.replace('style="background:#e6ffe6;"', 'class="diff-add"')
            diff_html = diff_html.replace('style="background:#ffe6e6;"', 'class="diff-del"')
            
            # Call DeepSeek API for explanation
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"""Explain the changes between these two versions of code:
                    
                    ORIGINAL CODE:
                    ```
                    {old_content}
                    ```
                    
                    NEW CODE:
                    ```
                    {new_content}
                    ```
                    
                    Please provide a clear, concise explanation of the changes."""}
                ],
                temperature=0.3,
                max_tokens=2000,
                stream=True
            )
            
            # Return the streaming response and the diff HTML
            return {
                "success": True,
                "stream": response,
                "diff_html": diff_html
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to explain changes"
            }
    
    def compare_versions(self, script_id, version1_id, version2_id):
        """
        Compare two versions of a script and return the diff.
        
        Args:
            script_id (int): ID of the script
            version1_id (int): ID of the first version
            version2_id (int): ID of the second version
        
        Returns:
            dict: Diff visualization and metadata
        """
        try:
            # Get the script and versions
            script = Script.query.get(script_id)
            
            if not script:
                return {
                    "success": False,
                    "error": "Script not found",
                    "message": "Failed to compare versions: Script not found"
                }
            
            version1 = ScriptVersion.query.get(version1_id)
            version2 = ScriptVersion.query.get(version2_id)
            
            if not version1 or not version2:
                return {
                    "success": False,
                    "error": "One or both versions not found",
                    "message": "Failed to compare versions: One or both versions not found"
                }
            
            # Generate diff
            diffs = self.dmp.diff_main(version1.content, version2.content)
            self.dmp.diff_cleanupSemantic(diffs)
            diff_html = self.dmp.diff_prettyHtml(diffs)
            
            # Get explanation from the newer version
            explanation = version2.changes if version2.version > version1.version else version1.changes
            
            return {
                "success": True,
                "script": script.to_dict(),
                "version1": version1.to_dict(),
                "version2": version2.to_dict(),
                "diff_html": diff_html,
                "explanation": explanation,
                "message": "Versions compared successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to compare versions"
            }
    
    def get_script_versions(self, script_id):
        """
        Get all versions of a script.
        
        Args:
            script_id (int): ID of the script
        
        Returns:
            dict: List of script versions
        """
        try:
            script = Script.query.get(script_id)
            
            if not script:
                return {
                    "success": False,
                    "error": "Script not found",
                    "message": "Failed to get script versions: Script not found"
                }
            
            versions = ScriptVersion.query.filter_by(script_id=script_id).order_by(ScriptVersion.version).all()
            
            return {
                "success": True,
                "script": script.to_dict(),
                "versions": [version.to_dict() for version in versions],
                "message": f"Retrieved {len(versions)} versions successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get script versions"
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
    
    def _extract_code_and_explanation(self, content):
        """
        Extract code and explanation from AI response.
        
        Returns:
            tuple: (code, explanation)
        """
        # Check if response contains a code block
        if "```" in content:
            explanation_parts = []
            code_parts = []
            in_code_block = False
            
            for line in content.split('\n'):
                if line.startswith("```"):
                    in_code_block = not in_code_block
                    continue
                
                if in_code_block:
                    code_parts.append(line)
                else:
                    explanation_parts.append(line)
            
            code = '\n'.join(code_parts)
            explanation = '\n'.join(explanation_parts).strip()
            
        else:
            # No code block found, try to infer code and explanation
            lines = content.split('\n')
            
            # Assume first few lines are explanation
            for i, line in enumerate(lines):
                if line.strip() and (line.strip().startswith("def ") or 
                                    line.strip().startswith("class ") or 
                                    line.strip().startswith("import ") or 
                                    line.strip().startswith("# ")):
                    explanation = '\n'.join(lines[:i]).strip()
                    code = '\n'.join(lines[i:]).strip()
                    break
            else:
                # If no clear code indicators found, make a best guess
                explanation = content
                code = ""
        
        return code, explanation

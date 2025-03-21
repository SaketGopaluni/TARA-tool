import os
import json
from openai import OpenAI
from diff_match_patch import diff_match_patch
from database import db, Script, ScriptVersion

class CodingModule:
    def __init__(self, api_key, model):
        """Initialize the coding module with API credentials."""
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.dmp = diff_match_patch()

    def generate_script(self, prompt, language="python"):
        """
        Generate a new script based on the provided prompt.
        
        Args:
            prompt (str): Description of the script to generate
            language (str): Programming language for the script
        
        Returns:
            dict: Generated script and metadata
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
                max_tokens=4000
            )
            
            script_content = response.choices[0].message.content.strip()
            
            # Extract code from markdown code blocks if present
            if script_content.startswith("```") and script_content.endswith("```"):
                script_content = self._extract_code_from_markdown(script_content)
            
            # Create database entry
            title = prompt.split('\n')[0].strip() if '\n' in prompt else prompt[:50] + "..."
            script = Script(title=title, content=script_content, language=language)
            db.session.add(script)
            db.session.commit()
            
            # Create initial version
            script_version = ScriptVersion(
                script_id=script.id,
                content=script_content,
                version=1,
                changes="Initial script generation"
            )
            db.session.add(script_version)
            db.session.commit()
            
            return {
                "success": True,
                "script": script.to_dict(),
                "message": "Script generated successfully"
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
            dict: Debugged script and explanation
        """
        system_message = """You are an expert code debugger specializing in identifying and fixing errors in code.
        Analyze the provided code, identify any bugs, errors, or potential issues, and provide a fixed version
        of the code along with explanations for each fix."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Debug the following code:\n\n{script_content}"}
                ],
                temperature=0.2,
                max_tokens=4000
            )
            
            result_content = response.choices[0].message.content.strip()
            
            # Extract code and explanation
            debugged_code, explanation = self._extract_code_and_explanation(result_content)
            
            # Update the script in the database
            script = Script.query.get(script_id)
            if not script:
                return {
                    "success": False,
                    "error": "Script not found",
                    "message": "Failed to debug script: Script not found"
                }
            
            # Create new version
            current_version = ScriptVersion.query.filter_by(script_id=script_id).order_by(ScriptVersion.version.desc()).first()
            new_version = current_version.version + 1 if current_version else 1
            
            script_version = ScriptVersion(
                script_id=script.id,
                content=debugged_code,
                version=new_version,
                changes=explanation
            )
            
            # Update the script with the debugged code
            script.content = debugged_code
            
            db.session.add(script_version)
            db.session.commit()
            
            # Generate diff
            diffs = self.dmp.diff_main(script_content, debugged_code)
            self.dmp.diff_cleanupSemantic(diffs)
            diff_html = self.dmp.diff_prettyHtml(diffs)
            
            return {
                "success": True,
                "script": script.to_dict(),
                "explanation": explanation,
                "diff_html": diff_html,
                "message": "Script debugged successfully"
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
            dict: Modified script and explanation
        """
        system_message = """You are an expert code modifier. Your task is to modify the provided code
        according to the user's request. Provide the complete modified code along with a concise
        explanation of the changes you made."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Modify the following code according to this request: '{modification_request}'\n\n{script_content}"}
                ],
                temperature=0.2,
                max_tokens=4000
            )
            
            result_content = response.choices[0].message.content.strip()
            
            # Extract code and explanation
            modified_code, explanation = self._extract_code_and_explanation(result_content)
            
            # Update the script in the database
            script = Script.query.get(script_id)
            if not script:
                return {
                    "success": False,
                    "error": "Script not found",
                    "message": "Failed to modify script: Script not found"
                }
            
            # Create new version
            current_version = ScriptVersion.query.filter_by(script_id=script_id).order_by(ScriptVersion.version.desc()).first()
            new_version = current_version.version + 1 if current_version else 1
            
            script_version = ScriptVersion(
                script_id=script.id,
                content=modified_code,
                version=new_version,
                changes=explanation
            )
            
            # Update the script with the modified code
            script.content = modified_code
            
            db.session.add(script_version)
            db.session.commit()
            
            # Generate diff
            diffs = self.dmp.diff_main(script_content, modified_code)
            self.dmp.diff_cleanupSemantic(diffs)
            diff_html = self.dmp.diff_prettyHtml(diffs)
            
            return {
                "success": True,
                "script": script.to_dict(),
                "explanation": explanation,
                "diff_html": diff_html,
                "message": "Script modified successfully"
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
            dict: Explanation of changes and diff visualization
        """
        system_message = """You are an expert code analyzer. Your task is to explain the differences
        between two versions of code. Provide a detailed yet concise explanation of what has changed
        and why these changes might have been made."""
        
        try:
            # Generate diffs
            diffs = self.dmp.diff_main(old_content, new_content)
            self.dmp.diff_cleanupSemantic(diffs)
            diff_html = self.dmp.diff_prettyHtml(diffs)
            
            # Create diff text for AI analysis
            diff_text = ""
            for op, text in diffs:
                if op == -1:
                    diff_text += f"- {text}\n"
                elif op == 1:
                    diff_text += f"+ {text}\n"
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Explain the following changes in the code:\n\n{diff_text}"}
                ],
                temperature=0.2,
                max_tokens=2000
            )
            
            explanation = response.choices[0].message.content.strip()
            
            return {
                "success": True,
                "explanation": explanation,
                "diff_html": diff_html,
                "message": "Changes explained successfully"
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
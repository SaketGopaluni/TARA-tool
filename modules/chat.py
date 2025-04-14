import logging
from openai import OpenAI, OpenAIError
import os
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatModule:
    """Handles chat interactions with an AI assistant using OpenRouter."""

    def __init__(self, config):
        """Initialize the ChatModule with application configuration."""
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

    def get_response(self, user_message, chat_history=None):
        """Gets a response from the OpenRouter chat model based on the user message and history."""
        system_prompt = "You are TARA Assistant, an expert AI knowledgeable about automotive cybersecurity, ECUs (Electronic Control Units), Threat Analysis and Risk Assessment (TARA), STRIDE, and related security concepts. Be helpful, informative, and concise."
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # Add chat history if provided
        if chat_history:
            for entry in chat_history: # Assuming history is a list of {'role': 'user/assistant', 'content': 'message'}
                 if isinstance(entry, dict) and 'role' in entry and 'content' in entry:
                    messages.append({"role": entry['role'], "content": entry['content']})
                 else:
                     logger.warning(f"Skipping invalid chat history entry: {entry}")

        # Add the current user message
        messages.append({"role": "user", "content": user_message})

        try:
            logger.info(f"Calling OpenRouter model: {self.model} for chat with headers: {self.extra_headers}")
            completion = self.client.chat.completions.create(
                extra_headers=self.extra_headers,
                model=self.model,
                messages=messages,
                temperature=0.7, 
                max_tokens=1500 # Adjust as needed
            )
            response_content = completion.choices[0].message.content
            logger.info("OpenRouter chat call successful.")
            return {
                "success": True,
                "response": response_content.strip()
            }
        except OpenAIError as e:
            logger.error(f"OpenRouter API call failed in chat module: {e}")
            return {"success": False, "error": f"OpenRouter API Error: {e}"}
        except Exception as e:
            logger.error(f"An unexpected error occurred during OpenRouter call: {e}")
            return {"success": False, "error": f"An unexpected error occurred: {e}"} # Return error dict

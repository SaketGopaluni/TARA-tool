import logging
import base64
import json
from openai import OpenAI, OpenAIError
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FATranscriberModule:
    """Handles FA diagram transcription using AI."""

    def __init__(self, config):
        """Initialize the FATranscriberModule with application configuration."""
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

    def transcribe_image(self, image_data, filename=None, content_type=None):
        """Transcribes a FA diagram image using OpenRouter AI vision capabilities."""
        try:
            # Prepare base64 encoded image
            if isinstance(image_data, bytes):
                encoded_image = base64.b64encode(image_data).decode('utf-8')
            else:
                # Assume already base64 encoded
                encoded_image = image_data
            
            # Create the system prompt to instruct the AI
            system_prompt = """
You are an expert in functional architecture (FA) diagrams analysis for automotive systems. You need to extract information from a car architecture diagram showing ECUs and their communications. Follow these instructions precisely:

1. Identify the **Sheet Name** at the top-left corner of the diagram.

2. Identify all **rectangular boxes** which represent ECUs. These are your Start and End ECUs based on the direction of communication flow.

3. Identify any **rhombus shapes** which represent relay ECUs.

4. Find all **messages** contained within blue dashed boundaries near communication lines between ECUs.

5. Locate any **red dashed lines** that encompass ECUs and/or messages, along with their identifiers.

6. For each message, determine:
   - The exact message content
   - The Start ECU and End ECU (rectangular shapes at the communication endpoints)
   - The Sending ECU and Receiving ECU (based on proximity to the message)
   - Any Dashed Line identifier associated with that message/ECU

7. Create a structured table with these exact columns:
   - Sheet Name
   - Message
   - Start ECU
   - End ECU
   - Sending ECU
   - Receiving ECU
   - Dashed Line

8. For multiple messages between the same ECUs, create multiple rows with all data.

Format your response as a clean JSON array with each object having the 7 fields mentioned above.
Do not include any text outside the JSON array. Use the exact column names shown above as keys.
            """
            
            # User message with the image
            user_message = {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Analyze this functional architecture diagram and extract the information as instructed."
                    },
                    {
                        "type": "image_url",
                        "image_url": f"data:{content_type};base64,{encoded_image}"
                    }
                ]
            }
            
            # Create the messages array
            messages = [
                {"role": "system", "content": system_prompt},
                user_message
            ]
            
            logger.info(f"Calling OpenRouter model: {self.model} for FA transcription")
            # Call the OpenRouter API with the image
            completion = self.client.chat.completions.create(
                extra_headers=self.extra_headers,
                model=self.model,
                messages=messages,
                temperature=0.3,  # Lower temperature for more deterministic results
                max_tokens=2500   # Adjust based on expected output size
            )
            
            # Extract and process the response
            response_content = completion.choices[0].message.content
            logger.info("OpenRouter FA transcription call successful.")
            
            # Clean up the response to ensure it's valid JSON
            # Remove any markdown code blocks if present
            if response_content.startswith("```json"):
                response_content = response_content.split("```json")[1]
                if "```" in response_content:
                    response_content = response_content.split("```")[0]
            elif response_content.startswith("```"):
                response_content = response_content.split("```")[1]
                if "```" in response_content:
                    response_content = response_content.split("```")[0]
            
            # Strip whitespace
            response_content = response_content.strip()
            
            try:
                # Try to parse as JSON
                result = json.loads(response_content)
                
                # Standardize the key names to match our database model
                standardized_result = []
                for item in result:
                    standardized_item = {
                        "sheet_name": item.get("Sheet Name", ""),
                        "message": item.get("Message", ""),
                        "start_ecu": item.get("Start ECU", ""),
                        "end_ecu": item.get("End ECU", ""),
                        "sending_ecu": item.get("Sending ECU", ""),
                        "receiving_ecu": item.get("Receiving ECU", ""),
                        "dashed_line": item.get("Dashed Line", "")
                    }
                    standardized_result.append(standardized_item)
                
                return {
                    "success": True,
                    "data": standardized_result
                }
            except json.JSONDecodeError as json_err:
                logger.error(f"Failed to parse AI response as JSON: {json_err}")
                return {
                    "success": False,
                    "error": f"The AI response could not be parsed as JSON: {json_err}",
                    "raw_response": response_content
                }
            
        except OpenAIError as e:
            logger.error(f"OpenRouter API call failed in FA transcriber module: {e}")
            return {
                "success": False,
                "error": f"OpenRouter API Error: {e}"
            }
        except Exception as e:
            logger.error(f"An unexpected error occurred during OpenRouter call: {e}")
            return {
                "success": False, 
                "error": f"An unexpected error occurred: {e}"
            }

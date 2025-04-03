import os
import uuid
from openai import OpenAI
from database import db, ChatSession, ChatMessage
from flask import current_app

class ChatModule:
    def __init__(self, app=None):
        """Initialize the chat module with DeepSeek API credentials from environment variable."""
        # Store Flask app reference if provided
        self.app = app
        
        # Fetch the API key from the environment or app config
        if app:
            api_key = app.config.get('DEEPSEEK_API_KEY')
            self.model = app.config.get('DEEPSEEK_MODEL', 'deepseek-chat')
        else:
            api_key = os.getenv("DEEPSEEK_API_KEY")
            self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
            
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not set in environment or app config")
        
        # Initialize the OpenAI client with DeepSeek's base URL and API key
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        
        # Define prompt templates for different types of queries
        self.prompt_templates = {
            "ecu_explanation": """You are an expert in automotive cybersecurity, specifically focusing on Electronic Control Units (ECUs).
            Provide detailed explanations about ECUs, their functions, and their role in automotive cybersecurity.
            Include information on architecture, common vulnerabilities, protection mechanisms, and industry standards.""",
            
            "damage_scenario": """You are an expert in automotive security risk assessment. Generate potential 
            damage scenarios based on the CIA (Confidentiality, Integrity, Availability) triad for the specified 
            system or component. For each scenario, describe the impact on the vehicle, potential safety implications, 
            and severity assessment.""",
            
            "threat_scenario": """You are an expert in automotive threat modeling. Create detailed threat scenarios 
            using the STRIDE model (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, 
            Elevation of Privilege) for the specified system or component. For each threat type, describe the
            attack vector, potential impact, and likelihood assessment.""",
            
            "attack_pattern": """You are an expert in automotive cybersecurity. Based on the provided dataflow
            description, generate possible attack patterns that could exploit vulnerabilities in the system.
            Include attack prerequisites, steps, impact, and potential mitigations for each pattern.""",
            
            "general": """You are an expert in automotive cybersecurity, specializing in Threat Analysis and Risk Assessment (TARA).
            Provide helpful, accurate information related to automotive cybersecurity, ECUs, threat modeling, and risk assessment.
            When appropriate, reference industry standards such as ISO 21434, SAE J3061, and related best practices."""
        }
    
    def create_session(self):
        """
        Create a new chat session.
        
        Returns:
            dict: Session information
        """
        try:
            session_id = str(uuid.uuid4())
            
            # Create database entry
            chat_session = ChatSession(session_id=session_id)
            db.session.add(chat_session)
            db.session.commit()
            
            return {
                "success": True,
                "session": chat_session.to_dict(),
                "message": "Chat session created successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create chat session"
            }
    
    def send_message(self, session_id, message, query_type="general"):
        """
        Send a message to the chat and get a response.
        
        Args:
            session_id (str): ID of the chat session
            message (str): User message
            query_type (str): Type of query (ecu_explanation, damage_scenario, threat_scenario, attack_pattern, general)
        
        Returns:
            dict: Assistant response or a generator if streaming is enabled
        """
        try:
            # Get the chat session
            chat_session = ChatSession.query.filter_by(session_id=session_id).first()
            
            # Auto-create the session if it doesn't exist
            if not chat_session:
                chat_session = ChatSession(session_id=session_id)
                db.session.add(chat_session)
                db.session.commit()
                
            # Create database entry for user message
            user_message = ChatMessage(
                session_id=chat_session.id,
                role="user",
                content=message
            )
            db.session.add(user_message)
            db.session.commit()
            
            # Get the prompt template for the query type
            system_content = self.prompt_templates.get(query_type, self.prompt_templates["general"])
            
            # Get previous messages
            previous_messages = ChatMessage.query.filter_by(session_id=chat_session.id).order_by(ChatMessage.created_at).all()
            
            # Format messages for DeepSeek API
            messages = [{"role": "system", "content": system_content}]
            
            # Add previous messages (limited to last 10 for context management)
            for msg in previous_messages[-10:]:
                messages.append({"role": msg.role, "content": msg.content})
            
            # Generate response
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
                stream=True
            )
            
            # Return the streaming response and session info
            return {
                "success": True,
                "stream": response,
                "session_id": session_id,
                "chat_session_id": chat_session.id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to send message"
            }
    
    def get_conversation_history(self, session_id):
        """
        Get the conversation history for a chat session.
        
        Args:
            session_id (str): ID of the chat session
        
        Returns:
            dict: Conversation history
        """
        try:
            # Get the chat session
            chat_session = ChatSession.query.filter_by(session_id=session_id).first()
            
            if not chat_session:
                return {
                    "success": False,
                    "error": "Chat session not found",
                    "message": "Failed to get conversation history: Chat session not found"
                }
            
            # Get conversation history
            messages = ChatMessage.query.filter_by(session_id=chat_session.id).order_by(ChatMessage.created_at).all()
            
            return {
                "success": True,
                "session": chat_session.to_dict(),
                "messages": [message.to_dict() for message in messages],
                "message": f"Retrieved {len(messages)} messages successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get conversation history"
            }
    
    def clear_conversation_history(self, session_id):
        """
        Clear the conversation history for a chat session.
        
        Args:
            session_id (str): ID of the chat session
        
        Returns:
            dict: Status message
        """
        try:
            # Get the chat session
            chat_session = ChatSession.query.filter_by(session_id=session_id).first()
            
            if not chat_session:
                return {
                    "success": False,
                    "error": "Chat session not found",
                    "message": "Failed to clear conversation history: Chat session not found"
                }
            
            # Delete all messages for this session
            ChatMessage.query.filter_by(session_id=chat_session.id).delete()
            db.session.commit()
            
            return {
                "success": True,
                "message": "Conversation history cleared successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to clear conversation history"
            }
    
    def generate_ecu_explanation(self, session_id, ecu_type):
        """
        Generate an explanation about a specific type of ECU.
        
        Args:
            session_id (str): ID of the chat session
            ecu_type (str): Type of ECU to explain
        
        Returns:
            dict: Explanation
        """
        message = f"Explain the {ecu_type} ECU, its functions, common interfaces, security concerns, and importance in automotive systems."
        return self.send_message(session_id, message, query_type="ecu_explanation")
    
    def generate_damage_scenario(self, session_id, component, cia_aspect):
        """
        Generate a damage scenario based on CIA triad.
        
        Args:
            session_id (str): ID of the chat session
            component (str): Component or system to analyze
            cia_aspect (str): Aspect of CIA to focus on (confidentiality, integrity, availability)
        
        Returns:
            dict: Damage scenario
        """
        message = f"Generate a damage scenario for {component} focusing on the {cia_aspect} aspect of the CIA triad."
        return self.send_message(session_id, message, query_type="damage_scenario")
    
    def generate_threat_scenario(self, session_id, component, stride_aspect):
        """
        Generate a threat scenario based on STRIDE model.
        
        Args:
            session_id (str): ID of the chat session
            component (str): Component or system to analyze
            stride_aspect (str): Aspect of STRIDE to focus on
        
        Returns:
            dict: Threat scenario
        """
        message = f"Generate a threat scenario for {component} focusing on the {stride_aspect} aspect of the STRIDE model."
        return self.send_message(session_id, message, query_type="threat_scenario")
    
    def generate_attack_pattern(self, session_id, dataflow_description):
        """
        Generate attack patterns based on dataflow description.
        
        Args:
            session_id (str): ID of the chat session
            dataflow_description (str): Description of the dataflow
        
        Returns:
            dict: Attack patterns
        """
        message = f"Based on the following dataflow description, generate possible attack patterns:\n\n{dataflow_description}"
        return self.send_message(session_id, message, query_type="attack_pattern")

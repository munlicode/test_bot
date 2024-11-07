from flask import Flask, current_app
from datetime import datetime, timedelta
import json
import time
from openai import OpenAI
import app.ottle.test_functions as functions
import os
from dotenv import load_dotenv

load_dotenv()

GENERATE_TIME=25
open_api = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=open_api)

# In-memory session storage
user_sessions = {}
SESSION_EXPIRATION_HOURS = 4

def is_session_expired(last_active):
    """Check if the session has expired"""
    return datetime.now() > last_active + timedelta(hours=SESSION_EXPIRATION_HOURS)

def get_or_create_session(wa_id, name):
    """Get existing session or create a new one"""
    current_time = datetime.now()
    session = user_sessions.get(wa_id)
    
    if session is None or is_session_expired(session["last_active"]):
        # Create new thread for OpenAI conversation
        thread = client.beta.threads.create()
        session = {
            "thread_id": thread.id,
            "last_active": current_time,
            "name": name,
            "is_new": True
        }
        user_sessions[wa_id] = session
    else:
        session["last_active"] = current_time
        session["is_new"] = False
    
    return session

def generate_response(message_body, wa_id, name):
    """Generate response using OpenAI assistant with session management"""
    try:
        # Get or create session
        session = get_or_create_session(wa_id, name)
        
        # Get assistant ID
        assistant_id = functions.create_assistant(client)
        
        # Add user message to thread
        client.beta.threads.messages.create(
            thread_id=session["thread_id"],
            role="user",
            content=message_body
        )
        
        # Create and run the assistant
        run = client.beta.threads.runs.create(
            thread_id=session["thread_id"],
            assistant_id=assistant_id
        )
        
        # Wait for response (with timeout)
        start_time = time.time()
        while time.time() - start_time < GENERATE_TIME:  
        
            run = client.beta.threads.runs.retrieve(
                thread_id=session["thread_id"],
                run_id=run.id
            )   
           
            if run.status == 'completed':
                messages = client.beta.threads.messages.list(
                    thread_id=session["thread_id"]
                )
                message_content = messages.data[0].content[0].text
                
                # Clean up annotations
                annotations = message_content.annotations
                for annotation in annotations:
                    message_content.value = message_content.value.replace(
                        annotation.text, ''
                    )
                
                response_text = message_content.value
                if session["is_new"]:
                    response_text = f"Welcome {session['name']}! " + response_text
                
                return response_text
            
            if run.status == 'requires_action':
                # Handle function calls
                for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                    if tool_call.function.name == "place_order":
                        arguments = json.loads(tool_call.function.arguments)
                        output = functions.place_order(
                            arguments["name"], 
                            arguments["phone"],
                            arguments["order"],
                            arguments["address"],
                            arguments["order_time"]
                        )
                        client.beta.threads.runs.submit_tool_outputs(
                            thread_id=session["thread_id"],
                            run_id=run.id,
                            tool_outputs=[{
                                "tool_call_id": tool_call.id,
                                "output": json.dumps(output)
                            }]
                        )
            
            
 
            
            time.sleep(1)
        
        return "I'm sorry, but I couldn't generate a response in time. Please try again."
    
    except Exception as e:
        print(f"Error generating response: {str(e)}")
        return "I apologize, but I encountered an error. Please try again later."












































































# def process_text_for_whatsapp(text):
#     """Format text for WhatsApp messages"""
#     # Add any necessary formatting for WhatsApp
#     # For example, replacing markdown with WhatsApp formatting
#     formatted_text = text.replace('*', '*') # Bold
#     formatted_text = formatted_text.replace('_', '_') # Italic
#     formatted_text = formatted_text.replace('```', '```') # Code blocks
#     return formatted_text

# def get_text_message_input(recipient, message):
#     """Prepare WhatsApp message data"""
#     return {
#         "messaging_product": "whatsapp",
#         "recipient_type": "individual",
#         "to": recipient,
#         "type": "text",
#         "text": {
#             "preview_url": False,
#             "body": message
#         }
#     }

# def process_whatsapp_message(body):
#     """Process incoming WhatsApp message"""
#     try:
#         # Extract message details
#         wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
#         name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
#         message = body["entry"][0]["changes"][0]["value"]["messages"][0]
#         message_body = message["text"]["body"]
        
#         # Generate response
#         response = generate_response(message_body, wa_id, name)
#         response = process_text_for_whatsapp(response)
        
#         # Prepare and send message
#         data = get_text_message_input(current_app.config["RECIPIENT_WAID"], response)
#         send_message(data)
        
#         return True
    
#     except Exception as e:
#         print(f"Error processing WhatsApp message: {str(e)}")
#         return False

# def clear_expired_sessions():
#     """Clean up expired sessions"""
#     current_time = datetime.now()
#     expired_wa_ids = [
#         wa_id for wa_id, session in user_sessions.items()
#         if is_session_expired(session["last_active"])
#     ]
    
#     for wa_id in expired_wa_ids:
#         user_sessions.pop(wa_id, None)

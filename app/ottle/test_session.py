from flask import Flask, current_app
from datetime import datetime, timedelta
import json
import time
from openai import OpenAI
import app.ottle.test_functions as functions
import traceback
from dotenv import load_dotenv
import os

load_dotenv()

GENERATE_TIME=25
open_api=os.getenv("OPENAI_API_KEY")

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
        thread = client.beta.threads.create()
        session = {
            "thread_id": thread.id,
            "last_active": current_time,
            "name": name,
            "is_new": True,
            "order_info": {
                "name": name,  # Initialize with known information
                "phone": wa_id,
                "order": None,
                "address": None,
                "order_time": None
            }  # Add this to store order details
        }
        user_sessions[wa_id] = session
    else:
        session["last_active"] = current_time
        session["is_new"] = False
    
    return session

def generate_response(message_body, wa_id, name):
    try:
        print("\n=== Starting Response Generation ===")
        print(f"Message: {message_body}")
        print(f"WA ID: {wa_id}")
        print(f"Name: {name}")
        
        # Get or create session
        session = get_or_create_session(wa_id, name)
        
        # Add message to thread with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                client.beta.threads.messages.create(
                    thread_id=session["thread_id"],
                    role="user",
                    content=message_body
                )
                break
            except Exception as e:
                if "run is active" in str(e).lower():
                    # Get active runs
                    runs = client.beta.threads.runs.list(thread_id=session["thread_id"])
                    for run in runs.data:
                        if run.status in ["queued", "in_progress"]:
                            try:
                                client.beta.threads.runs.cancel(
                                    thread_id=session["thread_id"],
                                    run_id=run.id
                                )
                            except:
                                pass
                    time.sleep(1)
                if attempt == max_retries - 1:
                    raise

        # Get assistant ID
        assistant_id = functions.create_assistant(client)
        
        # Create and run the assistant
        run = client.beta.threads.runs.create(
            thread_id=session["thread_id"],
            assistant_id=assistant_id
        )
        
        # Wait for response (with timeout)
        start_time = time.time()
        while time.time() - start_time < GENERATE_TIME:  
            run_status = client.beta.threads.runs.retrieve(
                thread_id=session["thread_id"],
                run_id=run.id
            )
            
            print(f"Current run status: {run_status.status}")
            
            if run_status.status == 'completed':
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
            
            if run_status.status == 'requires_action':
                print("\n=== Function Call Required ===")
                for tool_call in run_status.required_action.submit_tool_outputs.tool_calls:
                    print(f"Function being called: {tool_call.function.name}")
                    
                    if tool_call.function.name == "place_order":
                        try:
                            arguments = json.loads(tool_call.function.arguments)
                            print("\nReceived arguments:")
                            print(json.dumps(arguments, indent=2))
                            
                            # Update session order info with new information
                            session["order_info"].update(arguments)
                            
                            # Use accumulated order info
                            order_info = session["order_info"]
                            
                            # Check for all required fields
                            required_fields = ['name', 'phone', 'order', 'address', 'order_time']
                            missing_fields = [field for field in required_fields if field not in order_info or not order_info[field]]
                            
                            if missing_fields:
                                missing_fields_str = ', '.join(missing_fields)
                                error_message = f"To complete your order, I need the following information: {missing_fields_str}"
                                print(f"\nMissing fields: {missing_fields_str}")
                                return error_message
                            
                            output = functions.place_order(
                                name=order_info["name"],
                                phone=order_info["phone"],
                                order=order_info["order"],
                                address=order_info["address"],
                                order_time=order_info["order_time"]
                            )  
                            print("\nOrder successfully created:")
                            print(json.dumps(output, indent=2))
                            
                            client.beta.threads.runs.submit_tool_outputs(
                                thread_id=session["thread_id"],
                                run_id=run.id,
                                tool_outputs=[{
                                    "tool_call_id": tool_call.id,
                                    "output": json.dumps(output)
                                }]
                            )
                        except KeyError as ke:
                            error_msg = f"Missing required field: {ke}"
                            print(f"\n{error_msg}")
                            return f"I need your {ke} to process the order. Could you please provide it?"
                        except ValueError as ve:
                            error_msg = str(ve)
                            print(f"\nValidation error: {error_msg}")
                            return f"Please provide {error_msg}"
                        except Exception as func_error:
                            print(f"\nError in create_lead function: {str(func_error)}")
                            traceback.print_exc()
                            return "I encountered an error while processing your order. Please make sure all information is provided correctly."
            
            time.sleep(1)
        
        print("\nTimeout reached while generating response")
        return "I'm sorry, but I couldn't process your request in time. Please try again."
    
    except Exception as e:
        print(f"\nError generating response: {str(e)}")
        traceback.print_exc()
        return "I apologize, but I encountered an error. Please try again."
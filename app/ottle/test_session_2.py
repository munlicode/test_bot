"""
In this file changes will be made in generate_response()
It will be responsible for generating response when run.status == "requires_action" => collect all necessary data from current session to place order such as phone number, if not in data of current session.
The main point of this approuch is to try to collect place order (MOCK) without asking order over again.
"""




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
open_api = os.getenv()

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
        thread =  client.beta.threads.create()
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
        session =  get_or_create_session(wa_id, name)
        
        # Get assistant ID
        assistant_id =  functions.create_assistant(client)
        print("IDDDDDDDDDDDDDDDDDD",assistant_id)
        # Add user message to thread
        client.beta.threads.messages.create(
            thread_id=session["thread_id"],
            role="user",
            content=message_body
        )
        
        # Create and run the assistant
        run =  client.beta.threads.runs.create(
            thread_id=session["thread_id"],
            assistant_id=assistant_id
        )
        
        # Wait for response (with timeout)
        # start_time = time.time()
        # while time.time() - start_time < GENERATE_TIME:  
        
        while True:
           
            run = client.beta.threads.runs.retrieve(
                thread_id=session["thread_id"],
                run_id=run.id
            )   
            # print("Run:",run)
            print("STATUS -----------------------------------------------------------------------",run.status)
            if run.status == 'completed':
# messages
                messages = client.beta.threads.messages.list(
                    thread_id=session["thread_id"]
                )
                for every in messages:
                    print(f"Role: {every.role};\n\nMessage: {every.content[0].text.value}\n\n-\n\n")
                message_content = messages.data[0].content[0].text
# message_content                
                print("message_content:", message_content)
                # Clean up annotations
                annotations = message_content.annotations
                for annotation in annotations:
                    message_content.value = message_content.value.replace(
                        annotation.text, ''
                    )
                print("Annotations:", annotations)
# annotations
                response_text = message_content.value
                print("Response 1:", response_text)
                if session["is_new"]:
                    response_text = f"Welcome {session['name']}! " + response_text
                print("Response 2:", response_text) 
                return response_text
# response_text
            if run.status == 'requires_action':
                # Handle function calls
                print(run.required_action.submit_tool_outputs.tool_calls)
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
                        print("Tool call:",tool_call)
                        print("Arguments:",arguments)
                        print("client.beta.threads.runs.submit_tool_outputs:",client.beta.threads.runs.submit_tool_outputs)
# run.required_action.submit_tool_outputs.tool_calls
# tool_call
# arguments
# client.beta.threads.runs.submit_tool_outputs
            
 
            time.sleep(1)
        return "I'm sorry, but I couldn't generate a response in time. Please try again."
    
    except Exception as e:
        print(f"Error generating response: {str(e)}")
        return "I apologize, but I encountered an error. Please try again later."











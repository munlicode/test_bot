import json
import requests
import os
from openai import OpenAI
from app.ottle.prompts import assistant_instructions
import os
from dotenv import load_dotenv

load_dotenv()

FRONTPAD_API_KEY =os.getenv("FRONTPAD_API_KEY") # os.environ['AIRTABLE_API_KEY']


# Add lead to Airtable
def place_order(name, phone, order, address, order_time):
  url = ""
  headers = {
      "Authorization": FRONTPAD_API_KEY,
      "Content-Type": "application/json"
  }
  data = {"records": [{"fields": {"Name": name, "Phone": phone, "Order": order, "Address": address, "Order Time": order_time}}]}
  print("Data:", data)
  response = requests.post(url, headers=headers, json=data)
  print("Response:", response)
  if response.status_code == 200:
    print("Lead created successfully.")
    return response.json()
  else:
    print(f"Failed to create lead: {response.text}")


# Create or load assistant
def create_assistant(client):
  assistant_file_path = 'assistant.json'
  
  # If there is an assistant.json file already, then load that assistant
  if os.path.exists(assistant_file_path):
    with open(assistant_file_path, 'r') as file:
      assistant_data = json.load(file)
      assistant_id = assistant_data['assistant_id']
      print("Loaded existing assistant ID.")
  else:
    # If no assistant.json is present, create a new assistant using the below specifications
    
    file_ids = []
    file_paths = []

    # Upload each file and collect file IDs
    for file_path in file_paths:
        with open(file_path, "rb") as f:
            file = client.files.create(file=f, purpose='assistants')
            file_ids.append(file.id)

    # file = client.files.create(file=open(r"C:\Users\Nurzhan\BSP\personal\app\ottle\knowledge.docx", "rb"),
    #                            purpose='assistants')

    assistant = client.beta.assistants.create(
        # Change prompting in prompts.py file
        instructions=assistant_instructions,
        model="gpt-4-1106-preview",
        tools=[
        {
            "type": "function",  # Keep this for lead capture
            "function": {
                "name": "place_order",
                "description": "You are assistant who takes orders from user",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Full name of the lead."
                        },
                        "phone": {
                            "type": "string",
                            "description": "Phone number of the lead including country code."
                        },
                        "order": {
                            "type": "string",
                            "description": "Ordered products."
                        },
                        "address": {
                            "type": "string",
                            "description": "Address for delivery assigned by customer."
                        },
                        "order_time": {
                            "type": "string",
                            "description": "Time of order delivery"
                        }
                    },
                    "required": ["name", "phone", "order", "address", "order_time"]
            }
            }
        },
        {
            "type": "code_interpreter"  # If you need code execution
        },
        {
            "type": "file_search"  # If you need to search for files
        }
    ],
    tool_resources={
        "code_interpreter": {
            "file_ids": file_ids
        }
    }
)

    # Create a new assistant.json file to load on future runs
    with open(assistant_file_path, 'w') as file:
      json.dump({'assistant_id': assistant.id}, file)
      print("Created a new assistant and saved the ID.")

    assistant_id = assistant.id

  return assistant_id

def valid_recipient(recipient):
  valid = ""
  print(recipient[0])
  if recipient[0] == "7":
    valid += "78" + recipient[1:]
  print(valid)
  return valid
import json
import requests
import os
from openai import OpenAI
from app.ottle.prompts import assistant_instructions
from dotenv import load_dotenv

load_dotenv()

# Ensure that the OpenAI API key is securely retrieved from an environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Init OpenAI Client
client = OpenAI(api_key=OPENAI_API_KEY)

def place_order(name, phone, order, address, order_time):
    """
    Create a lead with all required parameters
    """
    # Validate each field individually
    missing_fields = []
    if not name or name.strip() == "":
        missing_fields.append("name")
    if not phone or phone.strip() == "":
        missing_fields.append("phone")
    if not order or order.strip() == "":
        missing_fields.append("order")
    if not address or address.strip() == "":
        missing_fields.append("address")
    if not order_time or order_time.strip() == "":
        missing_fields.append("order_time")
    
    if missing_fields:
        # Instead of raising an error, return a status indicating what's missing
        return {
            "success": False,
            "missing_fields": missing_fields
        }

    print("\n=== ORDER DETAILS ===")
    print(f"Name: {name}")
    print(f"Phone: {phone}")
    print(f"Order: {order}")
    print(f"Address: {address}")
    print(f"Order Time: {order_time}")
    print("===================\n")
    
    return {
        "success": True,
        "data": {
            "name": name,
            "phone": phone,
            "order": order,
            "address": address,
            "order_time": order_time
        }
    }

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
# {
#   "name": "create_lead",
#   "description": "Create a new lead with customer order information",
#   "parameters": {
#     "type": "object",
#     "properties": {
#       "name": {
#         "type": "string",
#         "description": "Customer's full name"
#       },
#       "phone": {
#         "type": "string",
#         "description": "Customer's phone number"
#       },
#       "order": {
#         "type": "string",
#         "description": "Customer's order details"
#       },
#       "address": {
#         "type": "string",
#         "description": "Delivery address"
#       },
#       "order_time": {
#         "type": "string",
#         "description": "Preferred delivery time"
#       }
#     },
#     "required": ["name", "phone", "order", "address", "order_time"]
#   }
# }
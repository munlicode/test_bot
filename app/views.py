import logging
import json
import time
import threading
from flask import Blueprint, request, jsonify, current_app

from .decorators.security import signature_required
from .whatsapp.whatsapp import (
    process_whatsapp_message,
    is_valid_whatsapp_message,
)

webhook_blueprint = Blueprint("webhook", __name__)

# Queue to collect messages within the batching timeframe
message_batch = []
batch_lock = threading.Lock()
BATCH_INTERVAL = 5  # Define the gap in seconds
batch_timer = None

def start_batch_timer():
    """Start the batch timer to process messages after the interval."""
    global batch_timer
    if batch_timer is None or not batch_timer.is_alive():
        batch_timer = threading.Timer(BATCH_INTERVAL, process_batch)
        batch_timer.start()

def process_batch():
    """Process all collected messages in the batch and send one response."""
    global message_batch, batch_timer
    with batch_lock:
        if message_batch:
            # Combine all messages in the batch into a single response
            combined_response = combine_messages(message_batch)
            for user_message in combined_response:
                wa_id = user_message['wa_id']
                name = user_message['name']
                messages = user_message['messages']
                send_response(messages, wa_id, name)  # Send a single response
                print("Message batch", message_batch)
            message_batch = []  # Clear the batch after processing
        
        # Reset the timer after processing the batch
        batch_timer = None


def combine_messages(messages_body):
    """Combine all messages in the batch into a single response for each user."""
    print(messages_body)
    
    data = []

    for msg in messages_body:
        wa_id = msg["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
        for d in data:
            if wa_id == d['wa_id']:
                message = msg["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]
                d['messages'].append(message)

            else:
                name = msg["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
                message = msg["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]

                # Data for new user that should be inserted into global data about all messages
                new_data = {'wa_id': wa_id, 
                            'name': name, 
                            'messages': [message]}
                data.append(new_data)
    
    result_data = []
    for d in data:
        wa_id = d['wa_id']
        name = d['name']
        messages =  "\n".join(d['messages'])

        # Append data that is been adjusted
        new_result_data = {'wa_id': wa_id, "name": name, 'messages': messages}
        result_data.append(new_result_data)
    
    print(f"Combined Messages: {result_data}")
    return result_data

def send_response(response, wa_id, name):
    """Simulate sending a single response."""
    process_whatsapp_message(response, wa_id, name)  # Assuming this sends the response to WhatsApp
    logging.info("Sending combined response: %s", response)

def handle_message():
    """
    Handle incoming webhook events from the WhatsApp API.
    """
    global batch_timer
    body = request.get_json()

    # Check if it's a WhatsApp status update
    if (
        body.get("entry", [{}])[0]
        .get("changes", [{}])[0]
        .get("value", {})
        .get("statuses")
    ):
        logging.info("Received a WhatsApp status update.")
        return jsonify({"status": "ok"}), 200

    try:
        if is_valid_whatsapp_message(body):
            # Lock batch to safely append messages
            with batch_lock:
                message_batch.append(body)
                # Start the timer if it's the first message in the batch
                start_batch_timer()

            return jsonify({"status": "ok"}), 200
        else:
            # If the request is not a WhatsApp API event, return an error
            return (
                jsonify({"status": "error", "message": "Not a WhatsApp API event"}),
                404,
            )
    except json.JSONDecodeError:
        logging.error("Failed to decode JSON")
        return jsonify({"status": "error", "message": "Invalid JSON provided"}), 400


# def handle_message():
#     """
#     Handle incoming webhook events from the WhatsApp API.

#     This function processes incoming WhatsApp messages and other events,
#     such as delivery statuses. If the event is a valid message, it gets
#     processed. If the incoming payload is not a recognized WhatsApp event,
#     an error is returned.

#     Every message send will trigger 4 HTTP requests to your webhook: message, sent, delivered, read.

#     Returns:
#         response: A tuple containing a JSON response and an HTTP status code.
#     """
#     body = request.get_json()
#     # logging.info(f"request body: {body}")

#     # Check if it's a WhatsApp status update
#     if (
#         body.get("entry", [{}])[0]
#         .get("changes", [{}])[0]
#         .get("value", {})
#         .get("statuses")
#     ):
#         logging.info("Received a WhatsApp status update.")
#         return jsonify({"status": "ok"}), 200

#     try:
#         if is_valid_whatsapp_message(body):
#             process_whatsapp_message(body)
#             return jsonify({"status": "ok"}), 200
#         else:
#             # if the request is not a WhatsApp API event, return an error
#             return (
#                 jsonify({"status": "error", "message": "Not a WhatsApp API event"}),
#                 404,
#             )
#     except json.JSONDecodeError:
#         logging.error("Failed to decode JSON")
#         return jsonify({"status": "error", "message": "Invalid JSON provided"}), 400


# Required webhook verifictaion for WhatsApp
def verify():
    # Parse params from the webhook verification request
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    # Check if a token and mode were sent
    if mode and token:
        # Check the mode and token sent are correct
        if mode == "subscribe" and token == current_app.config["VERIFY_TOKEN"]:
            # Respond with 200 OK and challenge token from the request
            logging.info("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            # Responds with '403 Forbidden' if verify tokens do not match
            logging.info("VERIFICATION_FAILED")
            return jsonify({"status": "error", "message": "Verification failed"}), 403
    else:
        # Responds with '400 Bad Request' if verify tokens do not match
        logging.info("MISSING_PARAMETER")
        return jsonify({"status": "error", "message": "Missing parameters"}), 400


@webhook_blueprint.route("/webhook", methods=["GET"])
def webhook_get():
    return verify()

@webhook_blueprint.route("/webhook", methods=["POST"])
@signature_required
def webhook_post():
    return handle_message()



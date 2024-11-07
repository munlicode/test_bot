import logging
from flask import current_app, jsonify
import json
import requests
import re
from app.ottle.test_session_2 import generate_response
from app.ottle.functions import valid_recipient

ACCESS_TOKEN = "EAALrO9Smry0BO1DOZBnJ1pPUT3fOomSIgRhQ4KkhTMIhq3bZAi4ZB7693nF7swl0Kr0jjb9ePZBVIudhx2QsYdm2QYgWg1jgz3VmiWOSPPn6MwBuAmZCWyrHJXL5D3bveoozNosDZB4t8RLQQgf1TLMGQ2Hm9vHh5yPfsxAklX8EblHc3SkDWkqdKFEZCPkYiqeF88zc67sc9j6AYrN1tZAdDZCdS7jdZAfh5ca9pGYT1gJpntPDuTbD6KgwZDZD"
# perm ACCESS_TOKEN="EAALrO9Smry0BO3jhuxxXoNlHcTQZCTckxXzBvvbav3yvTEnHzz13iwYJByD6TX66iIqaCWDFNKBmYbkADl3ePPkjGin879t5MAHpylU3EqRsvfR5ZBSi457ZBWho3MXxMn4mvwquMmo9SCkZBiO5BhsHEnFIZCk8uZAbc6SIzMZAmpgaZCnhVWmZCYwZC0J1QVRmN2kJzCgBrEqvPL3afj"
VERSION="v21.0"
PHONE_NUMBER_ID="502888606231401"
def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    print(f"Recipient_WAID: {recipient}")
    recipient = valid_recipient(recipient)
    return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    

# for i in recipient.char()

def send_message(data):
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"

    try:
        response = requests.post(
            url, headers=headers, json=data, timeout=60
        )  # 10 seconds timeout as an example
                # Log the response before raising an error
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except (
        requests.RequestException
    ) as e:  # This will catch any general request exception
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        # Process the response as normal
        log_http_response(response)
        return response


def process_text_for_whatsapp(text):
    # Remove brackets
    pattern = r"\【.*?\】"
    # Substitute the pattern with an empty string
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text


def process_whatsapp_message(message, wa_id, name):
    print(message)
    response = generate_response(message, wa_id, name)
    response = process_text_for_whatsapp(response)
    data = get_text_message_input(wa_id, response)
    send_message(data)
            

def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )

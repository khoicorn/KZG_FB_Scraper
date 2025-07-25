from flask import Flask, request, jsonify
import json
from lark_bot.core import handle_incoming_message
from lark_bot.config import VERIFICATION_TOKEN
import logging
import threading

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)

def verify_token(data):
    """Verify the incoming request token"""
    received_token = data.get('header', {}).get('token')
    return received_token == VERIFICATION_TOKEN

def process_message_async(data, chat_type):
    """Xử lý tin nhắn trong luồng riêng"""
    try:
        # Extract message content
        message_content = data.get('event', {}).get('message', {}).get('content', {})
        message_json = json.loads(message_content)
        text = message_json.get('text', '').strip()
        
        logger.info(f"Processing message: {text}, chat_type: {chat_type}")
        
        # Group chat logic - only respond to commands starting with /
        # if chat_type == "group":
        #     if text.startswith('/'):
        #         # Remove the / prefix from the text
        #         modified_text = text[1:]  # Remove first character (/)
        #         logger.info(f"Group command detected, modified: '{text}' -> '{modified_text}'")
                
        #         # Modify the data to remove the / prefix
        #         message_json['text'] = modified_text
        #         data['event']['message']['content'] = json.dumps(message_json)
                
        #         # Process the command in group
        #         handle_incoming_message(data)
        #     else:
        #         logger.warning("No command in group")
        
        # P2P chat logic - respond to all messages
        # elif chat_type == "p2p":
        # logger.info("Processing P2P message")
        handle_incoming_message(data)
        
        # else:
        #     logger.warning(f"Unknown chat type: {chat_type}")
            
    except Exception as e:
        logger.error(f"Message processing error: {e}")
        
@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "ok", "message": "Bot is running"})

@app.route('/webhook', methods=['POST'])
def webhook():
    # ENHANCED DEBUG: Show all event types and details
    
    data = request.json
    chat_type = data.get("event", {}).get("message", {}).get("chat_type")

    # URL verification
    if data.get('type') == 'url_verification':
        return jsonify({'challenge': data.get('challenge')})
    
    # 1. Verify the token first
    if not verify_token(data):
        return jsonify({'error': 'Invalid token'}), 403
    
    # 3. Xử lý sự kiện tin nhắn không đồng bộ
    if data.get("header", {}).get("event_type") == "im.message.receive_v1":
        threading.Thread(target=process_message_async, args=(data, chat_type)).start()
        return jsonify({"code": 0})
    
    return jsonify({"code": 0, "message": "Event ignored"})


if __name__ == "__main__":
    app.run(port=5000, debug=True)
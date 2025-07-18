from flask import Flask, request, jsonify
from lark_bot.core import handle_incoming_message
from lark_bot.config import VERIFICATION_TOKEN

app = Flask(__name__)

def verify_token(data):
    """Verify the incoming request token"""
    received_token = data.get('header', {}).get('token')
    return received_token == VERIFICATION_TOKEN

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print(data)
    # URL verification
    if data.get('type') == 'url_verification':
        return jsonify({'challenge': data.get('challenge')})
    
    # 1. Verify the token first
    if not verify_token(data):
        return jsonify({'error': 'Invalid token'}), 403
    
    # Handle message events
    if data.get("header", {}).get("event_type") == "im.message.receive_v1":
        try:
            handle_incoming_message(data)
        except:
            return jsonify({"error": "Failed to process message"}), 500
        
    return jsonify({"code": 0})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
import json
from .state_managers import state_manager
from .command_handlers import command_handler

def handle_incoming_message(event_data):
    # Access the nested structure correctly
    message = event_data["event"]["message"]
    print("Received message:", message)
    chat_id = message["chat_id"]
    
    # Parse the JSON content string
    content = json.loads(message["content"])
    text = content.get("text", "").strip().lower()

    print("Parsed content:", text)
    
    # Get current user state
    current_state = state_manager.get_state(chat_id)
    print(f"Current state: {current_state}, chat_id: {chat_id}, text: {text}")

    # Handle cancel command regardless of state - but use command_handler
    if text == "cancel":
        command_handler.handle_command(chat_id, text)
        return

    # Process message based on state
    if current_state == "AWAITING_SEARCH_TERM":
        command_handler.handle_search_term(chat_id, text)
    elif current_state is None:  # Use 'is None' instead of '== None'
        command_handler.handle_command(chat_id, text)
    elif current_state == "IN_PROGRESS":
        if text == "cancel":
            command_handler.handle_command(chat_id, text)
        else:
            command_handler.lark_api.send_text(chat_id, "🔄 Your request is still being processed. Type 'cancel' to stop it.")
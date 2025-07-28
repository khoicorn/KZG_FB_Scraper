import json
from .state_managers import state_manager
from .command_handlers import command_handler
from .logger import message_logger

def handle_incoming_message(event_data):
    # Access the nested structure correctly
    print(event_data)
    message = event_data["event"]["message"]
    print("Received message:", message)
    chat_id = message["chat_id"]
    message_id = message["message_id"]
    user_id = event_data["event"]["sender"]["sender_id"]["user_id"]
    
    # Parse the JSON content string
    content = json.loads(message["content"])
    text = content.get("text", "").strip().lower()

    print("Parsed content:", text)

    # Log incoming message
    message_logger.log_message(chat_id, text, direction="incoming")

    # Store chat_id mapping only if state is None
    current_state = state_manager.get_state(user_id)
    if current_state is None:
        print(f"State is None for user_id {user_id}, setting chat_id mapping")
        state_manager.set_state(user_id, None, chat_id, message_id)

    print(f"Current state: {current_state}, user_id: {user_id}, chat_id: {chat_id}, text: {text}")

    # Handle cancel command regardless of state
    if text == "cancel":
        command_handler.handle_command(user_id, text)
        return

    # Process message based on state
    if current_state == "AWAITING_SEARCH_TERM":
        command_handler.handle_search_term(user_id, text)
    elif current_state == "IN_PROGRESS":
        command_handler.lark_api.reply_to_message(
            message_id,
            "🔄 A search is already in progress. Type 'cancel' to stop it and start a new one."
        )
    elif current_state is None:
        command_handler.handle_command(user_id, text)
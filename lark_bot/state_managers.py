import threading
import time

class UserStateManager:
    def __init__(self):
        self.user_states = {}  # Tracks state by user_id
        self.active_processes = {}  # Tracks active processes by user_id
        self.cancel_events = {}  # Tracks cancel events by user_id
        self.user_chat_mapping = {}  # Maps user_id to their current chat_id
        self.user_message_mapping = {}  # Maps user_id to message_id and root_id
        self.lock = threading.Lock()
    
    def set_state(self, user_id, state, chat_id, message_id=None, root_id=None):
        with self.lock:
            print(f"Setting state for user_id {user_id} to {state}, chat_id: {chat_id}, message_id: {message_id}, root_id: {root_id}")
            self.user_states[user_id] = state
            if chat_id:
                self.user_chat_mapping[user_id] = chat_id
            # Store message_id and root_id if provided
            if message_id or root_id:
                self.user_message_mapping[user_id] = {
                    'message_id': message_id,
                    'root_id': root_id
                }
    
    def get_state(self, user_id):
        with self.lock:
            state = self.user_states.get(user_id, None)
            print(f"Getting state for user_id {user_id}: {state}")
            return state
    
    def clear_state(self, user_id):
        with self.lock:
            print(f"Clearing state for user_id {user_id}")
            self.user_states.pop(user_id, None)
            # Clear cancel events when clearing state
            if user_id in self.cancel_events:
                del self.cancel_events[user_id]
            # Keep chat_id and message_id/root_id mappings even after state clear
    
    def get_chat_id(self, user_id):
        with self.lock:
            chat_id = self.user_chat_mapping.get(user_id)
            print(f"Getting chat_id for user_id {user_id}: {chat_id}")
            return chat_id
    
    def get_message_info(self, user_id):
        """
        Retrieve message_id and root_id for a user_id.
        Returns a dict with 'message_id' and 'root_id', or None if not found.
        """
        with self.lock:
            message_info = self.user_message_mapping.get(user_id, {'message_id': None, 'root_id': None})
            print(f"Getting message info for user_id {user_id}: {message_info}")
            return message_info

    def register_process(self, user_id, process, chat_id=None, message_id=None, root_id=None):
        with self.lock:
            print(f"Registering process for user_id {user_id}, chat_id: {chat_id}, message_id: {message_id}, root_id: {root_id}")
            self.active_processes[user_id] = {
                'process': process,
                'timestamp': time.time(),
                'thread': threading.current_thread()
            }
            # Create a fresh cancel event for this process
            self.cancel_events[user_id] = threading.Event()
            if chat_id:
                self.user_chat_mapping[user_id] = chat_id
            if message_id or root_id:
                self.user_message_mapping[user_id] = {
                    'message_id': message_id,
                    'root_id': root_id
                }
            
    def request_cancel(self, user_id):
        """Cancel active process for the given user_id"""
        with self.lock:
            print(f"🔴 Cancellation requested for user {user_id}")
            
            if user_id in self.active_processes:
                print(f"🔴 Found active process for user {user_id}")
                
                # Signal cancellation
                if user_id in self.cancel_events:
                    self.cancel_events[user_id].set()
                
                # Force stop the process
                process_info = self.active_processes[user_id]
                process_info['process'].force_stop()
                
                # Clean up active processes but DON'T clear state here
                del self.active_processes[user_id]
                
                return True
            
            print(f"🔴 No active process for user {user_id}")
            return False

    def should_cancel(self, user_id):
        """Check if cancellation was requested for the given user_id"""
        with self.lock:
            return user_id in self.cancel_events and self.cancel_events[user_id].is_set()
    
    def cleanup_stale_processes(self):
        """Call this periodically to remove dead processes"""
        with self.lock:
            current_time = time.time()
            stale_keys = [
                key for key, info in self.active_processes.items()
                if current_time - info['timestamp'] > 3600  # 1 hour timeout
            ]
            for key in stale_keys:
                if key in self.active_processes:
                    del self.active_processes[key]
                if key in self.cancel_events:
                    del self.cancel_events[key]

# ✅ Shared instance used across project
state_manager = UserStateManager()
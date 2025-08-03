import threading
import time
from collections import defaultdict
from typing import Optional

class UserStateManager:
    def __init__(self):
        self.user_states = {}
        self.active_processes = {}
        self.cancel_events = {}
        self.user_chat_mapping = {}
        self.user_message_mapping = defaultdict(lambda: {'message_id': None, 'root_id': None})
        self.lock = threading.RLock()  # Use reentrant lock for nested operations
        self.cleanup_thread = threading.Thread(target=self.cleanup_stale_processes, daemon=True)
        self.cleanup_thread.start()
    
    def set_state(self, user_id, state, chat_id=None, message_id=None, root_id=None):
        with self.lock:
            self.user_states[user_id] = state
            if chat_id:
                self.user_chat_mapping[user_id] = chat_id
            if message_id or root_id:
                self.user_message_mapping[user_id] = {
                    'message_id': message_id,
                    'root_id': root_id
                }
    
    def get_state(self, user_id) -> Optional[str]:
        with self.lock:
            return self.user_states.get(user_id)
    
    def clear_state(self, user_id):
        with self.lock:
            if user_id in self.user_states:
                del self.user_states[user_id]
            if user_id in self.cancel_events:
                del self.cancel_events[user_id]
    
    def get_chat_id(self, user_id) -> Optional[str]:
        with self.lock:
            return self.user_chat_mapping.get(user_id)
    
    def get_message_info(self, user_id) -> dict:
        with self.lock:
            return self.user_message_mapping[user_id]

    def register_process(self, user_id, process, chat_id=None, message_id=None, root_id=None):
        with self.lock:
            self.active_processes[user_id] = {
                'process': process,
                'timestamp': time.time()
            }
            self.cancel_events[user_id] = threading.Event()
            if chat_id:
                self.user_chat_mapping[user_id] = chat_id
            if message_id or root_id:
                self.user_message_mapping[user_id] = {
                    'message_id': message_id,
                    'root_id': root_id
                }
            
    def request_cancel(self, user_id) -> bool:
        """Cancel active process for the given user_id"""
        with self.lock:
            if user_id not in self.active_processes:
                return False
                
            # Signal cancellation
            if user_id in self.cancel_events:
                self.cancel_events[user_id].set()
            
            # Force stop the process
            process_info = self.active_processes[user_id]
            process_info['process'].force_stop()
            
            # Clean up
            del self.active_processes[user_id]
            return True

    def should_cancel(self, user_id) -> bool:
        """Check if cancellation was requested"""
        with self.lock:
            event = self.cancel_events.get(user_id)
            return event and event.is_set()
    
    def cleanup_stale_processes(self):
        """Periodically clean up stale processes"""
        while True:
            time.sleep(300)  # Every 5 minutes
            with self.lock:
                current_time = time.time()
                stale_keys = [
                    user_id for user_id, info in self.active_processes.items()
                    if current_time - info['timestamp'] > 3600  # 1 hour timeout
                ]
                for user_id in stale_keys:
                    if user_id in self.active_processes:
                        del self.active_processes[user_id]
                    if user_id in self.cancel_events:
                        del self.cancel_events[user_id]

# Shared instance
state_manager = UserStateManager()
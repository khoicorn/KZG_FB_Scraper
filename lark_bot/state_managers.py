import threading
import time

class UserStateManager:
    def __init__(self):
        self.user_states = {}
        self.active_processes = {}
        self.cancel_events = {}
        self.lock = threading.Lock()  # Add missing lock
    
    def set_state(self, chat_id, state):
        with self.lock:
            self.user_states[chat_id] = state
        
    def get_state(self, chat_id):
        with self.lock:
            return self.user_states.get(chat_id, None)
    
    def clear_state(self, chat_id):
        with self.lock:
            self.user_states.pop(chat_id, None)
            # Also clear cancel events when clearing state
            if chat_id in self.cancel_events:
                del self.cancel_events[chat_id]

    def register_process(self, chat_id, process):
        with self.lock:
            self.active_processes[chat_id] = {
                'process': process,
                'timestamp': time.time(),
                'thread': threading.current_thread()
            }
            # Create a fresh cancel event for this process
            self.cancel_events[chat_id] = threading.Event()
            
    def request_cancel(self, chat_id):
        """Cancel active process for the given chat_id"""
        with self.lock:
            print(f"🔴 Cancellation requested for {chat_id}")
            
            if chat_id in self.active_processes:
                print(f"🔴 Found active process for {chat_id}")
                
                # Signal cancellation
                if chat_id in self.cancel_events:
                    self.cancel_events[chat_id].set()
                
                # Force stop the process
                process_info = self.active_processes[chat_id]
                process_info['process'].force_stop()
                
                # Clean up active processes but DON'T clear state here
                # Let the async process handle state cleanup
                del self.active_processes[chat_id]
                
                return True
            
            print(f"🔴 No active process for {chat_id}")
            return False

    def should_cancel(self, chat_id):
        """Check if cancellation was requested for the given chat_id"""
        with self.lock:
            return chat_id in self.cancel_events and self.cancel_events[chat_id].is_set()
    
    def cleanup_stale_processes(self):
        """Call this periodically to remove dead processes"""
        with self.lock:
            current_time = time.time()
            stale_chats = [
                chat_id for chat_id, info in self.active_processes.items()
                if current_time - info['timestamp'] > 3600  # 1 hour timeout
            ]
            for chat_id in stale_chats:
                if chat_id in self.active_processes:
                    del self.active_processes[chat_id]
                if chat_id in self.cancel_events:
                    del self.cancel_events[chat_id]

# ✅ Shared instance used across project
state_manager = UserStateManager()
# state_managers.py
import threading
import time

class UserStateManager:
    def __init__(self):
        self.user_states = {}
        self.active_processes = {}
        self.cancel_events = {}
        self.lock = threading.Lock()
    
    def set_state(self, chat_id, state, thread_id=None):
        with self.lock:
            key = self._get_key(chat_id, thread_id)
            self.user_states[key] = state
        
    def get_state(self, chat_id, thread_id=None):
        with self.lock:
            key = self._get_key(chat_id, thread_id)
            return self.user_states.get(key, None)
    
    def clear_state(self, chat_id, thread_id=None):
        with self.lock:
            key = self._get_key(chat_id, thread_id)
            self.user_states.pop(key, None)
            # Also clear cancel events when clearing state
            if key in self.cancel_events:
                del self.cancel_events[key]

    def register_process(self, chat_id, process, thread_id=None):
        with self.lock:
            key = self._get_key(chat_id, thread_id)
            self.active_processes[key] = {
                'process': process,
                'timestamp': time.time(),
                'thread': threading.current_thread()
            }
            # Create a fresh cancel event for this process
            self.cancel_events[key] = threading.Event()
            
    def request_cancel(self, chat_id, thread_id=None):
        """Cancel active process for the given chat_id and thread_id"""
        with self.lock:
            key = self._get_key(chat_id, thread_id)
            print(f"🔴 Cancellation requested for {key}")
            
            if key in self.active_processes:
                print(f"🔴 Found active process for {key}")
                
                # Signal cancellation
                if key in self.cancel_events:
                    self.cancel_events[key].set()
                
                # Force stop the process
                process_info = self.active_processes[key]
                process_info['process'].force_stop()
                
                # Clean up active processes but DON'T clear state here
                # Let the async process handle state cleanup
                del self.active_processes[key]
                
                return True
            
            print(f"🔴 No active process for {key}")
            return False

    def should_cancel(self, chat_id, thread_id=None):
        """Check if cancellation was requested for the given chat_id and thread_id"""
        with self.lock:
            key = self._get_key(chat_id, thread_id)
            return key in self.cancel_events and self.cancel_events[key].is_set()
    
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

    def _get_key(self, chat_id, thread_id=None):
        """Generate a unique key for chat_id and thread_id combination"""
        if thread_id:
            return f"{chat_id}:{thread_id}"
        return str(chat_id)

# ✅ Shared instance used across project
state_manager = UserStateManager()
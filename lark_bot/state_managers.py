import threading
import time
from collections import defaultdict
from typing import Optional
import json, os

DOMAINS_FILE = "logs/domains.json"
SCHEDULES_FILE = "logs/schedules.json"

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

        self.chat_domains = self._load_json(DOMAINS_FILE)
        self.chat_schedules = self._load_json(SCHEDULES_FILE)
        self.last_run_key = {}
    
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
    # --- persistence helpers ---
    def _load_json(self, path):
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_json(self, path, data):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)

    # ---------------- Domain management ----------------
    def add_domain(self, chat_id, domain) -> bool:
        with self.lock:
            cid = str(chat_id)
            domains = self.chat_domains.setdefault(cid, [])
            if domain in domains:
                return False
            domains.append(domain)
            self._save_json(DOMAINS_FILE, self.chat_domains)
            return True

    def remove_domain(self, chat_id, domain) -> bool:
        with self.lock:
            cid = str(chat_id)
            domains = self.chat_domains.get(cid, [])
            new_domains = [d for d in domains if d != domain]
            if len(new_domains) == len(domains):
                return False
            self.chat_domains[cid] = new_domains
            self._save_json(DOMAINS_FILE, self.chat_domains)
            return True

    def get_domains(self, chat_id):
        with self.lock:
            return list(self.chat_domains.get(str(chat_id), []))

    # ---------------- Schedule management (multi) ----------------
    def _normalize_sched_container(self, chat_id: str):
        cid = str(chat_id)
        sched = self.chat_schedules.get(cid)
        if sched is None:
            self.chat_schedules[cid] = []
        elif isinstance(sched, dict):
            self.chat_schedules[cid] = [sched]
            self._save_json(SCHEDULES_FILE, self.chat_schedules)
        elif isinstance(sched, list):
            pass
        else:
            self.chat_schedules[cid] = []
            self._save_json(SCHEDULES_FILE, self.chat_schedules)

    def _dedupe_contains(self, arr, hour: int, minute: int, tz_offset: int) -> bool:
        for it in arr:
            if int(it.get("hour", -1)) == hour and int(it.get("minute", -1)) == minute and int(it.get("tz_offset", 0)) == tz_offset:
                return True
        return False
    
    # def _make_label(self, hour: int, minute: int, tz_offset: int) -> str:
    #     return f"{hour:02d}:{minute:02d}GMT{tz_offset:+d}"

    def add_schedule(self, chat_id, when_time, tz_offset_hours: int, allow_duplicate: bool = False) -> bool:
        with self.lock:
            cid = str(chat_id)
            self._normalize_sched_container(cid)
            arr = self.chat_schedules[cid]
            h, m, tz = int(when_time.hour), int(when_time.minute), int(tz_offset_hours)
            if not allow_duplicate and self._dedupe_contains(arr, h, m, tz):
                return False
            arr.append({"hour": h, "minute": m, "tz_offset": tz})
            arr.sort(key=lambda x: (int(x.get("tz_offset", 0)), int(x.get("hour", 0)), int(x.get("minute", 0))))
            self._save_json(SCHEDULES_FILE, self.chat_schedules)
            return True

    # Back-compat (if anything still calls set_schedule)
    def set_schedule(self, chat_id, when_time, tz_offset_hours: int):
        self.add_schedule(chat_id, when_time, tz_offset_hours, allow_duplicate=False)

    def remove_schedule(self, chat_id, hour: int, minute: int, tz_offset: int) -> bool:
        with self.lock:
            cid = str(chat_id)
            self._normalize_sched_container(cid)
            arr = self.chat_schedules.get(cid, [])
            orig = len(arr)
            self.chat_schedules[cid] = [
                s for s in arr
                if not (int(s.get("hour", -1)) == hour and int(s.get("minute", -1)) == minute and int(s.get("tz_offset", 0)) == tz_offset)
            ]
            if len(self.chat_schedules[cid]) != orig:
                self._save_json(SCHEDULES_FILE, self.chat_schedules)
                return True
            return False

    def get_schedule(self, chat_id):
        with self.lock:
            cid = str(chat_id)
            self._normalize_sched_container(cid)
            arr = self.chat_schedules.get(cid, [])
            if not arr:
                return None
            if len(arr) == 1:
                return arr[0]
            return list(arr)

    def get_schedules(self, chat_id):
        with self.lock:
            cid = str(chat_id)
            self._normalize_sched_container(cid)
            return list(self.chat_schedules.get(cid, []))
        
# Shared instance
state_manager = UserStateManager()
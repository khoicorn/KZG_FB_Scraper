import json
import threading
from datetime import datetime
from pathlib import Path

class OptimizedLogger:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, log_dir="logs"):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.__initialized = False
            return cls._instance
            
    def __init__(self, log_dir="logs"):
        if not self.__initialized:
            self.log_dir = Path(log_dir)
            self.current_log_file = None
            self.current_month = None
            self.__initialized = True
            
            # Đảm bảo thư mục log tồn tại
            self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_log_file(self):
        """Xác định file log hiện tại theo tháng"""
        current_month = datetime.now().strftime("%Y-%m")
        
        if self.current_month != current_month:
            log_file = self.log_dir / f"chat_logs_{current_month}.json"
            
            # Khởi tạo file nếu chưa tồn tại
            if not log_file.exists():
                log_file.touch()
            
            self.current_log_file = log_file
            self.current_month = current_month
        
        return self.current_log_file
    
    def log_message(self, user_id, message_id, chat_id, message, direction="incoming"):
        """Ghi log message với format tối ưu"""
        log_file = self._get_log_file()
        timestamp = datetime.now().isoformat()
            # Format duy nhất cho msg
        msg_content = (
            message if direction == "incoming"
            else (message[:10] + "..." if len(message) > 10 else message)
        )

        # Tối ưu format log
        log_entry = {
            "uid": user_id,
            "mid": message_id,
            "ts": timestamp,  # viết tắt timestamp
            "cid": str(chat_id),  # viết tắt chat_id
            "dir": direction[:1],  # 'i' hoặc 'o'
            "msg": msg_content
        }
        
        # Ghi log an toàn với lock
        with threading.Lock():
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

# Global instance
message_logger = OptimizedLogger()
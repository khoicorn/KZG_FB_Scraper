import requests
import os
import json
from .config import APP_ID, APP_SECRET
from .logger import message_logger

class LarkAPI:
    def __init__(self):
        self.access_token = self._get_access_token()
    
    def _get_access_token(self):
        url = "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": APP_ID, "app_secret": APP_SECRET}
        response = requests.post(url, json=payload)
        return response.json().get("tenant_access_token")
    
    def send_text(self, chat_id, text, thread_id=None):
        url = "https://open.larksuite.com/open-apis/message/v4/send/"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        payload = {
            "chat_id": chat_id,
            "msg_type": "text"
        }

        # Add thread_id if provided
        if thread_id:
            payload["root_id"] = thread_id
        
        payload["content"] = {
                "text": text
            }

        print("PAYLOAD:", payload)

        # Log message with thread_id support
        message_logger.log_message(chat_id, text, direction="outgoing", thread_id=thread_id)
        response  = requests.post(url, headers=headers, json=payload)
        print(response.status_code, response.json())
    
    def send_file(self, chat_id, file_buffer, filename, thread_id=None):
        """
        Uploads and sends in-memory file
        """
        # Step 1: Upload file directly from memory
        upload_url = "https://open.larksuite.com/open-apis/im/v1/files"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        files = {
            'file': (filename, file_buffer, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        }
        data = {'file_type': 'stream', 'file_name': filename}
        
        upload_response = requests.post(
            upload_url, 
            headers=headers, 
            files=files, 
            data=data
        )
        
        # Handle upload errors
        if upload_response.status_code != 200:
            raise Exception(f"Upload failed: {upload_response.text}")
        
        file_key = upload_response.json().get("data", {}).get("file_key")
        
        if not file_key:
            raise Exception("File upload failed: No file_key in response")
        
        # Step 2: Send message with file
        send_url = "https://open.larksuite.com/open-apis/im/v1/messages"
        params = {"receive_id_type": "chat_id"}
        payload = {
            "receive_id": chat_id,
            "msg_type": "file"
            # "content": json.dumps({"file_key": file_key})
        }

        # Add thread_id if provided
        if thread_id:
            payload["root_id"] = thread_id
            
        payload["content"] = json.dumps({"file_key": file_key})
        send_response = requests.post(
            send_url, 
            params=params, 
            headers=headers, 
            json=payload
        )
        
        # Handle send errors
        # Log message with thread_id support
        message_logger.log_message(chat_id, f"Sent file: {filename}", "outgoing", thread_id=thread_id)
        
        if send_response.status_code != 200:
            raise Exception(f"Send failed: {send_response.text}")
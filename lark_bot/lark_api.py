import requests
# Configure logging
import os
import json
from .config import APP_ID, APP_SECRET

class LarkAPI:
    def __init__(self):
        self.access_token = self._get_access_token()
    
    def _get_access_token(self):
        url = "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": APP_ID, "app_secret": APP_SECRET}
        response = requests.post(url, json=payload)
        return response.json().get("tenant_access_token")
    
    def send_text(self, chat_id, text):
        url = "https://open.larksuite.com/open-apis/message/v4/send/"
        headers = {
        "Authorization": f"Bearer {self.access_token}",
        "Content-Type": "application/json; charset=utf-8"
        }
        payload = {
            "chat_id": chat_id,
            "msg_type": "text",
            "content": {
                 "text": text
                 }
        }
        print(payload)
        requests.post(url, headers=headers, json=payload)
    
    def send_file(self, chat_id, file_buffer, filename):
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
                "msg_type": "file",
                "content": json.dumps({"file_key": file_key})
            }
            
            send_response = requests.post(
                send_url, 
                params=params, 
                headers=headers, 
                json=payload
            )
            
            # Handle send errors
            if send_response.status_code != 200:
                raise Exception(f"Send failed: {send_response.text}")
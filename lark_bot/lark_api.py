import requests
import os
import json
import time
from .config import APP_ID, APP_SECRET
from .logger import message_logger

class LarkAPI:
    def __init__(self):
        self.access_token = None
        self.token_expires_at = 0
        self._refresh_access_token()
    
    def _refresh_access_token(self):
        """Get a new access token from Lark API"""
        url = "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": APP_ID, "app_secret": APP_SECRET}
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            self.access_token = data.get("tenant_access_token")
            
            # Set expiration time (Lark tokens typically expire in 2 hours = 7200 seconds)
            # We refresh 5 minutes early to be safe (7200 - 300 = 6900 seconds)
            expires_in = data.get("expire", 7200)  # Default to 2 hours if not specified
            self.token_expires_at = time.time() + expires_in - 300
            
            print(f"Access token refreshed, expires in {expires_in} seconds")
            
        except requests.RequestException as e:
            print(f"Failed to refresh access token: {e}")
            raise Exception(f"Token refresh failed: {e}")
    
    def _ensure_valid_token(self):
        """Check if token is still valid, refresh if needed"""
        if not self.access_token or time.time() >= self.token_expires_at:
            print("Token expired or missing, refreshing...")
            self._refresh_access_token()
    
    def _make_authenticated_request(self, method, url, **kwargs):
        """Make a request with automatic token refresh on 401 errors"""
        self._ensure_valid_token()
        
        # Add authorization header
        headers = kwargs.get('headers', {})
        headers["Authorization"] = f"Bearer {self.access_token}"
        kwargs['headers'] = headers
        
        # Make the request
        response = requests.request(method, url, **kwargs)
        
        # If we get 401 (unauthorized), try refreshing token once
        if response.status_code == 401:
            print("Received 401, refreshing token and retrying...")
            self._refresh_access_token()
            headers["Authorization"] = f"Bearer {self.access_token}"
            kwargs['headers'] = headers
            response = requests.request(method, url, **kwargs)
        
        return response
    
    def send_text(self, chat_id, text):
        url = "https://open.larksuite.com/open-apis/message/v4/send/"
        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }
        payload = {
            "chat_id": chat_id,
            "msg_type": "text",
            "content": {
                 "text": text
                 }
        }
        # print(payload)

        message_logger.log_message(chat_id, text, direction="outgoing")
        response = self._make_authenticated_request('POST', url, headers=headers, json=payload)
        
        if response.status_code != 200:
            print(f"Failed to send text message: {response.text}")

    def send_interactive_card(self, chat_id):
        """
        Sends a clean text-based command menu card
        """
        url = "https://open.larksuite.com/open-apis/message/v4/send/"
        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }

        # Using subtle colors for headers and dividers only
        divider_color = "#E5E7EB"  # Light gray divider
        
        card_content = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "🤖 FB Chat Bot"
                },
                            "subtitle": {
                "tag": "plain_text",
                "content": "Excel report results in 1-2 minutes"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**Basic Commands:**\n" + 
                                "**📙 /help** - Show available commands\n" +
                                "**🔍 /search domain.com** - Start scraping the target domain\n" +
                                "**⛔ /cancel** - Cancel any in-progress search\n"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**Example:**\n" + 
                                " /search chatbuypro.com\n" +
                                " /search thaidealzone.com"
                    }
                },
                               {
                    "tag": "hr",
                    "style": {
                        "color": divider_color
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "📋 Bot handles **1 request** at a time. New requests will be queued."
                    }
                }
            ]
        }

        payload = {
            "chat_id": chat_id,
            "msg_type": "interactive",
            "card": card_content
        }

        print(payload)

        message_logger.log_message(chat_id, "Sent Command menu", direction="outgoing")
        response = self._make_authenticated_request('POST', url, headers=headers, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"Failed to send card: {response.text}")
    
    def send_file(self, chat_id, file_buffer, filename):
        """
        Uploads and sends in-memory file
        """
        # Step 1: Upload file directly from memory
        upload_url = "https://open.larksuite.com/open-apis/im/v1/files"
        
        files = {
            'file': (filename, file_buffer, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        }
        data = {'file_type': 'stream', 'file_name': filename}
        
        upload_response = self._make_authenticated_request(
            'POST',
            upload_url, 
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
        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }
        payload = {
            "receive_id": chat_id,
            "msg_type": "file",
            "content": json.dumps({"file_key": file_key})
        }
        
        send_response = self._make_authenticated_request(
            'POST',
            send_url, 
            params=params, 
            headers=headers, 
            json=payload
        )
        
        # Handle send errors
        message_logger.log_message(chat_id, f"Sent file: {filename}", "outgoing")
        
        if send_response.status_code != 200:
            raise Exception(f"Send failed: {send_response.text}")
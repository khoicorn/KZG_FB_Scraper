import requests
# Configure logging
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

        message_logger.log_message(chat_id, text, direction= "outgoing")
        requests.post(url, headers=headers, json=payload)

    def send_interactive_card(self, chat_id):
        """
        Sends a clean text-based command menu card
        """
        url = "https://open.larksuite.com/open-apis/message/v4/send/"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
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
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"Failed to send card: {response.text}")
    
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
            message_logger.log_message(chat_id, f"Sent file: {filename}", "outgoing")
            
            if send_response.status_code != 200:
                raise Exception(f"Send failed: {send_response.text}")
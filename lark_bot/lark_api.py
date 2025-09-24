import requests
# import os
import json
import time
from datetime import datetime, timedelta
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

    def reply_to_message(self, message_id: str, content=None, text: str = None, card: dict = None, 
                    reply_in_thread: bool = True, msg_type: str = "text"):
        """
        Replies to a specific message in Lark/Feishu with text or interactive card
        
        Args:
            message_id (str): ID of the message to reply to
            content: Legacy parameter for backward compatibility
            text (str): Text content of the reply (for text messages)
            card (dict): Interactive card content (for card messages)
            reply_in_thread (bool): Whether to reply in thread form
            msg_type (str): Message type - "text" or "interactive"
            
        Returns:
            str: Reply message ID if successful, None otherwise
        """
        url = f"https://open.larksuite.com/open-apis/im/v1/messages/{message_id}/reply"
        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }
        
        # Determine message type and content
        if card is not None:
            # Interactive card message
            msg_type = "interactive"
            message_content = json.dumps(card)
            
        elif text is not None:
            # Text message
            msg_type = "text"
            message_content = json.dumps({"text": text})
        elif content is not None:
            # Legacy support - assume it's text
            msg_type = "text"
            message_content = json.dumps({"text": content})
        else:
            print("Error: No content provided (text or card)")
            return None
        
        payload = {
            "content": message_content,
            "msg_type": msg_type,
            "reply_in_thread": reply_in_thread
        }
        
        try:
            response = self._make_authenticated_request('POST', url, headers=headers, json=payload)
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("code") == 0:
                reply_message_id = response_data["data"]["message_id"]
                
                # Log the message
                log_content = text if text else f"Interactive Card: {card.get('header', {}).get('title', {}).get('content', 'Card')}"
                message_logger.log_message(user_id= None,
                                           message_id= message_id,
                                            chat_id= None,
                                             message= log_content, 
                                             direction="outgoing")
                
                print(f"Successfully replied with {msg_type} message. Reply ID: {reply_message_id}")
                return reply_message_id
            else:
                error_msg = response_data.get("msg", "Unknown error")
                print(f"Failed to reply to message {message_id}. Error: {error_msg} (Code: {response_data.get('code')})")
                return None
                
        except Exception as e:
            print(f"Exception occurred while replying to message {message_id}: {str(e)}")
            return None
        
    def update_card_message(self, message_id: str, card: dict):
        """
        Updates an existing interactive card message in Lark/Feishu
        
        Args:
            message_id (str): ID of the message to be updated
            card (dict): New interactive card content
            
        Returns:
            bool: True if successful, False otherwise
        """
        url = f"https://open.larksuite.com/open-apis/im/v1/messages/{message_id}"
        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }
        
        payload = {
            "content": json.dumps(card)
        }
        
        try:
            response = self._make_authenticated_request('PATCH', url, headers=headers, json=payload)
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("code") == 0:
                print(f"Successfully updated card message {message_id}")
                return True
            else:
                error_msg = response_data.get("msg", "Unknown error")
                error_code = response_data.get("code", "Unknown code")
                print(f"Failed to update message {message_id}. Error: {error_msg} (Code: {error_code})")
                return False
                
        except Exception as e:
            print(f"Exception occurred while updating message {message_id}: {str(e)}")
            return False
    
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

        message_logger.log_message(user_id= None,
                                   message_id= None,
                                   chat_id= chat_id, 
                                   message= text, 
                                   direction="outgoing")
        response = self._make_authenticated_request('POST', url, headers=headers, json=payload)
        
        if response.status_code != 200:
            print(f"Failed to send text message: {response.text}")

        try:
            data = response.json()
            return data.get("data", {}).get("message_id")
        except Exception:
            return None

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
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "🤖 FB Chat Bot"},
                "subtitle": {"tag": "plain_text", "content": "Excel report results in 1-2 minutes"},
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            "**Basic Commands:**\n"
                            "📙 **/help** : Show available commands\n"
                            "🔍 **/search** domain.com : Start scraping the target domain\n"
                            "⛔ **/cancel** : Cancel any in-progress search\n"
                        )
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            "**Daily Crawl Commands:**\n"
                            "🌐 **/add_domain** - **/remove_domain** domain.com : add or remove domains to crawl\n"
                            "🕒 **/add_schedule** - **/remove_schedule** HH:MM : add or remove schedules (time in GMT+7)\n"
                            "ℹ️ **/list** : Show saved domains and schedules\n"
                        )
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            "**Examples:**\n"
                            "/search chatbuypro.com\n"
                            "/add_domain chatbuypro.com, thaidealzone.com\n"
                            "/add_schedule 09:00, 13:00, 18:30\n"
                            "/remove_schedule domain.com\n"
                            "/remove_schedule a"
                        )
                    }
                },
                {"tag": "hr", "style": {"color": divider_color}},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "📋 Bot handles **1 request at a time**. New requests will be queued."
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

        message_logger.log_message(user_id = None,
                                   message_id= None,
                                   chat_id= chat_id, 
                                   message= "Sent Command menu", 
                                   direction="outgoing")
        response = self._make_authenticated_request('POST', url, headers=headers, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"Failed to send card: {response.text}")
        
            # NEW: return message_id so we can update this card later
        try:
            data = response.json()
            return data.get("data", {}).get("message_id")
        except Exception:
            return None
        
    def send_file(self, message_id, file_buffer, filename, reply_in_thread = True):
        """
        Uploads and sends in-memory file
        """
        # Step 1: Upload file directly from memory
        upload_url = "https://open.larksuite.com/open-apis/im/v1/files"

          # Tính expire_time (UTC timestamp mili giây)
        # expire_at = int((datetime.utcnow() + timedelta(minutes=5)).timestamp() * 1000)  # 5 phút sau

        files = {
            'file': (filename, file_buffer, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        }
        data = {'file_type': 'stream', 
                'file_name': filename
                }
        
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
        send_url = f"https://open.larksuite.com/open-apis/im/v1/messages/{message_id}/reply"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        
        payload = {
            "msg_type": "file",
            "content": json.dumps({"file_key": file_key}),
            "reply_in_thread": reply_in_thread
        }
        
        send_response = self._make_authenticated_request(
            'POST',
            send_url, 
            headers=headers, 
            json=payload
        )
        
        # Handle send errors
        if send_response.status_code != 200:
            send_error = send_response.json()
            error_msg = send_error.get('msg', 'Unknown send error')
            error_code = send_error.get('code', 'UNKNOWN')
            raise Exception(f"Failed to send file: {error_msg} (Code: {error_code})")
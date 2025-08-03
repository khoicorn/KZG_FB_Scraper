from .state_managers import state_manager
from .lark_api import LarkAPI
from .file_processor import generate_excel_report
from tools import *
import threading
import re
import urllib.parse  # Import the specific submodule

# from .state_managers import state_manager
# from .lark_api import LarkAPI
# from .file_processor import generate_excel_report
# import threading
# import re
# import urllib.parse
# from functools import lru_cache

# @lru_cache(maxsize=128)
def clean_url(url):
    """Optimized URL cleaning with caching"""
    if "[" in url:
        match = re.search(r'\[(.*?)\]', url)
        if match:
            url = match.group(1)

    parsed = urllib.parse.urlparse(url)
    return parsed.netloc if parsed.scheme else url

class CommandHandler:
    def __init__(self):
        self.lark_api = LarkAPI()
        self.start_reponse = {
            "help": self.show_help_menu,
            "hi": self.show_help_menu,
            "menu": self.show_help_menu,
            "start": self.show_help_menu,
            "hello": self.show_help_menu
        }
    
    def handle_command(self, user_id, text):
        text = text.strip().lower()
        message_info = state_manager.get_message_info(user_id)
        message_id = message_info["message_id"]
        chat_id = state_manager.get_chat_id(user_id)
        
        if not chat_id:
            print(f"Error: No chat_id for user {user_id}")
            return
        
        # Handle known commands
        if handler := self.start_reponse.get(text):
            handler(chat_id)
        elif text.startswith("search "):
            domain = text[7:].strip()  # More efficient slicing
            self.handle_search_term(user_id, domain)
        elif text == "search":
            self.lark_api.reply_to_message(message_id, 
                "❌ Please provide a domain to search.\n\n💡 Example: 'search chatbuypro.com'")
        elif text == "cancel":
            if state_manager.request_cancel(user_id):
                self.lark_api.reply_to_message(message_id, "⛔ Canceling...")
            else:
                self.lark_api.reply_to_message(message_id, "👀 No active process to cancel.")
        else:
            self.lark_api.reply_to_message(message_id, 
                "❌ Sorry, I didn't understand. Type 'help' for options")
    
    def handle_search_term(self, user_id, search_term):
        message_info = state_manager.get_message_info(user_id)
        message_id = message_info["message_id"]
        chat_id = state_manager.get_chat_id(user_id)
        
        if not chat_id:
            print(f"Error: No chat_id for user {user_id}")
            return
        
        # Check if search already in progress
        if state_manager.get_state(user_id) == "IN_PROGRESS":
            self.lark_api.reply_to_message(
                message_id,
                "🔄 A search is already in progress. Type 'cancel' to stop it and start a new one."
            )
            return

        search_term = clean_url(search_term)
        print(f"Cleaned search term: {search_term}")

        if not self.is_valid_domain(message_id, search_term):
            return

        print("Starting search...")
        state_manager.set_state(user_id, "IN_PROGRESS", chat_id)

        # Create processing card
        card = domain_processing_card(search_word=search_term, progress_percent=0)
        reply_message_id = self.lark_api.reply_to_message(
            message_id=message_id,
            card=card,
            reply_in_thread=True
        )
        
        # Start background thread
        threading.Thread(
            target=self.process_search_async,
            args=(user_id, search_term, reply_message_id),
            daemon=True
        ).start()
    
    def process_search_async(self, user_id, search_term, bot_reply_id):
        message_info = state_manager.get_message_info(user_id)
        message_id = message_info["message_id"]
        chat_id = state_manager.get_chat_id(user_id)
        
        if not chat_id:
            print(f"Error: No chat_id for user {user_id}")
            return
        
        try:
            crawler = FacebookAdsCrawler(search_term, chat_id, bot_reply_id)
            state_manager.register_process(user_id, crawler, chat_id)
            
            # Check cancellation before starting
            if state_manager.should_cancel(user_id):
                self.lark_api.reply_to_message(message_id, "⛔ Process cancelled before starting!")
                return
                    
            file_buffer, filename, df = generate_excel_report(crawler)
            encoded_term = urllib.parse.quote(search_term)
            link = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all&q={encoded_term}&search_type=keyword_unordered"
            
            # Handle results if not cancelled
            if not state_manager.should_cancel(user_id):
                if df.empty:
                    card = search_no_result_card(search_word=search_term, href=link)
                    self.lark_api.update_card_message(bot_reply_id, card=card)
                else:
                    card = search_complete_card(
                        search_word=search_term,
                        num_results=df.shape[0],
                        href=link
                    )
                    self.lark_api.update_card_message(message_id=bot_reply_id, card=card)
                    self.lark_api.send_file(message_id, file_buffer, filename)
            else:
                self.lark_api.reply_to_message(message_id, "⛔ Process cancelled successfully!")
        except Exception as e:
            if not state_manager.should_cancel(user_id):
                self.lark_api.reply_to_message(message_id, f"❌ Error processing request: {str(e)}")
            else:
                self.lark_api.reply_to_message(message_id, "⛔ Process cancelled due to error!")
        finally:
            # Cleanup resources
            if 'file_buffer' in locals() and file_buffer:
                try:
                    file_buffer.close()
                except:
                    pass
            state_manager.clear_state(user_id)

    def show_help_menu(self, chat_id):
        self.lark_api.send_interactive_card(chat_id)

    def is_valid_domain(self, message_id, domain):
        print(f"Validating domain: {domain}")
        
        # Quick checks first for efficiency
        if '@' in domain or len(domain) < 4:
            self.lark_api.reply_to_message(message_id, 
                "❌ Invalid domain format. Please provide a valid domain [e.g., chatbuypro.com]:")
            return False

        # Use compiled regex for efficiency
        domain_pattern = re.compile(
            r'^([a-zA-Z0-9-]{2,}\.)+[a-zA-Z]{2,}$'
        )

        if not domain_pattern.fullmatch(domain):
            self.lark_api.reply_to_message(message_id, 
                "❌ Invalid domain or domain is too short. \nPlease provide a valid domain [e.g., chatbuypro.com]:")
            return False

        return True

command_handler = CommandHandler()
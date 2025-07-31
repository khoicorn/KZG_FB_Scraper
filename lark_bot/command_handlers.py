from .state_managers import state_manager
from .lark_api import LarkAPI
from .file_processor import generate_excel_report
from tools import *
import threading
import re
import urllib.parse  # Import the specific submodule

def clean_url(url):

    if "[" in url:

        match = re.search(r'\[(.*?)\]', url)  # Non-greedy match between []
        if match:
            url = match.group(1)  # "chatbuypromax.com"

    parsed = urllib.parse.urlparse(url)
    return parsed.netloc if parsed.scheme else url

class CommandHandler:
    def __init__(self):
        self.lark_api = LarkAPI()
    
    def handle_command(self, user_id, text):
        text = text.strip().lower()
        chat_id = state_manager.get_chat_id(user_id)
        message_id = state_manager.get_message_info(user_id)["message_id"]
        # print(chat_id, message_id)

        if not chat_id:
            print("Error: No chat_id found for user")
            return
        
        if text in ["help", "hi", "menu", "start", "hello"]:
            self.show_help_menu(chat_id)
            
        elif text.startswith("search "):
            # Direct search: "search chatbuypro.com"
            domain = text.replace("search", "", 1).strip()
            self.handle_search_term(user_id, domain)

        elif text == "search":
            # state_manager.set_state(chat_id, "AWAITING_SEARCH_TERM")
            self.lark_api.reply_to_message(message_id, "❌ Please provide a domain to search.\n\n💡 Example: 'search chatbuypro.com'")

        elif text == "cancel":
            if state_manager.request_cancel(user_id):
                self.lark_api.reply_to_message(message_id, "⛔ Canceling...")
            else:
                self.lark_api.reply_to_message(message_id, "👀 No active process to cancel.")

        else:
            self.lark_api.reply_to_message(message_id, "❌ Unrecognized command. Type 'help' for options")
    
    def handle_search_term(self, user_id, search_term):
        chat_id = state_manager.get_chat_id(user_id)
        message_id = state_manager.get_message_info(user_id)["message_id"]

        if not chat_id:
            print("Error: No chat_id found for user")
            return
        
        # Check if a search is already in progress
        if state_manager.get_state(user_id) == "IN_PROGRESS":
            self.lark_api.reply_to_message(
                message_id,
                "🔄 A search is already in progress. Type 'cancel' to stop it and start a new one."
            )
            return

        search_term = clean_url(search_term)  # Clean the URL to get the domain
        print(search_term)

        if not self.is_valid_domain(chat_id, search_term):
            return

        print("Searching ...")
        state_manager.set_state(user_id, "IN_PROGRESS", chat_id)

        reply_message_id = self.lark_api.reply_to_message(
            message_id = message_id,
            card= domain_processing_card(search_word= search_term,
                                         progress_percent= 0),
            reply_in_thread= True
        )

        print("PROCESSING ID", reply_message_id)
        
        # Process in background if domain is valid
        threading.Thread(
            target=self.process_search_async,
            args=(user_id, search_term, reply_message_id),
            daemon=True
        ).start()
    
    def process_search_async(self, user_id, search_term, bot_reply_id):
        chat_id = state_manager.get_chat_id(user_id)
        message_id = state_manager.get_message_info(user_id)["message_id"]

        if not chat_id:
            print("Error: No chat_id found for user")
            return
        
        file_buffer = None

        try:
            crawler = FacebookAdsCrawler(search_term, chat_id, bot_reply_id)
            
            # Register the process BEFORE starting
            state_manager.register_process(user_id, crawler, chat_id)
            
            # Check if cancelled before starting
            if state_manager.should_cancel(user_id):
                self.lark_api.reply_to_message(message_id, "⛔ Process cancelled before starting!")
                return
                    
            file_buffer, filename, df = generate_excel_report(crawler)
            print(df)
            # Only send results if not cancelled
            if not state_manager.should_cancel(user_id):
                if df.empty:
                    # self.lark_api.reply_to_message(message_id, "❌ No results found for this domain.\n")
                    encoded_term = urllib.parse.quote(search_term)
                    link = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all&q={encoded_term}&search_type=keyword_unordered"
                    message = f"🔗 Visit for more info: {link}"
                    # self.lark_api.reply_to_message(message_id, message)
                    
                    self.lark_api.update_card_message(bot_reply_id, card= 
                                                      search_no_result_card(
                                                          search_word=search_term,
                                                          href= link
                                                      ))
                else:
                    # self.lark_api.reply_to_message(message_id, f"✅ Search completed: {df.shape[0]} results.")
                    self.lark_api.update_card_message(message_id= bot_reply_id,
                                                      card = search_complete_card(
                                                          search_word= search_term,
                                                          num_results= df.shape[0]
                                                      ))
                    self.lark_api.send_file(message_id, file_buffer, filename)
            else:
                self.lark_api.reply_to_message(message_id, "⛔ Process cancelled successfully!")

        except Exception as e:
            if not state_manager.should_cancel(user_id):
                self.lark_api.reply_to_message(message_id, f"❌ Error processing request: {str(e)}")
            else:
                self.lark_api.reply_to_message(message_id, "⛔ Process cancelled due to error!")
                
        finally:
            # Always clean up resources
            if file_buffer:
                try:
                    file_buffer.close()
                except:
                    pass
            
            # Clear state and log
            print(f"Clearing state for user_id: {user_id}")
            state_manager.clear_state(user_id)
            
            # Remove from active processes if still there
            with state_manager.lock:
                if user_id in state_manager.active_processes:
                    del state_manager.active_processes[user_id]
            
    def show_help_menu(self, chat_id):
        # help_text = (
        #     "🤖 FB Ads Scraper\n"
        #     "──────────────────────\n"
        #     "🔍 `search domain.com`\n"
        #     "⛔ `cancel`\n"
        #     "📙 `help`\n"
        #     "──────────────────────\n"
        #     "⚡ Excel results in 1-2 mins"
        # )
        # print(help_text)
        self.lark_api.send_interactive_card(chat_id)

    def is_valid_domain(self, chat_id, domain):
        print("DOMAIN CLEANED:", domain)
        # Reject if input contains '@'
        if '@' in domain:
            self.lark_api.send_text(chat_id, "❌ Domain contains '@'. \nPlease provide a valid domain [e.g., chatbuypro.com]:")
            return False

        # Require at least one dot and check domain pattern
        domain_pattern = re.compile(
            r'^([a-zA-Z0-9-]{2,}\.)+[a-zA-Z]{2,}$'  # part before dot must be at least 2 chars
        )

        # Match full domain and ensure it's not too short
        if not domain_pattern.fullmatch(domain):
            self.lark_api.send_text(chat_id, "❌ Invalid request. \nPlease provide a valid domain [e.g., chatbuypro.com]:")
            return False

        # Additional optional check: min total length
        if len(domain) < 8:  # e.g., x.co is 4 chars, a.com is 5
            self.lark_api.send_text(chat_id, "❌ Domain is too short. \nPlease provide a valid domain [e.g., chatbuypro.com]:")
            return False

        return True


command_handler = CommandHandler()
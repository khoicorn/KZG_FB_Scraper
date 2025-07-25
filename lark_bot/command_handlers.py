from .state_managers import state_manager
from .lark_api import LarkAPI
from .file_processor import generate_excel_report
from tools import FacebookAdsCrawler
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
    
    def handle_command(self, chat_id, text):
        text = text.strip().lower()
        # print(text)

        if text in ["help", "hi", "menu", "start", "hello"]:
            self.show_help_menu(chat_id)
            
        elif text.startswith("search "):
            # Direct search: "search chatbuypro.com"
            domain = text.replace("search", "", 1).strip()
            self.handle_search_term(chat_id, domain)

        elif text == "search":
            # state_manager.set_state(chat_id, "AWAITING_SEARCH_TERM")
            self.lark_api.send_text(chat_id, "❌ Please provide a domain to search.\n\n💡 Example: 'search chatbuypro.com'")

        elif text == "cancel":
            if state_manager.request_cancel(chat_id):
                self.lark_api.send_text(chat_id, "⛔ Canceling...")
            else:
                self.lark_api.send_text(chat_id, "👀 No active process to cancel.")

        else:
            self.lark_api.send_text(chat_id, "❌ Unrecognized command. Type 'help' for options")
    
    def handle_search_term(self, chat_id, search_term):
        # Validate the search term is a domain (e.g., "thaidealzone.com")
        # print(search_term)

        search_term = clean_url(search_term)  # Clean the URL to get the domain
        print(search_term)

        if not self.is_valid_domain(chat_id, search_term):
            # self.lark_api.send_text(chat_id, "❌ Invalid request. \nPlease provide a valid domain [e.g., chatbuypro.com]:")
            return

        print("Searching ...")
        state_manager.set_state(chat_id, "IN_PROGRESS")
        self.lark_api.send_text(chat_id, "🔍 Processing your request. This may take a minute...\n\n💡 Type 'cancel' anytime to stop the process")
        
        # Process in background if domain is valid
        threading.Thread(
            target=self.process_search_async,
            args=(chat_id, search_term),
            daemon=True
        ).start()
    
    
    def process_search_async(self, chat_id, search_term):
        file_buffer = None
        try:
            crawler = FacebookAdsCrawler(search_term, chat_id)
            
            # Register the process BEFORE starting
            state_manager.register_process(chat_id, crawler)
            
            # Check if cancelled before starting
            if state_manager.should_cancel(chat_id):
                self.lark_api.send_text(chat_id, "⛔ Process cancelled before starting!")
                return
                
            file_buffer, filename, df = generate_excel_report(crawler)
            
            # Only send results if not cancelled
            if not state_manager.should_cancel(chat_id):
                if df.empty:
                    self.lark_api.send_text(chat_id, "❌ No results found for this domain.\n")

                    # Encode the search term to be URL-safe
                    encoded_term = urllib.parse.quote(search_term)
                    link = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all&q={encoded_term}&search_type=keyword_unordered"
                    message = f"🔗 Visit for more info: {link}"
                    # Send the message
                    self.lark_api.send_text(chat_id, message)
                else:
                    self.lark_api.send_text(chat_id, f"✅ Search completed: {df.shape[0]} results.")
                    self.lark_api.send_file(chat_id, file_buffer, filename)
            else:
                self.lark_api.send_text(chat_id, "⛔ Process cancelled successfully!")

        except Exception as e:
            if not state_manager.should_cancel(chat_id):
                self.lark_api.send_text(chat_id, f"❌ Error processing request: {str(e)}")
            else:
                self.lark_api.send_text(chat_id, "⛔ Process cancelled due to error!")
            
        finally:
            # Always clean up resources
            if file_buffer:
                try:
                    file_buffer.close()
                except:
                    pass
            
            # Clear state in finally block to ensure it always happens
            state_manager.clear_state(chat_id)
            
            # Remove from active processes if still there
            with state_manager.lock:
                if chat_id in state_manager.active_processes:
                    del state_manager.active_processes[chat_id]
            
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
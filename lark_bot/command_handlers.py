from .state_managers import state_manager
from .lark_api import LarkAPI
from .file_processor import generate_excel_report
from tools import FacebookAdsCrawler
import threading
import re

class CommandHandler:
    def __init__(self):
        self.lark_api = LarkAPI()
    
    def handle_command(self, chat_id, text):
        text = text.strip().lower()

        if text in ["help", "hi", "menu"]:
            self.show_help_menu(chat_id)
            
        elif text.startswith("search "):
            # Direct search: "search chatbuypro.com"
            domain = text.replace("search", "", 1).strip()
            self.handle_search_term(chat_id, domain)

        elif text == "search":
            state_manager.set_state(chat_id, "AWAITING_SEARCH_TERM")
            self.lark_api.send_text(chat_id, "💬 Type a domain to search [e.g. chatbuypro.com]:")

        elif text == "cancel":
            if state_manager.request_cancel(chat_id):
                self.lark_api.send_text(chat_id, "⛔ Canceling...")
            else:
                self.lark_api.send_text(chat_id, "ℹ️ No active process to cancel.")

        elif text == "help":
            self.show_help_menu(chat_id)

        else:
            self.lark_api.send_text(chat_id, "❌ Unrecognized command. Type 'help' for options")
    
    def handle_search_term(self, chat_id, search_term):
        # Validate the search term is a domain (e.g., "thaidealzone.com")
        print(search_term)

        if not self.is_valid_domain(search_term):
            self.lark_api.send_text(chat_id, "❌ Invalid request. \nPlease provide a valid domain [e.g., chatbuypro.com]:")
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
                    self.lark_api.send_text(chat_id, "❌ No results found for this domain.")
                else:
                    self.lark_api.send_text(chat_id, "✅ Search completed successfully!")
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
        help_text = (
            "🤖 FB Ads Scraper | Quick Commands\n"
            "─────────────────────────────────────\n"
            "🔍 Search\n"
            "▸ `search`: start search function\n"
            "▸ `search domain.com`: direct search\n\n"
            "⛔ Cancel\n"
            "▸ `cancel`: during any operation\n\n"
            "🆘 Help\n"
            "▸ `help` | `hi` | `menu`: show this guide\n"
            "─────────────────────────────────────\n"
            "⚡ Results delivered as Excel within 1-2 mins"
        )
        print(help_text)
        self.lark_api.send_text(chat_id, help_text)

    def is_valid_domain(self, domain):
        domain_pattern = re.compile(
            r'^([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$'
        )
        return bool(domain_pattern.fullmatch(domain))

command_handler = CommandHandler()
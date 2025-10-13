from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from selenium.webdriver.chrome.service import Service

from lark_bot import LarkAPI
from lark_bot.state_managers import state_manager
from .interactive_card_library import *

import logging

import re
import pandas as pd
# from datetime import datetime
import time
import threading
import queue
# import requests
from selenium_stealth import stealth
# import io
# from openpyxl import Workbook
# from openpyxl.drawing.image import Image as OpenPyxlImage
# from openpyxl.utils import get_column_letter
# from PIL import Image as PILImage
# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
import os
import zipfile

def create_proxy_extension(host, port, user, pw, file_path):
    """Creates a Chrome extension .zip file for an authenticated proxy."""
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = f'''
    var config = {{
            mode: "fixed_servers",
            rules: {{
              singleProxy: {{
                scheme: "http",
                host: "{host}",
                port: parseInt({port})
              }},
              bypassList: ["localhost"]
            }}
          }};

    chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});

    function callbackFn(details) {{
        return {{
            authCredentials: {{
                username: "{user}",
                password: "{pw}"
            }}
        }};
    }}

    chrome.webRequest.onAuthRequired.addListener(
                callbackFn,
                {{urls: ["<all_urls>"]}},
                ['blocking']
    );
    '''
    # Create the zip file
    with zipfile.ZipFile(file_path, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)
    
    return file_path

class CrawlerQueue:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.queue = queue.Queue()
                cls._instance.active = False
                cls._instance.current_chat_id = None
                cls._instance.queue_list = []  # Thêm list để track thứ tự
        return cls._instance
    
    def add_request(self, crawler):
        """Thêm yêu cầu vào hàng đợi"""
        with self._lock:
            self.queue.put(crawler)
            self.queue_list.append(crawler.chat_id)  # Track thứ tự
            
            # Gửi message về vị trí trong queue
            position = len(self.queue_list)
            if self.active:
                # Nếu đang có request chạy, vị trí sẽ là position + 1 (vì có 1 đang chạy)
                # crawler.lark_api.reply_to_message(
                #     crawler.message_id,
                #     f"⏳ You’re queued at spot #{position}. I’ll ping you when it starts."
                # )
                crawler.lark_api.update_card_message(crawler.message_id, 
                                        card= queue_card(search_word= crawler.keyword,
                                         position= position)
                                         )
        
        if not self.active:
            self._process_next()

    def _process_next(self):
        """Xử lý yêu cầu tiếp theo trong hàng đợi"""
        with self._lock:
            if not self.queue.empty():
                self.active = True
                next_crawler = self.queue.get()
                self.current_chat_id = next_crawler.chat_id
                
                # Remove từ queue_list
                if next_crawler.chat_id in self.queue_list:
                    self.queue_list.remove(next_crawler.chat_id)
                
                # Update position cho các request còn lại
                self._update_queue_positions()
                
                # Tạo thread mới để chạy crawler
                threading.Thread(
                    target=self._run_crawler, 
                    args=(next_crawler,),
                    daemon=True
                ).start()
            else:
                self.active = False
                self.current_chat_id = None
    
    def _update_queue_positions(self):
        """Cập nhật và thông báo vị trí mới cho các request trong queue"""
        for i, chat_id in enumerate(self.queue_list, 1):
            # Tìm crawler tương ứng trong queue để gửi message
            temp_queue = list(self.queue.queue)
            for crawler in temp_queue:
                if crawler.chat_id == chat_id:
                    # crawler.lark_api.reply_to_message(
                    #     crawler.message_id,
                    #     f"📍 Current position in queue: #{i}"
                    # )
                    crawler.lark_api.update_card_message(crawler.message_id, 
                        card= queue_card(search_word= crawler.keyword,
                            position= i)
                            )
                    break
    
    def _run_crawler(self, crawler):
        """Chạy crawler và xử lý yêu cầu tiếp theo khi hoàn thành"""
        try:
            
            crawler.crawl()  # Gọi phương thức crawl chính
            
            # Chỉ xử lý kết quả nếu không bị cancel
            if not crawler.should_stop():
                crawler.data_to_dataframe()  # Xử lý dữ liệu
                # Note: send_results() method không có trong code gốc
                # Có thể cần implement hoặc xử lý ở nơi khác
                
        except Exception as e:
            if not crawler.should_stop():
                crawler.lark_api.reply_to_message(
                    crawler.message_id, 
                    f"❌ Error during processing: {str(e)}"
                )
        finally:
            with self._lock:
                self.active = False
                self.current_chat_id = None
            self._process_next()  # Xử lý yêu cầu tiếp theo
    
    def get_queue_position(self, chat_id):
        """Kiểm tra vị trí trong hàng đợi"""
        with self._lock:
            if self.current_chat_id == chat_id:
                return 0  # Đang chạy
            
            try:
                position = self.queue_list.index(chat_id) + 1
                return position
            except ValueError:
                return None  # Không có trong hàng đợi
    
    def remove_from_queue(self, chat_id):
        """Remove request khỏi queue khi bị cancel"""
        with self._lock:
            # Remove từ queue_list
            if chat_id in self.queue_list:
                self.queue_list.remove(chat_id)
            
            # Remove từ queue (phức tạp hơn vì queue.Queue không support remove trực tiếp)
            temp_items = []
            while not self.queue.empty():
                item = self.queue.get()
                if item.chat_id != chat_id:
                    temp_items.append(item)
            
            # Put lại các items không bị remove
            for item in temp_items:
                self.queue.put(item)
            
            # Update positions cho các request còn lại
            self._update_queue_positions()
    
class FacebookAdsCrawler:

    # Pre-compiled regex patterns (class-level variables)
    _LIBRARY_ID_PATTERN = re.compile(r'Library ID:\s*(\d+)')
    _DATE_PATTERN = re.compile(r'\b\d{1,2}\s\w{3}\s\d{4}\b')

    def __init__(self, keyword, chat_id, message_id = False):
        self.keyword = keyword
        self.ad_card_class = "x1plvlek xryxfnj x1gzqxud x178xt8z x1lun4ml xso031l xpilrb4 xb9moi8 xe76qn7 x21b0me x142aazg x1i5p2am x1whfx0g xr2y4jy x1ihp6rs x1kmqopl x13fuv20 x18b5jzi x1q0q8m5 x1t7ytsu x9f619"
        self.driver = None
        self.ads_data = []
        self.lark_api = LarkAPI()
        self.chat_id = message_id
        self._stop_event = threading.Event()
        self.queue_manager = CrawlerQueue()  # Thêm dòng này
        self.message_id = message_id

    def force_stop(self):
        """More reliable stopping mechanism"""
        print(f"🛑 Force stopping crawler for {self.chat_id}")
        self._stop_event.set()
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
        except Exception as e:
            print(f"Error during force stop: {e}")

    def should_stop(self):
        """Check if we should stop (either internal or external cancellation)"""
        return self._stop_event.is_set() or state_manager.should_cancel(self.chat_id)
    
    def initialize_driver(self):
        """Initializes the driver using a specific Chrome profile and adds timeouts."""
        if self.should_stop():
            return False

        options = Options()
        print("\nStart initialized successfully.")
        # --- Performance / Speed Optimizations ---
        options.add_argument("--headless=new")        # Run headless Chrome (no GUI)
        options.add_argument("--disable-gpu")         # Disable GPU (not needed in headless)
        options.add_argument("--disable-extensions")  # Disable Chrome extensions
        options.add_argument("--disable-infobars")    # Hide "Chrome is being controlled" banner
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        
        # --- Network / Rendering Optimizations ---
        options.add_argument("--blink-settings=imagesEnabled=false")   # Don’t load images
        options.add_argument("--disable-features=TranslateUI")         # Disable translate popup
        options.add_argument("--mute-audio")                           # Disable sound
        options.add_argument("--disable-sync")                         # Disable Google sync
        options.add_argument("--disable-notifications")                # Block push notifications
        options.add_argument("--no-default-browser-check")

        # --- Memory / CPU Optimizations ---
        options.add_argument("--disable-dev-shm-usage")  # already have
        options.add_argument("--no-sandbox")             # already have
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-popup-blocking")

        # --- Optionally limit logs ---
        options.add_argument("--log-level=3")            # Suppress console logs
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        service = Service()
        self.driver = webdriver.Chrome(service=service, options=options)

        # --- CRUCIAL: Add Timeouts ---
        # This prevents the script from hanging indefinitely on page loads or element searches.
        self.driver.set_page_load_timeout(30) # Fails if a page takes >30s to load
        self.driver.implicitly_wait(5)       # Waits up to 5s for elements to appear

        print("\n✅ Driver initialized successfully.")
        return True

    
    def start(self):
        """Phương thức để bắt đầu crawl thông qua hàng đợi"""
        # Kiểm tra xem request đã có trong queue chưa
        position = self.queue_manager.get_queue_position(self.chat_id)
        
        if position is not None:
            if position == 0:
                return
            else:
                self.lark_api.reply_to_message(
                    self.message_id,
                    f"⏳ Your request is in waiting list (No #{position})"
                )
            return
        
        # Thêm vào queue
        self.queue_manager.add_request(self)
        
    def fetch_ads_page(self):
        """Load the Facebook Ads Library page"""
        if self.should_stop():
            return False
        url = (f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&"
               f"is_targeted_country=false&media_type=all&q={self.keyword}&search_type=keyword_unordered")
        self.driver.get(url)
        
        # time.sleep(8)

        try:
            # NOTE: This selector is unstable. Find a better one (e.g., 'div[role="article"]')
            # for long-term reliability.
            css_selector = "." + self.ad_card_class.replace(" ", ".")
            
            print("Waiting up to 10 seconds for initial ads to load...")
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
            print("✅ Initial ads loaded.")
            return True
        except TimeoutException:
            print("❌ Timed out waiting for initial ads. The page may be empty or the selector is wrong.")
            return False
    def get_dim_keyword(self) -> pd.DataFrame:
        """
        If a dim_keyword CSV exists for this search word, read it.
        Otherwise, open the page, open Filters → Advertisers, scroll all, save CSV, and return it.
        """
        # Try both naming styles (you mentioned ".com" in the key)
        csv_candidates = [
            f"ref_data//dim_keyword_{self.keyword}.com.csv",
            f"ref_data//dim_keyword_{self.keyword}.csv",
        ]
        existing_path = next((p for p in csv_candidates if os.path.exists(p)), None)

        if existing_path:
            dim_keyword = pd.read_csv(existing_path, dtype=str)
            dim_keyword["keyword"] = self.keyword
            # dim_keyword = dim_keyword[dim_keyword["id"] != "all_pages"]
            dim_keyword = dim_keyword.drop_duplicates()
            return dim_keyword

        # If not found => build it by scraping the Advertiser list
        # if not self.fetch_ads_page():
        #     raise RuntimeError("Failed to open Ads Library search page.")
        if not self.initialize_driver():
            return
        print("DONE INITALIZE DRIVER")

        if not self.fetch_ads_page():
            return
        print("DONE GET URL")
        time.sleep(1)

        dim_keyword = self.scrape_advertiser_list_from_filters()
        out_path = f"ref_data//dim_keyword_{self.keyword}.csv"
        dim_keyword.to_csv(out_path, index=False)
        return dim_keyword
    
    def scrape_advertiser_list_from_filters(self) -> pd.DataFrame:
        """
        Open Filters → Advertisers combobox, scroll to load all options, collect (id, name).
        Returns a DataFrame with columns: id, name, keyword
        """
        self.fetch_ads_page
        wait = WebDriverWait(self.driver, 20)

        # 1) Open Filter panel
        filter_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and contains(., 'Filters')]"))
        )
        filter_button.click()

        # 2) Open Advertisers combobox (label text can vary; we target by role first)
        advertiser_dropdown = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//div[@role='combobox' and .//text()='All advertisers']"))
        )
        advertiser_dropdown.click()

        # 3) Scroll the listbox and collect options
        scrollable_container = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='listbox']")))
        option_locator = (By.XPATH, ".//div[@role='option']")

        seen = set()
        rows = []
        last_count = -1

        while True:
            options = scrollable_container.find_elements(*option_locator)
            for opt in options:
                opt_id = opt.get_attribute("id") or ""
                opt_name = (opt.get_attribute("textContent") or "").strip()
                key = (opt_id, opt_name)
                if key not in seen and opt_id:
                    seen.add(key)
                    rows.append([opt_id, opt_name])

            if len(options) == last_count:
                break
            last_count = len(options)

            # Scroll last option into view to trigger lazy load
            self.driver.execute_script("arguments[0].scrollIntoView(true);", options[-1])
            time.sleep(0.8)

        df = pd.DataFrame(rows, columns=["id", "name"])
        df["keyword"] = self.keyword
        df.drop_duplicates(inplace=True)
        return df

    def fetch_ads_page_by_id(self, page_name: str) -> bool:
        """
        Open Ads Library page filtered by advertiser/page id.
        """
        search_word = f"{self.keyword} {page_name}"
        if self.should_stop():
            return False

        url = (
            "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&"
            f"is_targeted_country=false&media_type=all&q={search_word}&search_type=keyword_unordered"
        )
        self.driver.get(url)
        print("Search for:", search_word)

        try:
            css_selector = "." + self.ad_card_class.replace(" ", ".")
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
            return True
        except TimeoutException:
            return False
        
    def scrape_current_page_ads(self):
        """
        Find all ad cards on the CURRENT page and append their parsed dicts to self.ads_data.
        """
        css_selector = "." + self.ad_card_class.replace(" ", ".")
        elements = self.driver.find_elements(By.CSS_SELECTOR, css_selector)

        for ad in elements:
            if self.should_stop():
                return
            ad_data = self.process_ad_element(ad)
            if ad_data:
                ad_data["ad_number"] = len(self.ads_data) + 1
                self.ads_data.append(ad_data)

    def scroll_to_bottom(self):
        """
        Scrolls and clicks 'Load More' buttons until all content is loaded.
        This replaces the old scroll_to_bottom method.
        """
        if self.should_stop(): return False

        self.lark_api.update_card_message(
            self.message_id,
            card=domain_processing_card(search_word=self.keyword, progress_percent=10)
        )

        # Use a 'strikes' system. If scrolling and clicking fail a few
        # times in a row, we assume we're done.
        strikes = 0
        max_strikes = 3 

        while strikes < max_strikes:
            if self.should_stop(): return False

            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # 1. SCROLL: Attempt to trigger infinite scroll
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            try:
                # 2. WAIT: Wait for new content from the scroll
                WebDriverWait(self.driver, 15).until(
                    lambda d: d.execute_script("return document.body.scrollHeight") > last_height
                )
                
                # If successful, reset strikes and continue the loop
                logger.info("New content loaded via scrolling.")
                strikes = 0
            
            except TimeoutException:
                # 3. CLICK: Scrolling failed, now try clicking a button
                logger.warning("Scrolling did not load new content. Looking for a button...")

        logger.info("✅ Finished scrolling and loading all content.")
        if not self.should_stop():
            self.lark_api.update_card_message(
                self.message_id,
                card=domain_processing_card(search_word=self.keyword, progress_percent=40)
            )
        return True
    
    def _is_page_stabilized(self, driver, last_height):
        """Check if page height remains constant for 3 consecutive checks"""
        heights = []
        for _ in range(3):
            heights.append(driver.execute_script("return document.body.scrollHeight"))
            time.sleep(0.5)  # Short interval between checks
        
        return all(h == heights[0] for h in heights) and heights[0] == last_height
            
    def extract_library_id(self, text):
        match = self._LIBRARY_ID_PATTERN.search(text)
        return match.group(1) if match else None
        
    def extract_date(self, text):
        match = self._DATE_PATTERN.search(text)
        return match.group() if match else None
    
    def process_ad_element(self, ad_element):
        """Optimized element processing with batched JS execution"""
        if self.should_stop():
            return None

        try:
            ad_data = self.driver.execute_script("""
                const element = arguments[0];
                const text = element.innerText;

                // Extract media
                let company = null;
                let avatarUrl = null;
                let imageUrl = null;
                let videoUrl = null;
                let thumbnailUrl = null;

                const imgs = element.querySelectorAll('img');
                for (const img of imgs) {
                    if (img.alt && !company) {
                        company = img.alt.trim();
                        avatarUrl = img.src;
                    } else if (!imageUrl) {
                        imageUrl = img.src;
                        thumbnailUrl = img.src;
                    }
                }

                // Extract video
                const video = element.querySelector('video');
                if (video) {
                    videoUrl = video.src;
                    thumbnailUrl = video.poster || thumbnailUrl;
                }

                // Extract links
                let destinationUrl = null;
                let pixelId = null;
                const links = element.querySelectorAll('a');
                for (const link of links) {
                    const url = link.href;
                    if (url && url.includes('l.facebook.com')) {
                        if (url.includes('pixelId')) {
                            pixelId = url.split('pixelId')[1].split('&')[0].replace('%3D', '');
                            destinationUrl = url;
                        } else {
                            destinationUrl = url;
                            break;
                        }
                    }
                }

                // Get Primary Text and Headline/Description
                let primaryText = null;
                let headlineText = null;

                const el1 = element.querySelector("._7jyr._a25-");   // first class
                if (el1) primaryText = el1.innerText;

                const el2 = element.querySelector(".x6s0dn4.x2izyaf.x78zum5.x1qughib.x15mokao.x1ga7v0g.xde0f50.x15x8krk.xexx8yu.xf159sx.xwib8y2.xmzvs34"); 
                if (el2) headlineText = el2.innerText;

                return {
                    text,
                    company,
                    avatarUrl,
                    imageUrl,
                    videoUrl,
                    thumbnailUrl,
                    destinationUrl,
                    pixelId,
                    primaryText,
                    headlineText
                };
            """, ad_element)

            if "Library ID" not in ad_data['text']:
                return None

            lib_id = self.extract_library_id(ad_data['text'])
            start_date = self.extract_date(ad_data['text'])

            return {
                "text_snippet": ad_data['text'][:100].replace("\n", " ") + "...",
                "library_id": lib_id,
                "ad_start_date": start_date,
                "company": ad_data['company'],
                "avatar_url": ad_data['avatarUrl'],
                "image_url": ad_data['imageUrl'],
                "video_url": ad_data['videoUrl'],
                "thumbnail_url": ad_data['thumbnailUrl'],
                "destination_url": ad_data['destinationUrl'],
                "pixel_id": ad_data['pixelId'],
                "primary_text": ad_data['primaryText'],
                "headline_text": ad_data['headlineText']
            }

        except Exception as e:
            print(f"Error processing ad: {e}")
            return None
                
    def _extract_media(self, ad_element):
        """Extract image and video data from ad"""
        if self.should_stop():
            return {}
            
        media_data = {
            "company": None,
            "avatar_url": None,
            "image_url": None,
            "video_url": None,
            "thumbnail_url": None
        }
        
        try:
            # Process images
            img_tags = ad_element.find_elements(By.TAG_NAME, "img")
            for img in img_tags:
                if self.should_stop():
                    break
                    
                src = img.get_attribute("src")
                alt = img.get_attribute("alt")
                
                if alt and not media_data["avatar_url"]:
                    media_data["avatar_url"] = src
                    media_data["company"] = alt.strip()
                elif not media_data["image_url"]:
                    media_data["image_url"] = src
                    media_data["thumbnail_url"] = src

            # Process video
            if not self.should_stop():
                try:
                    video_tag = ad_element.find_element(By.TAG_NAME, "video")
                    media_data["video_url"] = video_tag.get_attribute("src")
                    media_data["thumbnail_url"] = video_tag.get_attribute("poster")
                except NoSuchElementException:
                    pass
            

                    
        except Exception as e:
            print(f"Error extracting media: {e}")
            
        return media_data
        
    def _extract_links(self, ad_element):
        """Extract links and pixel data from ad"""
        if self.should_stop():
            return {}
            
        link_data = {
            "destination_url": None,
            "pixel_id": None
        }
        
        try:
            href_tags = ad_element.find_elements(By.TAG_NAME, "a")
            for href in href_tags:
                if self.should_stop():
                    break
                    
                url = href.get_attribute("href")
                if url and "l.facebook.com" in url:
                    if "pixelId" in url:
                        # Extract pixel ID from URL
                        link_data["destination_url"] = url
                        link_data["pixel_id"] = url.split("pixelId")[-1].split("&")[0].strip()
                    else:
                        # If no pixelId, just store the destination URL
                        link_data["destination_url"] = url
                        break
        except Exception as e:
            print(f"Error extracting links: {e}")
            
        return link_data
        
    # def crawl(self):
    #     """Main method to execute the crawl"""
    #     try:
    #         if not self.initialize_driver():
    #             return
    #         print("DONE INITALIZE DRIVER")

    #         if not self.fetch_ads_page():
    #             return
    #         print("DONE GET URL")
    #         time.sleep(2)
    #     # --- Main Script ---

    #         print("Looking for the 'Filters' button...")
    #        # --- Corrected and Integrated Code for your 'crawl' method ---

    #         try:
    #             # 1. Click the main "Filters" button to open the panel
    #             wait = WebDriverWait(self.driver, 20)
    #             filter_button = wait.until(
    #                 EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and contains(., 'Filters')]"))
    #             )
    #             print("'Filters' button found. Clicking it...")
    #             filter_button.click()

    #             # 2. Click the "Advertiser" dropdown inside the filter panel to open the list
    #             advertiser_dropdown = wait.until(
    #                 # This selector targets the combobox for advertisers
    #                 EC.element_to_be_clickable((By.XPATH, "//div[@role='combobox' and .//text()='All advertisers']"))
    #             )
    #             print("'Advertiser' dropdown found. Clicking it...")
    #             advertiser_dropdown.click()
                
    #             # --- SCROLL AND SCRAPE LOGIC STARTS HERE ---

    #             # 3. Find the scrollable container that holds the options
    #             # This is often a div with role='listbox'. You may need to inspect the page to confirm.
    #             scrollable_container_locator = (By.XPATH, "//div[@role='listbox']")
    #             scrollable_container = wait.until(
    #                 EC.presence_of_element_located(scrollable_container_locator)
    #             )
    #             print("✅ Found the scrollable list container.")

    #             # Locator for the individual options inside the container
    #             all_options_locator = (By.XPATH, ".//div[@role='option']") # The '.' makes the search relative to the container
    #             list_data =  []
    #             # list_rows = []
    #             last_count = 0
    #             while True:
    #                 # Find all options currently loaded within the container
    #                 option_elements = scrollable_container.find_elements(*all_options_locator)
    #                 current_count = len(option_elements)

    #                 for i, option in enumerate(option_elements):
    #                 # Using .get_attribute('textContent') is often more reliable than .text for complex elements
    #                     option_id = option.get_attribute('id')
    #                     option_name = option.get_attribute('textContent').strip()
    #                     print(f"Index: {i}, ID: {option_id}, NAME: {option_name}")
    #                     list_data.append([option_id, option_name])
    #                     # list_cols.append(option_name)
    #                     time.sleep(0.5)

    #                 # list_rows.append(list_cols)
    #                 if current_count == last_count:
    #                     # If scrolling down didn't load any new options, we're done.
    #                     print("No new options loaded. Exiting scroll loop.")
    #                     break

    #                 last_count = current_count

    #                 # 4. Scroll the LAST visible element into view to trigger the loading of the next batch.
    #                 print("Scrolling down to load more...")
    #                 self.driver.execute_script("arguments[0].scrollIntoView(true);", option_elements[-1])

    #                 # 5. Wait a moment for new items to load into the HTML
    #                 time.sleep(2) # Adjust this if loading is slower or faster

                    
    #             # Keep the browser open for a few seconds to see the result
    #             # time.sleep(10)
    #             print(list_data)
    #             dim_keyword = pd.DataFrame(list_data, columns=["id", "name"])
    #             dim_keyword["keyword"] = self.keyword
    #             dim_keyword.drop_duplicates(inplace = True)
    #             dim_keyword.to_csv(f"dim_keyword_{self.keyword}.csv", index=False)

    #         except Exception as e:
    #             print(f"❌ An error occurred during the process: {e}")
    #         time.sleep(10)

    #         print("\nStep 2: Fetching ad elements...")

    #         # time.sleep(10)

    #         # Locate ad elements
    #         if self.should_stop():
    #             return
       
    #         # 2. Call the dedicated function to perform scrolling and scraping
    #         # self.ads_data = self._scroll_and_scrape_ads()         

    #         count = 0
    #         # print(len(ad_elements))

    #         # Convert to CSS selector
    #         css_selector = "." + self.ad_card_class.replace(" ", ".")

    #         # Find elements
    #         elements = self.driver.find_elements(By.CSS_SELECTOR, css_selector)
    #         # threshold = len(elements)

    #         for ad in elements:
    #             # Check cancellation before processing each ad
    #             if self.should_stop():
    #                 print(f"🛑 Crawl cancelled during ad processing (processed {count} ads)")
    #                 return
                
    #             ad_data = self.process_ad_element(ad)

    #             if ad_data:
    #                 count += 1
    #                 ad_data["ad_number"] = count
    #                 self.ads_data.append(ad_data)
    #                 print(f"Processed ad #{count}: {ad_data['library_id']}")
                

    #         print("--Finished processing ads. Total ads found:", len(self.ads_data))
            
    #         if not self.should_stop():
    #             self.lark_api.update_card_message(self.message_id, 
    #                                     card= domain_processing_card(search_word= self.keyword,
    #                                      progress_percent= 80),)
    #     except Exception as e:
    #         print(f"Error during crawl: {e}")
    #         if not self.should_stop():
    #             self.lark_api.reply_to_message(self.message_id, f"❌ Error during crawl: {str(e)}")
    #     # finally:
    #     #     if self.driver:
    #     #         self.driver.quit()
    #     #         self.driver = None

    def crawl(self):
        """Main method to execute the crawl following the required logic."""
        try:
            if not self.initialize_driver():
                return

            # 1) Get advertiser IDs for this keyword (load CSV if exists; otherwise scrape & save)
            dim_keyword = self.get_dim_keyword()
            dim_keyword["name_clean"] = dim_keyword["name"].str.split(" ").str[0].str.strip()  

            # 2) For each advertiser ID: open page, scroll all, scrape ads
            #    (If CSV already existed, we skip re-scraping the advertiser list and go straight here)
            list_name = dim_keyword["name_clean"].dropna().astype(str).unique().tolist()

            total_ids = len(list_name)

            print(total_ids, list_name)
            for idx, page_name in enumerate(list_name, start=1):
                if self.should_stop():
                    return

                # Slight progress feedback via your Lark card (optional)
                pct = int(10 + 60 * idx / max(1, total_ids))  # 10→70%
                try:
                    self.lark_api.update_card_message(
                        self.message_id,
                        card=domain_processing_card(search_word=self.keyword, progress_percent=pct)
                    )
                except Exception:
                    pass

                if not self.fetch_ads_page_by_id(page_name):
                    continue

                # Scroll to bottom for this advertiser page
                # self.scroll_to_bottom()

                # Scrape all ads present on this advertiser page
                self.scrape_current_page_ads()

            # 3) Convert to DataFrame, clean, de-dupe, and save once
            self.data_to_dataframe()

            try:
                self.lark_api.update_card_message(
                    self.message_id,
                    card=domain_processing_card(search_word=self.keyword, progress_percent=100)
                )
            except Exception:
                pass

        except Exception as e:
            print(f"Error during crawl: {e}")
            # if not self.should_stop():
                # self.lark_api.reply_to_message(self.message_id, f"❌ Error during crawl: {str(e)}")
                
        # (Optional) keep driver open for debugging; otherwise close it here.
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

    def data_to_dataframe(self):  
        """Convert collected ads data to a DataFrame"""
        if self.should_stop():
            # Return empty dataframe if cancelled
            self.df = pd.DataFrame()
            return
            
        print("\nStep 3: Converting ads data to DataFrame...")
        df = pd.DataFrame(self.ads_data)

        if df.empty:
            self.df = df
            return
        
        # print(df.to_excel("test.xlsx"))

        filter_conditions = (df["image_url"].notnull() & df["video_url"].notnull()) | (~df["image_url"].notnull() & ~df["video_url"].notnull())

        df_cleaned = df[~filter_conditions].reset_index(drop=True)

        df_cleaned["ad_url"] = df_cleaned["image_url"].fillna(df_cleaned["video_url"])
        df_cleaned["ad_type"] = df_cleaned["image_url"].notnull().replace({True: "image", False: "video"})
        df_cleaned["pixel_id"] = df_cleaned["pixel_id"].str.replace("%3D", "")

        final_columns = [
            "library_id",
            "ad_start_date",
            "company",
            "pixel_id",
            "destination_url",
            "ad_type",
            "ad_url",
            "thumbnail_url",
            "primary_text",     # 👈 now placed here
            "headline_text"     # 👈 now placed here
            ]

        # print(f"--DataFrame created with rows: {df_cleaned.shape[0]} columns:", final_columns)
        df_cleaned.drop_duplicates(subset = ["library_id", "company"], inplace = True)
        self.df = df_cleaned[final_columns]
        print(self.df.columns)
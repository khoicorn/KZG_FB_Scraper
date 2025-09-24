from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from lark_bot import LarkAPI
from lark_bot.state_managers import state_manager
from .interactive_card_library import *

import re
import pandas as pd
# from datetime import datetime
import time
import threading
import queue
# import requests

# import io
# from openpyxl import Workbook
# from openpyxl.drawing.image import Image as OpenPyxlImage
# from openpyxl.utils import get_column_letter
# from PIL import Image as PILImage

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
        """Optimized driver configuration"""
        if self.should_stop():
            return False
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')  # Reduce resource usage
        options.add_argument('--disable-extensions')  # Improve performance
        options.add_argument('--disable-infobars')
        options.add_argument('--single-process')  # Lightweight mode
        options.add_argument('--window-size=1920,1080')  # Smaller than 1920x1080

        # Optional: reduce detection
        # options.add_argument('--disable-blink-features=AutomationControlled')

        self.driver = webdriver.Chrome(options=options)
            # Block fonts, stylesheets, and other non-essential resources
        # This must be done AFTER the driver is initialized
        try:
            self.driver.execute_cdp_cmd(
                "Network.setBlockedURLs", {
                    "urls": [
                        "*.css", 
                        "*.woff", 
                        "*.woff2", 
                        "*google-analytics.com*", 
                        "*googletagmanager.com*",
                        "*doubleclick.net*"
                    ]
                }
            )
            self.driver.execute_cdp_cmd("Network.enable", {})
            print("✅ Network request blocking enabled.")
        except Exception as e:
            print(f"⚠️ Could not enable network blocking: {e}")

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
            
            print("Waiting up to 30 seconds for initial ads to load...")
            wait = WebDriverWait(self.driver, 30)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
            print("✅ Initial ads loaded.")
            return True
        except TimeoutException:
            print("❌ Timed out waiting for initial ads. The page may be empty or the selector is wrong.")
            return False
    
        # return True

    def scroll_to_bottom(self):
            """Optimized scrolling with reduced attempts"""
            if self.should_stop():
                return False
                
            self.lark_api.update_card_message(
                self.message_id, 
                card=domain_processing_card(
                    search_word=self.keyword,
                    progress_percent=10
                )
            )
            
            # last_height = self.driver.execute_script("return document.body.scrollHeight")
            # scroll_attempt = 0
            # max_attempts = 10  # Reduced from 10 to 6

            wait = WebDriverWait(self.driver, 10) # Timeout for each new scroll load
            retries = 3 # How many times to retry if the page stops loading
            
            while retries > 0:
                    if self.should_stop():
                        return False

                    last_height = self.driver.execute_script("return document.body.scrollHeight")
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    
                    try:
                        # Wait until the page height has actually increased
                        wait.until(
                            lambda driver: driver.execute_script("return document.body.scrollHeight") > last_height
                        )
                        retries = 3 # Reset retries if content loads
                    except TimeoutException:
                        retries -= 1
                        print(f"Page content did not load after a scroll. Retries left: {retries}")

            self.lark_api.update_card_message(
                self.message_id, 
                card=domain_processing_card(
                    search_word=self.keyword,
                    progress_percent=40
                )
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
        
    def crawl(self):
        """Main method to execute the crawl"""
        try:
            if not self.initialize_driver():
                return
                
            if not self.fetch_ads_page():
                return
                
            if not self.scroll_to_bottom():
                return

            print("\nStep 2: Fetching ad elements...")

            # time.sleep(10)

            # Locate ad elements
            if self.should_stop():
                return
                
            count = 0
            # print(len(ad_elements))

            # Convert to CSS selector
            css_selector = "." + self.ad_card_class.replace(" ", ".")

            # Find elements
            elements = self.driver.find_elements(By.CSS_SELECTOR, css_selector)
            # threshold = len(elements)

            for ad in elements:
                # Check cancellation before processing each ad
                if self.should_stop():
                    print(f"🛑 Crawl cancelled during ad processing (processed {count} ads)")
                    return
                
                ad_data = self.process_ad_element(ad)

                if ad_data:
                    count += 1
                    ad_data["ad_number"] = count
                    self.ads_data.append(ad_data)
                    print(f"Processed ad #{count}: {ad_data['library_id']}")
                

            print("--Finished processing ads. Total ads found:", len(self.ads_data))
            
            if not self.should_stop():
                self.lark_api.update_card_message(self.message_id, 
                                        card= domain_processing_card(search_word= self.keyword,
                                         progress_percent= 80),)
        except Exception as e:
            print(f"Error during crawl: {e}")
            if not self.should_stop():
                self.lark_api.reply_to_message(self.message_id, f"❌ Error during crawl: {str(e)}")
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
        self.df = df_cleaned[final_columns]
        print(self.df.columns)
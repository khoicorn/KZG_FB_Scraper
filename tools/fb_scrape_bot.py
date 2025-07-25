from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from lark_bot import LarkAPI
from lark_bot.state_managers import state_manager

import re
import pandas as pd
from datetime import datetime
import time
import threading
import queue

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
                crawler.lark_api.send_text(
                    crawler.chat_id,
                    f"⏳ You’re queued at spot #{position}. I’ll ping you when it starts."
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
                    crawler.lark_api.send_text(
                        chat_id,
                        f"📍 Current position in queue: #{i}"
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
                crawler.lark_api.send_text(
                    crawler.chat_id, 
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
    def __init__(self, keyword, chat_id):
        self.keyword = keyword
        self.ad_card_class = "x1plvlek xryxfnj x1gzqxud x178xt8z x1lun4ml xso031l xpilrb4 xb9moi8 xe76qn7 x21b0me x142aazg x1i5p2am x1whfx0g xr2y4jy x1ihp6rs x1kmqopl x13fuv20 x18b5jzi x1q0q8m5 x1t7ytsu x9f619"
        self.driver = None
        self.ads_data = []
        self.lark_api = LarkAPI()
        self.chat_id = chat_id
        self._stop_event = threading.Event()
        self.queue_manager = CrawlerQueue()  # Thêm dòng này

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
        """Initialize and configure the WebDriver"""
        if self.should_stop():
            return False
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        self.driver = webdriver.Chrome(options=options)
        self.driver.set_window_size(1920, 1080)
        return True
    
    def start(self):
        """Phương thức để bắt đầu crawl thông qua hàng đợi"""
        # Kiểm tra xem request đã có trong queue chưa
        position = self.queue_manager.get_queue_position(self.chat_id)
        
        if position is not None:
            if position == 0:
                self.lark_api.send_text(
                    self.chat_id,
                    "🔄 Your searchword is being processed..."
                )
            else:
                self.lark_api.send_text(
                    self.chat_id,
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
        
        time.sleep(5)

        # search_results = self.driver.find_elements(
        #     By.CSS_SELECTOR, ".x6s0dn4.x78zum5"
        # )
        # search_results = self.driver.find_elements(By.XPATH, "//*[contains(concat(' ', normalize-space(@class), ' '), ' x6s0dn4 ') and contains(concat(' ', normalize-space(@class), ' '), ' x78zum5 ') and @role='heading']")

        # # "and @role='heading'] 
        
        # if search_results:
        #     for search_result in search_results:
        #         text = search_result.text.lower()
        #         if "result" in search_result.text.lower():
        #             text = text.replace("results","").replace("result","").strip().replace("No results found","0")
        #             print(text)
        #             if int(text) == 0:
        #                 return False

        #         # print(f"Search result: {search_result.text}")
        # else:
        #     print("No results found")

        return True
        
    # def scroll_to_bottom(self):
    #     """Scroll to the bottom of the page to load all ads"""
    #     if self.should_stop():
    #         return False
            
    #     if not self.should_stop():
    #         self.lark_api.send_text(self.chat_id, "Start searching:\n🟩⬜⬜⬜⬜⬜⬜⬜⬜⬜ 10%")
        
    #     print("Step 1: Starting to scroll to the bottom of the page...")
    #     last_height = self.driver.execute_script("return document.body.scrollHeight")
        
    #     while True:
    #         if self.should_stop():
    #             return False
                
    #         self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    #         time.sleep(2)
            
    #         if self.should_stop():
    #             return False
                
    #         new_height = self.driver.execute_script("return document.body.scrollHeight")
    #         if new_height == last_height:
    #             print("--Reached the bottom of the page. All ads should be loaded!")
    #             break
    #         last_height = new_height
            
    #     time.sleep(8)
        
    #     if not self.should_stop():
    #         self.lark_api.send_text(self.chat_id, "🟩🟩🟩🟩⬜⬜⬜⬜⬜⬜ 40%")
        
    #     return True

    def scroll_to_bottom(self):
        """Scroll to the bottom of the page to load all ads with optimized waiting"""
        if self.should_stop():
            return False
            
        # Send initial progress message
        if not self.should_stop():
            self.lark_api.send_text(self.chat_id, "Start searching:\n🟩⬜⬜⬜⬜⬜⬜⬜⬜⬜ 10%")
        
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_attempt = 0
        max_attempts = 10  # Prevent infinite scrolling
        
        while scroll_attempt <= max_attempts:
            if self.should_stop():
                return False
                
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Use dynamic waiting instead of fixed sleep
            try:
                WebDriverWait(self.driver, 2).until(
                    lambda d: d.execute_script("return document.body.scrollHeight") > last_height
                )
            except TimeoutException:
                # No new content loaded within timeout
                print("-- Reached bottom of page")
                break
                
            # Check if we need to stop after waiting
            if self.should_stop():
                return False
                
            # Update height and attempt counter
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("-- Content height stabilized")
                break
                
            last_height = new_height
            scroll_attempt += 1
            print(f"-- New content loaded ({scroll_attempt}/{max_attempts})")
            
        # Final stabilization check
        try:
            WebDriverWait(self.driver, 3).until(
                lambda d: self._is_page_stabilized(d, last_height)
            )
        except TimeoutException:
            print("-- Page stabilization check timeout")
        
        if not self.should_stop():
            self.lark_api.send_text(self.chat_id, "🟩🟩🟩🟩⬜⬜⬜⬜⬜⬜ 40%")

        return True
    
    def _is_page_stabilized(self, driver, last_height):
        """Check if page height remains constant for 3 consecutive checks"""
        heights = []
        for _ in range(3):
            heights.append(driver.execute_script("return document.body.scrollHeight"))
            time.sleep(0.5)  # Short interval between checks
        
        return all(h == heights[0] for h in heights) and heights[0] == last_height
        
    def extract_library_id(self, text):
        """Extract Library ID from ad text"""
        match = re.search(r'Library ID:\s*(\d+)', text)
        return match.group(1) if match else None
        
    def extract_date(self, text):
        """Extract date from ad text"""
        match = re.search(r'\b\d{1,2}\s\w{3}\s\d{4}\b', text)
        return match.group() if match else None
        
    def process_ad_element(self, ad_element):
        """Extract data from a single ad element"""
        if self.should_stop():
            return None
            
        try:
            text = ad_element.text
            if "Library ID" not in text:
                return None
                
            ad_data = {
                "text_snippet": text[:100].replace("\n", " ") + "...",
                "library_id": self.extract_library_id(text),
                "ad_start_date": self.extract_date(text),
                **self._extract_media(ad_element),
                **self._extract_links(ad_element)
            }
            return ad_data
            
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
            "video_url": None
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
                    
            # Process video
            if not self.should_stop():
                try:
                    video_tag = ad_element.find_element(By.TAG_NAME, "video")
                    media_data["video_url"] = video_tag.get_attribute("src")
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

            # Locate ad elements
            if self.should_stop():
                return
                
            count = 0
            # ad_elements = self.driver.find_elements(By.CLASS_NAME, self.ad_card_class)
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
                self.lark_api.send_text(self.chat_id, "🟩🟩🟩🟩🟩🟩🟩🟩⬜⬜ 80%")
       
        except Exception as e:
            print(f"Error during crawl: {e}")
            if not self.should_stop():
                self.lark_api.send_text(self.chat_id, f"❌ Error during crawl: {str(e)}")
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
            "ad_url"]

        print(f"--DataFrame created with rows: {df_cleaned.shape[0]} columns:", final_columns)
        self.df = df_cleaned[final_columns]
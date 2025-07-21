from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from lark_bot import LarkAPI
from lark_bot.state_managers import state_manager
import tempfile

import re
import pandas as pd
from datetime import datetime
import time
import threading

class FacebookAdsCrawler:
    def __init__(self, keyword, chat_id):
        self.keyword = keyword
        self.ad_card_class = "xh8yej3"
        self.driver = None
        self.ads_data = []
        self.lark_api = LarkAPI()
        self.chat_id = chat_id
        self._stop_event = threading.Event()

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

    # 🔑 Tạo thư mục tạm để Chrome dùng làm user profile mỗi lần
        user_data_dir = tempfile.mkdtemp()
        options.add_argument(f'--user-data-dir={user_data_dir}')

        self.driver = webdriver.Chrome(options=options)
        self.driver.set_window_size(1920, 1080)
        return True
        
    def fetch_ads_page(self):
        """Load the Facebook Ads Library page"""
        if self.should_stop():
            return False
        url = (f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&"
               f"is_targeted_country=false&media_type=all&q={self.keyword}&search_type=keyword_unordered")
        self.driver.get(url)
        time.sleep(5)
        return True
        
    def scroll_to_bottom(self):
        """Scroll to the bottom of the page to load all ads"""
        if self.should_stop():
            return False
            
        if not self.should_stop():
            self.lark_api.send_text(self.chat_id, "🟩⬜⬜⬜⬜⬜⬜⬜⬜⬜ 10%")
        
        print("Step 1: Starting to scroll to the bottom of the page...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while True:
            if self.should_stop():
                return False
                
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            if self.should_stop():
                return False
                
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("--Reached the bottom of the page. All ads should be loaded!")
                break
            last_height = new_height
            
        time.sleep(8)
        
        if not self.should_stop():
            self.lark_api.send_text(self.chat_id, "🟩🟩🟩🟩⬜⬜⬜⬜⬜⬜ 40%")
        
        return True
        
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
                    media_data["video_url"] = video_tag.get_attribute("poster")
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
            ad_elements = self.driver.find_elements(By.CLASS_NAME, self.ad_card_class)
            
            for ad in ad_elements:
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
import os
import time
import random
import sqlite3
import glob
import csv
import requests
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Import existing functions from your codebase
from fb_postListings import get_driver, handle_redirect_warning

class FacebookMarketplaceResponder:
    def __init__(self, database_path=None, debug=False):
        """
        Initialize the Facebook Marketplace auto-responder.
        
        Args:
            database_path: Path to the SQLite database (optional)
            debug: Enable debug logging
        """
        self.driver = get_driver()
        self.database_path = database_path
        self.debug = debug
        
        # Response templates
        self.responses = [
            "Hey I'm actually listing this on a rental app called Yoodlize! Reach out to me there! https://www.yoodlize.com/details/{listing_id}",
            "Thanks for your interest! Check it out on Yoodlize: https://www.yoodlize.com/details/{listing_id}",
            "Hi! Please contact me through Yoodlize instead: https://www.yoodlize.com/details/{listing_id}",
            "For a better rental experience, I've listed this item on Yoodlize: https://www.yoodlize.com/details/{listing_id}"
        ]
    
    def go_to_marketplace_messages(self):
        """Navigate to Facebook Marketplace messages inbox."""
        print("[🔍] Opening Facebook Marketplace messages...")
        try:
            self.driver.get("https://www.facebook.com/marketplace/inbox?targetTab=SELLER")
            return True
        except Exception as e:
            print(f"[❌] Error navigating to messages: {e}")
            return False
    
    def scroll_to_load_more_threads(self, scroll_count=3):
        """Scroll down to load more message threads."""
        print(f"[🔄] Scrolling to load more threads ({scroll_count} times)...")
        
        try:
            # Find the scrollable container
            main_content = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='main']"))
            )
            
            # Get initial thread count
            initial_threads = len(self.driver.find_elements(
              By.XPATH, "//div[@role='button'][.//img or .//*[name()='svg']//*[name()='image']]"


            ))
            
            # Scroll down multiple times
            for i in range(scroll_count):
                # Execute scroll
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", main_content)
                
                # Wait for content to load
                time.sleep(2)
                
                # Get new count
                new_threads = len(self.driver.find_elements(
                    By.XPATH, "//div[@role='button'][.//img or .//*[name()='svg']//*[name()='image']]"

                ))
                
                if self.debug:
                    print(f"[📊] Scroll {i+1}: Found {new_threads} threads (was {initial_threads})")
                
                # If no new threads were loaded, break early
                if new_threads <= initial_threads and i > 0:
                    break
                    
                initial_threads = new_threads
                
            return True
            
        except Exception as e:
            print(f"[❌] Error scrolling for more threads: {e}")
            return False

    def find_unread_messages(self):
        """Find and return all unread message threads."""
        print("[🔍] Looking for unread messages...")
        unread_threads = []
        
        try:
            # Wait for the messages to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='main']"))
            )
            
            # First, scroll to load more threads
            self.scroll_to_load_more_threads(scroll_count=5)
            
            # Find all conversation threads - use a selector that matches active threads with image tags
            threads = self.driver.find_elements(
                By.XPATH, 
                "//div[@role='button'][.//img or .//*[name()='svg']//*[name()='image']]"

            )
            
            if self.debug:
                print(f"[💬] Found {len(threads)} total message threads")
            
            # Process all threads and check if they're unread
            for thread in threads:
                print(f"[🔍] Checking thread: {thread.text}")
                try:
                    # Fixed: Use proper CSS selector syntax with dot prefix for class name
                    class_script = """
                        // Look for the specific unread class
                        const elements = arguments[0].querySelectorAll('.xwnonoy');
                        return elements.length > 0;
                    """
                    has_unread_class = self.driver.execute_script(class_script, thread)
                    
                    # Existing methods as fallback
                    has_blue_dot = False
                    has_bold_text = False
                    
                    # Only run these checks if the class check didn't find anything
                    if not has_unread_class:
                        # Method 1: Look for blue dot
                        script = """
                            const elements = arguments[0].querySelectorAll('div');
                            for (const el of elements) {
                                // Skip elements with no dimensions
                                if (el.offsetWidth === 0 || el.offsetHeight === 0) continue;
                                
                                // Get the computed style
                                const style = window.getComputedStyle(el);
                                const bgColor = style.backgroundColor;
                                
                                // Facebook's unread color is #0866ff which is rgb(8, 102, 255)
                                if (bgColor === 'rgb(8, 102, 255)' || 
                                    bgColor === '#0866ff' ||
                                    bgColor === 'rgb(24, 119, 242)' || 
                                    bgColor === 'rgb(22, 111, 229)' || 
                                    bgColor === 'rgb(0, 132, 255)') {
                                    
                                    // For small dot-like elements, this is definitely an unread indicator
                                    if (el.offsetWidth < 12 && el.offsetHeight < 12) {
                                        return true;
                                    }
                                }
                            }
                            return false;
                        """
                        has_blue_dot = self.driver.execute_script(script, thread)
                        
                        # Method 2: Check for bold text
                        bold_script = """
                            const textElements = arguments[0].querySelectorAll('span');
                            for (const el of textElements) {
                                const style = window.getComputedStyle(el);
                                // Font weights 600+ are definitely bold
                                if (parseInt(style.fontWeight) >= 600) {
                                    return true;
                                }
                            }
                            return false;
                        """
                        has_bold_text = self.driver.execute_script(bold_script, thread)
                    
                    if has_unread_class or has_blue_dot or has_bold_text:
                        unread_threads.append(thread)
                        if self.debug:
                            thread_text = thread.text.replace('\n', ' ')[:30]
                            print(f"[💬] Found unread thread: {thread_text}...")
                            if has_unread_class:
                                print("   - Detected via unread class (xwnonoy)")
                            if has_blue_dot:
                                print("   - Detected via blue dot")
                            if has_bold_text:
                                print("   - Detected via bold text")
                
                except Exception as e:
                    if self.debug:
                        print(f"[⚠️] Error checking thread: {e}")
        except Exception as e:
          print(f"[❌] Error finding unread messages: {e}")
          return []
        
        print(f"[💬] Found {len(unread_threads)} unread message threads")
        return unread_threads
        
    def open_thread_and_extract_info(self, thread):
        """Open a message thread and extract listing information."""
        try:
            # Click on the thread to open it
            self.driver.execute_script("arguments[0].click();", thread)
            time.sleep(2)  # Wait for thread to open fully
            
            # Extract listing info
            listing_info = {}
            
            # Find the marketplace listing section by looking for the span containing "Marketplace"
            marketplace_sections = self.driver.find_elements(
                By.XPATH,
                "//div[.//span[contains(text(), 'Marketplace')]]"
            )
            
            if marketplace_sections:
                # Find the marketplace section with the listing title
                for section in marketplace_sections:
                    try:
                        # Extract title directly from the section (looks for text after price)
                        title_spans = section.find_elements(
                            By.XPATH,
                            ".//span[contains(text(), '$') and contains(text(), 'Rent a')]"
                        )
                        
                        if title_spans:
                            full_text = title_spans[0].text
                            
                            # Extract price and title from the text (format: "$10 - Rent a Golf club set for men")
                            if '-' in full_text:
                                parts = full_text.split('-', 1)
                                price = parts[0].strip()
                                title = parts[1].strip()
                            else:
                                # If there's no dash, assume everything after $ and space is the title
                                price_end = full_text.find('$') + full_text[full_text.find('$'):].find(' ')
                                title = full_text[price_end:].strip()
                            
                            # Clean up title - remove "Rent a" prefix if present
                            if title.lower().startswith("rent a "):
                                title = title[7:]
                            
                            listing_info["title"] = title
                            listing_info["price"] = price
                            
                            if self.debug:
                                print(f"[📦] Extracted title: {title}")
                            
                            break
                    except Exception as e:
                        if self.debug:
                            print(f"[⚠️] Error extracting from section: {e}")
                        continue
            
            # If we didn't find the title in the sections, try an alternative approach
            if not listing_info.get("title"):
                # Look for any span with the listing title format
                title_elements = self.driver.find_elements(
                    By.XPATH,
                    "//span[contains(text(), 'Rent a')]"
                )
                
                if title_elements:
                    title = title_elements[0].text
                    # Clean up title - remove "Rent a" prefix if present
                    if title.lower().startswith("rent a "):
                        title = title[7:]
                    listing_info["title"] = title
            
            # Try to extract location/city if available
            try:
                location_elements = self.driver.find_elements(
                    By.XPATH, 
                    "//span[contains(text(), ',') and contains(@dir, 'auto')]"
                )
                if location_elements:
                    location = location_elements[0].text.strip()
                    # Extract city from "City, State"
                    if "," in location:
                        listing_info["city"] = location.split(",")[0].strip()
                    else:
                        listing_info["city"] = location
            except:
                listing_info["city"] = ""
            
            # If we found the listing info, return it
            if listing_info.get("title"):
                if self.debug:
                    print(f"[📦] Extracted listing info: {listing_info}")
                return listing_info
            else:
                print("[⚠️] No marketplace listing found in this conversation")
                return None
                
        except Exception as e:
            print(f"[❌] Error extracting listing info: {e}")
            return None
    
    def find_listing_id_in_database(self, title, city=None):
        """Query the database to find the listing ID based on title and city."""
        if not self.database_path:
            return None
        
        try:
            print(f"[🔍] Searching database for listing: '{title}' in {city or 'any city'}")
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Prepare the query
            query = "SELECT id FROM listings WHERE title LIKE ? "
            params = [f"%{title}%"]
            
            # Add city filter if provided
            if city:
                query += "AND city = ? "
                params.append(city)
            
            query += "ORDER BY created_at DESC LIMIT 1"
            
            # Execute the query
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            conn.close()
            
            if result:
                listing_id = result[0]
                print(f"[✅] Found listing ID in database: {listing_id}")
                return listing_id
            else:
                print("[⚠️] No matching listing found in database")
                return None
                
        except Exception as e:
            print(f"[❌] Database error: {e}")
            return None
    
    def find_listing_id_in_csv_files(self, title):
        """Search through CSV files to find a listing ID based on title."""
        print(f"[🔍] Searching CSV files for listing: '{title}'")
        
        try:
            # Get all data directories in reverse chronological order
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dirs = sorted(glob.glob(os.path.join(base_dir, "data_*")), reverse=True)
            
            for data_dir in data_dirs:
                csv_files = glob.glob(os.path.join(data_dir, "listings_*.csv"))
                
                for csv_file in csv_files:
                    if self.debug:
                        print(f"[🔍] Checking {csv_file}")
                    
                    try:
                        with open(csv_file, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            
                            for row in reader:
                                row_title = row.get('title', '')
                                
                                # Clean up title for comparison
                                if row_title.lower().startswith("rent a "):
                                    row_title = row_title[7:].strip()
                                
                                # Check for a match
                                if (title.lower() in row_title.lower() or 
                                    row_title.lower() in title.lower()):
                                    listing_id = row.get('id')
                                    if listing_id:
                                        print(f"[✅] Found listing ID in {csv_file}: {listing_id}")
                                        return listing_id
                    except Exception as e:
                        if self.debug:
                            print(f"[⚠️] Error reading {csv_file}: {e}")
            
            print("[⚠️] No matching listing found in CSV files")
            return None
            
        except Exception as e:
            print(f"[❌] Error searching CSV files: {e}")
            return None
    
    def find_listing_id_using_api(self, title, city=None):
        """Query the Yoodlize GraphQL API to find the listing ID."""
        try:
            print(f"[🔍] Querying API for listing: '{title}' in {city or 'any city'}")
            
            # Build GraphQL query
            graphql_query = """
            query FindListing {
                listing(
                    where: {
                        is_published: {_eq: true},
                        title: {_ilike: "%TITLE_PLACEHOLDER%"}
                    },
                    order_by: {created_at: desc},
                    limit: 1
                ) {
                    id
                    title
                }
            }
            """.replace("TITLE_PLACEHOLDER", title)
            
            # Add city filter if available
            if city:
                graphql_query = graphql_query.replace(
                    "title: {_ilike: \"%TITLE_PLACEHOLDER%\"}",
                    "title: {_ilike: \"%TITLE_PLACEHOLDER%\"}, listing_addresses: {user_address: {city: {_ilike: \"%CITY_PLACEHOLDER%\"}}}"
                ).replace("CITY_PLACEHOLDER", city)
            
            # Make API request
            response = requests.post(
                "https://yoodlize-hasura.herokuapp.com/v1/graphql",
                headers={"Content-Type": "application/json"},
                json={"query": graphql_query}
            )
            
            if response.status_code == 200:
                data = response.json()
                listings = data.get("data", {}).get("listing", [])
                
                if listings:
                    listing_id = listings[0].get("id")
                    print(f"[✅] Found listing ID via API: {listing_id}")
                    return listing_id
                else:
                    print("[⚠️] No matching listing found via API")
                    return None
            else:
                print(f"[❌] API request failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"[❌] API error: {e}")
            return None
    
    def send_reply(self, listing_id):
        """Send a reply message with the Yoodlize link."""
        try:
            # Select a random response template
            response = random.choice(self.responses).format(listing_id=listing_id)
            print(f"[✉️] Sending reply: {response}")
            
            # Find the message input field
            input_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.XPATH, 
                    "//div[@role='textbox' or @contenteditable='true']"
                ))
            )
            
            # Type message
            input_field.clear()
            input_field.send_keys(response)
            time.sleep(1)
            
            # Find and click the send button
            send_button = self.driver.find_element(By.XPATH, "//div[@aria-label='Press enter to send']")
            send_button.click()
            
            # Wait for message to send
            print("[✅] Reply sent successfully")
            return True
            
        except Exception as e:
            print(f"[❌] Error sending reply: {e}")
            return False
    
    def process_unread_messages(self):
        """Process all unread messages and send Yoodlize links."""
        print("[🔄] Starting to process unread messages...")
        
        # Navigate to messages inbox
        if not self.go_to_marketplace_messages():
            return 0
        
        # Find all unread threads
        unread_threads = self.find_unread_messages()
        if not unread_threads:
            print("[ℹ️] No unread messages to process")
            return 0
        
        processed_count = 0
        
        for thread in unread_threads:
            try:
                # Open the thread and extract listing info
                listing_info = self.open_thread_and_extract_info(thread)
                
                if not listing_info:
                    print("[⚠️] Could not extract listing info, skipping")
                    continue
                
                title = listing_info.get("title")
                city = listing_info.get("city")
                
                # Try to find the listing ID
                listing_id = None
                
                # Method 1: Database lookup
                if self.database_path:
                    listing_id = self.find_listing_id_in_database(title, city)
                
                # Method 2: API lookup
                if not listing_id:
                    listing_id = self.find_listing_id_using_api(title, city)
                
                # Method 3: CSV lookup
                if not listing_id:
                    listing_id = self.find_listing_id_in_csv_files(title)
                
                # If we found a listing ID, send a reply
                if listing_id:
                    if self.send_reply(listing_id):
                        processed_count += 1
                else:
                    print(f"[❌] Could not find listing ID for '{title}'")
                
                # Go back to inbox
                self.go_to_marketplace_messages()
                
            except Exception as e:
                print(f"[❌] Error processing thread: {e}")
                # Try to recover
                self.go_to_marketplace_messages()
        
        print(f"[📊] Successfully processed {processed_count} out of {len(unread_threads)} messages")
        return processed_count
    
    def run(self):
        """Run the auto-responder."""
        try:
            print("[🚀] Starting Facebook Marketplace Auto-Responder")
            processed = self.process_unread_messages()
            
            if processed > 0:
                print(f"[🎉] Successfully replied to {processed} messages")
            else:
                print("[ℹ️] No messages were processed")
                
            return processed
            
        except Exception as e:
            print(f"[❌] An error occurred: {e}")
            return 0
        
        finally:
            print("[👋] Completing Facebook Marketplace message processing")
            # Don't close the browser - let the calling code decide

def main():
    """Run the auto-responder as a standalone script."""
    print("="*60)
    print("📱 Facebook Marketplace Auto-Responder")
    print("="*60)
    
    # Default database path - modify as needed
    default_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "listings.db")
    
    # Check if database exists, otherwise set to None
    db_path = default_db_path if os.path.exists(default_db_path) else None
    
    # Create and run the auto-responder
    responder = FacebookMarketplaceResponder(database_path=db_path, debug=True)
    
    try:
        responder.run()
    finally:
        # Ask before closing
        # input("\n[🏁] Press Enter to close the browser and exit...")
        try:
            responder.driver.quit()
        except:
            pass
        print("[👋] Goodbye!")

if __name__ == "__main__":
    main()
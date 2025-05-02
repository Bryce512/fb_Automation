import os
import time
import csv
import re
import glob
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Import functions from existing scripts
from fb_postListings import get_driver, post_listing, reset_browser_state, handle_redirect_warning

def get_listing_date(date_text):
    """
    Convert Facebook date text to datetime object.
    Handles formats like:
    - "Listed on 4/28"
    - "Listed on 09/02/2024"
    """
    now = datetime.now()
    
    if not date_text:
        print("[⚠️] Empty date text")
        return now
    
    # Clean up the date text - extract only the date part
    date_text = date_text.strip()
    if "Listed on" in date_text:
        date_text = date_text.replace("Listed on", "").strip()
    
    print(f"[🔍] Parsing date: '{date_text}'")
    
    # Try to parse as MM/DD/YYYY format
    if re.match(r'\d{1,2}/\d{1,2}/\d{4}', date_text):
        try:
            return datetime.strptime(date_text, "%m/%d/%Y")
        except ValueError:
            print(f"[⚠️] Failed to parse full date: {date_text}")
    
    # Try to parse as MM/DD format
    if re.match(r'\d{1,2}/\d{1,2}', date_text):
        try:
            month, day = map(int, date_text.split('/'))
            year = now.year
            
            # Create a date with the current year
            listing_date = datetime(year, month, day)
            
            # If the resulting date is in the future, it's probably from last year
            if listing_date > now:
                listing_date = datetime(year - 1, month, day)
            
            return listing_date
        except ValueError as e:
            print(f"[⚠️] Failed to parse MM/DD date: {date_text} - {e}")
    
    # Try to parse as month name and day (e.g. "April 15")
    try:
        # Add current year as Facebook doesn't show it
        date_with_year = f"{date_text}, {now.year}"
        date_obj = datetime.strptime(date_with_year, "%B %d, %Y")
        
        # If the resulting date is in the future, it's probably from last year
        if date_obj > now:
            date_obj = datetime(now.year - 1, date_obj.month, date_obj.day)
        
        return date_obj
    except ValueError:
        print(f"[⚠️] Could not parse date: {date_text}")
        # If all else fails, assume it's recent
        return now
        
def find_old_listings(driver, weeks_threshold=2, debug=False):
    """
    Find listings older than the specified number of weeks.
    Returns a list of tuples: (listing_title, listing_element, listing_date)
    """
    print(f"[🔍] Finding listings older than {weeks_threshold} weeks...")
    
    # Navigate to selling page
    driver.get("https://www.facebook.com/marketplace/you/selling")
    time.sleep(3)  # Wait for page to load
    
    # Handle any redirect warnings
    handle_redirect_warning(driver, debug)
    
    # Scroll down to load more listings
    # for _ in range(5):  # Scroll 5 times
    #     driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    #     time.sleep(2)
    
    listing_cards = []
    # Find all listings
    cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'html-div')]")
    for card in cards:
        # First check if this element actually contains a listing
        if not card.text or "Listed on" not in card.text:
            continue
        else:
            listing_cards.append(card)
    
    if debug:
        print(f"[💡] Found {len(listing_cards)} total listings")
    
    # Extract listing information
    old_listings = []
    cutoff_date = datetime.now() - timedelta(weeks=weeks_threshold)
    
    for card in listing_cards:
        try:
            full_card_text = card.text.strip()
            lines = full_card_text.splitlines()

            if not lines:
                print("[⚠️] Skipping empty listing card")
                continue

            title = re.search(r'Rent a ([^\n]+)', full_card_text)
            if title:
                title = title.group(1).strip()
                if debug:
                    print(f"[📌] Extracted title: {title}")
            else:
                print(f"[⚠️] Could not find title in card: {full_card_text}")
                continue


            # Try to extract 'Listed on <date>' from full text
            match = re.search(r'Listed on ([^\n]+)', full_card_text)
            if match:
                date_text = match.group(1).strip()
                if debug:
                    print(f"[📅] Extracted date text: '{date_text}'")
                
                listing_date = get_listing_date(date_text)

                # Check if the listing is old
                if listing_date < cutoff_date:
                    old_listings.append((title, card, listing_date))
                    if debug:
                        print(f"[📅] Found old listing: {title} ({listing_date.strftime('%Y-%m-%d')})")
            else:
                print(f"[⚠️] Could not find 'Listed on' date in card: {title}")

        except Exception as e:
            if debug:
                print(f"[⚠️] Error processing a listing: {e}")
    
    print(f"[📊] Found {len(old_listings)} listings older than {weeks_threshold} weeks")
    return old_listings

def delete_listing(driver, listing_tuple, debug=False):
    """Delete a listing from Facebook Marketplace using the card we already have."""
    title, listing_element, _ = listing_tuple
    print(f"[🗑️] Deleting listing: {title}")
    
    try:
        # APPROACH 1: First try to find the menu button within the card
        try:
            menu_button = listing_element.find_element(By.XPATH, 
                ".//div[contains(@aria-label, 'More options') or contains(@aria-label, 'More')]")
            
            if debug:
                print(f"[✅] Found menu button directly in card for: {title}")
            
            # Click the menu button
            driver.execute_script("arguments[0].click();", menu_button)
            time.sleep(1)
        except:
            # APPROACH 2: If menu button not found directly, find it using title
            if debug:
                print(f"[ℹ️] Menu button not found directly in card, trying by title: {title}")
            
            # Look for the menu button that specifically mentions this listing's title
            title_safe = title.replace("'", "\\'").replace('"', '\\"')
            menu_xpath = f"//div[contains(@aria-label, 'More options for Rent a {title_safe}') or contains(@aria-label, 'More actions for Rent a {title_safe}')]"
            
            menu_buttons = driver.find_elements(By.XPATH, menu_xpath)
            
            if menu_buttons:
                if debug:
                    print(f"[✅] Found menu button by title match for: {title}")
                driver.execute_script("arguments[0].click();", menu_buttons[0])
                time.sleep(1)
            else:
                # APPROACH 3: Last resort - click the card first, then find menu
                if debug:
                    print(f"[ℹ️] Menu button not found by title, clicking the card first: {title}")
                
                # Find an <a> element or role="button" in the card to click
                try:
                    clickable = listing_element.find_element(By.TAG_NAME, "a")
                    driver.execute_script("arguments[0].click();", clickable)
                    time.sleep(1.5)  # Give time for the listing detail to load
                    
                    # Now look for menu button in the detailed view
                    menu_buttons = driver.find_elements(By.XPATH, "//div[contains(@aria-label, 'More')]")
                    if menu_buttons:
                        if debug:
                            print(f"[✅] Found menu button after clicking into listing: {title}")
                        driver.execute_script("arguments[0].click();", menu_buttons[0])
                        time.sleep(1)
                    else:
                        raise Exception("Menu button not found after clicking listing")
                except Exception as e:
                    print(f"[❌] All attempts to find menu button failed: {e}")
                    driver.get("https://www.facebook.com/marketplace/you/selling")
                    time.sleep(1)
                    return False
        
        # Now that we've clicked the menu button, look for Delete option
        delete_options = driver.find_elements(By.XPATH, "//span[contains(text(), 'Delete listing')]")
        if not delete_options:
            delete_options = driver.find_elements(By.XPATH, "//span[contains(text(), 'Delete')]")
        
        if delete_options:
            driver.execute_script("arguments[0].click();", delete_options[0])
            time.sleep(1)
            
            # Find confirm delete button using multiple approaches
            print(f"[🔍] Looking for confirm delete button for: {title}")
            
            # APPROACH 1: Find the button that contains the Delete text 
            confirm_buttons = driver.find_elements(By.XPATH, "//div[@role='button']//span[contains(text(), 'Delete')]/ancestor::div[@role='button']")
            
            # APPROACH 2: If not found, look for any button with Delete text
            if not confirm_buttons:
                confirm_buttons = driver.find_elements(By.XPATH, "//button//span[contains(text(), 'Delete')]/parent::button")
            
            # APPROACH 3: Look for buttons in any dialogs
            if not confirm_buttons:
                confirm_buttons = driver.find_elements(By.XPATH, "//div[@role='dialog']//div[@role='button']//span[contains(text(), 'Delete')]/ancestor::div[@role='button']")
            
            if confirm_buttons:
                print(f"[🗑️] Confirming deletion for: {title}")
                
                # First make sure the dialog has focus
                driver.execute_script("arguments[0].focus();", confirm_buttons[0])
                # time.sleep(0.5)
                
                # Try multiple click methods
                try:
                    # Method 1: JavaScript click
                    driver.execute_script("arguments[0].click();", confirm_buttons[0])
                    
                    # Method 2: If JS click doesn't work, try ActionChains
                    # from selenium.webdriver.common.action_chains import ActionChains
                    # actions = ActionChains(driver)
                    # actions.move_to_element(confirm_buttons[0])
                    # actions.click()
                    # actions.perform()
                    
                    print(f"[✅] Successfully deleted: {title}")
                    time.sleep(2)  # Wait for deletion to complete
                    return True
                except Exception as e:
                    print(f"[⚠️] Error clicking confirm button: {e}")
                    # As a last resort, try sending Enter key
                    from selenium.webdriver.common.keys import Keys
                    confirm_buttons[0].send_keys(Keys.ENTER)
                    time.sleep(2)
                    print(f"[✅] Attempted deletion using Enter key: {title}")
                    return True
            else:
                print(f"[❌] Could not find confirm delete button for: {title}")
        
        # Go back to selling page
        driver.get("https://www.facebook.com/marketplace/you/selling")
        time.sleep(1)
        return False
        
    except Exception as e:
        print(f"[❌] Error deleting listing {title}: {e}")
        # Try to go back to selling page
        driver.get("https://www.facebook.com/marketplace/you/selling")
        time.sleep(1)
        return False

def find_csv_data_for_listing(title, listing_date=None, debug=False):
    """
    Find the CSV data for a listing based on its title and date.
    
    Args:
        title: The listing title to search for
        listing_date: The datetime when the listing was created
        debug: Whether to print debug information
    
    Returns:
        The CSV row data for the listing, or None if not found
    """
    # Normalize the title for comparison
    normalized_title = title.lower().replace("rent a ", "").strip()
    
    if debug:
        print(f"[🔍] Looking for CSV data for listing: {title}")
        print(f"[🔍] Normalized title: {normalized_title}")
    
    # First, try to find the CSV file based on listing date
    if listing_date:
        # The CSV file is typically created the day before the listing is posted
        csv_date = listing_date - timedelta(days=1)
        
        # Get the directory and filename patterns
        data_dir_pattern = f"data_{csv_date.strftime('%Y-%m-%d')}"
        csv_file_pattern = f"listings_{csv_date.strftime('%Y-%m-%d')}.csv"
        
        # Full path to the expected CSV file
        expected_csv_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            data_dir_pattern, 
            csv_file_pattern
        )
        
        if debug:
            print(f"[🔍] Looking for CSV from date: {csv_date.strftime('%Y-%m-%d')}")
            print(f"[🔍] Expected CSV path: {expected_csv_path}")
        
        # Check if this specific file exists
        if os.path.exists(expected_csv_path):
            if debug:
                print(f"[✅] Found date-matched CSV: {expected_csv_path}")
            
            try:
                with open(expected_csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row_title = row.get('title', '')
                        row_normalized = row_title.lower().replace("rent a ", "").strip()
                        
                        # Check for title match
                        if normalized_title == row_normalized or normalized_title in row_normalized or row_normalized in normalized_title:
                            if debug:
                                print(f"[✅] Found exact match in date-specific CSV for: {title}")
                            return row
            except Exception as e:
                if debug:
                    print(f"[⚠️] Error reading date-matched CSV: {e}")
    
    # If we didn't find a match based on date or date wasn't provided, 
    # fall back to the original approach of searching all CSVs
    if debug:
        print(f"[ℹ️] No date match found, searching all CSVs...")
    
    # Get all data directories (newest first)
    data_dirs = sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_*")), reverse=True)
    
    for data_dir in data_dirs:
        # Find CSV files in the directory
        csv_files = glob.glob(os.path.join(data_dir, "listings_*.csv"))
        
        for csv_file in csv_files:
            if debug:
                print(f"[🔍] Searching in {csv_file}")
                
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row_title = row.get('title', '')
                        row_normalized = row_title.lower().replace("rent a ", "").strip()
                        
                        # Use fuzzy matching for title comparison
                        if normalized_title == row_normalized or normalized_title in row_normalized or row_normalized in normalized_title:
                            if debug:
                                print(f"[✅] Found matching CSV data in {csv_file} for: {title}")
                            return row
            except Exception as e:
                if debug:
                    print(f"[⚠️] Error reading {csv_file}: {e}")
    
    print(f"[❌] Could not find CSV data for: {title}")
    return None

def delete_and_repost(driver, weeks_threshold=2, debug=False):
    """Delete listings older than the threshold and repost them."""
    # Find old listings
    old_listings = find_old_listings(driver, weeks_threshold, debug)
    
    if not old_listings:
        print("[ℹ️] No old listings to delete and repost.")
        return 0
    
    # Ask for confirmation
    print(f"\n[❓] Found {len(old_listings)} listings older than {weeks_threshold} weeks to delete and repost.")
    # print("[❓] Continue with deletion and reposting? (y/n)")
    # if input("> ").lower() != "y":
    #     print("[🛑] Operation cancelled by user")
    #     return 0
    
    reposted_count = 0
    for title, element, date in old_listings:
        # Delete the listing
        if delete_listing(driver, (title, element, date), debug):
            # Find corresponding CSV data using the listing date
            csv_data = find_csv_data_for_listing(title, listing_date=date, debug=debug)
            
            if csv_data:
                print(f"[🔄] Reposting: {title}")
                
                # Reset browser state before posting
                reset_browser_state(driver)
                
                # Post the listing with same data
                success = post_listing(
                    driver,
                    title=csv_data.get('title', ''),
                    price=csv_data.get('price', ''),
                    description=csv_data.get('description', ''),
                    location=csv_data.get('location'),
                    images=csv_data.get('images')
                )
                
                if success:
                    print(f"[✅] Successfully reposted: {title}")
                    reposted_count += 1
                else:
                    print(f"[❌] Failed to repost: {title}")
            else:
                print(f"[⚠️] Could not repost {title} - no CSV data found")
        
        # Reset browser state between operations
        reset_browser_state(driver)
    
    return reposted_count

def main():
    print("="*60)
    print("📦 Facebook Marketplace Old Listing Delete & Repost")
    print("="*60)
    print("\nThis tool automatically deletes listings older than 2 weeks and reposts them.")
    
    global weeks_threshold, debug_mode
    weeks_threshold = 2  # Default threshold in weeks
    debug_mode = True  # Default debug mode

    try:
        # Initialize driver with login check
        print("\n[🌐] Initializing browser and checking login status...")
        driver = get_driver()
        
        # Ask for threshold in weeks
        # print("\n[❓] How many weeks old should listings be to delete and repost? (default: 2)")
        # weeks_input = input("> ")
        # weeks_threshold = int(weeks_input) if weeks_input.isdigit() else 2
        
        # Ask for debug mode
        # print("\n[❓] Enable debug mode with detailed logs? (y/n, default: n)")
        # debug_mode = input("> ").lower() == "y"
        
        # Delete and repost old listings
        reposted_count = delete_and_repost(driver, weeks_threshold, debug_mode)
        
        if reposted_count > 0:
            print(f"\n[🎉] Successfully deleted and reposted {reposted_count} old listings!")
        else:
            print("\n[ℹ️] No listings were deleted and reposted.")
            
    except Exception as e:
        print(f"\n[❌] An error occurred: {e}")
    
    finally:
        # Keep browser open until user decides to close
        input("\n[🏁] Press Enter to close the browser and exit...")
        try:
            driver.quit()
        except:
            pass
        print("[👋] Goodbye!")

if __name__ == "__main__":
    main()


# NOTE: This isnt gonna work completely
    #  need data to test with. 
    # - deletes functionality not confirmed
    # - reposts functionality not confirmed
    # - would work for reposting once but then the 
    #       listing date changes and accessing the csv wouldnt work.
    #       * maybe we change dir name to reposted_ but leave the listing .csv the same
# TODO: Delete files after a certain amount of time (how long?)

# NOTE: This isnt gonna work completely
    #  need data to test with. 
    # - deletes functionality not confirmed
    # - reposts functionality not confirmed
    # - would work for reposting once but then the 
    #       listing date changes and accessing the csv wouldnt work.
    #       * maybe we change dir name to reposted_ but leave the listing .csv the same
# TODO: Delete files after a certain amount of time (how long?)

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
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

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
    
    # Wait for page to be fully ready before handling warnings
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'html-div')]"))
        )
    except:
        pass
    
    # Handle any redirect warnings - wrap in try-except to handle stale elements
    try:
        handle_redirect_warning(driver, debug)
    except Exception as e:
        if debug:
            print(f"[⚠️] Error handling redirect warning (may be stale element): {e}")
        # Continue anyway, the warning might not exist
        pass
    
    # Give page a moment to settle
    time.sleep(1)
    
    listing_cards = []
    max_retries = 3
    retry_count = 0
    
    # Retry finding listings if we hit stale element issues
    while retry_count < max_retries:
        try:
            listing_cards = []
            # Find all listings
            cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'html-div')]")
            for card in cards:
                # First check if this element actually contains a listing
                try:
                    if not card.text or "Listed on" not in card.text:
                        continue
                    else:
                        listing_cards.append(card)
                except StaleElementReferenceException:
                    # Skip stale elements and continue
                    if debug:
                        print(f"[⚠️] Skipped stale element")
                    continue
            
            # If we successfully got cards without stale element errors, break
            if listing_cards or retry_count == max_retries - 1:
                break
                
        except Exception as e:
            if debug:
                print(f"[⚠️] Error finding listings (retry {retry_count + 1}/{max_retries}): {e}")
            retry_count += 1
            time.sleep(1)
    
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
                if debug:
                    print("[⚠️] Skipping empty listing card")
                continue

            title = re.search(r'Rent a ([^\n]+)', full_card_text)
            if title:
                title = title.group(1).strip()
                if debug:
                    print(f"[📌] Extracted title: {title}")
            else:
                if debug:
                    print(f"[⚠️] Could not find title in card")
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
                if debug:
                    print(f"[⚠️] Could not find 'Listed on' date in card: {title}")

        except StaleElementReferenceException:
            if debug:
                print(f"[⚠️] Stale element encountered while processing listing, skipping")
            continue
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
        # Scroll the listing into view
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", listing_element)
        time.sleep(0.5)
        
        # Hover over the listing to make menu visible
        from selenium.webdriver.common.action_chains import ActionChains
        actions = ActionChains(driver)
        actions.move_to_element(listing_element).perform()
        time.sleep(0.5)
        
        menu_button = None
        
        # APPROACH 1: Find menu button by role="button" with aria-label containing "More options"
        menu_selectors = [
            ".//div[@role='button' and contains(@aria-label, 'More options')]",
            ".//div[@role='button' and contains(@aria-label, 'More actions')]",
            ".//div[@role='button']//i[@data-visualcompletion='css-img']/..",
            ".//div[@aria-label[contains(., 'More options')]]",
        ]
        
        for selector in menu_selectors:
            try:
                menu_button = listing_element.find_element(By.XPATH, selector)
                if debug:
                    print(f"[✅] Found menu button using selector: {selector}")
                break
            except:
                continue
        
        # APPROACH 2: If not found in card, search within parent container
        if not menu_button:
            try:
                parent_container = listing_element.find_element(By.XPATH, "..")
                menu_button = parent_container.find_element(By.XPATH, ".//div[@role='button' and contains(@aria-label, 'More options')]")
                if debug:
                    print(f"[✅] Found menu button in parent container")
            except:
                pass
        
        # APPROACH 3: Search the entire page for menu button with the listing title
        if not menu_button:
            try:
                # This handles titles with special characters better
                all_menu_buttons = driver.find_elements(By.XPATH, "//div[@role='button' and contains(@aria-label, 'More options')]")
                
                if all_menu_buttons:
                    if debug:
                        print(f"[ℹ️] Found {len(all_menu_buttons)} menu buttons on page, using first one near listing")
                    
                    # Try to find the one closest to our listing element
                    for btn in all_menu_buttons:
                        btn_location = btn.location
                        element_location = listing_element.location
                        
                        # Check if button is within reasonable distance of listing
                        distance = abs(btn_location['y'] - element_location['y'])
                        if distance < 200:  # Within 200px vertically
                            menu_button = btn
                            if debug:
                                print(f"[✅] Found nearby menu button")
                            break
                    
                    # If no nearby button found, use the first one
                    if not menu_button:
                        menu_button = all_menu_buttons[0]
                        if debug:
                            print(f"[⚠️] Using first menu button found")
            except:
                pass
        
        if not menu_button:
            print(f"[❌] Could not find menu button for: {title}")
            driver.get("https://www.facebook.com/marketplace/you/selling")
            time.sleep(1)
            return False
        
        # Click the menu button
        if debug:
            print(f"[🔍] Clicking menu button")
        
        driver.execute_script("arguments[0].click();", menu_button)
        time.sleep(1)
        
        # Wait for and find Delete option
        print(f"[🔍] Looking for Delete option...")
        
        delete_options = []
        try:
            # Look for "Delete listing" or "Delete"
            delete_options = driver.find_elements(By.XPATH, "//span[contains(text(), 'Delete listing')] | //span[contains(text(), 'Delete')]")
        except:
            pass
        
        if not delete_options:
            if debug:
                print(f"[ℹ️] Delete option not visible, checking page structure...")
            # Try looking in a menu/dialog context
            delete_options = driver.find_elements(By.XPATH, "//div[@role='menuitem']//span[contains(text(), 'Delete')] | //li[@role='menuitem']//span[contains(text(), 'Delete')]")
        
        if delete_options:
            if debug:
                print(f"[✅] Found Delete option, clicking...")
            
            driver.execute_script("arguments[0].click();", delete_options[0])
            time.sleep(1)
            
            # Look for confirmation button
            print(f"[🔍] Looking for confirmation button...")
            
            confirm_buttons = []
            
            # APPROACH 1: Look for button with aria-label="Delete" (most reliable)
            try:
                confirm_buttons = driver.find_elements(By.XPATH, 
                    "//div[@role='button' and @aria-label='Delete']")
                if confirm_buttons:
                    if debug:
                        print(f"[✅] Found {len(confirm_buttons)} Delete button(s) by aria-label")
            except:
                pass
            
            # APPROACH 2: Look in dialog context
            if not confirm_buttons:
                try:
                    confirm_buttons = driver.find_elements(By.XPATH, 
                        "//div[@role='dialog']//div[@role='button' and contains(., 'Delete')]")
                    if confirm_buttons and debug:
                        print(f"[✅] Found Delete button in dialog")
                except:
                    pass
            
            # APPROACH 3: Look in alertdialog
            if not confirm_buttons:
                try:
                    confirm_buttons = driver.find_elements(By.XPATH, 
                        "//div[@role='alertdialog']//div[@role='button' and contains(., 'Delete')]")
                    if confirm_buttons and debug:
                        print(f"[✅] Found Delete button in alertdialog")
                except:
                    pass
            
            # APPROACH 4: Fallback - look for any button with Delete text
            if not confirm_buttons:
                try:
                    confirm_buttons = driver.find_elements(By.XPATH, 
                        "//div[@role='button']//span[contains(text(), 'Delete')]/ancestor::div[@role='button']")
                    if confirm_buttons and debug:
                        print(f"[✅] Found Delete button by text")
                except:
                    pass
            
            if confirm_buttons:
                if debug:
                    print(f"[🗑️] Clicking confirmation button...")
                
                # Try multiple click methods to ensure it registers
                try:
                    # First, scroll into view
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", confirm_buttons[1])
                    time.sleep(0.3)
                    
                    # Try JavaScript click first
                    driver.execute_script("arguments[0].click();", confirm_buttons[1])
                    time.sleep(0.5)
                    
                    # Also try ActionChains as backup
                    from selenium.webdriver.common.action_chains import ActionChains
                    ActionChains(driver).click(confirm_buttons[1]).perform()
                    
                    time.sleep(1)  # Wait for deletion to complete
                    
                    # Verify deletion by checking if page reloaded
                    current_url = driver.current_url
                    if "marketplace/you/selling" in current_url or "marketplace" in current_url:
                        print(f"[✅] Successfully deleted: {title}")
                        return True
                    else:
                        print(f"[⚠️] Button clicked but page state unclear")
                        time.sleep(2)
                        return True  # Assume success
                    
                except Exception as click_error:
                    if debug:
                        print(f"[⚠️] Error clicking button: {click_error}")
                    time.sleep(2)
                    return True  # Assume success anyway
            else:
                print(f"[❌] Could not find confirm delete button")
                if debug:
                    print(f"[ℹ️] Looking for any dialog on page...")
                    dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog'] | //div[@role='alertdialog']")
                    print(f"[ℹ️] Found {len(dialogs)} dialog(s)")
        else:
            print(f"[❌] Delete option not found in menu")
        
        # Go back to selling page
        driver.get("https://www.facebook.com/marketplace/you/selling")
        time.sleep(1)
        return False
        
    except Exception as e:
        print(f"[❌] Error deleting listing {title}: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        
        try:
            driver.get("https://www.facebook.com/marketplace/you/selling")
            time.sleep(1)
        except:
            pass
        
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
    reposted_count = 0
    max_iterations = 50  # Safety limit to prevent infinite loops
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        # Find old listings (fresh query each time - avoids stale elements)
        old_listings = find_old_listings(driver, weeks_threshold, debug)
        
        if not old_listings:
            print("[ℹ️] No more old listings to delete and repost.")
            break
        
        if iteration == 1:
            print(f"\n[❓] Found {len(old_listings)} listings older than {weeks_threshold} weeks to delete and repost.")
        
        # Process the first listing in the fresh list
        title, element, date = old_listings[0]
        
        print(f"\n[🔄] Processing listing {iteration}: {title}")
        
        try:
            # Delete the listing
            if delete_listing(driver, (title, element, date), debug):
                # Fi
                # nd corresponding CSV data using the listing date
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
                        # Break on repost failure to avoid infinite loop
                        break
                else:
                    print(f"[⚠️] Could not repost {title} - no CSV data found")
                    # Continue to next listing
                    reset_browser_state(driver)
            else:
                print(f"[❌] Failed to delete: {title}")
                # Continue to next listing
                reset_browser_state(driver)
        
        except Exception as e:
            print(f"[❌] Error processing listing {title}: {e}")
            reset_browser_state(driver)
            break
    
    if iteration >= max_iterations:
        print(f"[⚠️] Reached maximum iterations limit ({max_iterations})")
    
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
        try:
            driver.quit()
        except:
            pass
        print("[👋] Goodbye!")

if __name__ == "__main__":
    main()

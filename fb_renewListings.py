import os
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains

def get_driver():
    """Set up and return a Chrome WebDriver with appropriate options."""
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    import os
    import getpass
    import glob

    # Get current username
    username = getpass.getuser()
    print(f"[👤] Current user: {username}")
    
    # Define base profile directory and pattern
    home_dir = os.path.expanduser("~")
    profile_base = os.path.join(home_dir, ".fb_")
    
    # Check if a profile already exists for this user
    user_profile = os.path.join(home_dir, f".fb_{username}")
    
    # Look for any existing FB profiles
    existing_profiles = glob.glob(f"{profile_base}*")
    
    # Determine which profile to use
    if os.path.exists(user_profile):
        profile_path = user_profile
        print(f"[✅] Using existing profile: {profile_path}")
    elif existing_profiles:
        # Use the first existing profile found
        profile_path = existing_profiles[0]
        existing_user = os.path.basename(profile_path).replace(".fb_", "")
        print(f"[ℹ️] Using existing profile for user '{existing_user}': {profile_path}")
    else:
        # Create new profile for current user
        profile_path = user_profile
        print(f"[🆕] Creating new profile: {profile_path}")
        
        # Ensure the directory exists
        os.makedirs(profile_path, exist_ok=True)
    
    # Set up Chrome options with the selected profile
    chrome_options = Options()
    chrome_options.add_argument(f"--user-data-dir={profile_path}")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_experimental_option("detach", True)
    
    # Add a profile indicator to the window title
    profile_username = os.path.basename(profile_path).replace(".fb_", "")
    chrome_options.add_argument(f"--window-name=FB Marketplace ({profile_username})")
    
    print(f"[🔍] Setting up Chrome with profile: {profile_path}")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def renew_listings(driver, max_renewals=None, debug=True):
    """Automatically renew expired Facebook Marketplace listings.
    
    Args:
        driver: The Selenium WebDriver instance
        max_renewals: Maximum number of listings to renew (None for all)
        debug: Whether to print debug messages
    
    Returns:
        int: Number of successfully renewed listings
    """
    print("[🔄] Starting the listing renewal process...")
    
    # Navigate to the selling page
    driver.get("https://www.facebook.com/marketplace/you/selling")
    time.sleep(5)  # Wait for page to load
    
    renewed_count = 0
    
    try:
        # Look for "Renew Listing" buttons
        if debug:
            print("[🔍] Looking for 'Renew Listing' buttons...")
        
        # Scroll down a few times to load more listings
        for _ in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        
        # Find all renew buttons using multiple approaches
        renew_buttons = []
        
        # Approach 1: Direct XPath for buttons containing "Renew Listing" text
        buttons = driver.find_elements(By.XPATH, "//span[contains(text(), 'Renew Listing')]/ancestor::button | //span[contains(text(), 'Renew Listing')]/ancestor::*[@role='button']")
        if buttons:
            renew_buttons.extend(buttons)
            if debug:
                print(f"[💡] Found {len(buttons)} renew buttons by direct text match")
        
        # Approach 2: JavaScript approach for more thorough search
        js_buttons = driver.execute_script("""
            var buttons = [];
            var elements = document.querySelectorAll('button, [role="button"], a');
            for (var i = 0; i < elements.length; i++) {
                if (elements[i].textContent.includes('Renew') && 
                    elements[i].textContent.includes('Listing') && 
                    elements[i].offsetParent !== null) {
                    buttons.push(elements[i]);
                }
            }
            return buttons;
        """)
        
        if js_buttons:
            # Add only buttons that aren't already in our list
            for button in js_buttons:
                if button not in renew_buttons:
                    renew_buttons.append(button)
            
            if debug:
                print(f"[💡] Found {len(js_buttons)} additional renew buttons via JavaScript")
        
        total_buttons = len(renew_buttons)
        if debug:
            print(f"[📊] Total 'Renew Listing' buttons found: {total_buttons}")
        
        if total_buttons == 0:
            print("[ℹ️] No listings need renewal at this time.")
            return 0
        
        # Determine how many to renew
        to_renew = total_buttons if max_renewals is None else min(max_renewals, total_buttons)
        
        # Ask for confirmation
        print(f"[❓] Found {to_renew} listings to renew. Continue? (y/n)")
        if input().lower() != "y":
            print("[🛑] Renewal process cancelled by user")
            return 0
        
        # Click each renew button
        for i, button in enumerate(renew_buttons[:to_renew], 1):
            try:
                # Get the listing title if possible
                listing_info = "unknown listing"
                try:
                    # Try to get the title from nearby elements
                    title_element = driver.execute_script("""
                        var button = arguments[0];
                        var parent = button;
                        // Go up a few levels
                        for (var i = 0; i < 5; i++) {
                            parent = parent.parentElement;
                            if (!parent) break;
                            
                            // Look for title elements within this parent
                            var headings = parent.querySelectorAll('h2, h3, h4, a[href*="item"]');
                            if (headings.length > 0) {
                                return headings[0];
                            }
                        }
                        return null;
                    """, button)
                    
                    if title_element:
                        listing_info = title_element.text.strip() or "unnamed listing"
                except:
                    pass
                    
                # Scroll the button into view
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                time.sleep(0.5)
                
                # Click the button
                driver.execute_script("arguments[0].click();", button)
                
                # Wait for confirmation or any potential dialog
                time.sleep(2)
                
                # Check for any confirmation dialogs and accept them
                try:
                    confirm_buttons = driver.find_elements(By.XPATH, 
                        "//span[contains(text(), 'Confirm') or contains(text(), 'OK') or contains(text(), 'Yes')]")
                    if confirm_buttons:
                        driver.execute_script("arguments[0].click();", confirm_buttons[0])
                        time.sleep(1)
                except:
                    pass
                
                print(f"[✅] Renewed listing {i}/{to_renew}: {listing_info}")
                renewed_count += 1
                
                # Add a small delay between renewals
                time.sleep(random.uniform(1.0, 2.0))
                
            except Exception as e:
                if debug:
                    print(f"[❌] Error renewing listing {i}/{to_renew}: {e}")
        
        print(f"[🎉] Successfully renewed {renewed_count}/{to_renew} listings!")
        return renewed_count
        
    except Exception as e:
        print(f"[❌] Error during renewal process: {e}")
        return renewed_count

def main(driver=None, close_browser=False):
    """Run the renewal process.
    
    Args:
        driver: Existing WebDriver instance (optional)
        close_browser: Whether to close the browser when done (default: True)
    """
    global max_renewals, debug_mode
    max_renewals = None
    debug_mode = False
    
    try:
        # Setup WebDriver if not provided
        browser_created = False
        if driver is None:
            print("\n[🔧] Setting up browser...")
            driver = get_driver()
            browser_created = True
        
        # Perform the renewals
        renewed = renew_listings(driver, max_renewals=max_renewals, debug=debug_mode)
        
        # Summary
        if renewed > 0:
            print(f"\n[✅] Success! Renewed {renewed} listings.")
        else:
            print("\n[ℹ️] No listings were renewed.")
        
        return renewed
        
    except Exception as e:
        print(f"\n[❌] An error occurred during renewal: {e}")
        return 0
    
    finally:
        # Only close the browser if we created it and close_browser is True
        if browser_created and close_browser:
            try:
                driver.quit()
                print("[🔒] Browser closed")
            except:
                pass
            print("[👋] Goodbye!")

if __name__ == "__main__":
    main()
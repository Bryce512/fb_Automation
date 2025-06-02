import os
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from fb_postListings import get_driver

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
    time.sleep(3)  # Allow initial page load
    
    renewed_count = 0
    
    try:
        # Look for "Renew Listing" buttons
        if debug:
            print("[🔍] Looking for 'Renew Listing' buttons...")
        
        # Use the improved scrolling function to load all listings
        scroll_to_load_all_listings(driver, max_scrolls=15, scroll_delay=1.0, debug=debug)
        
        # Find all renew buttons using multiple approaches
        renew_buttons = []
        
        # Approach 1: Direct XPath for buttons containing "Renew Listing" text
        buttons = driver.find_elements(By.XPATH, "//*[contains(text(), 'Renew listing')]/ancestor::button | //span[contains(text(), 'Renew Listing')]/ancestor::*[@role='button']")
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
                    elements[i].textContent.includes('listing') && 
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
                time.sleep(0.2)
                
                # Click the button
                driver.execute_script("arguments[0].click();", button)
                
                # Wait for confirmation or any potential dialog
                time.sleep(.5)
                
                # First try to handle the specific "Renew your listing?" dialog
                dialog_handled = handle_renew_dialog(driver, debug)
                
                # If the specific dialog wasn't found, check for generic confirmation dialogs
                if not dialog_handled:
                    try:
                        confirm_buttons = driver.find_elements(By.XPATH, 
                            "//span[contains(text(), 'Confirm') or contains(text(), 'OK') or contains(text(), 'Yes')]")
                        if confirm_buttons:
                            driver.execute_script("arguments[0].click();", confirm_buttons[0])
                            time.sleep(.4)
                    except Exception as e:
                        if debug:
                            print(f"[⚠️] Error with generic confirmation dialog: {e}")
                
                print(f"[✅] Renewed listing {i}/{to_renew}: {listing_info}")
                renewed_count += 1
                
                
            except Exception as e:
                if debug:
                    print(f"[❌] Error renewing listing {i}/{to_renew}: {e}")
        
        print(f"[🎉] Successfully renewed {renewed_count}/{to_renew} listings!")
        return renewed_count
        
    except Exception as e:
        print(f"[❌] Error during renewal process: {e}")
        return renewed_count

def handle_renew_dialog(driver, debug=True):
    """Handle the 'Renew your listing?' dialog by clicking the confirmation button.
    
    Args:
        driver: The Selenium WebDriver instance
        debug: Whether to print debug messages
    
    Returns:
        bool: True if dialog was found and handled, False otherwise
    """
    try:
        # Look for the dialog heading "Renew your listing?"
        dialog_heading = driver.find_elements(By.XPATH, "//h2//span[contains(text(), 'Renew your listing?')]")
        
        # Look for the "Renew listing" button within the dialog
        renew_buttons = driver.find_elements(By.XPATH, 
            "//span[contains(text(), 'Renew listing')]/ancestor::div[@role='button']")
        
        if dialog_heading and renew_buttons:
            if debug:
                print("[🔄] Found 'Renew your listing?' dialog, confirming...")
            
            # Click the "Renew listing" button in the dialog
            driver.execute_script("arguments[0].click();", renew_buttons[0])
            time.sleep(.2)
            return True
            
        return False
        
    except Exception as e:
        if debug:
            print(f"[⚠️] Error handling renewal dialog: {e}")
        return False

def scroll_to_load_all_listings(driver, max_scrolls=15, scroll_delay=1.0, debug=True):
    """
    Scroll down the page gradually to load all listings.
    
    Args:
        driver: The Selenium WebDriver instance
        max_scrolls: Maximum number of scroll attempts
        scroll_delay: Delay between scrolls in seconds
        debug: Whether to print debug messages
    """
    if debug:
        print(f"[📜] Loading all listings by scrolling (max {max_scrolls} scrolls)...")
    
    previous_height = 0
    scroll_count = 0
    
    while scroll_count < max_scrolls:
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        scroll_count += 1
        
        # Wait to load page
        time.sleep(scroll_delay)
        
        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        if debug:
            print(f"[📜] Scroll {scroll_count}/{max_scrolls} - Page height: {new_height}")
        
        # Break if no new content was loaded
        if new_height == previous_height:
            if debug:
                print(f"[📜] No new content after scroll {scroll_count}, stopping scrolling")
            break
            
        previous_height = new_height
    
    # Final scroll back to top to ensure all elements are rendered properly
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(0.5)
    
    # Now scroll down gradually to ensure all content is loaded
    total_height = driver.execute_script("return document.body.scrollHeight")
    viewport_height = driver.execute_script("return window.innerHeight")
    
    if debug:
        print(f"[📜] Gradual scroll through page (total height: {total_height}px)")
    
    # Scroll in smaller increments to ensure all elements load
    for i in range(0, total_height, viewport_height // 2):
        driver.execute_script(f"window.scrollTo(0, {i});")
        time.sleep(0.2)
    
    # Final scroll to the bottom
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)

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
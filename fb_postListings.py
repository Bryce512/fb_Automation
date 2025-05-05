from datetime import datetime
import os, csv, time
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sys

# Global settings
DEBUG_MODE = False  # Global debug flag, will be set from main()
AUTO_PUBLISH = False  # Global auto-publish flag, will be set from main()

def get_driver():
    """Set up and return a Chrome WebDriver with appropriate options."""
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    import os
    import getpass
    import glob
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    # Get current username
    username = getpass.getuser()
    print(f"[👤] Current user: {username}")
    
    # Define base profile directory and pattern
    home_dir = os.path.expanduser("~")
    profile_base = os.path.join(home_dir, ".fb_")
    
    # Look for any existing FB profiles
    existing_profiles = glob.glob(f"{profile_base}*")
    
    # Get profile names for display
    profile_names = [os.path.basename(p).replace(".fb_", "") for p in existing_profiles]
    
    # Determine which profile to use
    selected_profile = None
    
    if existing_profiles:
        if len(existing_profiles) == 1:
            # Single profile found
            selected_profile = existing_profiles[0]
            existing_user = os.path.basename(selected_profile).replace(".fb_", "")
            print(f"[✅] Using existing profile for user '{existing_user}': {selected_profile}")
        else:
            # Multiple profiles found - ask user which one to use
            print("\n[❓] Multiple Facebook profiles found. Please select one:")
            for i, profile_name in enumerate(profile_names, 1):
                print(f"  {i}. {profile_name}")
            print(f"  {len(profile_names) + 1}. Create new profile for {username}")
            
            # Get user selection
            try:
                selection = int(input("> "))
                if 1 <= selection <= len(existing_profiles):
                    selected_profile = existing_profiles[selection - 1]
                    selected_user = profile_names[selection - 1]
                    print(f"[✅] Selected profile for user '{selected_user}': {selected_profile}")
                else:
                    # User wants new profile
                    selected_profile = None
            except ValueError:
                # Invalid input, default to current user
                print("[⚠️] Invalid selection, defaulting to new profile")
                selected_profile = None
    
    # Create new profile if none selected
    if not selected_profile:
        selected_profile = os.path.join(home_dir, f".fb_{username}")
        print(f"[🆕] Creating new profile: {selected_profile}")
        
        # Ensure the directory exists
        os.makedirs(selected_profile, exist_ok=True)
    
    # Set up Chrome options with the selected profile
    chrome_options = Options()
    chrome_options.add_argument(f"--user-data-dir={selected_profile}")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_experimental_option("detach", True)
    
    # Add a profile indicator to the window title
    profile_username = os.path.basename(selected_profile).replace(".fb_", "")
    chrome_options.add_argument(f"--window-name=FB Marketplace ({profile_username})")
    
    print(f"[🔍] Setting up Chrome with profile: {selected_profile}")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Open Facebook and check if logged in
    print("[🌐] Opening Facebook to check login status...")
    driver.get("https://www.facebook.com/")
    
    # Wait for page to load
    time.sleep(2)
    
    # Check if we need to log in
    login_required = False
    
    # Method 1: Check URL for login indicators
    if "login" in driver.current_url or "nologin" in driver.current_url:
        login_required = True
    
    # Method 2: Look for login elements
    try:
        login_elements = driver.find_elements(By.XPATH, "//button[contains(text(), 'Log') and contains(text(), 'In')]")
        if login_elements:
            login_required = True
    except:
        pass
    
    # Method 3: Look for "Create new account" button which appears on login page
    try:
        create_account = driver.find_elements(By.XPATH, "//*[contains(text(), 'Create new account') or contains(text(), 'Create New Account')]")
        if create_account:
            login_required = True
    except:
        pass
    
    if login_required:
        print("\n[⚠️] Login required for this profile")
        print("[👉] Please log in to Facebook in the browser window")
        print("[ℹ️] The script will continue after you log in successfully.")
        print("[⏳] Waiting for login...")
        
        # Wait for login to complete (look for elements that only appear after login)
        max_wait_time = 300  # 5 minutes
        wait_interval = 5  # Check every 5 seconds
        waited = 0
        
        while waited < max_wait_time:
            # Check for successful login
            try:
                # Method 1: Look for marketplace link which is visible after login
                marketplace_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/marketplace')]")
                if marketplace_links:
                    print("[✅] Login successful!")
                    break
                
                # Method 2: Check if URL changed to news feed or home
                if "home" in driver.current_url or "news_feed" in driver.current_url:
                    print("[✅] Login successful!")
                    break
                
                # Method 3: Look for profile picture which appears after login
                profile_pics = driver.find_elements(By.XPATH, "//div[@aria-label='Your profile' or @aria-label='Account']")
                if profile_pics:
                    print("[✅] Login successful!")
                    break
            except:
                pass
            
            # Still not logged in, wait and check again
            time.sleep(wait_interval)
            waited += wait_interval
            if waited % 30 == 0:  # Show message every 30 seconds
                print(f"[⏳] Still waiting for login... ({waited} seconds)")
        
        if waited >= max_wait_time:
            print("[❌] Login timeout exceeded. Please run the script again after logging in.")
            driver.quit()
            sys.exit(1)
    else:
        print("[✅] Already logged in to Facebook")
    
    # Navigate to Marketplace
    # print("[🛒] Opening Facebook Marketplace...")
    # driver.get("https://www.facebook.com/marketplace/")
    # time.sleep(2)
    
    return driver


def find_element_by_text(driver, text, element_type=None, debug=False):
    """Find an element by text and return the related input field."""
    # wait = WebDriverWait(driver, 10)
    
    if debug:
        print(f"[🔍] Looking for element with text: '{text}'")
    
    try:
        # Method 3: Find any element containing the text
        elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{text}')]")
        
        if debug:
            print(f"[💡] Found {len(elements)} elements containing '{text}'")
        
        for i, element in enumerate(elements):
            if debug:
                print(f"[🔍] Checking element {i+1}/{len(elements)}")
            
            # First approach: Check following input elements
            try:
                # If element_type is specified, look for that type; otherwise use a generic approach
                xpath = f"./following::{element_type}" if element_type else "./following::input | ./following::textarea | ./following::select"
                result = element.find_element(By.XPATH, xpath)
                if debug:
                    print(f"[✅] Found element as following sibling")
                return result
            except:
                # Second approach: Check parent's children
                try:
                    parent = element.find_element(By.XPATH, "./ancestor::div[position() <= 3]")
                    xpath = f".//{element_type}" if element_type else ".//input | .//textarea | .//select"
                    result = parent.find_element(By.XPATH, xpath)
                    if debug:
                        print(f"[✅] Found element as child of ancestor")
                    return result
                except:
                    if debug:
                        print(f"[❌] Couldn't find related input for this element")
                    continue
        
        # If we get here, no element was found
        if debug:
            print(f"[❌] No suitable element found for '{text}'")
        return None
    
    except Exception as e:
        if debug:
            print(f"[❌] Error finding element with text '{text}': {e}")
        return None

def upload_images(driver, image_paths, debug=False):
    """Upload multiple images to the listing."""
    if not image_paths:
        print("[⚠️] No image paths provided")
        return False
        
    # Convert single image path to list for consistent handling
    if isinstance(image_paths, str):
        image_paths = [image_paths]
    
    uploaded_count = 0
    
    for i, image in enumerate(image_paths):
        # for image in images:
        if isinstance(image, str):
            # More thorough cleaning for quotes and spaces
            image = image.strip().strip("'\"").strip()
            print(f"[🔍] Processing image: {image}")
        
        if not os.path.exists(image):
            print(f"[⚠️] Image file does not exist: {image}")
            continue
        
        try:
            if i == 0:  # For the first image
                # Direct approach - look for file inputs immediately
                file_inputs = driver.find_elements(By.XPATH, "//input[@type='file']")
                if file_inputs:
                    file_inputs[0].send_keys(image)
                    time.sleep(0.25)  # Allow upload to start
                    uploaded_count += 1
                    print(f"[📸] Uploaded primary image: {os.path.basename(image)}")
                else:
                    # If no file input found, try clicking a photo button first
                    photo_buttons = driver.find_elements(By.XPATH, "//span[contains(text(), 'Add Photo')]")
                    if photo_buttons:
                        driver.execute_script("arguments[0].click();", photo_buttons[0])
                        time.sleep(0.3)  # Wait for file dialog to appear
                        
                        # Look for file input again
                        file_inputs = driver.find_elements(By.XPATH, "//input[@type='file']")
                        if file_inputs:
                            file_inputs[0].send_keys(image_paths[i])
                            time.sleep(0.1)
                            uploaded_count += 1
                            print(f"[📸] Uploaded primary image: {os.path.basename(image)}")
            else:  # For additional images
                # Look for "Add Photos" or "+" buttons for additional images
                add_buttons = driver.find_elements(By.XPATH, 
                    "//span[contains(text(), 'Add Photo') or contains(text(), 'Add More')]/..|"
                    "//div[contains(@aria-label, 'Add photo') or contains(@aria-label, 'Add more')]")
                
                if add_buttons:
                    # Try to find the most appropriate button (usually the "+" button)
                    suitable_button = None
                    for button in add_buttons:
                        # Prefer smaller elements (usually the + button)
                        if button.is_displayed():
                            suitable_button = button
                            break
                    
                    if suitable_button:
                        # Scroll to the button
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", suitable_button)
                        time.sleep(0.1)
                        
                        # Click the button
                        driver.execute_script("arguments[0].click();", suitable_button)
                        # time.sleep(0.5)
                        
                        # Look for file input
                        file_inputs = driver.find_elements(By.XPATH, "//input[@type='file']")
                        if file_inputs:
                            file_inputs[0].send_keys(image)
                            time.sleep(0.1)
                            uploaded_count += 1
                            print(f"[📸] Uploaded additional image {i+1}: {os.path.basename(image)}")
                else:
                    # Try JavaScript approach to find + add more photos button
                    clicked = driver.execute_script("""
                        // Look for add photo buttons or + icons
                        var buttons = document.querySelectorAll('div, span, button');
                        for (var i = 0; i < buttons.length; i++) {
                            var elem = buttons[i];
                            if ((elem.textContent.includes('Add Photo') || 
                                elem.textContent.includes('Add More') ||
                                elem.textContent === '+' ||
                                elem.getAttribute('aria-label') && 
                                (elem.getAttribute('aria-label').includes('Add photo') || 
                                elem.getAttribute('aria-label').includes('Add more'))) &&
                                elem.offsetParent !== null) {
                                
                                elem.scrollIntoView({behavior: 'smooth', block: 'center'});
                                elem.click();
                                return true;
                            }
                        }
                        return false;
                    """)
                    
                    if clicked:
                        time.sleep(0.1)
                        file_inputs = driver.find_elements(By.XPATH, "//input[@type='file']")
                        if file_inputs:
                            file_inputs[0].send_keys(image)
                            time.sleep(0.1)
                            uploaded_count += 1
                            print(f"[📸] Uploaded additional image {i+1}: {os.path.basename(image)}")
        
        except Exception as e:
            if debug:
                print(f"[❌] Error uploading image {i+1}: {e}")
                
    print(f"[📊] Uploaded {uploaded_count}/{len(image_paths)} images")
    return uploaded_count == len(image_paths)

def set_location(driver, location_text, debug=False):
    """Set the listing location efficiently - optimized version."""
    try:
        if debug:
            print(f"[🔍] Setting location to: {location_text}")
        
        # First try to find location field directly
        location_field = find_element_by_text(driver, "Location", debug=debug)
        
        # If not found, look for More details
        if not location_field:
            # Try to click More details button
            more_details = driver.find_elements(By.XPATH, "//*[contains(text(), 'More details')]")
            if (more_details and len(more_details) > 0):
                driver.execute_script("arguments[0].click();", more_details[0])
                time.sleep(0.1)  # Reduced wait time
                
                # Try to find location field again
                location_field = find_element_by_text(driver, "Location", debug=debug)
        
        if not location_field:
            return False
        
        # Simplified clearing: Select all and delete
        location_field.click()
        ActionChains(driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.DELETE).perform()
        # time.sleep(0.3)
        
        # Enter new location
        location_field.send_keys(location_text)
        time.sleep(0.5)  # Reduced wait time
        
        # Select first suggestion
        location_field.send_keys(Keys.DOWN, Keys.ENTER)
        
        return True
    
    except Exception as e:
        if debug:
            print(f"[❌] Error setting location: {e}")
        return False

def click_hide_from_friends(driver, debug=False):
    """Click the 'Hide from friends' option."""
    try:
        if debug:
            print("[🔍] Looking for 'Hide from friends' option...")
        
        # Try multiple approaches to find and click the element
        
        # First approach: Direct text match
        hide_elements = driver.find_elements(By.XPATH, "//span[contains(text(), 'Hide from friends')]")
        
        if hide_elements:
            if debug:
                print(f"[💡] Found {len(hide_elements)} 'Hide from friends' elements")
            
            # Click the parent div to activate the toggle
            parent_div = driver.execute_script("""
                var span = arguments[0];
                // Go up to find a clickable parent
                var element = span;
                for (var i = 0; i < 5; i++) {
                    if (!element.parentElement) break;
                    element = element.parentElement;
                    if (element.tagName.toLowerCase() === 'div' && 
                        (element.onclick || 
                         window.getComputedStyle(element).cursor === 'pointer')) {
                        return element;
                    }
                }
                return span.parentElement;
            """, hide_elements[0])
            
            # Scroll element into view
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", parent_div)
            # time.sleep(1)
            
            # Click the element
            driver.execute_script("arguments[0].click();", parent_div)
            
            if debug:
                print("[✅] Clicked 'Hide from friends' option")
            return True
        
        # Second approach: Look for similar text if exact match not found
        hide_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Hide') and contains(text(), 'friends')]")
        
        if hide_elements:
            if debug:
                print(f"[💡] Found {len(hide_elements)} alternative 'Hide from friends' elements")
            driver.execute_script("arguments[0].click();", hide_elements[0])
            if debug:
                print("[✅] Clicked 'Hide from friends' option (alternative)")
            return True
        
        # Try JavaScript approach as last resort
        hide_clicked = driver.execute_script("""
            var elements = document.querySelectorAll('span, div');
            for (var i = 0; i < elements.length; i++) {
                var text = elements[i].textContent || '';
                if (text.includes('Hide from friends')) {
                    // Try clicking this element
                    elements[i].click();
                    
                    // Also try clicking parent for toggle behavior
                    if (elements[i].parentElement) {
                        elements[i].parentElement.click();
                    }
                    
                    return true;
                }
            }
            return false;
        """)
        
        if hide_clicked:
            if debug:
                print("[✅] Clicked 'Hide from friends' using JavaScript")
            return True
        else:
            if debug:
                print("[⚠️] Could not find 'Hide from friends' option")
            return False
        
    except Exception as e:
        if debug:
            print(f"[❌] Error clicking 'Hide from friends': {e}")
        return False

def publish_listing(driver, debug=False):
    """Click Next, then Publish to complete the listing."""
    try:
        if debug:
            print("[🔍] Looking for 'Next' button...")
        
        # First click Next
        next_clicked = False
        
        # Try multiple approaches to find the Next button
        # Approach 1: Look for the text directly
        next_buttons = driver.find_elements(By.XPATH, "//span[contains(text(), 'Next')]")
        
        if next_buttons:
            for button in next_buttons:
                try:
                    # Find the clickable parent
                    clickable = driver.execute_script("""
                        var element = arguments[0];
                        // Go up to find a clickable parent
                        for (var i = 0; i < 5; i++) {
                            if (element.tagName.toLowerCase() === 'button' || 
                                element.tagName.toLowerCase() === 'a' || 
                                element.getAttribute('role') === 'button' ||
                                element.onclick) {
                                return element;
                            }
                            if (!element.parentElement) break;
                            element = element.parentElement;
                        }
                        return arguments[0].parentElement;
                    """, button)
                    
                    # Scroll to it
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", clickable)
                    # time.sleep(0.5)
                    
                    # Click it
                    driver.execute_script("arguments[0].click();", clickable)
                    next_clicked = True
                    
                    if debug:
                        print("[✅] Clicked 'Next' button")
                    
                    break
                except Exception as e:
                    if debug:
                        print(f"[⚠️] Error clicking this 'Next' button: {e}")
        
        # If direct approach didn't work, try JavaScript
        if not next_clicked:
            if debug:
                print("[🔍] Trying JavaScript approach for 'Next' button...")
            
            clicked = driver.execute_script("""
                // Look for buttons or clickable elements containing 'Next'
                var elements = document.querySelectorAll('button, [role="button"], div, span');
                for (var i = 0; i < elements.length; i++) {
                    if (elements[i].textContent.includes('Next') && 
                        elements[i].offsetParent !== null) {
                        elements[i].scrollIntoView({behavior: 'smooth', block: 'center'});
                        elements[i].click();
                        return true;
                    }
                }
                return false;
            """)
            
            if clicked:
                if debug:
                    print("[✅] Clicked 'Next' button using JavaScript")
                next_clicked = True
                time.sleep(.1)
        
        # Now look for the Publish button
        if next_clicked:
            if debug:
                print("[🔍] Looking for 'Publish' button...")
            
            # Approach 1: Look for the text directly
            publish_buttons = driver.find_elements(By.XPATH, "//span[contains(text(), 'Publish')]")
            
            if publish_buttons:
                for button in publish_buttons:
                    try:
                        # Find the clickable parent
                        clickable = driver.execute_script("""
                            var element = arguments[0];
                            // Go up to find a clickable parent
                            for (var i = 0; i < 5; i++) {
                                if (element.tagName.toLowerCase() === 'button' || 
                                    element.tagName.toLowerCase() === 'a' || 
                                    element.getAttribute('role') === 'button' ||
                                    element.onclick) {
                                    return element;
                                }
                                if (!element.parentElement) break;
                                element = element.parentElement;
                            }
                            return arguments[0].parentElement;
                        """, button)
                        
                        # Scroll to it
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", clickable)
                        time.sleep(0.2)
                        
                        # Click it
                        driver.execute_script("arguments[0].click();", clickable)
                        
                        if debug:
                            print("[✅] Clicked 'Publish' button")
                        
                        # Wait for publishing to complete
                        # time.sleep(3)
                        return True
                    except Exception as e:
                        if debug:
                            print(f"[⚠️] Error clicking this 'Publish' button: {e}")
            
            # If direct approach didn't work, try JavaScript
            if debug:
                print("[🔍] Trying JavaScript approach for 'Publish' button...")
            
            clicked = driver.execute_script("""
                // Look for buttons or clickable elements containing 'Publish'
                var elements = document.querySelectorAll('button, [role="button"], div, span');
                for (var i = 0; i < elements.length; i++) {
                    if (elements[i].textContent.includes('Publish') && 
                        elements[i].offsetParent !== null) {
                        elements[i].scrollIntoView({behavior: 'smooth', block: 'center'});
                        elements[i].click();
                        return true;
                    }
                }
                return false;
            """)
            
            if clicked:
                if debug:
                    print("[✅] Clicked 'Publish' button using JavaScript")
                # time.sleep(3)
                return True
        
        if debug:
            print("[⚠️] Could not find 'Publish' button")
        return False
    
    except Exception as e:
        if debug:
            print(f"[❌] Error publishing listing: {e}")
        return False
    
def handle_redirect_warning(driver, debug=False):
    """
    Detect and handle Facebook redirect warnings or loops.
    Returns True if a warning was detected and handled, False otherwise.
    """
    if debug:
        print("[🔍] Checking for redirect warnings...")
    
    try:
        # Method 1: Look for common redirect warning text
        warning_texts = [
            "Leave site?", 
            "Do you want to leave this site?",
            "Changes you made may not be saved",
            "Page redirected too many times",
            "ERR_TOO_MANY_REDIRECTS",
            "redirect warning",
            "Stay on Page",
            "Continue",
            "Leave Page",
            "Something went wrong",
            "Try Again"
        ]
        
        for text in warning_texts:
            elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{text}')]")
            if elements:
                print(f"[⚠️] Detected warning: '{text}'")
                
                # Look for "Stay on Page" or "Continue" buttons
                stay_buttons = driver.find_elements(By.XPATH, 
                    "//*[contains(text(), 'Stay') or contains(text(), 'Continue') or " +
                    "contains(text(), 'Cancel') or contains(text(), 'Try Again') or " +
                    "contains(text(), 'OK') or contains(text(), 'Okay')]")
                
                if stay_buttons:
                    for button in stay_buttons:
                        if button.is_displayed():
                            driver.execute_script("arguments[0].click();", button)
                            print("[✅] Clicked button to resolve warning")
                            time.sleep(.2)  # Wait for dialog to close
                            return True
                
                # If no specific button found, just click the first clickable element in the dialog
                if elements[0].is_displayed():
                    parent = driver.execute_script("""
                        var element = arguments[0];
                        
                        // Try to find a button or link nearby
                        var buttons = document.querySelectorAll('button, a, [role="button"]');
                        for (var i = 0; i < buttons.length; i++) {
                            if (buttons[i].offsetParent !== null && (
                                buttons[i].textContent.includes('Stay') || 
                                buttons[i].textContent.includes('Continue') || 
                                buttons[i].textContent.includes('Cancel') ||
                                buttons[i].textContent.includes('Try Again') ||
                                buttons[i].textContent.includes('OK'))) {
                                return buttons[i];
                            }
                        }
                        
                        // If no button found, try parent elements
                        var current = element;
                        for (var i = 0; i < 5; i++) {
                            if (!current.parentElement) break;
                            current = current.parentElement;
                            if (current.tagName.toLowerCase() === 'button' || 
                                current.getAttribute('role') === 'button' ||
                                window.getComputedStyle(current).cursor === 'pointer') {
                                return current;
                            }
                        }
                        
                        // Last resort: return the element itself
                        return element;
                    """, elements[0])
                    
                    driver.execute_script("arguments[0].click();", parent)
                    print("[✅] Clicked element to dismiss warning")
                    time.sleep(.1)
                    return True
        
        # Method 2: Check for Chrome's built-in redirect warning
        try:
            # Switch to alert if present
            alert = driver.switch_to.alert
            alert_text = alert.text
            
            print(f"[⚠️] Detected browser alert: {alert_text}")
            alert.dismiss()  # Click "Cancel" or "Stay"
            print("[✅] Dismissed browser alert")
            time.sleep(.1)
            return True
        except:
            pass
        
        # Method 3: Check for specific Chrome error page
        if "ERR_TOO_MANY_REDIRECTS" in driver.page_source:
            print("[⚠️] Detected too many redirects error page")
            # Go back to marketplace
            driver.get("https://www.facebook.com/marketplace/create/item")
            time.sleep(.3)
            return True
            
        # Method 4: Check if current URL indicates an error
        if "error" in driver.current_url or "problem" in driver.current_url:
            print("[⚠️] Detected error in URL")
            driver.get("https://www.facebook.com/marketplace/create/item")
            time.sleep(.3)
            return True
        
        return False  # No warning detected
        
    except Exception as e:
        if debug:
            print(f"[❌] Error checking for redirect warnings: {e}")
        return False

def retry_failed_action(driver, action_function, action_args=None, max_retries=2, debug=False):
    """
    Retry a failed action with error handling.
    
    Args:
        driver: WebDriver instance
        action_function: Function to retry (will be called with *action_args)
        action_args: Arguments to pass to the action function (tuple/dict)
        max_retries: Maximum number of retry attempts
        debug: Enable debug output
    
    Returns:
        The result of the action function, or False if all retries failed
    """
    if action_args is None:
        action_args = ()
    
    for attempt in range(max_retries + 1):
        if attempt > 0:
            print(f"[🔄] Retry attempt {attempt}/{max_retries}")
        
        try:
            # Check for any redirect warnings first
            handle_redirect_warning(driver, debug)
            
            # Execute the action (could be upload_images, set_price, etc.)
            if isinstance(action_args, dict):
                result = action_function(**action_args)
            else:
                result = action_function(*action_args)
                
            # If successful, return the result
            if result:
                return result
                
            # If the action returned False but didn't raise an exception,
            # check for redirect warnings before retrying
            if handle_redirect_warning(driver, debug):
                print("[ℹ️] Handled warning after failed action")
                continue
                
        except Exception as e:
            print(f"[⚠️] Error during action: {e}")
            if handle_redirect_warning(driver, debug):
                print("[ℹ️] Handled warning after exception")
                continue
            
        # After handling any errors, refresh the page if needed
        if attempt < max_retries:
            print("[🔄] Refreshing page state before retry...")
            try:
                current_url = driver.current_url
                if "marketplace/create" not in current_url:
                    driver.get("https://www.facebook.com/marketplace/create/item")
                    time.sleep(.3)
                else:
                    # Just refresh the current page
                    driver.refresh()
                    time.sleep(.3)
            except:
                # If refresh fails, go back to marketplace
                driver.get("https://www.facebook.com/marketplace/create/item")
                time.sleep(.3)
    
    # If we get here, all retries failed
    print("[❌] Action failed after all retry attempts")
    return False

def post_listing(driver, title, price, description, location, images, category=None, attempt = 1, max_attempts=5):
    global DEBUG_MODE, AUTO_PUBLISH
    debug = DEBUG_MODE  # Use global debug setting
    
    print(f"[📄] Posting: {title}")
    driver.get("https://www.facebook.com/marketplace/create/item")
    
    try:
        # Wait for page to load
        # time.sleep(1)

        
        # 1. Upload images FIRST
        if images:
            print("[🔍] Uploading images...")
            # Convert single image path to list if needed
            # if isinstance(image_path, str):
            #     image_paths = [image_paths]
                
            # Filter out non-existent images
            valid_images = images.strip()[1:-1].split(',') 
            # valid_images = [img for img in image_path if img and os.path.exists(img)]

            if valid_images:
                if upload_images(driver, valid_images, debug=debug):
                    print("[📸] Images uploaded successfully")
                else:
                    handle_redirect_warning(driver, debug=debug)
                    print("[⚠️] Failed to upload images")
            else:
                print("[⚠️] No valid images to upload")
        
        # 2. Title
        print("[🔍] Finding title field...")
        title_input = find_element_by_text(driver, "Title", debug=debug)
        if title_input:
            title_input.send_keys(title)
            print("[✅] Title entered")
        else:
            handle_redirect_warning(driver, debug=debug)
            print("[❌] Could not find title field")
            return False
        # time.sleep(random.uniform(0.2, 0.5))
        
        # Replace your price entry code with this:

        # 3. Price
        print("[🔍] Finding price field...")
        price_input = find_element_by_text(driver, "Price", debug=debug)
        if price_input:
            try:
                # Get the actual price from the row data or fallback to 1000
                price_str = str(price)
                print(f"[🔍] Attempting to enter price: {price_str}")
                
                # First try to get the actual input element
                price_element = price_input
                element_tag = driver.execute_script("return arguments[0].tagName.toLowerCase();", price_element)
                
                # If we found a non-input element, find the actual input nearby
                if element_tag != "input":
                    print("[🔍] Found a non-input price element, locating the actual input...")
                    try:
                        # Get the input from parent
                        price_element = driver.execute_script("""
                            var element = arguments[0];
                            var parent = element.parentElement;
                            return parent.querySelector('input');
                        """, price_input)
                        
                        if not price_element:
                            # Look in surrounding elements
                            price_element = driver.find_element(By.XPATH, "//input[@aria-invalid='true' or @aria-describedby]")
                    except:
                        pass
                
                # Clear any existing value first
                driver.execute_script("arguments[0].value = '';", price_element)
                
                # Try multiple methods to set the price
                # Method 1: JavaScript direct value assignment
                driver.execute_script("arguments[0].value = arguments[1];", price_element, price_str)
                
                # Method 2: Trigger input events after setting value
                driver.execute_script("""
                    var input = arguments[0];
                    input.value = arguments[1];
                    
                    // Trigger events that Facebook's validation might be listening for
                    var inputEvent = new Event('input', { bubbles: true });
                    var changeEvent = new Event('change', { bubbles: true });
                    var keydownEvent = new KeyboardEvent('keydown', { key: '1', bubbles: true });
                    var keyupEvent = new KeyboardEvent('keyup', { key: '1', bubbles: true });
                    
                    // Dispatch all events
                    input.dispatchEvent(inputEvent);
                    input.dispatchEvent(changeEvent);
                    input.dispatchEvent(keydownEvent);
                    input.dispatchEvent(keyupEvent);
                """, price_element, price_str)
                
                # Method 3: Use ActionChains as a backup
                try:
                    actions = ActionChains(driver)
                    actions.click(price_element)
                    actions.pause(0.1)
                    
                    # Clear existing value
                    actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL)
                    actions.send_keys(Keys.BACK_SPACE)
                    actions.pause(0.1)
                    
                    # Type the new value with pauses between characters
                    for char in price_str:
                        actions.send_keys(char)
                        actions.pause(0.05)
                    
                    actions.perform()
                except Exception as e:
                    print(f"[⚠️] ActionChains method failed: {e}")
                
                print("[✅] Price entered using multiple methods")
                
            except Exception as e:
                print(f"[❌] Error entering price: {e}")
                print("retrying price input...")
                handle_redirect_warning(driver, debug=debug)
                
                # Try a last-resort method - find by specific attributes
                try:
                    print("[🔍] Attempting direct XPath selection for price field...")
                    price_inputs = driver.find_elements(By.XPATH, "//input[@type='text' and (contains(@class, 'x1i10hfl') or @aria-invalid='true')]")
                    
                    if price_inputs:
                        for input_element in price_inputs:
                            try:
                                driver.execute_script("arguments[0].value = arguments[1];", input_element, price_str)
                                driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", input_element)
                                print("[✅] Found alternative price input and entered value")
                                break
                            except:
                                continue
                except Exception as e:
                    print(f"[❌] Last resort price entry failed: {e}")
                    return False
        else:
            handle_redirect_warning(driver, debug=debug)
            print("[❌] Could not find price field")
            return False
        # time.sleep(random.uniform(0.8, 1.2))
        
        # 4. Category
        print("[🔍] Setting category to Miscellaneous...")
        category_input = find_element_by_text(driver, "Category", debug=debug)
        if category_input:
            # Use JavaScript to ensure the click works
            category_input.click()
            category_input.send_keys("miscellaneous")
            category_input.send_keys(Keys.DOWN)
            category_input.send_keys(Keys.ENTER)
            # driver.execute_script("arguments[0].click();", category_input)
            time.sleep(.2)  # Allow dropdown to open fully
            
            try:
                # Try multiple selectors for Miscellaneous in the dropdown
                selectors = [
                    "//span[contains(text(), 'Miscellaneous')]",
                ]
                
                for selector in selectors:
                    try:
                        options = driver.find_elements(By.XPATH, selector)
                        if options:
                            # Click the first matching option
                            driver.execute_script("arguments[0].click();", options[0])
                            print("[✅] Category set to Miscellaneous")
                            # time.sleep(1)
                            break
                    except:
                        continue
                
                # If none of the selectors worked, use a JavaScript fallback
                if not any(driver.find_elements(By.XPATH, s) for s in selectors):
                    driver.execute_script("""
                        var elements = document.querySelectorAll('span, div, li');
                        for (var i = 0; i < elements.length; i++) {
                            if (elements[i].textContent.includes('Miscellaneous')) {
                                elements[i].click();
                                return true;
                            }
                        }
                        return false;
                    """)
                    print("[✅] Category set using JavaScript")
            except Exception as e:
                print(f"[⚠️] Could not select Miscellaneous category: {e}")
        else:
            print("[⚠️] Could not find category field")
        # time.sleep(random.uniform(0.2, 0.5))
        
        # 5. Condition
        print("[🔍] Setting condition to Used - Good...")
        try:
            # Look for label with role="combobox" that contains "Condition"
            condition_combobox = driver.find_element(By.XPATH, "//label[@role='combobox']//span[contains(text(), 'Condition')]/..")
            
            # If that doesn't work, try alternate methods to find the combobox
            if not condition_combobox:
                condition_combobox = driver.find_element(By.XPATH, "//*[@role='combobox' and contains(.//span/text(), 'Condition')]")
            
            # Scroll to it
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", condition_combobox)
            # time.sleep(.1)
            
            print("[🔍] Found condition dropdown, attempting to click...")
            
            # REMOVED HIGHLIGHTING - Use a direct click on the exact element
            driver.execute_script("arguments[0].click();", condition_combobox)
            
            # Wait for dropdown to open
            time.sleep(.1)
            
            # Look for "Used - Good" in the options
            good_options = driver.find_elements(By.XPATH, "//*[contains(text(), 'Used - Good') or contains(text(), 'Good')]")
            
            if good_options and len(good_options) > 0:
                print(f"[🔍] Found {len(good_options)} potential 'Good' condition options")
                
                # Click the first one that seems most appropriate
                for option in good_options:
                    option_text = option.text.strip()
                    if "Used" in option_text and "Good" in option_text:
                        driver.execute_script("arguments[0].click();", option)
                        print(f"[✅] Selected condition: {option_text}")
                        # time.sleep(0.5)
                        break
                else:
                    # If no perfect match, click the first one with "Good"
                    driver.execute_script("arguments[0].click();", good_options[0])
                    print(f"[✅] Selected condition: {good_options[0].text.strip()}")
            else:
                # No visible options found, try keyboard navigation
                print("[🔍] No visible condition options, trying keyboard navigation...")
                ActionChains(driver).send_keys(Keys.DOWN).pause(0.5).send_keys(
                    Keys.DOWN).pause(0.5).send_keys(Keys.DOWN).pause(0.5).send_keys(Keys.ENTER).perform()
                print("[✓] Used keyboard navigation to select condition")
            
            # Wait for selection to register
            # time.sleep(1)
            
        except Exception as e:
            print(f"[⚠️] Error setting condition: {e}")
        # time.sleep(random.uniform(0.8, 1.2))
        
        # 6. Description
        print("[🔍] Finding description field...")
        desc_input = find_element_by_text(driver, "Description", element_type="textarea", debug=debug)
        
        if desc_input:
            parts = description.split('[BREAK]')
            print(parts)
            desc_input.send_keys(parts[0])
            desc_input.send_keys(Keys.ENTER)  # Creates a line break
            desc_input.send_keys(Keys.ENTER)  # Double line break
            desc_input.send_keys(parts[1].strip("'"))
        else:
            print("[❌] Could not find description field")
            # Don't return False here since we've already filled out other fields
        # time.sleep(random.uniform(0.8, 1.2))
        
        # 7. Location
        if location:
            print(f"[🔍] Setting location to {location}...")
            set_location(driver, location, debug=debug)
            # time.sleep(random.uniform(.5, 1))
        
        # 8. Click "Hide from friends" option if available
        print("[🔍] Looking for 'Hide from friends' option...")
        if click_hide_from_friends(driver, debug=debug):
            print("[✓] 'Hide from friends' option selected")
        else:
            print("[ℹ️] 'Hide from friends' option not found or not clickable")
        # time.sleep(random.uniform(0.8, 1.2))
        
        # 9. Handle publishing based on AUTO_PUBLISH setting
        if AUTO_PUBLISH:
            print("[🔍] Auto-publishing listing...")
            if publish_listing(driver, debug=debug):
                print("[✅] Listing published successfully")
            else:
                print("[❌] Failed to auto-publish the listing")
                if attempt < max_attempts:
                    print(f"[🔄] Retrying to post listing... attempt {attempt}/3")
                    post_listing(driver, title, price, description, location, images, category, attempt+1)
                else:
                    print("[❌] Too many attempts, need manual fix...")
                    print("[🧍] Review post manually, then press Enter to continue...")
                    input()
        else:
            print("[🧍] Review post manually, then press Enter to continue...")
            input()
        
        return True
        
    except Exception as e:
        print(f"[❌] Error posting '{title}': {e}")
        input("🛑 Fix the issue and press Enter to retry or continue...")
        return False

def reset_browser_state(driver):
    """Reset browser state between listings to prevent detection"""
    print("[🔄] Resetting browser state for next listing...")
    
    # Clear cookies for the marketplace domain only
    driver.execute_script("""
        var domain = 'facebook.com';
        var cookiesToKeep = document.cookie.split('; ').filter(c => {
            return c.includes('c_user') || c.includes('xs') || c.includes('datr');
        });
        document.cookie.split(';').forEach(function(c) {
            if (!cookiesToKeep.some(keep => c.trim().startsWith(keep.split('=')[0]))) {
                document.cookie = c.replace(/^ +/, '').replace(/=.*/, '=;expires=' + new Date().toUTCString() + ';path=/');
            }
        });
    """)
    
    # Clear localStorage for marketplace
    driver.execute_script("localStorage.removeItem('marketplace_recently_viewed');")
    
    # Navigate away and back
    driver.get("https://www.facebook.com")
    time.sleep(.1)
    
    return True


def bulk_upload_listings(driver, csv_path):
    """Upload multiple listings at once using Facebook's bulk upload feature."""
    print(f"[📦] Starting bulk upload from: {csv_path}")
    
    try:
        # STEP 1: Navigate to the bulk upload page
        print("[🌐] Opening Facebook Marketplace bulk upload page...")
        driver.get("https://www.facebook.com/marketplace/create/bulk")
        
        # Wait for the page to load and file input to appear
        print("[⏳] Waiting for file input to be available...")
        wait = WebDriverWait(driver, 20)
        file_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
        print("[✅] File input located")
        
        # STEP 2: Upload the file directly
        absolute_path = os.path.abspath(csv_path)
        print(f"[📤] Uploading CSV file: {absolute_path}")
        file_input.send_keys(absolute_path)
        print("[📤] File path sent to input element")
        
        # STEP 3: Wait for confirmation or success
        print("[⏳] Waiting for upload confirmation or processing...")
        upload_success = False
        max_wait = 120
        elapsed = 0

        while elapsed < max_wait:
            # Check for success or progression indicators
            success_texts = ["success", "uploaded", "Next", "Continue", "Finish"]
            for text in success_texts:
                elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{text}')]")
                for elem in elements:
                    if elem.is_displayed():
                        print(f"[✅] Upload confirmed by presence of: '{text}'")
                        upload_success = True
                        # Optionally click "Next" or continue
                        if text in ["Next", "Continue", "Finish"]:
                            driver.execute_script("arguments[0].click();", elem)
                        break
                if upload_success:
                    break

            if upload_success:
                break

            # Check for error messages
            error_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'error') or contains(text(), 'Error') or contains(text(), 'failed') or contains(text(), 'Failed')]")
            if error_elements:
                print(f"[❌] Upload error detected: {error_elements[0].text}")
                return False

            time.sleep(2)
            elapsed += 2
            if elapsed % 10 == 0:
                print(f"[⏳] Still waiting... ({elapsed}s)")

        if not upload_success:
            print("[⚠️] Upload did not complete within timeout.")
            return False

        print("[🎉] Bulk upload completed successfully!")
        return True

    except Exception as e:
        print(f"[❌] Error during bulk upload: {e}")
        return False

def complete_bulk_listings(driver, regular_csv_path):
    """Add images and location data to bulk uploaded listings."""
    print("[🔄] Adding details to uploaded listings...")
    
    try:
        # Load the regular CSV for image paths and locations
        with open(regular_csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            listings = list(reader)
            
        if not listings:
            print("[⚠️] No listings found in the regular CSV file.")
            return 0
            
        print(f"[📊] Found {len(listings)} listings to complete.")
        
        # Navigate to Marketplace inventory/drafts
        print("[🌐] Opening Marketplace inventory...")
        driver.get("https://www.facebook.com/marketplace/you/selling")
        time.sleep(2)
        
        # Look for "Drafts" tab and click it if not already active
        draft_tabs = driver.find_elements(By.XPATH, "//*[contains(text(), 'Drafts')]")
        for tab in draft_tabs:
            if tab.is_displayed():
                try:
                    parent = driver.execute_script("""
                        var elem = arguments[0];
                        for (var i = 0; i < 5; i++) {
                            if (elem.getAttribute('role') === 'tab' || 
                                elem.tagName.toLowerCase() === 'a' || 
                                elem.getAttribute('href')) {
                                return elem;
                            }
                            if (!elem.parentElement) break;
                            elem = elem.parentElement;
                        }
                        return elem.parentElement;
                    """, tab)
                    
                    driver.execute_script("arguments[0].click();", parent)
                    print("[✅] Clicked on Drafts tab")
                    time.sleep(1)
                    break
                except:
                    pass
        
        # Process each listing
        successful = 0
        for i, row in enumerate(listings, 1):
            title = row.get('title', '')
            if not title:
                print(f"[⚠️] Listing {i} has no title, skipping")
                continue
                
            print(f"\n[🔄] Processing listing {i}/{len(listings)}: {title}")
            
            # Find this listing in the drafts
            found = False
            listing_elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{title.replace('Rent a ', '')}')]")
            
            for elem in listing_elements:
                try:
                    # Find clickable parent/container
                    listing_container = driver.execute_script("""
                        var elem = arguments[0];
                        for (var i = 0; i < 8; i++) {
                            if (elem.tagName.toLowerCase() === 'a' || 
                                elem.getAttribute('role') === 'link' ||
                                elem.getAttribute('href') ||
                                elem.onclick) {
                                return elem;
                            }
                            if (!elem.parentElement) break;
                            elem = elem.parentElement;
                        }
                        return null;
                    """, elem)
                    
                    if listing_container:
                        driver.execute_script("arguments[0].click();", listing_container)
                        print(f"[✅] Found and clicked on listing: {title}")
                        found = True
                        time.sleep(2)
                        break
                except Exception as e:
                    print(f"[⚠️] Error clicking listing element: {e}")
                    continue
            
            if not found:
                print(f"[⚠️] Could not find listing '{title}' in drafts")
                continue
            
            # Now we're on the edit page for this listing
            # Add images
            images = row.get('images', '')
            if images:
                # Parse the image string - it can be in different formats
                if isinstance(images, str):
                    if images.startswith('[') and images.endswith(']'):
                        # This is a list representation in string format
                        image_list = images.strip('[]').split(',')
                        image_paths = [img.strip().strip('"\'') for img in image_list]
                    else:
                        # Single image path
                        image_paths = [images.strip()]
                        
                    # Upload the images
                    print(f"[🖼️] Uploading {len(image_paths)} images...")
                    upload_images(driver, image_paths)
            
            # Add location
            location = row.get('location', '')
            if location:
                print(f"[📍] Setting location: {location}")
                set_location(driver, location)
            
            # Click Next/Publish
            if publish_listing(driver, debug=DEBUG_MODE):
                successful += 1
                print(f"[✅] Successfully completed listing: {title}")
            else:
                print(f"[❌] Failed to publish listing: {title}")
            
            # Go back to drafts for next listing
            driver.get("https://www.facebook.com/marketplace/you/selling")
            time.sleep(1)
            
            # Make sure we're on Drafts tab again
            draft_tabs = driver.find_elements(By.XPATH, "//*[contains(text(), 'Drafts')]")
            for tab in draft_tabs:
                if tab.is_displayed():
                    try:
                        driver.execute_script("arguments[0].click();", tab)
                        time.sleep(1)
                        break
                    except:
                        pass
        
        print(f"\n[📊] Summary: Completed {successful}/{len(listings)} listings successfully.")
        return successful
        
    except Exception as e:
        print(f"[❌] Error completing bulk listings: {e}")
        return 0

def main():
    global DEBUG_MODE, AUTO_PUBLISH
    DEBUG_MODE = False
    AUTO_PUBLISH = True
    
    # Fetch fresh data if needed
    try:
        # Import these only if they exist and are needed
        from fb_fetchData import main as fetch_main
        fetch_main()
    except ImportError:
        print("[ℹ️] fb_fetchData module not found, skipping data fetch")
    
    # Initialize driver
    driver = get_driver()
    
    print("="*60)
    print("📦 Facebook Marketplace Bulk Uploader")
    print("="*60)
    print("\nThis tool automatically uploads listings to Facebook Marketplace using bulk upload.")
    
    try:
        # Construct paths for both bulk and regular CSV files
        date_str = datetime.now().strftime("%Y-%m-%d")
        data_dir = f"data_{date_str}"
        bulk_csv_path = f"{data_dir}/bulk_listings_{date_str}.csv"
        regular_csv_path = f"{data_dir}/listings_{date_str}.csv"
        
        # Verify files exist
        if not os.path.exists(bulk_csv_path):
            print(f"[❌] Bulk CSV file not found: {bulk_csv_path}")
            return
            
        if not os.path.exists(regular_csv_path):
            print(f"[❌] Regular CSV file not found: {regular_csv_path}")
            return
        
        print(f"[📂] Using bulk CSV: {bulk_csv_path}")
        print(f"[📂] Using regular CSV for details: {regular_csv_path}")
        
        # Step 1: Perform the bulk upload
        if bulk_upload_listings(driver, bulk_csv_path):
            print("[🎉] Bulk upload completed successfully!")
            
            # Step 2: Complete the listings with images and location
            successful = complete_bulk_listings(driver, regular_csv_path)
            
            if successful > 0:
                print(f"[🎉] Successfully completed and published {successful} listings!")
            else:
                print("[⚠️] No listings were successfully completed")
        else:
            print("[❌] Bulk upload failed, cannot proceed with completion")
    
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

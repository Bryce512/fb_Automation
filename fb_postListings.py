from datetime import datetime
import os, csv, time
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
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
                if (file_inputs and len(file_inputs) > 0):
                    file_inputs[0].send_keys(image)
                    time.sleep(0.25)  # Allow upload to start
                    uploaded_count += 1
                    print(f"[📸] Uploaded primary image: {os.path.basename(image)}")
                else:
                    # If no file input found, try clicking a photo button first
                    photo_buttons = driver.find_elements(By.XPATH, "//span[contains(text(), 'Add Photo')]")
                    if (photo_buttons and len(photo_buttons) > 0):
                        driver.execute_script("arguments[0].click();", photo_buttons[0])
                        time.sleep(0.3)  # Wait for file dialog to appear
                        
                        # Look for file input again
                        file_inputs = driver.find_elements(By.XPATH, "//input[@type='file']")
                        if (file_inputs and len(file_inputs) > 0):
                            file_inputs[0].send_keys(image_paths[i])
                            time.sleep(0.1)
                            uploaded_count += 1
                            print(f"[📸] Uploaded primary image: {os.path.basename(image)}")
            else:  # For additional images
                # Look for "Add Photos" or "+" buttons for additional images
                add_buttons = driver.find_elements(By.XPATH, 
                    "//span[contains(text(), 'Add Photo') or contains(text(), 'Add More')]/..|"
                    "//div[contains(@aria-label, 'Add photo') or contains(@aria-label, 'Add more')]")
                
                if (add_buttons and len(add_buttons) > 0):
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
                        if (file_inputs and len(file_inputs) > 0):
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
                        if (file_inputs and len(file_inputs) > 0):
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
        
        if (hide_elements and len(hide_elements) > 0):
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
        
        if (hide_elements and len(hide_elements) > 0):
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
        
        if (next_buttons and len(next_buttons) > 0):
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
            
            if (publish_buttons and len(publish_buttons) > 0):
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
            if (elements and len(elements) > 0):
                print(f"[⚠️] Detected warning: '{text}'")
                
                # Look for "Stay on Page" or "Continue" buttons
                stay_buttons = driver.find_elements(By.XPATH, 
                    "//*[contains(text(), 'Stay') or contains(text(), 'Continue') or " +
                    "contains(text(), 'Cancel') or contains(text(), 'Try Again') or " +
                    "contains(text(), 'OK') or contains(text(), 'Okay')]")
                
                if (stay_buttons and len(stay_buttons) > 0):
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
        
        # 3. Price
        print("[🔍] Finding price field...")
        try:
            # First try to find the label/span with "Price" text
            price_label = find_element_by_text(driver, "Price", debug=debug)
            
            if price_label:
                print("[✓] Found price label, now finding the associated input")
                
                # Use JavaScript to find the actual input element (sibling or child)
                price_input = driver.execute_script("""
                    var label = arguments[0];
                    
                    // Try to find the input in the same container
                    var container = label.closest('div');
                    if (container) {
                        var input = container.querySelector('input[type="text"]');
                        if (input) return input;
                    }
                    
                    // If not found, look for inputs near the label
                    var inputs = document.querySelectorAll('input[type="text"]');
                    for (var i = 0; i < inputs.length; i++) {
                        var rect1 = label.getBoundingClientRect();
                        var rect2 = inputs[i].getBoundingClientRect();
                        // Check if input is near the label (within reasonable distance)
                        if (Math.abs(rect1.top - rect2.top) < 50) {
                            return inputs[i];
                        }
                    }
                    return null;
                """, price_label)
                
                if price_input:
                    # More human-like interaction
                    price_str = str(price)
                    
                    # 1. Focus the element first
                    driver.execute_script("arguments[0].focus();", price_input)
                    time.sleep(0.1)
                    
                    # 2. Clear using backspace/delete to be more human-like
                    driver.execute_script("""
                        var input = arguments[0];
                        input.value = '';
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                    """, price_input)
                    
                    # 3. Type the price character by character like a human would
                    for char in price_str:
                        ActionChains(driver).send_keys(char).pause(0.05).perform()
                    
                    # 4. Press Tab to move to next field (this often triggers validation)
                    ActionChains(driver).send_keys(Keys.TAB).perform()
                    
                    print(f"[✅] Price set to {price_str} using human-like typing")
                    time.sleep(0.5)  # Wait for validation
                    
                    # 5. Verify the price was set correctly
                    current_value = driver.execute_script("return arguments[0].value;", price_input)
                    if current_value != price_str:
                        print(f"[⚠️] Price verification failed. Expected: {price_str}, Found: {current_value}")
                        
                        # Try one more time with direct method
                        driver.execute_script("""
                            var input = arguments[0];
                            var value = arguments[1];
                            input.value = value;
                            
                            // More extensive event simulation
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                            input.dispatchEvent(new Event('blur', { bubbles: true }));
                            
                            // Use React's synthetic events if available
                            if (window.React && window.React.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED) {
                                // Try to trigger React's synthetic events
                                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                                nativeInputValueSetter.call(input, value);
                            }
                        """, price_input, price_str)
                        
                        ActionChains(driver).send_keys(Keys.TAB).perform()
                        print("[🔄] Attempted alternative price setting method")
                    
                else:
                    handle_redirect_warning(driver, debug=debug)
                    print("[❌] Could not find price field")
                    return False
                
        except Exception as e:
            print(f"[❌] Error entering price: {e}")
            handle_redirect_warning(driver, debug=debug)
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
                        if (options and len(options) > 0):
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
            
            if (good_options and len(good_options) > 0):
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
        
        handle_redirect_warning(driver, debug=debug)

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

def main():
    global DEBUG_MODE, AUTO_PUBLISH
    DEBUG_MODE = False
    AUTO_PUBLISH = True
    sys.path.append(os.path.dirname(os.path.relpath("/fb_fetchData.py")))
    sys.path.append(os.path.dirname(os.path.relpath("/fb_renewListings.py")))
    from fb_fetchData import main as fetch_main
    from fb_renewListings import main as renew_main
    driver = get_driver()

    
    fetch_main()
    renew_main(driver)
    
    print("="*60)
    print("📦 Facebook Marketplace Listing Creator")
    print("="*60)
    print("\nThis tool automatically posts listings to Facebook Marketplace from a CSV file.")
    
    try:
        # Ask for debug mode
        # print("\n[❓] Enable debug mode with detailed logs? (y/n, default: n)")
        # DEBUG_MODE = input("> ").lower() == "y"  # Set global debug mode
        
        # Ask for CSV file path
        # print("\n[❓] Enter path to CSV file with listings (default: listings.csv):")
        csv_path = datetime.now().strftime("data_%Y-%m-%d") + "/listings_" + datetime.now().strftime("%Y-%m-%d") + ".csv"
        # csv_path = input("> ").strip() or "data_2025-04-27/listings_2025-04-27.csv"
        
        
        # Ask for auto-publish preference
        # print("\n[❓] Automatically publish listings without manual review? (y/n, default: n)")
        # AUTO_PUBLISH = input("> ").lower() == "y"  # Set global auto-publish flag
        
        if DEBUG_MODE:
            print(f"\n[🔧] Debug mode: {'ON' if DEBUG_MODE else 'OFF'}")
            print(f"[🔧] Auto-publish: {'ON' if AUTO_PUBLISH else 'OFF'}")
        
        # Process the CSV file
        print(f"\n[📂] Reading listings from {csv_path}...")
        
        try:
            with open(csv_path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                listings = list(reader)
                
                if not listings:
                    print("[⚠️] No listings found in the CSV file.")
                    return
                
                print(f"[📊] Found {len(listings)} listings to post.")
                
                
                successful = 0
                for i, row in enumerate(listings, 1):
                    print(f"\n[🔄] Posting listing {i}: {row.get('title', 'Unnamed listing')}")
                    
                    # Pass the auto_publish and debug_mode values through the global variables
                    success = post_listing(
                        driver,
                        title=row.get('title', ''),
                        price=row.get('price', ''),
                        description=row.get('description', ''),
                        category=row.get('category'),
                        location=row.get('location'),
                        images=row.get('images')
                    )
                    
                    if success:
                        successful += 1
                        print(f"[✅] Successfully posted: {row.get('title', 'Unnamed listing')}")
                    else:
                        print(f"[❌] Failed to post: {row.get('title', 'Unnamed listing')}")
                        # Ask if user wants to retry or continue
                        print("[❓] Retry this listing? (y/n, default: n)")
                        retry = input("> ").lower() == "y"
                        if retry:
                            print("[🔄] Retrying...")
                            if post_listing(
                                driver,
                                title=row.get('title', ''),
                                price=row.get('price', ''),
                                description=row.get('description', ''),
                                category=row.get('category'),
                                location=row.get('location'),
                                images=row.get('image_path')
                            ):
                                successful += 1
                                print(f"[✅] Successfully posted on retry: {row.get('title', 'Unnamed listing')}")
                    
                    # Ask if user wants to continue after each post
                    reset_browser_state(driver)
                
                print(f"\n[📊] Summary: Posted {successful}/{i} listings successfully.")
                
        except FileNotFoundError:
            print(f"[❌] CSV file not found: {csv_path}")
        except Exception as e:
            print(f"[❌] Error processing CSV: {e}")
    
    except Exception as e:
        print(f"\n[❌] An error occurred: {e}")
    
    finally:
        # Keep browser open until user decides to close
        # input("\n[🏁] Press Enter to close the browser and exit...")
        try:
            driver.quit()
        except:
            pass
        print("[👋] Goodbye!")

if __name__ == "__main__":
    main()

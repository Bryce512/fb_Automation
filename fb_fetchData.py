import os
import csv
import requests
from datetime import datetime, timedelta
import shutil

def create_directory(directory):
    """Create directory if it doesn't exist."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"[📁] Created directory: {directory}")
    return directory

def format_csv_friendly_text(text):
    """Format text to be CSV friendly by replacing quotes and newlines."""
    if text:
        # Replace double quotes with two double quotes (CSV escape format)
        text = text.replace('"', '""')
        # Replace newlines with spaces
        text = text.replace('\n', ' ')
    return text

def query_database(start_date, end_date):
    """Query the Hasura GraphQL database for listings within the date range."""
    print(f"[🔍] Querying database for listings between {start_date} and {end_date}...")
    
    # The correct GraphQL query format
    graphql_query = """
    query PublishedListings {
        listing(
            where: {
                is_published: {_eq: true},
                created_at: {_gte: "%s", _lte: "%s"}
            },
            order_by: {created_at: desc}
        ) {
            id
            title
            description
            base_price
            created_at
            listing_addresses {
                address_id
                list_id
                user_address {
                    city
                    state
                    zipcode
                }
            }
            listing_photos {
                name
            }
        }
    }
    """ % (start_date, end_date)
    
    # Payload for the POST request
    payload = {
        "query": graphql_query
    }
    
    # Make the API request
    try:
        response = requests.post(
            "https://yoodlize-hasura.herokuapp.com/v1/graphql",
            headers={"Content-Type": "application/json"},
            json=payload  # Using json parameter automatically handles JSON serialization
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Debug response
            if "data" not in data:
                print(f"[⚠️] Unexpected response format: {data}")
                return []
                
            listings = data.get("data", {}).get("listing", [])
            print(f"[✅] Retrieved {len(listings)} listings from database")
            
            # Debug first listing if available
            if listings and len(listings) > 0:
                print(f"[📄] First listing title: {listings[0].get('title', 'No title')}")
            
            return listings
        else:
            print(f"[❌] API request failed with status code: {response.status_code}")
            print(f"[❌] Error response: {response.text}")
            return []
            
    except Exception as e:
        print(f"[❌] Error querying database: {e}")
        return []

def download_images(listings, base_dir):
    """Download images for all listings."""
    image_base_url = "https://imagedelivery.net/yADbhFAVNAgt-DPVJpPhhg"
    
    # Track successful downloads and errors
    successful = 0
    failed = 0
    
    for listing in listings:
        listing_id = listing.get("id")
        photos = listing.get("listing_photos", [])
        
        if not photos:
            print(f"[⚠️] No photos for listing {listing_id}: {listing.get('title')}")
            continue
            
        # Create a list to store local image paths
        listing["local_images"] = []
        
        for idx, photo in enumerate(photos):
            image_name = photo.get("name")
            if not image_name:
                continue
                
            # Construct image URL
            image_url = f"{image_base_url}/{image_name}/public"
            
            # Construct local file path
            local_path = os.path.join(base_dir, f"{image_name}.jpg")
            
            # Download the image
            try:
                response = requests.get(image_url, stream=True)
                if response.status_code == 200:
                    with open(local_path, 'wb') as f:
                        response.raw.decode_content = True
                        shutil.copyfileobj(response.raw, f)
                    
                    # Add to the listing's local images
                    listing["local_images"].append(local_path)
                    successful += 1
                    
                    # Only print for the first image of each listing
                    # if idx == 0:
                        # print(f"[📸] Downloaded image for: {listing.get('title')}")
                else:
                    print(f"[❌] Failed to download image {image_name}: HTTP {response.status_code}")
                    failed += 1
            except Exception as e:
                print(f"[❌] Error downloading image {image_name}: {e}")
                failed += 1
    
    print(f"[📊] Image download summary: {successful} successful, {failed} failed")
    return listings

# Add this function to sanitize text for BMP compatibility
def sanitize_for_bmp(text):
    """
    Remove non-BMP characters that would cause ChromeDriver errors.
    BMP characters are those with Unicode code points below U+10000.
    """
    if not text:
        return ""
        
    # Filter out non-BMP characters
    sanitized = ''.join(c for c in text if ord(c) < 0x10000)
    
    # If characters were removed, add a note
    if len(sanitized) < len(text):
        removed_count = len(text) - len(sanitized)
        print(f"[⚠️] Removed {removed_count} non-BMP characters from description")
        
    return sanitized

def create_csv(listings, output_file):
    """Create a CSV file with listing information for Facebook Marketplace."""
    print(f"[📝] Creating CSV file: {output_file}")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow(["id", "title", "price", "description", "images", "location"])
        
        count = 0
        for listing in listings:
            # Skip listings without images
            if not listing.get("local_images"):
                continue

            id = listing.get("id", "")

            getTitle = listing.get("title", "")
            # Sanitize title
            getTitle = sanitize_for_bmp(getTitle)
                
            # Ensure title doesn't exceed 95 characters (including prefix)
            prefix = 'Rent a '
            max_title_length = 95
            
            # Check if title would be too long
            if len(prefix + getTitle) > max_title_length:
                # Truncate the title and add ellipsis
                available_length = max_title_length - len(prefix) - 3  # 3 chars for "..."
                getTitle = getTitle[:available_length] + "..."
                print(f"[✂️] Truncated title: {getTitle}")
            
            title = f'{prefix}{getTitle}'
            
            # Get the random description and sanitize
            random_desc = sanitize_for_bmp(get_random_description(getTitle))
            
            # Sanitize the main description from the database
            main_desc = sanitize_for_bmp(format_csv_friendly_text(listing.get("description", "")))
            
            # Combine with line break marker
            description = f'{random_desc} [BREAK] {main_desc}'
            
            price = int(listing.get("base_price", 0)/100)
            
            # Get location
            location = ""
            addresses = listing.get("listing_addresses", [])
            if addresses and addresses[0].get("user_address"):
                user_address = addresses[0]["user_address"]
                city = sanitize_for_bmp(user_address.get("city", ""))
                state = sanitize_for_bmp(user_address.get("state", ""))
                zipcode = sanitize_for_bmp(user_address.get("zipcode", ""))
                
                if zipcode:
                    location = zipcode
                elif city and state:
                    location = f"{city}, {state}"
                elif city:
                    location = city
            
            # Use the first image for the listing
            image_path = listing.get("local_images", [""])
            
            # Write the row
            writer.writerow([id, title, price, description, image_path, location])
            count += 1
    
    print(f"[✅] Created CSV with {count} listings")
    return count

def get_random_description(title):
    """Generate a random description for the listing."""
    i = hash(title) % 5  # Simple hash to get a number between 0 and 4
    descriptions = [
        f"I'm renting my {title} on the Yoodlize App! Check it out!",
        f"Check out my {title} for rent on the Yoodlize App!",
        f"Looking to rent my {title} through the Yoodlize App. Let me know if you're interested!",
        f"Renting out my {title} on the Yoodlize App. Message me for details!",
        f"Have a look at my {title} for rent on the Yoodlize App!",
    ]
    return descriptions[i % len(descriptions)]
    
def main():
    print("="*60)
    print("📦 Facebook Marketplace Data Fetcher")
    print("="*60)
    print("\nThis tool fetches listing data from the database and prepares it for posting.")
    
    try:
        # print("\n[❓] Which date range would you like to fetch?")
        # print("1. Yesterday")
        # print("2. Today")
        # print("3. Custom date range")
        # choice = input("> ")
        
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # if choice == "1":
            # Yesterday
        end_date = today - timedelta(seconds=1)  # 23:59:59 of yesterday
        start_date = end_date.replace(hour=0, minute=0, second=0)  # 00:00:00 of yesterday
        # elif choice == "2":
        #     # Today
        #     start_date = today
        #     end_date = datetime.now()
        # elif choice == "3":
        #     # Custom range
        #     print("\n[❓] Enter start date (YYYY-MM-DD):")
        #     start_date_str = input("> ")
        #     print("[❓] Enter end date (YYYY-MM-DD):")
        #     end_date_str = input("> ")
            
            # try:
            #     start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            #     end_date = datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1, seconds=-1)
            # except ValueError:
            #     print("[❌] Invalid date format. Using yesterday as default.")
            #     end_date = today - timedelta(seconds=1)
            #     start_date = end_date.replace(hour=0, minute=0, second=0)
        # else:
            # print("[⚠️] Invalid choice. Using yesterday as default.")
            # end_date = today - timedelta(seconds=1)
            # start_date = end_date.replace(hour=0, minute=0, second=0)
        
        # Format dates for query
        start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+00:00"
        end_date_str = end_date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+00:00"
        
        print(f"\n[📅] Fetching listings from {start_date.strftime('%Y-%m-%d %H:%M:%S')} to {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Create directory for today's date
        date_str = datetime.now().strftime("%Y-%m-%d")
        base_dir = create_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"data_{date_str}"))
        images_dir = create_directory(os.path.join(base_dir, "images"))
        
        # Query the database
        listings = query_database(start_date_str, end_date_str)
        
        if not listings:
            print("[⚠️] No listings found for the specified date range.")
            return
        
        # Download images
        listings_with_images = download_images(listings, images_dir)
        
        # Create CSV file
        csv_file = os.path.join(base_dir, f"listings_{date_str}.csv")
        create_csv(listings_with_images, csv_file)
        
        print("\n[🎉] Data fetch complete!")
        print(f"[📁] CSV file: {csv_file}")
        print(f"[📁] Images directory: {images_dir}")
        print("\n[ℹ️] You can now use the CSV file with fb_postNewListings.py to post these listings.")
        
    except Exception as e:
        print(f"\n[❌] An error occurred: {e}")
    
    print("\n[👋] Done!")

if __name__ == "__main__":
    main()
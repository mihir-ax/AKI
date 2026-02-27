import requests
from config import SHORTENER_API_URL, SHORTENER_API_KEY

def shorten_url(original_url, is_monetized=False):
    """
    Shorten a URL using ShortXLinks API.
    
    Args:
        original_url (str): The URL to shorten
        is_monetized (bool): Whether to monetize the shortened URL
    
    Returns:
        str: The shortened URL or None if failed
    """
    if not original_url:
        print("Error: No URL provided")
        return None
    
    headers = {
        "Authorization": f"Bearer {SHORTENER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "originalUrl": original_url,
        "isMonetized": is_monetized
    }

    try:
        response = requests.post(
            SHORTENER_API_URL, 
            headers=headers, 
            json=data,
            timeout=10  # Add timeout to prevent hanging
        )
        
        # Check if request was successful
        response.raise_for_status()
        
        res_data = response.json()
        
        if res_data.get("success"):
            short_url = res_data.get("shortUrl")
            if short_url:
                return short_url
            else:
                print("Error: No shortUrl in response")
        else:
            error_msg = res_data.get("message", "Unknown error")
            print(f"API Error: {error_msg}")
            
    except requests.exceptions.Timeout:
        print("Error: Request timed out")
    except requests.exceptions.ConnectionError:
        print("Error: Connection error - check your internet")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Request Error: {e}")
    except ValueError as e:
        print(f"JSON Decode Error: {e}")
    except Exception as e:
        print(f"Unexpected Error: {e}")
    
    return None

# Optional: Add a convenience function for monetized URLs
def shorten_url_monetized(original_url):
    """Shorten a URL with monetization enabled"""
    return shorten_url(original_url, is_monetized=True)

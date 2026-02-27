import requests
import urllib.parse
from config import SHORTENER_API_URL, SHORTENER_API_KEY

def shorten_url(original_url):
    """
    Shorten a URL using ShortXLinks API.
    """
    if not SHORTENER_API_KEY or SHORTENER_API_KEY == " ":
        print("❌ ERROR: SHORTENER_API_KEY is not set in .env file!")
        return None

    # Adhiktar shorteners is format ko use karte hain (GET Method)
    # Format: https://site.com/api?api=KEY&url=LINK
    
    # Hum URL ko encode karenge taaki special characters (?) issue na karein
    encoded_url = urllib.parse.quote(original_url)
    
    # Agar aapka API URL 'http://shortxlinks.com/api/v1/shorten' hai, 
    # toh ho sakta hai wo GET request accept kare is tarah:
    # Par shortener sites ka standard API endpoint aksar ye hota hai:
    # "https://shortxlinks.com/api" 
    
    api_endpoint = SHORTENER_API_URL.replace("/v1/shorten", "") # Clean the path if necessary
    
    params = {
        "api": SHORTENER_API_KEY,
        "url": original_url
    }

    try:
        # Hum GET request try kar rahe hain kyunki ye standard hai
        response = requests.get(api_endpoint, params=params, timeout=10)
        
        # Log for debugging (Aap terminal mein check kar sakte hain kya response aa raha hai)
        print(f"DEBUG: Shortener Status Code: {response.status_code}")
        
        res_data = response.json()
        print(f"DEBUG: API Response: {res_data}")

        # Shortener sites aksar ye keys use karti hain: 'shortened_url' ya 'link' ya 'url'
        if res_data.get("status") == "success" or res_data.get("shortened_url"):
            return res_data.get("shortened_url") or res_data.get("link") or res_data.get("url")
        
        # Agar upar wala kaam nahi kiya, toh hum aapka purana POST method try karenge
        # Lekin keys ko check karte hue
        headers = {"Authorization": f"Bearer {SHORTENER_API_KEY}"}
        json_data = {"originalUrl": original_url}
        
        post_res = requests.post(SHORTENER_API_URL, headers=headers, json=json_data, timeout=10)
        post_data = post_res.json()
        
        if post_data.get("success"):
            return post_data.get("shortUrl") or post_data.get("shortened_url")

    except Exception as e:
        print(f"❌ Shortener Error: {str(e)}")
    
    return None

import requests
from config import SHORTENER_API_URL, SHORTENER_API_KEY

def shorten_url(original_url):
    """
    Shorten a URL using ShortXLinks API.
    Returns the shortened URL or None if failed.
    """
    headers = {
        "Authorization": f"Bearer {SHORTENER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "originalUrl": original_url
    }

    try:
        response = requests.post(SHORTENER_API_URL, headers=headers, json=data)
        res_data = response.json()
        if res_data.get("success"):
            return res_data.get("shortUrl")
    except Exception as e:
        print(f"Error shortening URL: {e}")
    
    return None

import aiohttp
import urllib.parse

async def shorten_url(original_url, api_url, api_key):
    """
    Shorten a URL using dynamic API settings.
    """
    if not api_key or api_key.strip() == "":
        print("❌ ERROR: SHORTENER_API_KEY is missing!")
        return None

    # URL encode zaroori nahi hai params dict use karte waqt, aiohttp khud kar leta hai, 
    # but agar specific requirement hai toh theek hai.
    api_endpoint = api_url.replace("/v1/shorten", "") # Clean standard path

    params = {
        "api": api_key,
        "url": original_url
    }

    try:
        async with aiohttp.ClientSession() as session:
            # First try GET (Ye wala trigger hoga shortxlinks ke liye)
            async with session.get(api_endpoint, params=params, timeout=10) as response:
                # content_type=None ignore karega agar API ne galat header bheja
                res_data = await response.json(content_type=None) 
                
                if res_data.get("status") == "success" or res_data.get("shortenedUrl"):
                    # YAHAN ADD KIYA HAI "shortenedUrl" (CamelCase)
                    return res_data.get("shortenedUrl") or res_data.get("shortened_url") or res_data.get("link") or res_data.get("url")

            # Fallback to POST (Agar dusra koi API use kiya toh)
            headers = {"Authorization": f"Bearer {api_key}"}
            json_data = {"originalUrl": original_url}
            async with session.post(api_endpoint, headers=headers, json=json_data, timeout=10) as post_res:
                post_data = await post_res.json(content_type=None)
                if post_data.get("success") or post_data.get("status") == "success":
                    return post_data.get("shortUrl") or post_data.get("shortened_url") or post_data.get("shortenedUrl")

    except Exception as e:
        print(f"❌ Shortener Error: {str(e)}")

    return None

import aiohttp
import urllib.parse

async def shorten_url(original_url, api_url, api_key):
    """
    Shorten a URL using dynamic API settings.
    """
    if not api_key or api_key == " ":
        print("❌ ERROR: SHORTENER_API_KEY is missing!")
        return None

    encoded_url = urllib.parse.quote(original_url)
    api_endpoint = api_url.replace("/v1/shorten", "") # Clean standard path

    params = {
        "api": api_key,
        "url": original_url
    }

    try:
        async with aiohttp.ClientSession() as session:
            # First try GET
            async with session.get(api_endpoint, params=params, timeout=10) as response:
                res_data = await response.json()
                if res_data.get("status") == "success" or res_data.get("shortened_url"):
                    return res_data.get("shortened_url") or res_data.get("link") or res_data.get("url")

            # Fallback to POST
            headers = {"Authorization": f"Bearer {api_key}"}
            json_data = {"originalUrl": original_url}
            async with session.post(api_url, headers=headers, json=json_data, timeout=10) as post_res:
                post_data = await post_res.json()
                if post_data.get("success"):
                    return post_data.get("shortUrl") or post_data.get("shortened_url")

    except Exception as e:
        print(f"❌ Shortener Error: {str(e)}")

    return None

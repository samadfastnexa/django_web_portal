import http.client
import json
from django.conf import settings

def identify_crop(image_base64: str) -> dict:
    """
    Identifies a crop from a base64 encoded image using the Kindwise API.
    
    Args:
        image_base64 (str): The base64 encoded string of the image.
        
    Returns:
        dict: The API response containing identification results.
    """
    conn = http.client.HTTPSConnection("crop.kindwise.com")
    
    payload = json.dumps({
        "images": [image_base64],
        "similar_images": True
    })
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Api-Key': getattr(settings, 'KINDWISE_API_KEY', ''),
    }

    try:
        conn.request("POST", "/api/v1/identification", payload, headers)
        res = conn.getresponse()
        data = res.read()
        text = data.decode("utf-8", errors="replace") if data else ""
        # Treat 200/201/202 as successful responses
        if res.status not in (200, 201, 202):
            return {
                "error": "Kindwise API error",
                "status": res.status,
                "reason": res.reason,
                "body": text[:1000],
            }
        try:
            return json.loads(text)
        except Exception as e:
            return {
                "error": f"Invalid JSON from Kindwise: {e}",
                "status": res.status,
                "body": text[:1000],
            }
    except Exception as e:
        return {"error": str(e)}

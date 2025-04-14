from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup
import io
import re
from typing import Optional, List
import time
from PIL import Image
import base64

app = FastAPI(
    title="Enhanced Icon API",
    description="Advanced API to fetch and process transparent icons from Google Images",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def process_image(image_data: bytes, size: Optional[int] = None, format: str = 'PNG') -> tuple[bytes, str]:
    """
    Process the image data - resize and convert if needed
    """
    img = Image.open(io.BytesIO(image_data))
    
    # Convert to RGBA if not already
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Resize if size is specified
    if size:
        img = img.resize((size, size), Image.Resampling.LANCZOS)
    
    # Save to bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format=format, optimize=True, quality=90)
    img_byte_arr.seek(0)
    
    return img_byte_arr.getvalue(), f"image/{format.lower()}"

def get_google_image_data(query: str, max_retries: int = 3) -> List[tuple[bytes, str]]:
    """
    Get multiple image results from Google Images
    Returns list of (image_data, content_type) tuples
    """
    search_query = f"{query} icon transparent"
    url = f"https://www.google.com/search?q={search_query}&tbm=isch&tbs=ic:trans"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1"
    }
    
    results = []
    session = requests.Session()
    
    try:
        for attempt in range(max_retries):
            try:
                response = session.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                break
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(1)
        
        # Look for image URLs in different patterns
        patterns = [
            r'\["(https://[^"]+\.(?:png|jpg|jpeg|gif))",[^]]+\]',
            r'imgurl=(https://[^&]+\.(?:png|jpg|jpeg|gif))',
            r'src="(https://[^"]+\.(?:png|jpg|jpeg|gif))"'
        ]
        
        all_matches = []
        for pattern in patterns:
            matches = re.findall(pattern, response.text)
            all_matches.extend(matches)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = [x for x in all_matches if not (x in seen or seen.add(x))]
        
        # Try to get up to 3 valid images
        for img_url in unique_urls[:5]:  # Try first 5 URLs to get 3 valid ones
            try:
                img_response = session.get(img_url, headers={
                    "User-Agent": headers["User-Agent"],
                    "Referer": url
                }, timeout=10)
                img_response.raise_for_status()
                
                # Verify it's a valid image
                Image.open(io.BytesIO(img_response.content))
                
                results.append((img_response.content, img_response.headers.get('content-type', 'image/png')))
                if len(results) >= 3:
                    break
            except Exception as e:
                print(f"Skipping invalid image URL: {img_url}, Error: {str(e)}")
                continue
        
    except Exception as e:
        print(f"Error getting image data: {str(e)}")
    
    return results

@app.get("/{query}")
async def get_icon(
    query: str,
    size: Optional[int] = Query(None, gt=0, lt=1001, description="Size of the output image in pixels"),
    format: str = Query("PNG", regex="^(PNG|JPEG|GIF)$", description="Output image format"),
    index: int = Query(0, ge=0, lt=3, description="Index of the image to return (0-2)")
):
    """
    Enhanced endpoint to fetch and return the icon image with processing options
    """
    results = get_google_image_data(query)
    
    if not results:
        raise HTTPException(status_code=404, detail="No suitable icons found")
    
    try:
        image_data, content_type = results[min(index, len(results) - 1)]
        
        # Process the image if needed
        if size or format != "PNG":
            image_data, content_type = process_image(image_data, size, format)
        
        return StreamingResponse(
            io.BytesIO(image_data),
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=86400",
                "X-Total-Results": str(len(results))
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

# Add a base64 endpoint for direct embedding
@app.get("/{query}/base64")
async def get_icon_base64(
    query: str,
    size: Optional[int] = Query(None, gt=0, lt=1001),
    format: str = Query("PNG", regex="^(PNG|JPEG|GIF)$"),
    index: int = Query(0, ge=0, lt=3)
):
    """
    Get the icon as a base64 string for direct embedding
    """
    results = get_google_image_data(query)
    
    if not results:
        raise HTTPException(status_code=404, detail="No suitable icons found")
    
    try:
        image_data, _ = results[min(index, len(results) - 1)]
        
        if size or format != "PNG":
            image_data, content_type = process_image(image_data, size, format)
        
        base64_data = base64.b64encode(image_data).decode()
        return {
            "base64": f"data:image/{format.lower()};base64,{base64_data}",
            "total_results": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000) 
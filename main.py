from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup
import io
import re
from typing import Optional, List, Tuple, Union
import time
from PIL import Image
import base64
import cairosvg
import os
import sys
import uvicorn
import socket

# ASCII Art Banner
BANNER = """
╭━━━╮╱╱╱╱╱╱╱╱╱╱╭━━━╮╭━━━╮╭━━━╮
┃╭━╮┃╱╱╱╱╱╱╱╱╱╱┃╭━╮┃┃╭━━╯┃╭━╮┃
┃╰━━┳━━┳━╮╭━━╮┃┃╱┃┃┃╰━━╮┃╰━╯┃
╰━━╮┃╭╮┃╭╮┫┃━┫┃╰━╯┃┃╭━━╯┃╭━━╯
┃╰━╯┃╰╯┃┃┃┃┃━┫┃╭━╮┃┃╰━━╮┃┃
╰━━━┫╭━┻╯╰┻━━╯╰╯╱╰╯╰━━━╯╰╯
╱╱╱╱┃┃
╱╱╱╱╰╯
"""

app = FastAPI(
    title="Enhanced Icon API",
    description="Advanced API to fetch and process transparent icons from Google Images",
    version="2.1.0"
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
    # Handle SVG conversion if needed
    if format.upper() == 'SVG':
        try:
            # If the input is already SVG, return it as is
            if image_data[:5].lower() == b'<?xml' or image_data[:4].lower() == b'<svg':
                return image_data, "image/svg+xml"
            
            # Convert to PNG first if it's not SVG
            img = Image.open(io.BytesIO(image_data))
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
                
            # Resize if needed
            if size:
                img = img.resize((size, size), Image.Resampling.LANCZOS)
                
            # Save as PNG
            png_data = io.BytesIO()
            img.save(png_data, format='PNG')
            png_data.seek(0)
            
            # Convert PNG to SVG (very basic conversion)
            svg_data = f"""<svg width="{img.width}" height="{img.height}" xmlns="http://www.w3.org/2000/svg">
                          <image width="100%" height="100%" href="data:image/png;base64,{base64.b64encode(png_data.getvalue()).decode()}" />
                          </svg>"""
            
            return svg_data.encode(), "image/svg+xml"
        except Exception as e:
            print(f"SVG conversion error: {str(e)}")
            # Fallback to PNG if SVG conversion fails
            format = 'PNG'
    
    # Regular image processing for non-SVG formats
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
            r'\["(https://[^"]+\.(?:png|jpg|jpeg|gif|svg))",[^]]+\]',
            r'imgurl=(https://[^&]+\.(?:png|jpg|jpeg|gif|svg))',
            r'src="(https://[^"]+\.(?:png|jpg|jpeg|gif|svg))"'
        ]
        
        all_matches = []
        for pattern in patterns:
            matches = re.findall(pattern, response.text)
            all_matches.extend(matches)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = [x for x in all_matches if not (x in seen or seen.add(x))]
        
        # Try to get up to 10 valid images
        for img_url in unique_urls[:15]:  # Try first 15 URLs to get up to 10 valid ones
            try:
                img_response = session.get(img_url, headers={
                    "User-Agent": headers["User-Agent"],
                    "Referer": url
                }, timeout=10)
                img_response.raise_for_status()
                
                # Verify it's a valid image
                content_type = img_response.headers.get('content-type', '')
                
                # Special handling for SVG
                if 'svg' in content_type or img_url.lower().endswith('.svg'):
                    # Just ensure it's valid XML
                    if img_response.content[:5].lower() == b'<?xml' or img_response.content[:4].lower() == b'<svg':
                        results.append((img_response.content, "image/svg+xml"))
                else:
                    # For other images, verify with PIL
                    Image.open(io.BytesIO(img_response.content))
                    results.append((img_response.content, img_response.headers.get('content-type', 'image/png')))
                
                if len(results) >= 10:
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
    format: str = Query("PNG", regex="^(PNG|JPEG|GIF|SVG)$", description="Output image format"),
    index: int = Query(0, ge=0, lt=10, description="Index of the image to return (0-9)")
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
        if size or format.upper() != content_type.split('/')[-1].upper():
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
    format: str = Query("PNG", regex="^(PNG|JPEG|GIF|SVG)$"),
    index: int = Query(0, ge=0, lt=10)
):
    """
    Get the icon as a base64 string for direct embedding
    """
    results = get_google_image_data(query)
    
    if not results:
        raise HTTPException(status_code=404, detail="No suitable icons found")
    
    try:
        image_data, content_type = results[min(index, len(results) - 1)]
        
        if size or format.upper() != content_type.split('/')[-1].upper():
            image_data, content_type = process_image(image_data, size, format)
        
        base64_data = base64.b64encode(image_data).decode()
        
        # For SVG, the content type should be "image/svg+xml"
        mime_type = "image/svg+xml" if format.upper() == "SVG" else f"image/{format.lower()}"
        
        return {
            "base64": f"data:{mime_type};base64,{base64_data}",
            "total_results": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

def get_local_ip():
    """Get the local IP address"""
    try:
        # Create a socket to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "localhost"

def print_startup_message(host, port):
    """Print a detailed startup message with usage examples"""
    local_ip = get_local_ip()
    
    # Clear terminal
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Print banner and basic info
    print(f"\033[1;36m{BANNER}\033[0m")
    print(f"\033[1;32m✅ Icon API Server v2.1.0 is running!\033[0m")
    print(f"\033[1;37m{'='*80}\033[0m")
    
    # Docker detection
    in_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER') or os.environ.get('KUBERNETES_SERVICE_HOST')
    if in_docker:
        print(f"\033[1;33m🐳 Running inside Docker container\033[0m")
    
    # API URLs
    print(f"\033[1;34m🌐 API URLs:\033[0m")
    print(f"   \033[1;37m• Local:\033[0m      \033[1;36mhttp://localhost:{port}\033[0m")
    print(f"   \033[1;37m• Network:\033[0m    \033[1;36mhttp://{local_ip}:{port}\033[0m")
    if host == "0.0.0.0":
        print(f"   \033[1;37m• Container:\033[0m  \033[1;36mhttp://{socket.gethostname()}:{port}\033[0m")
    
    # Documentation URLs
    print(f"\033[1;34m📚 Documentation:\033[0m")
    print(f"   \033[1;37m• Swagger UI:\033[0m  \033[1;36mhttp://localhost:{port}/docs\033[0m")
    print(f"   \033[1;37m• ReDoc:\033[0m       \033[1;36mhttp://localhost:{port}/redoc\033[0m")
    print(f"   \033[1;37m• OpenAPI:\033[0m     \033[1;36mhttp://localhost:{port}/openapi.json\033[0m")
    
    # Example usage
    print(f"\033[1;34m🔍 Example Usage:\033[0m")
    print(f"   \033[1;37m• Basic icon:\033[0m           \033[1;36mhttp://localhost:{port}/github\033[0m")
    print(f"   \033[1;37m• With size:\033[0m            \033[1;36mhttp://localhost:{port}/python?size=64\033[0m")
    print(f"   \033[1;37m• Format conversion:\033[0m    \033[1;36mhttp://localhost:{port}/react?format=SVG\033[0m")
    print(f"   \033[1;37m• Alternative result:\033[0m   \033[1;36mhttp://localhost:{port}/docker?index=2\033[0m")
    print(f"   \033[1;37m• Base64 encoding:\033[0m      \033[1;36mhttp://localhost:{port}/nodejs/base64\033[0m")
    
    # Help info
    print(f"\033[1;37m{'='*80}\033[0m")
    print(f"\033[1;33m⚠️  Note: This API scrapes Google Images for transparent icons.\033[0m")
    print(f"\033[1;33m    First request might be slow as it needs to search and process images.\033[0m")
    print(f"\033[1;32m🚀 Press Ctrl+C to stop the server\033[0m")
    print(f"\033[1;37m{'='*80}\033[0m")
    sys.stdout.flush()

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 1234))
    
    # Print startup message
    print_startup_message(host, port)
    
    # Start server
    uvicorn.run(app, host=host, port=port) 
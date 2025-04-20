# Icon API

A powerful FastAPI service that fetches transparent icons from Google Images and serves them with various processing options.

## Features

- 🔍 Search for icons using natural language queries
- 🖼️ Returns transparent PNG icons by default
- 🔄 Multiple image options with indexing support (up to 10 results)
- 📐 Resize images on-the-fly with size parameter
- 🔡 Format conversion (PNG, JPEG, GIF, SVG)
- 📦 Base64 encoding for direct HTML embedding
- 🐳 Fully Dockerized for easy deployment

## API Endpoints

### Get Icon Image

```
GET /{query}?size={size}&format={format}&index={index}
```

Parameters:
- `query`: Search term for the icon (e.g., "coffee", "pizza", "facebook")
- `size` (optional): Size in pixels for the output image (1-1000)
- `format` (optional): Output format ("PNG", "JPEG", "GIF", or "SVG"). Default: "PNG" 
- `index` (optional): Which image result to return (0-9). Default: 0 (first result)

### Get Base64 Encoded Icon

```
GET /{query}/base64?size={size}&format={format}&index={index}
```

Returns JSON with base64 data ready to use in HTML/CSS:
```json
{
  "base64": "data:image/png;base64,iVBORw0KGgoAAA...",
  "total_results": 10
}
```

## Quick Start

### Using Docker

Pull the image from Docker Hub:

```bash
docker pull r04nx/icon-api:latest
```

Run the container:

```bash
docker run -p 5000:5000 r04nx/icon-api:latest
```

### Using Docker Compose

```bash
docker-compose up -d
```

## Usage Examples

### Basic Icon Request

Get a coffee icon:
```
http://localhost:5000/coffee
```

### With Size Parameter

Get a 64x64 GitHub icon:
```
http://localhost:5000/github?size=64
```

### Format Conversion

Get a Facebook icon in SVG format:
```
http://localhost:5000/facebook?format=SVG
```

### Alternative Image Results

Get the fifth result for a Twitter icon:
```
http://localhost:5000/twitter?index=4
```

### Base64 Encoding

Get a base64-encoded Python icon for direct HTML embedding:
```
http://localhost:5000/python/base64?format=SVG
```

Then use in HTML:
```html
<img src="data:image/svg+xml;base64,iVBORw0KGgoAAA...">
```

## Build Locally

1. Clone the repository:
```bash
git clone https://github.com/r04nx/icon-api.git
cd icon-api
```

2. Build the Docker image:
```bash
docker build -t icon-api .
```

3. Run the container:
```bash
docker run -p 5000:5000 icon-api
```

## Docker Image Rebuild

To rebuild the Docker image after changes:

```bash
# Build the new image
docker build -t icon-api:latest .

# Stop and remove any running container using the old image
docker stop icon-api-container || true
docker rm icon-api-container || true

# Run the new container
docker run -d -p 5000:5000 --name icon-api-container icon-api:latest
```

## Push to Docker Hub

If you want to push your own version to Docker Hub:

```bash
# Tag the image
docker tag icon-api:latest yourusername/icon-api:latest

# Login to Docker Hub
docker login

# Push the image
docker push yourusername/icon-api:latest
```

## Environmental Variables

- `HOST`: Host to bind (default: 0.0.0.0)
- `PORT`: Port to listen on (default: 5000)

## Technologies Used

- FastAPI - High-performance web framework
- Pillow - Python Imaging Library
- CairoSVG - SVG handling and conversion
- BeautifulSoup4 - Web scraping
- Uvicorn - ASGI server
- Docker - Containerization

## SVG Support Notes

The SVG support works in two ways:
1. Finding SVG images directly from search results
2. Converting other image formats to SVG when requested

For best results with SVG:
- Use with simple icons rather than complex images
- Specify a size parameter for better quality
- SVG conversion is basic and embeds PNG data for complex images

## License

MIT

## Disclaimer

This API is for educational purposes only. Use responsibly and consider Google's terms of service when deploying to production environments.

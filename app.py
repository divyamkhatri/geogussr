from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import json
import math
from pathlib import Path
import asyncio
import random
import re
from shapely.geometry import shape, Point
from playwright.async_api import async_playwright
import cv2
import numpy as np

app = Flask(__name__)
CORS(app)

# Store current game data
current_game = {
    'actual_lat': None,
    'actual_lon': None,
    'embed_url': None,
    'panoid': None
}

# Regex for panoid
PANOID_RE = re.compile(r"[?&]panoid=([A-Za-z0-9_\-]+)")

async def detect_blue_line(page):
    """Detect a blue Street View line by color filter in screenshot."""
    await page.screenshot(path="screenshot.png", full_page=True)
    image = cv2.imread("screenshot.png")
    if image is None:
        return None

    height, width, _ = image.shape
    top_crop, bottom_crop = 150, height - 150
    left_crop, right_crop = 500, width - 50
    cropped = image[top_crop:bottom_crop, left_crop:right_crop]

    hsv = cv2.cvtColor(cropped, cv2.COLOR_BGR2HSV)
    lower_blue = np.array([90, 80, 180])
    upper_blue = np.array([130, 255, 255])
    mask = cv2.inRange(hsv, lower_blue, upper_blue)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    largest = max(contours, key=cv2.contourArea)
    M = cv2.moments(largest)
    if M["m00"] == 0:
        return None

    cx = int(M["m10"] / M["m00"]) + left_crop
    cy = int(M["m01"] / M["m00"]) + top_crop
    return cx, cy

def load_polygon(map_input):
    """Load polygon either from path or from GeoJSON dict."""
    data = None
    if isinstance(map_input, (str, Path)):  # file path
        path = Path(map_input)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    elif isinstance(map_input, dict):  # already a dict
        data = map_input
    else:
        raise TypeError(f"Unsupported map_input type: {type(map_input)}")

    return shape(data["features"][0]["geometry"])

def get_random_point(polygon):
    minx, miny, maxx, maxy = polygon.bounds
    while True:
        point = Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
        if polygon.contains(point):
            return point.y, point.x  # lat, lon

async def collect_panoids_async(map_input, target_count=1):
    polygon = load_polygon(map_input)
    pano_data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        pegman_clicked = False
        current_lat = current_lon = None

        def handle_request(request):
            nonlocal pano_data, current_lat, current_lon
            m = PANOID_RE.search(request.url)
            if m:
                panoid = m.group(1)
                if all(d["panoid"] != panoid for d in pano_data):
                    embed_url = (
                        f"https://www.google.com/maps/embed?pb=!4v{random.randint(1000000000000,9999999999999)}"
                        f"!6m8!1m7!1s{panoid}!2m2!1d{current_lat}!2d{current_lon}"
                        "!3f0!4f0!5f0.7820865974627469"
                    )
                    pano_data.append({
                        "panoid": panoid,
                        "lat": current_lat,
                        "lon": current_lon,
                        "embed_url": embed_url
                    })
                    print(f"[+] Collected {len(pano_data)}/{target_count} → {panoid}")

        page.on("request", handle_request)

        while len(pano_data) < target_count:
            lat, lon = get_random_point(polygon)
            current_lat, current_lon = lat, lon

            zoom = random.randint(14, 17)
            await page.goto(f"https://www.google.com/maps/@{lat},{lon},{zoom}z")

            if not pegman_clicked:
                try:
                    pegman = await page.wait_for_selector('div[style*="pegman_v3"]', timeout=7000)
                    await pegman.click()
                    pegman_clicked = True
                except:
                    continue

            await page.wait_for_timeout(3000)
            pos = await detect_blue_line(page)
            if pos:
                x, y = pos
                await page.mouse.move(x, y, steps=15)
                await page.wait_for_timeout(4000)

        await browser.close()
    return pano_data

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula."""
    R = 6371  # Earth's radius in kilometers
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

def get_max_distance_in_bounds(geojson_path):
    """Calculate the maximum possible distance within the bounding area."""
    try:
        with open(geojson_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Get the polygon coordinates
        coords = data['features'][0]['geometry']['coordinates'][0]
        
        # Find the maximum distance between any two points in the polygon
        max_dist = 0
        for i in range(len(coords)):
            for j in range(i + 1, len(coords)):
                dist = calculate_distance(coords[i][1], coords[i][0], coords[j][1], coords[j][0])
                max_dist = max(max_dist, dist)
        
        return max_dist
    except Exception as e:
        print(f"Error calculating max distance: {e}")
        return 1000  # Fallback value

def get_bounding_center(geojson_path):
    """Get the center point of the bounding area."""
    try:
        with open(geojson_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Get the polygon coordinates
        coords = data['features'][0]['geometry']['coordinates'][0]
        
        # Calculate center point
        lats = [coord[1] for coord in coords]
        lons = [coord[0] for coord in coords]
        
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        
        return center_lat, center_lon
    except Exception as e:
        print(f"Error calculating center: {e}")
        return 20, 0  # Fallback to world center

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_game', methods=['POST'])
def start_game():
    try:
        # Check if bounding.geojson exists
        bounding_file = Path('bounding.geojson')
        if not bounding_file.exists():
            return jsonify({'error': 'bounding.geojson not found in current directory'}), 404
        
        # Get a random street view location
        pano_data = asyncio.run(collect_panoids_async('bounding.geojson', 1))
        
        if not pano_data:
            return jsonify({'error': 'Could not find Street View location in the specified area'}), 500
        
        location = pano_data[0]
        
        # Store current game data
        current_game['actual_lat'] = location['lat']
        current_game['actual_lon'] = location['lon']
        current_game['embed_url'] = location['embed_url']
        current_game['panoid'] = location['panoid']
        
        return jsonify({
            'embed_url': location['embed_url'],
            'success': True
        })
        
    except Exception as e:
        print(f"Error starting game: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/submit_guess', methods=['POST'])
def submit_guess():
    try:
        data = request.get_json()
        guess_lat = data['lat']
        guess_lon = data['lon']
        
        if current_game['actual_lat'] is None:
            return jsonify({'error': 'No active game'}), 400
        
        # Calculate distance
        distance = calculate_distance(
            current_game['actual_lat'], 
            current_game['actual_lon'],
            guess_lat, 
            guess_lon
        )
        
        # Get max possible distance in the bounding area
        max_distance = get_max_distance_in_bounds('bounding.geojson')
        
        # Calculate score (5000 points max, linearly decreasing to 0 at max_distance)
        if distance >= max_distance:
            score = 0
        else:
            score = int(5000 * (1 - distance / max_distance))
        
        return jsonify({
            'distance_km': round(distance, 2),
            'score': score,
            'actual_lat': current_game['actual_lat'],
            'actual_lon': current_game['actual_lon'],
            'guess_lat': guess_lat,
            'guess_lon': guess_lon,
            'max_distance': round(max_distance, 2)
        })
        
    except Exception as e:
        print(f"Error submitting guess: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_bounds')
def get_bounds():
    try:
        bounding_file = Path('bounding.geojson')
        if not bounding_file.exists():
            return jsonify({'error': 'bounding.geojson not found'}), 404
            
        with open(bounding_file, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
        
        # Also calculate and include center point
        center_lat, center_lon = get_bounding_center(bounding_file)
        
        return jsonify({
            'geojson': geojson_data,
            'center_lat': center_lat,
            'center_lon': center_lon
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

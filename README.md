# GeoGuessr Clone Setup Instructions

## Prerequisites
- Python 3.8+
- `bounding.geojson` file in the project root directory

## Installation

0. **Set Venv**
```bash
python -m venv <directory>
```

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

2. **Install Playwright browsers:**
```bash
playwright install chromium
```

3. **Create the templates directory:**
```bash
mkdir templates
```

4. **File structure should look like this:**
```
project-folder/
├── app.py
├── requirements.txt
├── bounding.geojson
└── templates/
    └── index.html
```

## Running the Application

1. **Make sure you have a `bounding.geojson` file** in the root directory. This file should contain a GeoJSON polygon defining the area where Street View locations will be collected.

   Example `bounding.geojson` structure:
   ```json
   {
     "type": "FeatureCollection",
     "features": [
       {
         "type": "Feature",
         "geometry": {
           "type": "Polygon",
           "coordinates": [[
             [longitude1, latitude1],
             [longitude2, latitude2],
             [longitude3, latitude3],
             [longitude4, latitude4],
             [longitude1, latitude1]
           ]]
         },
         "properties": {}
       }
     ]
   }
   ```

2. **Run the Flask application:**
```bash
python app.py
```

3. **Open your browser and navigate to:**
```
http://localhost:5000
```

## How to Play

1. Click "Start Game" on the home screen
2. Wait for a Street View location to load
3. Use the small map in the top-left corner to make your guess:
   - Click on the map to expand it to 75% of the screen
   - Click anywhere on the map to place your guess marker
4. Click "Submit Guess" to see your results
5. View your score based on how close your guess was to the actual location
6. Click "Play Again" to start a new round

## Features

- **Interactive Street View**: Embedded Google Street View for exploration
- **Expandable Map**: Small preview map that expands when clicked
- **Distance Calculation**: Haversine formula for accurate distance measurement
- **Scoring System**: Points awarded based on guess accuracy (max 5000 points)
- **Visual Results**: Shows both actual location and your guess on a map
- **Responsive Design**: Modern, clean interface with smooth animations

## Troubleshooting

- **"bounding.geojson not found"**: Make sure the file exists in the same directory as `app.py`
- **Street View fails to load**: Check that your bounding area contains valid Street View locations
- **Playwright errors**: Run `playwright install chromium` to install browser dependencies
- **CV2 import errors**: Make sure OpenCV is properly installed: `pip install opencv-python`

## Notes

- The application uses Playwright to scrape Street View locations, which may take a few seconds
- Make sure your `bounding.geojson` polygon contains areas with Street View coverage
- The scoring system gives maximum points for very close guesses and decreases exponentially with distance
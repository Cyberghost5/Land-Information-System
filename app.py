import os
import json
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GEOJSON_PATH = os.path.join(BASE_DIR, 'output_file.geojson')

def load_geojson():
    """Load and parse the GeoJSON parcel data."""
    if not os.path.exists(GEOJSON_PATH):
        raise FileNotFoundError(f"GeoJSON file not found at: {GEOJSON_PATH}")
    with open(GEOJSON_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

@app.route('/')
def index():
    """Serves the main frontend map page."""
    return render_template('index.html')

@app.route('/api/parcels', methods=['GET'])
def get_parcels():
    """Returns the full parcel GeoJSON dataset."""
    try:
        data = load_geojson()
        return jsonify(data), 200
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": "Failed to load parcel data", "details": str(e)}), 500

@app.route('/api/parcels/search/<parcel_id>', methods=['GET'])
def search_parcel(parcel_id):
    """
    Filters the GeoJSON dataset by parcel ID.
    Supports case-insensitive exact matching with fallback to partial matching.
    """
    try:
        data = load_geojson()
        cleaned_id = parcel_id.strip().lower()

        # Try exact match first
        matched_features = [
            f for f in data.get('features', [])
            if str(f.get('properties', {}).get('Parcel_ID', '')).strip().lower() == cleaned_id
        ]

        # Fallback to partial match if no exact match found
        if not matched_features:
            matched_features = [
                f for f in data.get('features', [])
                if cleaned_id in str(f.get('properties', {}).get('Parcel_ID', '')).strip().lower()
            ]

        if not matched_features:
            return jsonify({
                "type": "FeatureCollection",
                "features": [],
                "found": False,
                "message": f"Parcel ID '{parcel_id}' not found."
            }), 404

        return jsonify({
            "type": "FeatureCollection",
            "crs": data.get("crs"),
            "features": matched_features,
            "found": True,
            "count": len(matched_features)
        }), 200

    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": "Search failed", "details": str(e)}), 500

if __name__ == '__main__':
    # Debug mode on port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)

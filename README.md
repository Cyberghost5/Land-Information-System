# Land Information System (LIS)

An interactive, web-based Land Information System (LIS) and Cadastral Portal built with **Python (Flask)** and **Leaflet.js**, featuring geospatial data management, spatial reprojection, dynamic attribute inspection, and parcel search navigation.

---

## 🌟 Key Features

- **Interactive Cadastral Web Map**: Visualizes representative parcel polygons with semi-transparent fills, highlighted boundary strokes, and interactive hover effects.
- **On-the-Fly Coordinate Reprojection**: Handles cadastral data in **EPSG:32631 (WGS 84 / UTM Zone 31N)** and transforms coordinates to **EPSG:4326 (WGS 84)** for seamless overlay onto OpenStreetMap tiles.
- **Dynamic Attribute Inspector**: Clicking any parcel dynamically builds a popup table displaying all spatial and administrative attributes (Parcel ID, Registered Owner, Land Use, Area, Status, LGA, State, Title Number, Survey Plan, Record Date).
- **Spatial Search & Auto-Glide Navigation**:
  - Live search bar supporting case-insensitive exact matching and partial fallbacks via `/api/parcels/search/<parcel_id>`.
  - Native autocomplete suggestions (`<datalist>`) for fast lookup.
  - Smooth camera animation (`flyToBounds`) directly to the target parcel with an accent highlight.
- **RESTful API**: Clean JSON endpoints providing the full GeoJSON feature collection and targeted parcel queries with CORS enabled.

---

## 🏗️ Architecture & Workflow

1. **Digitization & Preprocessing**: Parcel boundaries digitized and verified in GIS tools (Google Earth Pro / QGIS).
2. **Backend**: Python + Flask REST API serving endpoints and managing parcel queries.
3. **Frontend**: HTML5, Modern CSS, Leaflet.js, and Proj4js for client-side coordinate transformation and spatial rendering.

---

## 🚀 Getting Started

### 1. Prerequisites

- Python 3.10+
- `pip` package manager

### 2. Installation

Clone the repository and install the dependencies:

```bash
git clone https://github.com/Cyberghost5/Land-Information-System.git
cd Land-Information-System
pip install -r requirements.txt
```

### 3. Run the Development Server

```bash
python app.py
```

The system will start in debug mode on **port 5000**. Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the interactive cadastral map web interface |
| `GET` | `/api/parcels` | Returns all 157 cadastral parcels as a GeoJSON FeatureCollection |
| `GET` | `/api/parcels/search/<parcel_id>` | Filters and returns the matched parcel feature(s) by Parcel ID |

---

## 📁 Project Structure

```
├── app.py                  # Main Flask application and REST API
├── requirements.txt        # Python package dependencies
├── output_file.geojson     # Spatial cadastral dataset (EPSG:32631)
├── parcel.json             # Auxiliary cadastral dataset
├── steps.jpeg              # Workflow and architecture diagram
├── templates/
│   └── index.html          # Full-screen Leaflet.js frontend application
└── README.md               # Project documentation
```

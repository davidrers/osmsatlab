
import os
import json
import pytest
import geopandas as gpd
from shapely.geometry import Polygon
from osmsatlab.io.osm import download_osm_data

def test_download_osm_data_bbox():
    """Test downloading OSM data using a bounding box."""
    # Small area in Enschede (University of Twente area approx)
    west, south = 6.8480, 52.2450
    east, north = 6.8520, 52.2480
    bbox = (west, south, east, north)
    
    print(f"Downloading OSM data for bbox: {bbox}")
    gdf = download_osm_data(bbox=bbox)
    
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert len(gdf) > 0
    # Basic check that we got some buildings (default tag)
    assert 'building' in gdf.columns or 'geometry' in gdf.columns

def test_download_osm_data_custom_geometry_geojson(tmp_path):
    """Test downloading OSM data using a GeoJSON file path."""
    # Define a simple polygon
    polygon_coords = [
        [6.8480, 52.2450],
        [6.8520, 52.2450],
        [6.8520, 52.2480],
        [6.8480, 52.2480],
        [6.8480, 52.2450]
    ]
    
    geojson_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [polygon_coords]
                }
            }
        ]
    }
    
    # Use pytest's tmp_path fixture for temporary file
    geojson_path = tmp_path / "test_area.geojson"
    with open(geojson_path, 'w') as f:
        json.dump(geojson_data, f)
        
    print(f"Testing download with GeoJSON path: {geojson_path}")
    gdf = download_osm_data(custom_geometry=str(geojson_path))
    
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert len(gdf) > 0

def test_download_osm_data_custom_geometry_shapely():
    """Test downloading OSM data using a Shapely polygon."""
    polygon_coords = [
        [6.8480, 52.2450],
        [6.8520, 52.2450],
        [6.8520, 52.2480],
        [6.8480, 52.2480],
        [6.8480, 52.2450]
    ]
    poly = Polygon(polygon_coords)
    
    print("Testing download with Shapely polygon...")
    gdf = download_osm_data(custom_geometry=poly)
    
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert len(gdf) > 0

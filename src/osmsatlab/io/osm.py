import osmnx as ox
import geopandas as gpd

def download_osm_data(bbox=None, custom_geometry=None, tags=None):
    """
    Download OSM data for a given bounding box or custom geometry.

    Args:
        bbox (tuple, optional): Bounding box as (west, south, east, north).
        custom_geometry (str or shapely.geometry.BaseGeometry, optional): Path to a GeoJSON file or a Shapely geometry.
        tags (dict, optional): Dictionary of tags to query. Defaults to None, which queries 'building'.

    Returns:
        geopandas.GeoDataFrame: GeoDataFrame containing the downloaded OSM features.
    
    Raises:
        ValueError: If neither bbox nor custom_geometry is provided, or if both are provided.
    """
    if bbox is None and custom_geometry is None:
        raise ValueError("Either bbox or custom_geometry must be provided.")
    if bbox is not None and custom_geometry is not None:
        raise ValueError("Provide either bbox or custom_geometry, not both.")

    if tags is None:
        tags = {'building': True}

    if custom_geometry is not None:
        # Handle custom geometry
        if isinstance(custom_geometry, str):
            # Assume it's a file path (e.g. GeoJSON)
            gdf_boundary = gpd.read_file(custom_geometry)
            # Combine all geometries into one (e.g. valid polygon or multipolygon)
            polygon = gdf_boundary.union_all()
        else:
            # Assume it is already a shapely geometry
            polygon = custom_geometry
            
        gdf = ox.features.features_from_polygon(polygon, tags=tags)
    else:
        # Handle bbox
        west, south, east, north = bbox
        # osmnx.features.features_from_bbox expects bbox=(west, south, east, north) in v2.0+
        gdf = ox.features.features_from_bbox(bbox=bbox, tags=tags)
    
    return gdf

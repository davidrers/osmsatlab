import numpy as np
import geopandas as gpd
from scipy.spatial import cKDTree

def build_nearest_neighbor_index(gdf):
    """
    Build a cKDTree from a GeoDataFrame of points.
    
    Args:
        gdf (geopandas.GeoDataFrame): GeoDataFrame containing point geometries.
        
    Returns:
        scipy.spatial.cKDTree: The KD-Tree index.
    """
    if gdf.empty:
        raise ValueError("Cannot build index for empty GeoDataFrame.")
        
    # Extract x, y coordinates
    # Ensure they are points
    coords = np.array(list(zip(gdf.geometry.x, gdf.geometry.y)))
    return cKDTree(coords)

def query_nearest_distances(tree, queries_gdf):
    """
    Query nearest distances for a set of points against a KDTree.
    
    Args:
        tree (scipy.spatial.cKDTree): The KD-Tree index.
        queries_gdf (geopandas.GeoDataFrame): GeoDataFrame containing query points.
        
    Returns:
        numpy.ndarray: Array of distances.
    """
    if queries_gdf.empty:
        return np.array([])
        
    query_coords = np.array(list(zip(queries_gdf.geometry.x, queries_gdf.geometry.y)))
    distances, _ = tree.query(query_coords, k=1)
    return distances

import geopandas as gpd
from osmsatlab.spatial.index import build_nearest_neighbor_index, query_nearest_distances
import warnings

def calculate_nearest_service_distance(population_gdf, services_gdf):
    """
    Calculate Euclidean distance from each population point to the nearest service.
    
    Args:
        population_gdf (geopandas.GeoDataFrame): Points representing population.
        services_gdf (geopandas.GeoDataFrame): Points representing services.
        
    Returns:
        geopandas.GeoDataFrame: A copy of population_gdf with a 'nearest_dist' column (in meters).
    """
    # Check CRS
    if population_gdf.crs.is_geographic or services_gdf.crs.is_geographic:
        warnings.warn("Input GeoDataFrames are in a geographic CRS. Distances will be incorrect (degrees). Project to a metric CRS first.")
        
    if population_gdf.crs != services_gdf.crs:
        raise ValueError("Population and Services must differ in CRS.")
        
    if services_gdf.empty:
        warnings.warn("No services provided. Setting distance to infinity.")
        gdf_out = population_gdf.copy()
        gdf_out['nearest_dist'] = float('inf')
        return gdf_out
        
    # Build Index
    tree = build_nearest_neighbor_index(services_gdf)
    
    # Query
    distances = query_nearest_distances(tree, population_gdf)
    
    gdf_out = population_gdf.copy()
    gdf_out['nearest_dist'] = distances
    return gdf_out

def calculate_coverage(population_gdf, distance_col='nearest_dist', threshold=1000.0):
    """
    Calculate the percentage and total of population within a distance threshold.
    
    Args:
        population_gdf (geopandas.GeoDataFrame): Population data with distance column.
        distance_col (str): Column name for distance.
        threshold (float): Distance threshold (same units as CRS, e.g., meters).
        
    Returns:
        dict: {'coverage_ratio': float, 'covered_population': float, 'total_population': float}
    """
    if distance_col not in population_gdf.columns:
        raise ValueError(f"Column '{distance_col}' not found in GeoDataFrame.")
    
    # Ensure population column exists, else assume 1 per point? No, WorldPop has 'population'.
    # If not present, warn and assume 1? Or fail? The task implies weighted by population.
    pop_col = 'population'
    if pop_col not in population_gdf.columns:
        warnings.warn(f"'{pop_col}' column not found. Calculating coverage based on point count (unweighted).")
        # Add temporary weight of 1
        data = population_gdf.copy()
        data[pop_col] = 1.0
    else:
        data = population_gdf
        
    total_pop = data[pop_col].sum()
    
    covered = data[data[distance_col] <= threshold]
    covered_pop = covered[pop_col].sum()
    
    ratio = covered_pop / total_pop if total_pop > 0 else 0.0
    
    return {
        'coverage_ratio': ratio,
        'covered_population': covered_pop,
        'total_population': total_pop
    }

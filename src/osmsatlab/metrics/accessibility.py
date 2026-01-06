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
    # First, a quick sanity check on the coordinate systems
    if population_gdf.crs.is_geographic or services_gdf.crs.is_geographic:
        warnings.warn("Hold on! It looks like you're using latitude/longitude (degrees). "
                      "This makes calculating distances in meters very inaccurate. "
                      "Please project your data to a metric CRS (like UTM) first!")
        
    if population_gdf.crs != services_gdf.crs:
        raise ValueError("The population and services checks are in different coordinate systems. We need them to match to compare distances!")
        
    if services_gdf.empty:
        warnings.warn("I couldn't find any services in the provided data. Assuming they are infinitely far away.")
        population_with_results = population_gdf.copy()
        # No services means infinite distance
        population_with_results['nearest_dist'] = float('inf')
        return population_with_results
        
    # Build a spatial index (KD-tree) so we can find neighbors fast
    search_tree = build_nearest_neighbor_index(services_gdf)
    
    # Ask the tree: "For each person, how far is the closest service?"
    distances_to_nearest = query_nearest_distances(search_tree, population_gdf)
    
    population_with_results = population_gdf.copy()
    population_with_results['nearest_dist'] = distances_to_nearest
    return population_with_results

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
        raise ValueError(f"I can't calculate coverage because I can't find the distance column '{distance_col}'. Did you run the distance calculation first?")
    
    # We need to know how many people are at each point. 
    # If the 'population' column is missing, we'll assume each point is just 1 person/household.
    count_column = 'population'
    if count_column not in population_gdf.columns:
        warnings.warn(f"I couldn't find a '{count_column}' column, so I'll just count the number of locations (points) instead of the total number of people.")
        # Create a working copy so we don't mess up the original data
        data_to_analyze = population_gdf.copy()
        data_to_analyze[count_column] = 1.0
    else:
        data_to_analyze = population_gdf
        
    total_people = data_to_analyze[count_column].sum()
    
    # Who has a service within the threshold distance?
    people_with_access = data_to_analyze[data_to_analyze[distance_col] <= threshold]
    count_with_access = people_with_access[count_column].sum()
    
    # Avoid dividing by zero if the world is empty
    access_ratio = count_with_access / total_people if total_people > 0 else 0.0
    
    return {
        'coverage_ratio': access_ratio,
        'covered_population': count_with_access,
        'total_population': total_people
    }

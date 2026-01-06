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

def calculate_network_distance(population_gdf, services_gdf, graph, weight='length'):
    """
    Calculate network distance (e.g., driving, walking) from population to nearest service.
    
    Args:
        population_gdf (geopandas.GeoDataFrame): Points representing population.
        services_gdf (geopandas.GeoDataFrame): Points representing services.
        graph (networkx.MultiDiGraph): The street network graph (from osmnx).
        weight (str): Edge attribute to minimize (e.g. 'length', 'travel_time').
        
    Returns:
        geopandas.GeoDataFrame: A copy of population_gdf with a 'nearest_dist' column.
        NaN or inf is used if no path is found.
    """
    import networkx as nx
    import osmnx as ox
    import numpy as np
    
    if services_gdf.empty:
        warnings.warn("No services found. Distances will be infinite.")
        results = population_gdf.copy()
        results['nearest_dist'] = float('inf')
        return results

    # 1. Snap points to the nearest graph nodes
    # We use centroids if they are polygons, but we expect points here usually.
    # Ensure they are in the same CRS as the graph (usually 4326 for osmnx default, but graph might be projected)
    # OSMSatLab usually projects data. The graph should be projected too for accurate meters!
    
    # We assume 'graph' is already projected (e.g. UTM).
    # osmnx.nearest_nodes expects X, Y.
    
    pop_x = population_gdf.geometry.x.values
    pop_y = population_gdf.geometry.y.values
    
    service_x = services_gdf.geometry.x.values
    service_y = services_gdf.geometry.y.values
    
    # Find nearest nodes
    pop_nodes = ox.distance.nearest_nodes(graph, pop_x, pop_y)
    service_nodes = ox.distance.nearest_nodes(graph, service_x, service_y)
    
    # 2. Compute shortest paths using multi-source Dijkstra
    # This finds the shortest distance from ANY of the source nodes to all other nodes in the graph.
    # unique service nodes to avoid redundant work
    unique_service_nodes = set(service_nodes)
    
    # This dictionary will map node_id -> distance to nearest service node
    node_distances = nx.multi_source_dijkstra_path_length(graph, sources=unique_service_nodes, weight=weight)
    
    # 3. Map distances back to population points
    distances = []
    for node in pop_nodes:
        dist = node_distances.get(node, float('inf'))
        distances.append(dist)
        
    results = population_gdf.copy()
    results['nearest_dist'] = distances
    
    return results

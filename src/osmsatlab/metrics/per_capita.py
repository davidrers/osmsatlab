import geopandas as gpd
import warnings

def calculate_services_per_capita(population_gdf, services_gdf):
    """
    Calculate the number of services per 1,000 people.
    
    Args:
        population_gdf (geopandas.GeoDataFrame): GeoDataFrame containing population data.
                                                 Must have a 'population' column.
        services_gdf (geopandas.GeoDataFrame): GeoDataFrame containing service points.
        
    Returns:
        float: Services per 1,000 people.
    """
    if population_gdf.empty:
        raise ValueError("I can't calculate per-capita metrics because the population data is empty!")
        
    if 'population' not in population_gdf.columns:
        raise ValueError("I need a 'population' column to know how many people live here, but I couldn't find one.")
        
    total_people = population_gdf['population'].sum()
    number_of_service_locations = len(services_gdf)
    
    # If there are no people, the metric is 0 (avoid dividing by zero)
    if total_people == 0:
        return 0.0
        
    # The math: (Services / People) * 1000
    services_per_thousand = (number_of_service_locations / total_people) * 1000.0
    return services_per_thousand

def calculate_population_per_service(population_gdf, services_gdf):
    """
    Calculate the number of people per service.
    
    Args:
        population_gdf (geopandas.GeoDataFrame): GeoDataFrame containing population data.
        services_gdf (geopandas.GeoDataFrame): GeoDataFrame containing service points.
        
    Returns:
        float: People per service. Returns infinity if no services are present.
    """
    if population_gdf.empty:
        raise ValueError("I can't calculate population per service because the population data is empty!")
        
    if 'population' not in population_gdf.columns:
        raise ValueError("I need a 'population' column to know how many people live here, but I couldn't find one.")
        
    total_people = population_gdf['population'].sum()
    number_of_service_locations = len(services_gdf)
    
    # If there are no services, the burden is infinite (technically undefined access)
    if number_of_service_locations == 0:
        return float('inf')
        
    # The math: Total People / Total Services
    avg_people_served = total_people / number_of_service_locations
    return avg_people_served

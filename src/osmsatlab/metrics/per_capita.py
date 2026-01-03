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
        raise ValueError("Population data is empty.")
        
    if 'population' not in population_gdf.columns:
        raise ValueError("Population GeoDataFrame must have a 'population' column.")
        
    total_pop = population_gdf['population'].sum()
    num_services = len(services_gdf)
    
    if total_pop == 0:
        return 0.0
        
    return (num_services / total_pop) * 1000.0

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
        raise ValueError("Population data is empty.")
        
    if 'population' not in population_gdf.columns:
        raise ValueError("Population GeoDataFrame must have a 'population' column.")
        
    total_pop = population_gdf['population'].sum()
    num_services = len(services_gdf)
    
    if num_services == 0:
        return float('inf')
        
    return total_pop / num_services

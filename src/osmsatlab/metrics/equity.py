def calculate_services_per_capita(population_gdf, services_gdf):
    """
    Calculate number of services per 1,000 people.
    
    Args:
        population_gdf (geopandas.GeoDataFrame): Population data (must have measure of total population).
        services_gdf (geopandas.GeoDataFrame): Services data.
        
    Returns:
        float: Services per 1,000 inhabitants.
    """
    if 'population' not in population_gdf.columns:
        raise ValueError("Population GeoDataFrame must have a 'population' column.")
        
    total_pop = population_gdf['population'].sum()
    num_services = len(services_gdf)
    
    if total_pop == 0:
        return float('inf') if num_services > 0 else 0.0
        
    return (num_services / total_pop) * 1000.0

def calculate_population_per_service(population_gdf, services_gdf):
    """
    Calculate average population per service.
    
    Args:
        population_gdf (geopandas.GeoDataFrame): Population data.
        services_gdf (geopandas.GeoDataFrame): Services data.
        
    Returns:
        float: Population per service.
    """
    if 'population' not in population_gdf.columns:
        raise ValueError("Population GeoDataFrame must have a 'population' column.")
        
    total_pop = population_gdf['population'].sum()
    num_services = len(services_gdf)
    
    if num_services == 0:
        return float('inf') if total_pop > 0 else 0.0
        
    return total_pop / num_services

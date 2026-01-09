"""
Spatial aggregation functions for population and service data.
"""

import geopandas as gpd


def sum_population_to_units(pop_points, units, pop_col="population"):
    """
    Aggregate population points into analysis units.
    
    Parameters
    ----------
    pop_points : GeoDataFrame
        Population points with population values
    units : GeoDataFrame
        Analysis units (polygons)
    pop_col : str, optional
        Name of the population column
        
    Returns
    -------
    GeoDataFrame
        Units with aggregated population values
    """
    pop = pop_points.to_crs(units.crs)
    joined = gpd.sjoin(pop[[pop_col, "geometry"]], units, how="left", predicate="within")
    agg = joined.groupby("unit_id")[pop_col].sum().reset_index()
    out = units.merge(agg, on="unit_id", how="left")
    out[pop_col] = out[pop_col].fillna(0.0)
    return out


def count_services_to_units(services_points, units):
    """
    Count service points per analysis unit.
    
    Parameters
    ----------
    services_points : GeoDataFrame
        Service location points
    units : GeoDataFrame
        Analysis units (polygons)
        
    Returns
    -------
    GeoDataFrame
        Units with service counts
    """
    svc = services_points.to_crs(units.crs)
    joined = gpd.sjoin(svc[["geometry"]], units, how="left", predicate="within")
    counts = joined.groupby("unit_id").size().reset_index(name="service_count")
    out = units.merge(counts, on="unit_id", how="left")
    out["service_count"] = out["service_count"].fillna(0).astype(float)
    return out

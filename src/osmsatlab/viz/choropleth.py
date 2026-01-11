"""
Choropleth mapping functions for spatial data visualization.
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt


def plot_choropleth(gdf, column, title, aoi, log1p=False):
    """
    Create a choropleth map with basemap and AOI outline.
    
    Parameters
    
    gdf : GeoDataFrame
        Data to plot (must contain the specified column)
    column : str
        Column name to visualize
    title : str
        Map title
    aoi : shapely.geometry
        Area of interest boundary to overlay
    log1p : bool, optional
        If True, apply log(1+x) transformation to the data
        
    Returns
    
    tuple
        (fig, ax) matplotlib figure and axes objects
    """
    d = gdf.copy()
    d[column] = pd.to_numeric(d[column], errors="coerce").fillna(0)
    if log1p:
        d[column] = np.log1p(d[column])

    fig, ax = plt.subplots(figsize=(9, 9))
    d.plot(
        ax=ax,
        column=column,
        legend=True,
        linewidth=0.35,
        edgecolor="white",
        cmap="viridis",
        missing_kwds={"color": "lightgrey", "label": "No data"},
    )

    gpd.GeoSeries([aoi], crs=d.crs).boundary.plot(ax=ax, linewidth=2)

    minx, miny, maxx, maxy = aoi.bounds
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.set_axis_off()
    ax.set_title(title)

    try:
        import contextily as ctx
        ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)
    except Exception:
        pass

    return fig, ax

def plot_interactive_accessibility_map(lab, units, aoi, service_category, threshold_m, metric_type="euclidean"):
    """
    Create interactive Folium map showing median accessibility distance per unit.
    
    Parameters
    
    lab : OSMSatLab
        OSMSatLab instance with population and services
    units : GeoDataFrame
        Analysis units (polygons)
    aoi : shapely.geometry
        Area of interest boundary
    service_category : str
        Service category (e.g., 'healthcare', 'education')
    threshold_m : int
        Distance threshold in meters
    metric_type : str, optional
        Distance metric ('euclidean' or 'network')
        
    Returns
    
    folium.Map
        Interactive map object (use .save('filename.html') to export)
    """
    try:
        import folium
    except ImportError:
        raise ImportError("folium is required. Install with: pip install folium")
    
    # Calculate accessibility metrics
    acc = lab.calculate_accessibility_metrics(
        service_category=service_category,
        threshold=threshold_m,
        metric_type=metric_type
    )
    pop = acc["population_gdf"].copy()
    
    # Join population to units and compute median distance per unit
    pop = pop.to_crs(units.crs)
    joined = gpd.sjoin(
        pop[["nearest_dist", "geometry"]], 
        units[["unit_id", "geometry"]],
        how="left", 
        predicate="within"
    )
    
    med = joined.groupby("unit_id")["nearest_dist"].median().reset_index()
    unit_metric = units.merge(med, on="unit_id", how="left")
    
    # Convert to WGS84 for web mapping
    unit_wgs = unit_metric.to_crs(epsg=4326)
    aoi_wgs = gpd.GeoSeries([aoi], crs=units.crs).to_crs(epsg=4326).iloc[0]
    
    # Create map centered on AOI
    center = [aoi_wgs.centroid.y, aoi_wgs.centroid.x]
    m = folium.Map(location=center, zoom_start=10, tiles="CartoDB positron")
    
    # Add AOI boundary
    folium.GeoJson(
        data=gpd.GeoSeries([aoi_wgs]).__geo_interface__,
        name="AOI Boundary",
        style_function=lambda x: {"fillOpacity": 0, "color": "black", "weight": 2}
    ).add_to(m)
    
    # Add choropleth layer
    geojson = unit_wgs[["unit_id", "nearest_dist", "geometry"]].dropna(subset=["nearest_dist"]).to_json()
    
    folium.Choropleth(
        geo_data=geojson,
        data=unit_wgs.dropna(subset=["nearest_dist"]),
        columns=["unit_id", "nearest_dist"],
        key_on="feature.properties.unit_id",
        fill_color="YlOrRd",
        fill_opacity=0.75,
        line_opacity=0.2,
        legend_name=f"Median distance to nearest {service_category.replace('_', ' ')} (m)"
    ).add_to(m)
    
    # Add tooltips
    folium.GeoJson(
        unit_wgs.dropna(subset=["nearest_dist"]),
        name="Unit Details",
        tooltip=folium.GeoJsonTooltip(
            fields=["unit_id", "nearest_dist"],
            aliases=["Unit ID", "Median distance (m)"]
        )
    ).add_to(m)
    
    folium.LayerControl().add_to(m)
    
    return m

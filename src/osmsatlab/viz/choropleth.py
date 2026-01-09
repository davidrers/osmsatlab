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
    ----------
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
    -------
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

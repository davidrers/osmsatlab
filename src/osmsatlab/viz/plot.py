"""
Distribution plot functions for accessibility metrics.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def plot_distribution(values, title, bins=60, log10=False, x_label="Distance to nearest service (meters)"):
    """
    Create a histogram distribution plot with median line.
    
    Parameters
    
    values : array-like
        Values to plot (e.g., distances to services)
    title : str
        Plot title
    bins : int, optional
        Number of histogram bins
    log10 : bool, optional
        If True, apply log10 transformation to the data
    x_label : str, optional
        Label for x-axis
        
    Returns
    
    tuple
        (fig, ax) matplotlib figure and axes objects
    """
    s = pd.Series(values).replace([np.inf, -np.inf], np.nan).dropna()
    if log10:
        s = s[s > 0]
        s = np.log10(s)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.hist(s.values, bins=bins)

    if len(s):
        ax.axvline(float(np.nanmedian(s.values)), linewidth=2)

    ax.set_title(title)
    ax.set_ylabel("Number of population locations")
    ax.set_xlabel(("log₁₀(" + x_label + ")") if log10 else x_label)
    return fig, ax


def plot_pairwise(pop_units, svc_units, title, log1p=False):
    """
    Create a scatter plot showing relationship between population and service count.
    
    Parameters
    
    pop_units : GeoDataFrame
        Units with population data
    svc_units : GeoDataFrame
        Units with service count data
    title : str
        Plot title
    log1p : bool, optional
        If True, apply log(1+x) transformation to both axes
        
    Returns
    
    tuple
        (fig, ax) matplotlib figure and axes objects
    """
    # Merge the two datasets
    merged = pop_units[["unit_id", "population"]].merge(
        svc_units[["unit_id", "service_count"]], 
        on="unit_id",
        how="inner"
    )
    
    # Remove any rows with missing data
    merged = merged.dropna(subset=["population", "service_count"])
    
    x = merged["population"].values
    y = merged["service_count"].values
    
    if log1p:
        x = np.log1p(x)
        y = np.log1p(y)
    
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(x, y, alpha=0.6, edgecolors='k', linewidth=0.5)
    
    xlabel = "Population" + (" (log scale)" if log1p else "")
    ylabel = "Service count" + (" (log scale)" if log1p else "")
    
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    
    return fig, ax

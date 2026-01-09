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

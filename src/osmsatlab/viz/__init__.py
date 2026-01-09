"""
Visualization module for OSMSatLab spatial analysis.
"""

from .units import (
    aoi_geometry,
    analysis_units,
    nl_lau_units,
    grid_units
)

from .aggregation import (
    sum_population_to_units,
    count_services_to_units
)

from .choropleth import plot_choropleth
from .plot import plot_distribution
from .workflows import render_maps

__all__ = [
    'aoi_geometry',
    'analysis_units',
    'nl_lau_units',
    'grid_units',
    'sum_population_to_units',
    'count_services_to_units',
    'plot_choropleth',
    'plot_distribution',
    'render_maps',
]

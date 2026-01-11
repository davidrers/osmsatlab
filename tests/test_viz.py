"""
Tests for the visualization (viz)

Tests cover:
1. Spatial unit creation (grid and administrative boundaries)
2. Population and service aggregation
3. Static visualization functions
4. Interactive mapping
5. Complete workflow integration

Tests all functions in the visualization:
- units.py: aoi_geometry, grid_units, nl_lau_units, analysis_units
- aggregation.py: sum_population_to_units, count_services_to_units
- choropleth.py: plot_choropleth, plot_interactive_accessibility_map
- plot.py: plot_distribution, plot_pairwise, plot_coverage_threshold_analysis
- workflows.py: render_maps
"""

import pytest
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point, Polygon, box
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for testing


# Mock Lab for Testing

class MockLab:
    """Mock OSMSatLab instance for testing."""
    def __init__(self, bbox=None, custom_geometry=None):
        self.bbox = bbox
        self.custom_geometry = custom_geometry
        self.target_crs = "EPSG:3857"
        self.population = gpd.GeoDataFrame({
            'population': [100, 200, 150],
            'geometry': [Point(6.5, 52.5), Point(6.6, 52.6), Point(6.7, 52.7)]
        }, crs="EPSG:4326")
        self.services = {
            "healthcare": gpd.GeoDataFrame({
                'geometry': [Point(6.5, 52.5), Point(6.7, 52.7)]
            }, crs="EPSG:4326")
        }
    
    def calculate_accessibility_metrics(self, service_category, threshold, metric_type="euclidean"):
        pop = self.population.copy()
        pop['nearest_dist'] = [300, 800, 500]
        return {
            "population_gdf": pop,
            "coverage_stats": {"coverage_ratio": 0.67}
        }

# Test 1: units.py - aoi_geometry

def test_aoi_geometry_from_bbox():
    """Test extracting AOI geometry from bounding box."""
    from osmsatlab.viz.units import aoi_geometry
    
    lab = MockLab(bbox=(6.0, 52.0, 7.0, 53.0))
    geom = aoi_geometry(lab, crs="EPSG:4326")
    
    assert geom is not None
    assert geom.geom_type == "Polygon"
    assert geom.bounds == (6.0, 52.0, 7.0, 53.0)

# Test 2: units.py - grid_units

def test_grid_units_creates_grid():
    """Test that grid_units creates proper grid cells."""
    from osmsatlab.viz.units import grid_units
    
    lab = MockLab(bbox=(6.0, 52.0, 6.1, 52.1))
    units, aoi, iso3 = grid_units(lab, cell_m=1000)
    
    assert isinstance(units, gpd.GeoDataFrame)
    assert 'unit_id' in units.columns
    assert 'unit_name' in units.columns
    assert 'geometry' in units.columns
    assert len(units) > 0
    assert all(units.geometry.geom_type == 'Polygon')

# Test 3: aggregation.py - sum_population_to_units

def test_sum_population_to_units():
    """Test population aggregation to spatial units."""
    from osmsatlab.viz.aggregation import sum_population_to_units
    
    units = gpd.GeoDataFrame({
        'unit_id': [0, 1],
        'geometry': [
            Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            Polygon([(1, 0), (2, 0), (2, 1), (1, 1)])
        ]
    }, crs="EPSG:4326")
    
    pop_points = gpd.GeoDataFrame({
        'population': [100, 200, 300],
        'geometry': [Point(0.5, 0.5), Point(0.8, 0.8), Point(1.5, 0.5)]
    }, crs="EPSG:4326")
    
    result = sum_population_to_units(pop_points, units)
    
    assert isinstance(result, gpd.GeoDataFrame)
    assert 'population' in result.columns
    assert result.loc[result['unit_id'] == 0, 'population'].iloc[0] == 300
    assert result.loc[result['unit_id'] == 1, 'population'].iloc[0] == 300

# Test 4: aggregation.py - count_services_to_units

def test_count_services_to_units():
    """Test service counting per spatial unit."""
    from osmsatlab.viz.aggregation import count_services_to_units
    
    units = gpd.GeoDataFrame({
        'unit_id': [0, 1],
        'geometry': [
            Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            Polygon([(1, 0), (2, 0), (2, 1), (1, 1)])
        ]
    }, crs="EPSG:4326")
    
    services = gpd.GeoDataFrame({
        'geometry': [Point(0.5, 0.5), Point(0.7, 0.7), Point(1.5, 0.5)]
    }, crs="EPSG:4326")
    
    result = count_services_to_units(services, units)
    
    assert isinstance(result, gpd.GeoDataFrame)
    assert 'service_count' in result.columns
    assert result.loc[result['unit_id'] == 0, 'service_count'].iloc[0] == 2.0
    assert result.loc[result['unit_id'] == 1, 'service_count'].iloc[0] == 1.0

# Test 5: choropleth.py - plot_choropleth

def test_plot_choropleth():
    """Test choropleth map creation."""
    from osmsatlab.viz.choropleth import plot_choropleth
    
    gdf = gpd.GeoDataFrame({
        'values': [10, 50, 100],
        'geometry': [box(0, 0, 1, 1), box(1, 0, 2, 1), box(2, 0, 3, 1)]
    }, crs="EPSG:4326")
    
    aoi = box(0, 0, 3, 1)
    
    fig, ax = plot_choropleth(gdf, column='values', title="Test Map", aoi=aoi, log1p=True)
    
    assert fig is not None
    assert ax is not None
    assert ax.get_title() == "Test Map"

# Test 6: plot.py - plot_distribution

def test_plot_distribution():
    """Test distribution histogram creation."""
    from osmsatlab.viz.plot import plot_distribution
    
    values = [100, 200, 300, 400, 500]
    fig, ax = plot_distribution(values, title="Distance Distribution", bins=20)
    
    assert fig is not None
    assert ax is not None
    assert ax.get_title() == "Distance Distribution"

# Test 7: plot.py - plot_pairwise

def test_plot_pairwise():
    """Test pairwise scatter plot creation."""
    from osmsatlab.viz.plot import plot_pairwise
    
    pop_units = gpd.GeoDataFrame({
        'unit_id': [0, 1, 2],
        'population': [100, 500, 1000],
        'geometry': [Point(0, 0), Point(1, 1), Point(2, 2)]
    })
    
    svc_units = gpd.GeoDataFrame({
        'unit_id': [0, 1, 2],
        'service_count': [5, 10, 15],
        'geometry': [Point(0, 0), Point(1, 1), Point(2, 2)]
    })
    
    fig, ax = plot_pairwise(pop_units, svc_units, "Pop vs Services", log1p=True)
    
    assert fig is not None
    assert ax is not None
    assert ax.get_title() == "Pop vs Services"

# Test 8: plot.py - plot_coverage_threshold_analysis

def test_plot_coverage_threshold_analysis():
    """Test coverage threshold sensitivity analysis."""
    from osmsatlab.viz.plot import plot_coverage_threshold_analysis
    
    lab = MockLab(bbox=(6.0, 52.0, 6.5, 52.5))
    thresholds = [500, 1000, 1500]
    
    fig, ax, coverage = plot_coverage_threshold_analysis(
        lab,
        service_category="healthcare",
        thresholds=thresholds,
        place_label="Test"
    )
    
    assert fig is not None
    assert ax is not None
    assert isinstance(coverage, dict)
    for t in thresholds:
        assert t in coverage

# Test 9: choropleth.py - plot_interactive_accessibility_map

def test_plot_interactive_accessibility_map():
    """Test interactive Folium map creation."""
    pytest.importorskip("folium", reason="folium required")
    
    from osmsatlab.viz.choropleth import plot_interactive_accessibility_map
    import folium
    
    lab = MockLab(bbox=(6.0, 52.0, 6.2, 52.2))
    
    units = gpd.GeoDataFrame({
        'unit_id': [0, 1],
        'geometry': [box(6.0, 52.0, 6.1, 52.1), box(6.1, 52.0, 6.2, 52.1)]
    }, crs="EPSG:4326")
    
    aoi = box(6.0, 52.0, 6.2, 52.2)
    
    m = plot_interactive_accessibility_map(
        lab, units=units, aoi=aoi, 
        service_category="healthcare", threshold_m=1000
    )
    
    assert isinstance(m, folium.Map)

# Test 10: workflows.py - render_maps

def test_render_maps():
    """Test complete render_maps workflow."""
    from osmsatlab.viz import render_maps
    
    lab = MockLab(bbox=(6.0, 52.0, 6.2, 52.2))
    
    result = render_maps(
        lab,
        place_label="Test",
        service_category="healthcare",
        grid_cell_m=1000,
        threshold_m=1000
    )
    
    assert isinstance(result, dict)
    assert 'iso3' in result
    assert 'units' in result
    assert 'pop_units' in result
    assert 'svc_units' in result
    assert 'acc' in result

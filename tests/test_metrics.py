import pytest
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from osmsatlab.metrics.accessibility import calculate_nearest_service_distance, calculate_coverage
from osmsatlab.metrics.per_capita import calculate_services_per_capita, calculate_population_per_service
import numpy as np

@pytest.fixture
def mock_proj_crs():
    return "EPSG:3857" # web mercator (meters)

@pytest.fixture
def population_gdf(mock_proj_crs):
    # 3 points: (0,0), (1000,0), (5000, 0)
    # Pop: 10, 20, 5
    return gpd.GeoDataFrame(
        {'population': [10, 20, 5]},
        geometry=[Point(0, 0), Point(1000, 0), Point(5000, 0)],
        crs=mock_proj_crs
    )

@pytest.fixture
def services_gdf(mock_proj_crs):
    # 2 services: (10, 0), (2000, 0)
    return gpd.GeoDataFrame(
        {'id': [1, 2]},
        geometry=[Point(10, 0), Point(2000, 0)],
        crs=mock_proj_crs
    )

def test_nearest_distance(population_gdf, services_gdf):
    """
    Test nearest distance calculation.
    Point(0,0) -> Service(10,0) = 10m
    Point(1000,0) -> Service(10,0)=990m or Service(2000,0)=1000m. Nearest is 990m.
    Point(5000,0) -> Service(2000,0) = 3000m
    """
    res = calculate_nearest_service_distance(population_gdf, services_gdf)
    
    assert 'nearest_dist' in res.columns
    # Distances
    dists = res['nearest_dist'].values
    assert np.isclose(dists[0], 10.0)
    assert np.isclose(dists[1], 990.0)
    assert np.isclose(dists[2], 3000.0)

def test_coverage(population_gdf, services_gdf):
    """
    Test coverage within threshold.
    Pop1: 10 people, dist 10m
    Pop2: 20 people, dist 990m
    Pop3: 5 people, dist 3000m
    Total = 35
    
    Threshold 1000m:
    Pop1 and Pop2 covered (30 people). Ratio 30/35 = 0.857...
    """
    res = calculate_nearest_service_distance(population_gdf, services_gdf)
    stats = calculate_coverage(res, threshold=1000.0)
    
    assert stats['total_population'] == 35
    assert stats['covered_population'] == 30
    assert np.isclose(stats['coverage_ratio'], 30/35)

def test_services_per_capita(population_gdf, services_gdf):
    """
    Test equity: services per 1000 people.
    Total Pop: 35
    Total Services: 2
    Metric: (2 / 35) * 1000 = 57.14...
    """
    metric = calculate_services_per_capita(population_gdf, services_gdf)
    assert np.isclose(metric, (2/35)*1000)

def test_population_per_service(population_gdf, services_gdf):
    """
    Test equity: population per service.
    Total Pop: 35
    Total Services: 2
    Metric: 35 / 2 = 17.5
    """
    metric = calculate_population_per_service(population_gdf, services_gdf)
    assert np.isclose(metric, 17.5)

def test_empty_services(population_gdf, mock_proj_crs):
    empty_services = gpd.GeoDataFrame(columns=['geometry'], crs=mock_proj_crs)
    
    # Distance
    res = calculate_nearest_service_distance(population_gdf, empty_services)
    assert np.all(np.isinf(res['nearest_dist']))
    
    # Coverage (Should be 0)
    stats = calculate_coverage(res, threshold=1000)
    assert stats['covered_population'] == 0
    assert stats['coverage_ratio'] == 0.0

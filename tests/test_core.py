import pytest
from unittest.mock import MagicMock, patch
import geopandas as gpd
from shapely.geometry import Point
from osmsatlab.core import OSMSatLab

@pytest.fixture
def mock_proj_crs():
    return "EPSG:3857"

@patch('osmsatlab.core.get_population_data')
def test_load_population(mock_get_pop, mock_proj_crs):
    mock_get_pop.return_value = gpd.GeoDataFrame(
        {'population': [100]}, 
        geometry=[Point(0,0)], 
        crs="EPSG:4326"
    )
    
    lab = OSMSatLab(bbox=(0,0,1,1), crs=mock_proj_crs)
    lab.load_population()
    
    assert lab.population is not None
    assert lab.population.crs == mock_proj_crs
    assert len(lab.population) == 1

@patch('osmsatlab.core.download_osm_data')
def test_fetch_services(mock_download, mock_proj_crs):
    mock_download.return_value = gpd.GeoDataFrame(
        {'name': ['Hospital']},
        geometry=[Point(0,0)],
        crs="EPSG:4326"
    )
    
    lab = OSMSatLab(bbox=(0,0,1,1), crs=mock_proj_crs)
    lab.fetch_services(tags={'amenity': 'hospital'}, category_name='healthcare')
    
    assert 'healthcare' in lab.services
    assert lab.services['healthcare'].crs == mock_proj_crs
    assert len(lab.services['healthcare']) == 1

@patch('osmsatlab.core.get_population_data')
@patch('osmsatlab.core.download_osm_data')
def test_workflow(mock_download, mock_get_pop, mock_proj_crs):
    # Setup mock data
    mock_get_pop.return_value = gpd.GeoDataFrame(
        {'population': [10, 20]}, 
        geometry=[Point(0,0), Point(2000, 0)], # 0, 2km
        crs="EPSG:3857" # mocking already projected for simplicity or not? Code handles projection.
    )
    
    mock_download.return_value = gpd.GeoDataFrame(
        {'name': ['Clinic']},
        geometry=[Point(100,0)],
        crs="EPSG:3857"
    )
    
    lab = OSMSatLab(bbox=(0,0,10,10), crs="EPSG:3857")
    lab.load_population()
    lab.fetch_services({'amenity': 'clinic'}, 'health')
    
    # Accessibility
    acc = lab.calculate_accessibility_metrics('health', threshold=500)
    # Point(0,0) -> 100m (Covered)
    # Point(2000,0) -> 1900m (Not Covered)
    stats = acc['coverage_stats']
    assert stats['covered_population'] == 10
    assert stats['total_population'] == 30
    
    # Equity
    equity = lab.calculate_equity_metrics('health')
    # Services per 1000: (1 / 30) * 1000 = 33.333
    assert equity['services_per_1000'] == (1/30)*1000

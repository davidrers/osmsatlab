import pytest
from unittest.mock import MagicMock, patch
import geopandas as gpd
from shapely.geometry import box, Point, Polygon
import numpy as np
import rasterio
from rasterio.transform import from_origin
from osmsatlab.io.population import get_population_data, get_country_iso3

# Mock data for naturalearth_lowres
@pytest.fixture
def mock_world_data():
    # Create a simple world with two countries
    p1 = box(0, 0, 10, 10)
    p2 = box(10, 0, 20, 10)
    df = gpd.GeoDataFrame(
        {'iso_a3': ['CTA', 'CTB'], 'name': ['CountryA', 'CountryB']},
        geometry=[p1, p2],
        crs="EPSG:4326"
    )
    return df

@patch('osmsatlab.io.population.get_world_boundaries')
def test_get_country_iso3(mock_get_boundaries, mock_world_data):
    mock_get_boundaries.return_value = mock_world_data
    
    # Test point inside CountryA
    geom = box(1, 1, 2, 2)
    iso = get_country_iso3(geom)
    assert iso == 'CTA'
    
    # Test point inside CountryB
    geom = box(11, 1, 12, 2)
    iso = get_country_iso3(geom)
    assert iso == 'CTB'

@patch('osmsatlab.io.population.requests.get')
@patch('osmsatlab.io.population.rasterio.open')
@patch('osmsatlab.io.population.get_country_iso3')
@patch('osmsatlab.io.population.os.path.exists')
@patch('osmsatlab.io.population.open')
def test_get_population_data_flow(mock_open, mock_path_exists, mock_get_iso, mock_rio_open, mock_requests_get):
    # Setup mocks
    mock_get_iso.return_value = 'TST'
    
    # 1. Test Download (File does not exist)
    mock_path_exists.return_value = False
    
    # Mock requests response
    mock_response = MagicMock()
    mock_response.iter_content.return_value = [b'fake_data']
    mock_requests_get.return_value.__enter__.return_value = mock_response
    
    # Mock rasterio
    mock_dataset = MagicMock()
    mock_rio_open.return_value.__enter__.return_value = mock_dataset
    
    with patch('osmsatlab.io.population.rasterio.mask.mask') as mock_mask:
        data = np.array([[[10.0, 0.0], [5.0, -9999.0]]], dtype='float32')
        transform = from_origin(0, 10, 1, 1)
        mock_mask.return_value = (data, transform)
        mock_dataset.nodata = -9999.0
        mock_dataset.crs = "EPSG:4326"
        mock_dataset.meta = {'driver': 'GTiff', 'count': 1}
        
        bbox = (0, 8, 2, 10)
        get_population_data(bbox=bbox, year=2020)
        
        # Verify URL
        expected_url = "https://data.worldpop.org/GIS/Population/Global_2000_2020_1km/2020/TST/tst_ppp_2020_1km_Aggregated.tif"
        mock_requests_get.assert_called_with(expected_url, stream=True)
        
    # 2. Test Cache (File exists)
    mock_path_exists.return_value = True
    mock_requests_get.reset_mock()
    
    with patch('osmsatlab.io.population.rasterio.mask.mask') as mock_mask:
        mock_mask.return_value = (data, transform)
        get_population_data(bbox=bbox, year=2020)
        
        # Verify NO download
        mock_requests_get.assert_not_called()
        
        mock_mask.return_value = (data, transform)
        mock_dataset.nodata = -9999.0
        mock_dataset.crs = "EPSG:4326"
        mock_dataset.meta = {'driver': 'GTiff', 'count': 1}
        
        # Call function
        bbox = (0, 8, 2, 10) # Matches the transform sort of
        gdf = get_population_data(bbox=bbox)
        
        # Verify
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert len(gdf) == 2 # 10 and 5 should be kept. 0 might be kept depending on logic?
        # Logic was: (data != nodata) & (data > 0)
        # 10 > 0 -> Keep
        # 0 > 0 -> Drop (False)
        # 5 > 0 -> Keep
        # -9999 != -9999 -> False (Drop)
        
        assert len(gdf) == 2
        assert 10.0 in gdf['population'].values
        assert 5.0 in gdf['population'].values
        assert 'geometry' in gdf.columns


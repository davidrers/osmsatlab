from osmsatlab.io.osm import download_osm_data
from osmsatlab.io.population import get_population_data
from osmsatlab.metrics.accessibility import calculate_nearest_service_distance, calculate_coverage
from osmsatlab.metrics.equity import calculate_services_per_capita, calculate_population_per_service
import geopandas as gpd
import warnings

class OSMSatLab:
    """
    Core class for OSMSatLab analysis.
    Manages data (population, services) and facilitates accessibility/equity calculations.
    """
    
    def __init__(self, bbox=None, custom_geometry=None, crs="EPSG:3857"):
        """
        Initialize the analysis helper.
        
        Args:
            bbox (tuple, optional): (west, south, east, north).
            custom_geometry (shapely.Geometry or str, optional): Area of interest.
            crs (str): Target CRS for metric calculations (must be projected, default EPSG:3857).
        """
        if bbox is None and custom_geometry is None:
            raise ValueError("Must provide either bbox or custom_geometry.")
            
        self.bbox = bbox
        self.custom_geometry = custom_geometry
        self.target_crs = crs
        
        self.population = None
        self.services = {} # Dict of category -> GeoDataFrame
        
    def load_population(self, year=2020):
        """
        Download and load population data for the defined area.
        And projects it to the target CRS.
        """
        raw_pop = get_population_data(bbox=self.bbox, custom_geometry=self.custom_geometry, year=year)
        if raw_pop is not None and not raw_pop.empty:
            self.population = raw_pop.to_crs(self.target_crs)
        else:
            self.population = gpd.GeoDataFrame(columns=['population', 'geometry'], crs=self.target_crs)
        return self.population

    def fetch_services(self, tags, category_name="default"):
        """
        Download OSM services for the defined area.
        And projects it to the target CRS.
        
        Args:
            tags (dict): OSM tags to query.
            category_name (str): Key to store the services under (e.g. 'healthcare', 'education').
            
        Returns:
            geopandas.GeoDataFrame: The fetched services.
        """
        raw_osm = download_osm_data(bbox=self.bbox, custom_geometry=self.custom_geometry, tags=tags)
        
        # Ensure we only keep centroids/points for distance analysis usually?
        # WorldPop is points. OSM can be polygons.
        # For accessibility to a building, the centroid or boundary is fine.
        # Let's project first.
        if raw_osm is not None and not raw_osm.empty:
            projected = raw_osm.to_crs(self.target_crs)
            # Use centroids for polygons to simplify distance calc
            # (Note: this modifies geometry type to Point for all)
            projected['geometry'] = projected.geometry.centroid
            self.services[category_name] = projected
        else:
            # Empty
            self.services[category_name] = gpd.GeoDataFrame(columns=['geometry'], crs=self.target_crs)
            
        return self.services[category_name]
        
    def calculate_accessibility_metrics(self, service_category, threshold=1000):
        """
        Compute nearest distance and coverage for a specific service category.
        
        Args:
            service_category (str): Name of the category loaded via fetch_services.
            threshold (float): Distance threshold in meters (or CRS units).
            
        Returns:
            dict: { 'population_with_distances': GDF, 'coverage_stats': dict }
        """
        if self.population is None:
            raise ValueError("Population data not loaded. Call load_population() first.")
            
        if service_category not in self.services:
            raise ValueError(f"Service category '{service_category}' not found. Call fetch_services() first.")
            
        services = self.services[service_category]
        pop_with_dist = calculate_nearest_service_distance(self.population, services)
        
        coverage = calculate_coverage(pop_with_dist, distance_col='nearest_dist', threshold=threshold)
        
        return {
            "population_gdf": pop_with_dist,
            "coverage_stats": coverage
        }
        
    def calculate_equity_metrics(self, service_category):
        """
        Compute per-capita metrics for a specific service category.
        
        Args:
           service_category (str): Name of the category.
           
        Returns:
            dict: { 'services_per_1000': float, 'people_per_service': float }
        """
        if self.population is None:
            raise ValueError("Population data not loaded. Call load_population() first.")
            
        if service_category not in self.services:
            raise ValueError(f"Service category '{service_category}' not found. Call fetch_services() first.")
            
        services = self.services[service_category]
        
        spc = calculate_services_per_capita(self.population, services)
        pps = calculate_population_per_service(self.population, services)
        
        return {
            "services_per_1000": spc,
            "people_per_service": pps
        }

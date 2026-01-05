from osmsatlab.io.osm import download_osm_data
from osmsatlab.io.population import get_population_data
from osmsatlab.metrics.accessibility import calculate_nearest_service_distance, calculate_coverage
from osmsatlab.metrics.per_capita import calculate_services_per_capita, calculate_population_per_service
from osmsatlab.constants import SERVICE_DEFINITIONS
import geopandas as gpd
import warnings
from tqdm.auto import tqdm

class OSMSatLab:
    """
    Core class for OSMSatLab analysis.
    Manages data (population, services) and facilitates accessibility/equity calculations.
    """
    
    def __init__(self, bbox=None, custom_geometry=None, crs="EPSG:3857", load_population_year=2020, load_services=True):
        """
        Initialize the analysis helper.
        
        Args:
            bbox (tuple, optional): (west, south, east, north).
            custom_geometry (shapely.Geometry or str, optional): Area of interest.
            crs (str): Target CRS for metric calculations (must be projected, default EPSG:3857).
            load_population_year (int, optional): If provided, automatically loads population data for this year.
            load_services (bool, optional): If True, automatically loads all standard service categories.
        """
        if bbox is None and custom_geometry is None:
            raise ValueError("I need to know where we are looking! Please provide either a 'bbox' (bounding box) or 'custom_geometry'.")
            
        self.bbox = bbox
        self.custom_geometry = custom_geometry
        self.target_crs = crs
        
        self.population = None
        self.services = {} # Dict of category -> GeoDataFrame


        # Pre-load data if requested
        if load_population_year is not None:
            # Simple progress bar for population load
            with tqdm(total=1, desc=f"Loading population ({load_population_year})") as pbar:
                self.load_population(year=load_population_year)
                pbar.update(1)

        if load_services:
            # Progress bar for iterating through service categories
            for category, tags in tqdm(SERVICE_DEFINITIONS.items(), desc="Fetching services"):
                self.fetch_services(tags, category_name=category)
        
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
        
        # We usually want to calculate distances to specific points (like the entrance of a building),
        # rather than to the edge of a large polygon.
        # So, if we get polygons (like a large hospital campus), let's find their center point.
        # But first, we need to project the data so our math works in meters, not degrees!
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
            raise ValueError("I can't calculate accessibility without people! Please run `.load_population()` first so we know where everyone lives.")
            
        if service_category not in self.services:
            available_categories = list(self.services.keys())
            raise ValueError(f"I couldn't find the '{service_category}' services. I only have these ones right now: {available_categories}. Did you forget to fetch them?")
            
        points_of_interest = self.services[service_category]
        
        # Let's figure out how close everyone is to these services
        population_with_access_info = calculate_nearest_service_distance(self.population, points_of_interest)
        
        # Now, let's see how many people are 'close enough' based on our threshold
        coverage_stats = calculate_coverage(population_with_access_info, distance_col='nearest_dist', threshold=threshold)
        
        return {
            "population_gdf": population_with_access_info,
            "coverage_stats": coverage_stats
        }
        
    def calculate_per_capita_metrics(self, service_category):
        """
        Compute per-capita metrics for a specific service category.
        
        Args:
            service_category (str): Name of the category.
            
        Returns:
            dict: { 'services_per_1000': float, 'people_per_service': float }
        """
        if self.population is None:
            raise ValueError("I can't calculate equity metrics without population data! Please run `.load_population()` first.")
            
        if service_category not in self.services:
            available = list(self.services.keys())
            raise ValueError(f"I don't have any data for '{service_category}'. I can only analyze: {available}.")
            
        points_of_interest = self.services[service_category]
        
        # How many services are there for every 1000 people?
        services_density = calculate_services_per_capita(self.population, points_of_interest)
        
        # Conversely, how many people does each service have to serve on average?
        burden_per_service = calculate_population_per_service(self.population, points_of_interest)
        
        return {
            "services_per_1000": services_density,
            "people_per_service": burden_per_service
        }

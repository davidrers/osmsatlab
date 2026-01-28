from osmsatlab.io.osm import download_osm_data
from osmsatlab.io.population import get_population_data
from osmsatlab.io.modis import get_modis_temperature
from osmsatlab.io.sentinel2 import get_sentinel2_imagery
from osmsatlab.metrics.accessibility import calculate_nearest_service_distance, calculate_coverage
from osmsatlab.metrics.per_capita import calculate_services_per_capita, calculate_population_per_service
from osmsatlab.metrics.heat_exposure import calculate_heat_exposure_index
from osmsatlab.metrics.temperature import calculate_temporal_median_temperature
from osmsatlab.metrics.correlation import calculate_temperature_correlation
from osmsatlab.vis.animation import create_timelapse
from osmsatlab.constants import SERVICE_DEFINITIONS
import geopandas as gpd
import xarray as xr
import pandas as pd
import warnings
from tqdm.auto import tqdm

class OSMSatLab:
    """
    Core class for OSMSatLab analysis.
    Manages data (population, services) and facilitates accessibility/equity calculations.
    """
    
    def __init__(self, bbox=None, custom_geometry=None, city=None, crs="EPSG:3857", load_population_year=2020, load_services=False):
        """
        Initialize the analysis helper.
        
        Args:
            bbox (tuple, optional): (west, south, east, north).
            custom_geometry (shapely.Geometry or str, optional): Area of interest.
            city (str, optional): Name of a city to geocode and use as the area of interest.
            crs (str): Target CRS for metric calculations (must be projected, default EPSG:3857).
            load_population_year (int, optional): If provided, automatically loads population data for this year.
            load_services (bool, optional): If True, automatically loads all standard service categories.
        """
        # Handle city geocoding if provided
        if city:
            import osmnx as ox
            try:
                # Geocode the city to a GeoDataFrame
                city_gdf = ox.geocode_to_gdf(city)
                # Take the first result's geometry
                custom_geometry = city_gdf.geometry.iloc[0]
                print(f"Successfully located '{city}'")
            except Exception as e:
                raise ValueError(f"Could not find the city '{city}'. Please check the spelling or try a more specific name.") from e

        if bbox is None and custom_geometry is None:
            raise ValueError("I need to know where we are looking! Please provide either a 'bbox' (bounding box), 'custom_geometry', or a 'city' name.")
            
        self.bbox = bbox
        self.custom_geometry = custom_geometry
        self.target_crs = crs
        
        self.population = None
        self.services = {} # Dict of category -> GeoDataFrame
        self.networks = {} # Dict of network_type -> NetworkX Graph
        self.satellite_data = {} # Dict of source -> xarray.DataArray


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
        
    def calculate_accessibility_metrics(self, service_category, threshold=1000, metric_type="euclidean"):
        """
        Compute nearest distance and coverage for a specific service category.
        
        Args:
            service_category (str): Name of the category loaded via fetch_services.
            threshold (float): Distance threshold. 
                               If metric_type is 'euclidean', in meters.
                               If metric_type is network-based (e.g. 'drive'), in minutes.
            metric_type (str): "euclidean" (standard straight line) or a network type like "drive", "walk", "bike".
            
        Returns:
            dict: { 'population_with_distances': GDF, 'coverage_stats': dict }
        """
        if self.population is None:
            raise ValueError("I can't calculate accessibility without people! Please run `.load_population()` first so we know where everyone lives.")
            
        if service_category not in self.services:
            available_categories = list(self.services.keys())
            raise ValueError(f"I couldn't find the '{service_category}' services. I only have these ones right now: {available_categories}. Did you forget to fetch them?")
            
        points_of_interest = self.services[service_category]
        
        # Calculate distances
        if metric_type == "euclidean":
            population_with_access_info = calculate_nearest_service_distance(self.population, points_of_interest)
        else:
            # Assume metric_type is a network mode (e.g. 'drive', 'walk')
            # Ensure the network is loaded
            if metric_type not in self.networks:
                print(f"Network '{metric_type}' not found in cache. Downloading from OSM...")
                self.load_street_network(metric_type)
            
            graph = self.networks[metric_type]
            
            # Use the new network distance function with time weighting
            from osmsatlab.metrics.accessibility import calculate_network_distance
            
            # We want time-based metrics (minutes)
            weight = 'travel_time'
            population_with_access_info = calculate_network_distance(self.population, points_of_interest, graph, weight=weight)
            
            # The result is in seconds (because osmnx calculates travel_time in seconds).
            # Convert to minutes.
            # Handle infinite values carefully
            population_with_access_info['nearest_dist'] = population_with_access_info['nearest_dist'].apply(lambda x: x / 60.0 if x != float('inf') else x)
        
        # Now, let's see how many people are 'close enough' based on our threshold
        coverage_stats = calculate_coverage(population_with_access_info, distance_col='nearest_dist', threshold=threshold)
        
        return {
            "population_gdf": population_with_access_info,
            "coverage_stats": coverage_stats
        }

    def load_street_network(self, network_type="drive"):
        """
        Download and process the street network from OSM.
        
        Args:
            network_type (str): 'drive', 'walk', 'bike', etc.
        """
        from osmsatlab.io.osm import download_street_network
        import osmnx as ox

        # Download raw graph
        G_raw = download_street_network(bbox=self.bbox, custom_geometry=self.custom_geometry, network_type=network_type)
             
        # Project the graph to our target CRS (meters)
        # osmnx.project_graph usually projects to UTM automatically if no CRS provided,
        # but we want to match self.target_crs
        if G_raw is not None:
            G_proj = ox.project_graph(G_raw, to_crs=self.target_crs)
            self.networks[network_type] = G_proj
        return self.networks.get(network_type)
        
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

    # --- Remote Sensing Methods ---

    def load_satellite_data(self, source="temperature", start_date=None, end_date=None, **kwargs):
        """
        Unified loader for satellite data.
        
        Args:
            source (str): 'temperature' (MODIS) or 'sentinel2'.
            start_date (str): YYYY-MM-DD.
            end_date (str): YYYY-MM-DD.
            **kwargs: Additional arguments passed to the underlying fetcher 
                      (e.g., cloud_cover_max, add_ndvi for Sentinel-2).
                      
        Returns:
            xarray.DataArray: The fetched data.
        """
        if start_date is None or end_date is None:
             raise ValueError("Please provide both start_date and end_date.")

        print(f"Fetching {source} data from {start_date} to {end_date}...")
        
        if source == "temperature":
            # For temperature, we default to weekly composites if not specified, for smoother maps
            if "composite_period" not in kwargs:
                kwargs["composite_period"] = "1W"
                
            data = get_modis_temperature(
                bbox=self.bbox, 
                custom_geometry=self.custom_geometry, 
                start_date=start_date, 
                end_date=end_date,
                **kwargs
            )
        elif source == "sentinel2":
            data = get_sentinel2_imagery(
                bbox=self.bbox, 
                custom_geometry=self.custom_geometry, 
                start_date=start_date, 
                end_date=end_date,
                **kwargs
            )
        else:
            raise ValueError(f"Unknown source '{source}'. Supported: 'temperature', 'sentinel2'.")
            
        self.satellite_data[source] = data
        return data

    def calculate_heat_exposure(self, start_date, end_date):
        """
        Calculate Heat Exposure Index for a specific period.
        
        Smart Strategy:
        1. Checks if 'temperature' data is already loaded.
        2. If loaded data covers the requested period, it SLICES the data in memory (Fast).
        3. If not, it FETCHES new data for the specific range (Fallback).
        """
        # 1. Prepare Temperature Data
        lst_subset = None
        
        if "temperature" in self.satellite_data:
            existing_data = self.satellite_data["temperature"]
            
            try:
                # Check strict coverage
                # Convert to pandas Timestamp for comparison
                data_min = pd.Timestamp(existing_data.time.min().values)
                data_max = pd.Timestamp(existing_data.time.max().values)
                req_start = pd.Timestamp(start_date)
                req_end = pd.Timestamp(end_date)
                
                if req_start >= data_min and req_end <= data_max:
                    sliced = existing_data.sel(time=slice(start_date, end_date))
                    if sliced.time.size > 0:
                        print(f"Reusing loaded temperature data ({sliced.time.size} steps covered)...")
                        lst_subset = sliced
                    else:
                        print("Slice is empty despite range overlap. Fetching fresh data...")
                else:
                    print(f"Loaded data ({data_min.date()} to {data_max.date()}) does not cover requested range. Fetching fresh data...")
            except Exception as e:
                print(f"Coverage check failed: {e}. Fetching fresh data...")

        return calculate_heat_exposure_index(
            bbox=self.bbox, 
            custom_geometry=self.custom_geometry, 
            start_date=start_date, 
            end_date=end_date,
            lst_data=lst_subset # Pass the subset (or None to trigger fetch)
        )

    def calculate_temporal_temperature(self, start_date, end_date, aggregation="1W"):
        """
        Calculate temporal median temperature.
        Supports Smart Reuse of loaded 'temperature' data.
        """
        lst_subset = None
        if "temperature" in self.satellite_data:
             existing_data = self.satellite_data["temperature"]
             try:
                data_min = pd.Timestamp(existing_data.time.min().values)
                data_max = pd.Timestamp(existing_data.time.max().values)
                req_start = pd.Timestamp(start_date)
                req_end = pd.Timestamp(end_date)
                
                if req_start >= data_min and req_end <= data_max:
                     sliced = existing_data.sel(time=slice(start_date, end_date))
                     if sliced.time.size > 0:
                         print(f"Reusing loaded temperature data ({sliced.time.size} steps covered)...")
                         lst_subset = sliced
                else:
                     print("Loaded data does not fully cover requested range. Fetching fresh data...")
             except Exception:
                 pass
        
        return calculate_temporal_median_temperature(
            bbox=self.bbox,
            custom_geometry=self.custom_geometry,
            start_date=start_date,
            end_date=end_date,
            aggregation=aggregation,
            lst_data=lst_subset
        )

    def calculate_correlation(self, index_type, start_date, end_date, tensor=False):
        """
        Calculate correlation between Temperature and Index (NDVI/NDBI).
        Fetches necessary data (LST + Sentinel-2) automatically.
        """
        lst_subset = None
        s2_subset = None
        
        # 1. Reuse LST?
        if "temperature" in self.satellite_data:
             existing_data = self.satellite_data["temperature"]
             try:
                data_min = pd.Timestamp(existing_data.time.min().values)
                data_max = pd.Timestamp(existing_data.time.max().values)
                req_start = pd.Timestamp(start_date)
                req_end = pd.Timestamp(end_date)
                
                if req_start >= data_min and req_end <= data_max:
                     sliced = existing_data.sel(time=slice(start_date, end_date))
                     if sliced.time.size > 0:
                         print(f"Reusing loaded temperature data for correlation ({sliced.time.size} steps)...")
                         lst_subset = sliced
             except Exception:
                 pass

        # 2. Reuse Sentinel-2?
        if "sentinel2" in self.satellite_data:
            existing_s2 = self.satellite_data["sentinel2"]
            try:
                # Coverage check
                data_min = pd.Timestamp(existing_s2.time.min().values)
                data_max = pd.Timestamp(existing_s2.time.max().values)
                req_start = pd.Timestamp(start_date)
                req_end = pd.Timestamp(end_date)
                
                if req_start >= data_min and req_end <= data_max:
                    # Band check
                    bands_needed = ["B04", "B08"] if index_type == "NDVI" else ["B08", "B11"]
                    bands_present = existing_s2.band.values
                    if all(b in bands_present for b in bands_needed):
                         sliced = existing_s2.sel(time=slice(start_date, end_date))
                         if sliced.time.size > 0:
                             print(f"Reusing loaded Sentinel-2 data ({sliced.time.size} steps)...")
                             s2_subset = sliced
                    else:
                        print(f"Loaded Sentinel-2 data missing bands for {index_type} (needs {bands_needed}). Fetching fresh...")
            except Exception:
                pass

        return calculate_temperature_correlation(
            index_type=index_type,
            bbox=self.bbox,
            custom_geometry=self.custom_geometry,
            start_date=start_date,
            end_date=end_date,
            tensor=tensor,
            lst_data=lst_subset,
            s2_data=s2_subset
        )

    def animate(self, source, output_path, **kwargs):
        """
        Create a timelapse animation from loaded satellite data.
        
        Args:
            source (str): 'temperature' or 'sentinel2'.
            output_path (str): Filename for GIF.
            **kwargs: Arguments for create_timelapse (fps, cmap, etc).
        """
        if source not in self.satellite_data:
            raise ValueError(f"No data loaded for '{source}'. Run .load_satellite_data('{source}') first.")
            
        data = self.satellite_data[source]
        create_timelapse(data, output_path=output_path, **kwargs)

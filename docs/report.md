# OSMSatLab Technical Report

## 1. Problem Statement

The objective of this project is to evaluate how well different urban populations can access essential services using OpenStreetMap (OSM) and globally available population datasets. Accessibility is measured as the distance or travel cost to the nearest service and the share of population covered within defined thresholds (e.g., within 500 m, 1 km, or 15 minutes walking). Per-capita analysis quantifies how many services exist relative to population (e.g., services per 1,000 inhabitants and population per service), enabling comparison across neighborhoods and administrative units. Together, these indicators support equity assessments, highlighting where service distribution is sufficient and where underserved areas remain.

## 2. Datasets

### OpenStreetMap (OSM)
*   **Source**: OpenStreetMap database, accessed via the `osmnx` Python library.
*   **Description**: We extract vector data for specific service categories corresponding to urban amenities (Health, Education, Food, Emergency). We also extract the street network graph for calculating accurate travel distances.
*   **Processing**:
    *   **Features/POIs**: Features are queried via `osmnx.features.features_from_bbox` or `features_from_polygon` using specific tags (e.g., `amenity=hospital`).
    *   **Network**: The street network is retrieved using `osmnx.graph_from_bbox` or `graph_from_polygon` (configured for 'drive' or 'walk' modes). The graph is processed to add edge speeds and travel times (using `add_edge_speeds` and `add_edge_travel_times`) to facilitate routing.

### WorldPop
*   **Source**: WorldPop Global Project Population Data (UN-adjusted, 1km resolution).
*   **Description**: Gridded population counts consisting of estimated people per grid cell (~1km at the equator). This provides a globally consistent population baseline.
*   **Processing**:
    1.  **ISO3 Identification**: The system determines the country ISO3 code by performing a spatial intersection between the user's Area of Interest (AOI) and the **Natural Earth 110m Admin 0 Countries** dataset. This reference dataset is downloaded once and cached locally. The code calculates the overlap area between the AOI and intersecting countries, selecting the country with the largest intersection to ensure the correct population file is used.
    2.  **Caching Strategy**: To optimize performance and bandwidth, we implement a persistent file-based cache in the user's home directory (`~/.cache/osmsatlab`).
        *   **Reference Data**: Natural Earth boundaries are cached as `ne_110m_admin_0_countries.geojson`.
        *   **Population Data**: WorldPop rasters are cached in `~/.cache/osmsatlab/worldpop` with the filename format `{iso3}_ppp_{year}_1km_Aggregated.tif`.
    3.  **Data Retrieval**: If the specific country file is not present in the cache, the system constructs a dynamic URL to the WorldPop data repository (e.g., `https://data.worldpop.org/...`) and downloads the full country GeoTIFF in chunks to handle potentially large files efficiently.
    4.  **Raster Extraction**: The cached raster is opened using `rasterio`. It is masked/clipped to the exact geometry of the AOI. Finally, pixels with valid population counts (>0) are vectorized into a `GeoDataFrame` of points, maintaining the original population values.

## 3. Methodology

### Methodological Choices
We adopted a modular "Facade" design pattern for the software architecture, utilizing a central class `OSMSatLab` to manage the entire workflow. 
*   **Initialization**: The object is initialized with an Area of Interest (AOI). During this initialization phase, it orchestrates the automatic retrieval and projection of all necessary datasets (WorldPop population grid and OSM service POIs) into the target Coordinate Reference System (CRS).
*   **Analysis Interface**: Once initialized, all analyses are performed through member functions of this object (e.g., `calculate_accessibility_metrics()`, `calculate_per_capita_metrics()`), abstracting the complexity of the underlying `io`, `spatial`, and `metrics` sub-modules from the user. We strictly enforce data projection before any distance calculations to ensure accuracy.

### Geospatial Algorithms & Indexing
To efficiently solve the "nearest service" problem for thousands of population points, we utilize spatial indexing:

1.  **KD-Tree (k-dimensional tree)**:
    *   **Application**: Used for rapid Euclidean distance calculations.
    *   **Process**: We construct a `scipy.spatial.cKDTree` using the coordinates of all service locations. Then, for every population point, we query this tree to find the nearest neighbor (`k=1`) in $O(\log n)$ time complexity on average, rather than comparing every person to every service ($O(n \cdot m)$).

2.  **Shortest Path Search (Dijkstra)**:
    *   **Application**: Used for network-based distance calculations (walking/driving).
    *   **Process**: We map both population points and service locations to their nearest nodes on the street network graph. We then use a Multi-source Dijkstra algorithm (`networkx.multi_source_dijkstra_path_length`) to compute the shortest path cost from *any* of the service nodes to all other reachable nodes in the graph. This is computationally more efficient than running individual Dijkstra searches for every population point.

### Algorithms & Math Formulations

**1. Accessibility (Distance)**
For a population point $p$ and a set of services $S$:
$$ d_{min}(p) = \min_{s \in S} \text{dist}(p, s) $$
Where $\text{dist}$ is either the Euclidean distance or the shortest path distance on the graph.

**2. Coverage Ratio**
The coverage ratio $C_T$ quantifies the proportion of the total population that has access to a service within a specific threshold $T$ (e.g., 1000m or 15 minutes). It is calculated by summing the population at all locations $p$ where the nearest service is within the threshold distance, and dividing by the total population of the study area:
$$ C_T = \frac{\sum_{p \in P \mid d_{min}(p) \le T} \text{pop}(p)}{\sum_{p \in P} \text{pop}(p)} $$
Where:
*   $P$ is the set of all population points.
*   $\text{pop}(p)$ is the population count at location $p$.
*   The condition $d_{min}(p) \le T$ selects only those population points that are within the service range.

**3. Per-Capita Metrics**
*   **Services per 1,000 Inhabitants**:
    $$ M_{sp1k} = \left( \frac{|S|}{\sum_{p \in P} \text{pop}(p)} \right) \times 1000 $$
*   **Population per Service**:
    $$ M_{pps} = \frac{\sum_{p \in P} \text{pop}(p)}{|S|} $$

### Programming Paradigms
*   **Object-Oriented Programming (OOP)**: Central to `osmsatlab.core`, where the `OSMSatLab` class encapsulates analysis state and abstracts data complexity through a unified interface.
*   **Functional / Vectorized Processing**: Used for efficiency via `numpy` and `pandas` to replace loops. Applied in `io.population` for raster masking and in `metrics` for high-speed columnar calculations on GeoDataFrames.

### Test Driven Approach & Version Control
*   **Test-Driven Development (TDD)**: We engaged in a rigorous testing strategy, implementing unit tests (using `pytest`) for core functionalities—such as data downloading logic, metric calculations, and spatial queries—alongside the code development. This ensured robust handling of edge cases (e.g., empty datasets or disjoint geometries).
*   **Version Control**: The project utilized Git for version control, adhering to a structured workflow with frequent commits and feature branches. We followed semantic versioning principles for package releases (`setup.py`).

The following figures show the Git history along with the tests performed for the project.

## 4. Results

The project has been successfully packaged and published to the Python Package Index (PyPI). It is available for installation via:
*   **PyPI**: `pip install osmsatlab`
*   **Source Repository**: `pip install git+https://github.com/davidrers/osmsatlab.git`
*   **Local Archive**: `pip install dist/osmsatlab-0.1.0.tar.gz`

### Application Example
The following script demonstrates the library's capability to automate the analysis workflow. It initializes the environment for a specific region (Usaquén, Bogotá), downloads the data, and iteratively computes accessibility and equity metrics for multiple service categories.

```python
from osmsatlab.core import OSMSatLab
import matplotlib.pyplot as plt

def workflow(osm_lab):
    # Iterate over defined service categories
    for category in ['healthcare', 'education_early', 'education_school', 'education_higher', 'food', 'emergency', 'green_space', 'public_transport']:
        
        # 1. Calculate Accessibility Metrics
        # Compute coverage for different modes of transport and thresholds:
        # - Euclidean distance (1km radius)
        # - Driving network distance (5 minutes)
        # - Walking network distance (10 minutes)
        results_eucl = osm_lab.calculate_accessibility_metrics(service_category=category, threshold=1000, metric_type='euclidean')
        results_drive = osm_lab.calculate_accessibility_metrics(service_category=category, threshold=5, metric_type='drive')
        results_walk = osm_lab.calculate_accessibility_metrics(service_category=category, threshold=10, metric_type='walk')
        
        # Extract coverage statistics dictionaries
        stat_e = results_eucl['coverage_stats']
        stat_d = results_drive['coverage_stats']
        stat_w = results_walk['coverage_stats']

        # Output Accessibility Results
        print('-------------------------------------------------------------------------')
        print(f"CATEGORY: {category.upper()}")
        print(f"Euclidean (1km):  {stat_e['coverage_ratio']:.2%} coverage ({stat_e['covered_population']:,} people)")
        print(f"Driving (5min):   {stat_d['coverage_ratio']:.2%} coverage ({stat_d['covered_population']:,} people)")
        print(f"Walking (10min):  {stat_w['coverage_ratio']:.2%} coverage ({stat_w['covered_population']:,} people)")

        # 2. Calculate Per-Capita (Equity) Metrics
        # services_per_1000: Number of facilities per 1,000 residents
        # people_per_service: Average number of people served by one facility
        results = osm_lab.calculate_per_capita_metrics(service_category=category)
        print('--------------------------------------------')
        print(f"services_per_1000 (category {category}): {results['services_per_1000']}")
        print(f"people_per_service (category {category}): {results['people_per_service']}")
        print('------------------------------------------------------------------------------------------------------------')

# Define the bounding box for the study area (Usaquén, Bogotá)
bbox_usaquen = (-74.0870, 4.6760, -73.9970, 4.8360)

# Initialize the OSMSatLab analysis object
# This step automatically handles:
# - ISO3 identification and WorldPop data download
# - OSM feature extraction and street network retrieval
# - Projection of all datasets to the appropriate CRS
osm_lab = OSMSatLab(bbox=bbox_usaquen)

# Execute the analysis workflow
workflow(osm_lab)
```

## 5. Discussion
*(This section to be filled based on results. Example points to consider in final version:)*
*   *Limitations of 1km resolution population data for micro-analysis.*
*   *Impact of "edge effects" (services just outside the bounding box are ignored).*
*   *Difference between Euclidean and Network distances in irregular road networks.*

## 6. Conclusion
*(This section to be filled after project completion).*

## 7. Workload Distribution
*(To be filled by students).*

## 8. References
1.  **OpenStreetMap**: OpenStreetMap contributors. (2025). Planet dump retrieved from https://planet.openstreetmap.org
2.  **WorldPop**: WorldPop (www.worldpop.org - School of Geography and Environmental Science, University of Southampton; Department of Geography and Geosciences, University of Louisville; Departement de Geographie, Universite de Namur) and Center for International Earth Science Information Network (CIESIN), Columbia University (2018). Global High Resolution Population Denominators Project - Funded by The Bill and Melinda Gates Foundation (OPP1134076).
3.  **OSMnx**: Boeing, G. (2017). OSMnx: New Methods for Acquiring, Constructing, Analyzing, and Visualizing Complex Street Networks. Computers, Environment and Urban Systems, 65, 126-139.

## Appendix: API Reference

### Class `osmsatlab.core.OSMSatLab`
The main facade class for orchestrating the geospatial analysis.

#### `__init__(bbox=None, custom_geometry=None, crs="EPSG:3857", load_population_year=2020, load_services=True)`
Initializes the analysis environment.
*   **bbox**: Tuple of (west, south, east, north) coordinates.
*   **custom_geometry**: Path to GeoJSON or Shapely geometry for the Area of Interest.
*   **crs**: Projected CRS to be used for metric calculations (default: "EPSG:3857").
*   **load_population_year**: Year to automatically load WorldPop data for (default: 2020).
*   **load_services**: If True, pre-loads standard OSM service categories.

#### `load_population(year=2020)`
Downloads (if not cached) and loads WorldPop data for the AOI, projecting it to the target CRS. Returns the population GeoDataFrame.

#### `fetch_services(tags, category_name="default")`
Downloads OSM features matching the provided tags within the AOI. Projects them to the target CRS and converts polygons to centroids for analysis.

#### `load_street_network(network_type="drive")`
Downloads and projects the OSM street network graph for the specified mode (e.g., 'drive', 'walk'). Cached locally.

#### `calculate_accessibility_metrics(service_category, threshold=1000, metric_type="euclidean")`
Computes distance-based accessibility metrics.
*   **service_category**: The category of services to analyze (e.g., 'healthcare').
*   **threshold**: Distance (meters) or Time (minutes) threshold for coverage calculation.
*   **metric_type**: 'euclidean' for straight-line distance, or a network type ('drive', 'walk') for path-based distance.
*   **Returns**: Dictionary containing:
    *   `population_gdf`: GeoDataFrame of population points with a new `nearest_dist` column.
    *   `coverage_stats`: Dictionary with `coverage_ratio`, `covered_population`, and `total_population`.

#### `calculate_per_capita_metrics(service_category)`
Computes equity metrics based on population counts.
*   **service_category**: The category of services to analyze.
*   **Returns**: Dictionary containing:
    *   `services_per_1000`: Number of services per 1,000 people.
    *   `people_per_service`: Average population served per facility.

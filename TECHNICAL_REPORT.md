# Technical Report: Integrated Urban Heat Island and Vulnerability Analysis

## 1. Problem Statement

Rapid urbanization and climate change have intensified the **Urban Heat Island (UHI)** effect, posing severe health risks to city dwellers. However, addressing this challenge requires more than just mapping high temperatures; effective policy depends on understanding *who* is exposed and whether they have access to essential services like healthcare. Historically, this type of comprehensive analysis has been limited by the technical difficulty of processing massive global satellite datasets.

The objective of this project was to overcome these barriers by developing a **scalable, cloud-native computational framework**. Our goals were to:
1.  **Democratize Analysis**: Leverage modern cloud tools (Stackstac, Dask) to make high-performance satellite processing accessible without specialized infrastructure.
2.  **Assess the Full Picture**: Move beyond simple heat mapping to measure the "triple burden" of Heat, Population Density, and minimal Access to services.
3.  **Guide Action**: Provide clear, high-resolution insights that urban planners can use to identify priority intervention areas.

## 2. Datasets

We utilized a multi-modal approach combining raster and vector datasets from open-source global providers.

### 2.1. Raster Sources
*   **MODIS Land Surface Temperature (LST)**:
    *   **Source**: Microsoft Planetary Computer (Collection: `modis-11a1-061`).
    *   **Description**: Daily Land Surface Temperature (Day/Night). We utilized the `LST_Day_1km` band converted to Celsius.
    *   **Resolution**: 1km spatial, Daily temporal.
*   **Sentinel-2 Level-2A**:
    *   **Source**: Microsoft Planetary Computer.
    *   **Description**: Optical imagery used for calculating indices like **NDVI** (Normalized Difference Vegetation Index) and **NDBI** (Normalized Difference Built-up Index) to correlate with temperature.
    *   **Resolution**: 10m spatial, ~5-day temporal.
*   **WorldPop**:
    *   **Source**: WorldPop global project.
    *   **Description**: Gridded population counts (unconstrained).
    *   **Resolution**: 100m spatial, Annual (2020 used).

### 2.2. Vector Sources
*   **OpenStreetMap (OSM)**:
    *   **Source**: Overpass API via `osmnx`.
    *   **Description**: We retrieve vector geometries for critical service categories (Health, Education, Food, Emergency) alongside administrative city boundaries. This includes Points of Interest (POIs) and street networks for distance calculations.
    *   **Spatial Extent**: Dynamic fetching based on the user-defined Area of Interest (AOI).
*   **Administrative Units (LAU)**:
    *   **Source**: GISCO (Eurostat).
    *   **Description**: Local Administrative Units (LAU) for the Netherlands, providing standardized statistical zones for aggregating raster metrics.
    *   **Spatial Extent**: National coverage (Netherlands), filtered spatially by the analysis AOI.

## 3. Methodology

The core logic is encapsulated within the `OSMSatLab` library, which employs a modular architecture separating I/O, Metrics, and Core workflow management. A single `OSMSatLab` instance serves as the central interface, providing unified access to all datasets (POIs, Sentinel-2, MODIS, Population) and analysis methods. To ensure reliability and reproducibility, the development followed a rigorous **Test-Driven Development (TDD)** approach validation via `pytest`, supported by systematic **Version Control** with Git.

### 3.1. Raster Data Processing & Data Cubes
We employed a modern cloud-native approach to handle high-dimensional satellite data, leveraging **Xarray** and **Stackstac** to construct 4D Data Cubes (time, band, y, x).

*   **Unified Loading Interface**: The `.load_satellite_data` method acts as a high-level abstraction, orchestrating the complex retrieval of both Sentinel-2 and MODIS archives. It allows users to seamlessly switch between data sources while maintaining a consistent output format.
*   **Advanced Filtering**: To ensure data quality, we implemented a multi-stage filtering process:
    *   **Time Range Filtering**: Scenes are strictly filtered based on the user-defined start and end dates.
    *   **Local Cloud Masking**: Critically, we go beyond scene-level metadata. By loading the Scene Classification Layer (SCL) for Sentinel-2, we identify specific pixels flagged as "Cloud High Probability" or "Cloud Shadow". These are optionally masked (replaced with NaN) to prevent contamination of the analysis.
    *   **Spatial Coverage Filter**: We implemented a check (`min_coverage`) to discard scenes that technically intersect the bounding box but only cover a negligible fraction of the area of interest.
*   **Lazy Evaluation with Dask & COGs**: By leveraging **Cloud Optimized Geotiffs (COGs)**, the system fetches only the byte-ranges corresponding to the requested Area of Interest (AOI), avoiding full-image downloads. **Dask** builds a symbolic task graph of these operations, deferring execution until absolutely necessary (e.g., rendering a plot). This allows us to define complex pipelines on terabytes of data while keeping memory usage minimal.
*   **Virtual Indices & Compositing**: Spectral indices (NDVI, NDBI) are computed on-the-fly within the Dask graph without intermediate storage. Additionally, the `composite_period` parameter allows for robust temporal aggregation (e.g., monthly median) to minimize cloud contamination.

### 3.2. Algorithms & Math Formulations
Our framework combines raster algebra—leveraging high-performance **NumPy** arrays, **Xarray** data cubes, and **PyTorch** tensors—with vector data integration to compute explainable environmental metrics.

*   **Temporal Temperature Aggregation**: The `.calculate_temporal_temperature` algorithm reduces the 4D Data Cube along the time axis using `xarray.resample(time=freq).median()`. This median compositing approach is statistically robust, effectively mitigating outliers caused by transient cloud cover or sensor anomalies while preserving the seasonal signal.

*   **Spatio-Temporal Correlation**: The `.calculate_correlation` method quantifies the relationship between urban form (indices) and temperature (LST).
    *   *Alignment*: Essential grid alignment is performed using `rioxarray.reproject_match`, resampling the 10m Sentinel-2 index to the coarse 1km MODIS grid.
    *   *Metric*: We compute the Pearson Correlation Coefficient ($r$) on flattened, valid pixel arrays:
        $$ r = \frac{\sum(x_i - \bar{x})(y_i - \bar{y})}{\sqrt{\sum(x_i - \bar{x})^2 \sum(y_i - \bar{y})^2}} $$

*   **Heat Exposure Index (HEI)**: The `calculate_heat_exposure_index` method quantifies human risk by identifying areas where extreme temperatures intersect with high population density. It synthesizes the physical hazard (LST) and the social exposure (Population) into a single metric.
    *   *Normalization*: To combine disparate scales (Temperature $\approx$ 30°C vs Population $\approx$ 100s), we use **Robust Min-Max Normalization** based on quantiles ($Q_{0.02}, Q_{0.98}$) to suppress outliers:
        $$ X'_{norm} = \frac{X - Q_{0.02}}{Q_{0.98} - Q_{0.02}} $$
    *   *Product*: $$ HEI = Norm(LST) \times Norm(Population) $$

*   **Integrated Vulnerability**: The `calculate_heat_access_vulnerability` method fuses the raster-derived HEI with **vector-based accessibility metrics (specifically, Euclidean distance to nearest Healthcare facility)** to identify areas of compounding risk.
    *   *Zonal Statistics*: We implement a custom zonal algorithm (using `rasterio.features.rasterize`) to aggregate the HEI raster into administrative vector units.
    *   *Tensor Processing*: The final weighted combination is computed using **PyTorch Tensors**, allowing for efficient gradients in future optimization steps:
        $$ V_{score} = w_h \cdot HEI_{zonal} + w_a \cdot Distance_{health} + w_p \cdot Pop_{total} $$

### 3.3. Visualization Module
The visualization workflow separates data generation from rendering. 
*   **Dynamic Time-Lapse (.animate)**: Although extending beyond the core assignment requirements, we implemented a robust `.animate` method (via `matplotlib.animation`) to visualize the temporal evolution of any 4D Data Cube. This allows users to generate "ready-to-go" GIFs for any location globally, dynamically visualizing changes in RGB imagery, Land Surface Temperature, or spectral indices (NDVI) over time.
*   **Static Metrics**: Standardized plotting functions (`plot_distribution`, `plot_pairwise`) provide immediate visual verification of statistical relationships and distributions.



## 4. Results

The framework was tested on **Overijssel, Netherlands** and **Soacha, Colombia**.

### 4.1. Raster Data Processing & Data Cubes
We successfully established a workflow that can fetch and process satellite imagery for any location on Earth. By using lazy evaluation, we handled complex, high-dimensional datasets without needing a supercomputer. In practice, this means we can retrieve years of data and generate ready-to-use visualizations—like time-lapse animations of temperature or vegetation—in just a matter of minutes. This efficiency allows us to focus more on the analysis rather than waiting for downloads.

### 4.2. Temporal Trends
The `calculate_temporal_temperature` analysis revealed clear seasonal patterns in LST. By leveraging this method, we can rapidly generate trend graphs for any location globally, enabling the immediate identification of seasonal anomalies or warming trends. The `.animate` function further enhances this by producing visual time-series, highlighting peak heat events such as those observed in Summer 2023.

### 4.3. Correlation Analysis
Using `calculate_correlation`, we assessed the relationship between LST and Urban indices.
*   **NDBI vs LST**: Showed a **positive correlation** (r > 0.5), confirming that built-up areas retain more heat.
*   **NDVI vs LST**: Showed a **negative correlation**, illustrating the cooling effect of vegetation ("Park Cool Island" effect).

**Performance Benchmark (NumPy vs. PyTorch)**:
We implemented the correlation calculation using both NumPy arrays and PyTorch tensors to test scalability. Benchmarking revealed a performance crossover point at approximately 1 million pixels:
*   **Small Scales (< 100k pixels)**: NumPy is significantly faster (e.g., ~0.5ms vs ~3.0ms for 10k) due to lower initialization overhead.
*   **Large Scales (> 1M pixels)**: PyTorch demonstrates superior scaling. At 10 million pixels, the Tensor implementation (55.9ms) was nearly **3x faster** than NumPy (153.0ms), justifying the use of Tensors for high-resolution regional analysis.

### 4.4. Integrated Vulnerability Analysis (Heat + Access)
The final **Vulnerability Score** synthesizes the physical hazard (Heat), social exposure (Population), and lack of coping capacity (Access).
*   **Result**: The generated map (see `Heat-Access Priority Index.png`) successfully highlights "red zones"—neighborhoods experiencing the "triple burden" of high temperatures, dense population, and poor access to healthcare.
*   **Significance**: This multi-criteria approach identifies priority areas that would be missed by looking at temperature maps alone, providing a more equitable basis for urban planning interventions.

### 4.5. Documentation
To facilitate reproducibility and reuse, we have published comprehensive documentation for the project:

*   **Repository**: [GitHub Link](https://github.com/davidrers/osmsatlab)
*   **API Reference**: [Online Documentation](https://davidrers.github.io/osmsatlab/)
*   **Installation**: Refer to the [README.md](README.md) for setup instructions (`poetry install`).
*   **Interactive Examples**:
    *   [Accessibility Analysis](docs/examples/interactive_testing_accesibility_analysis.ipynb)
    *   [Heat Island Analysis](docs/examples/interactive_testing_heat_island_analysis.ipynb)

## 5. Discussion

The main takeaway from this exercise was discovering the flexibility and ease that the modern python geospatial stack offers. Tools like `stackstac` make fetching historical satellite imagery surprisingly simple, and when combined with **Cloud Optimized GeoTIFFs (COGs)** and **Dask** for lazy evaluation, they become an impressively powerful toolset. This allows us to process vast amounts of data without complex infrastructure, bringing high-performance computing to a standard laptop.

### 5.1. Design Choices & Trade-offs
Our solution prioritized **modularity and transparency**. By implementing core algorithms (like Zonal Stats) from scratch using NumPy and Rasterio, we avoided dependency bloat. However, integrating disparate data sources introduced challenges:
*   **Resolution Mismatch**: We successfully aligned coarse MODIS (1km) temperature data with high-res Sentinel-2 (10m) indices using `reproject_match`, acknowledging that this introduces spatial generalization.
*   **PyTorch vs. NumPy**: While our benchmark showed PyTorch is superior for massive scales (>1M pixels), using Tensors for simple weighted sums on small study areas proved to be computational overkill. Nevertheless, it establishes the necessary infrastructure for future GPU scaling.

### 5.2. Limitations
*   **Cloud Cover**: This remains a hard limitation for optical remote sensing. In regions like **Enschede** or tropical areas like Soacha, persistent cloud cover severely limits the availability of usable Sentinel-2 and MODIS LST data. While our median compositing strategy mitigates this, it cannot reconstruct data during prolonged overcast periods.
*   **Modifiable Areal Unit Problem (MAUP)**: The vulnerability index results are sensitive to the size and shape of the administrative units chosen.

## 6. Conclusion

This project successfully implemented an end-to-end pipeline for Urban Heat Island analysis. We learned effective strategies for:
1.  **Hybrid Geocomputation**: Integrating disparate data models (Raster/Vector) requires rigorous CRS management and alignment strategies.
2.  **Data Caching**: Implementing local caching for OSM and STAC queries significantly sped up iterative development.
3.  **Scientific Software Design**: Building a clean API (`lab.function()`) hides complexity from the user while maintaining scientific rigor in the backend.

The resulting tool provides urban planners with actionable, high-resolution insights into environmental justice issues.

## 7. Workload Distribution

*   **David Alfonso Reyes Munoz (s359853)**:
    *   Core library architecture (`OSMSatLab` facade class, module structure).
    *   Data acquisition modules (`io.osm`, `io.population`).
    *   Spatial indexing implementation (KD-tree) and Network routing (Dijkstra via OSMnx).
    *   Accessibility metrics calculation and Caching system design.
    *   Package configuration, PyPI deployment, and Git setup.
    *   Comprehensive test suite for core and metrics modules.

*   **Anisha (s3592103)**:
    *   **Integrated Vulnerability Analysis (Heat + Access)**.
    *   Visualization module development (`viz` package: `units.py`, `aggregation.py`, `choropleth.py`, `plot.py`).
    *   Spatial unit generation (grid tessellation, LAU boundary integration).
    *   Data aggregation functions and Static visualization implementation.
    *   Interactive Folium map and Workflow integration (`render_maps`).
    *   Comprehensive test suite for visualization module and Example scripts.

## 8. References

1.  **WorldPop**: (www.worldpop.org) - School of Geography and Environmental Science, University of Southampton.
2.  **OpenStreetMap**: (www.openstreetmap.org) - OpenStreetMap Foundation.
3.  **Planetary Computer**: (planetarycomputer.microsoft.com) - Microsoft.
4.  **Xarray**: Hoyer, S. & Hamman, J., (2017). *xarray: N-D labeled Arrays and Datasets in Python*.

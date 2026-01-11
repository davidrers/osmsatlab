# OSMSatLab

**OSMSatLab** is a Python library for comprehensive urban accessibility and equity analysis. It seamlessly integrates **OpenStreetMap (OSM)** service locations with **WorldPop** raster population data to calculate high-resolution coverage metrics.

Designed for ease of use, it automates data retrieval, processing, and visualization through a single unified interface.

## Key Features

-   **Automated Data Retrieval**: Automatically identifies countries, downloads WorldPop geotiffs, and fetches cached OSM data for any given area.
-   **Multi-Modal Analysis**: Calculates distances using Euclidean, Driving (approximate), and Walking network metrics.
-   **Coverage & Equity**: Computes:
    -   **Coverage Ratio**: Percent of population within a specific service threshold (e.g., 1km).
    -   **Service Density**: Services per 1,000 inhabitants.
    -   **Service Burden**: Population per service.
-   **Integrated Visualization**: Built-in plotting tools for population choropleths, service density maps, and distance histograms.
-   **Efficient Architecture**: Uses spatial indexing (KD-trees) and raster-vector hybridization for high-performance analysis on large regions.

## Installation

You can install `osmsatlab` using pip or Poetry.

### Using Poetry (Recommended)
```bash
poetry add osmsatlab
```

### Using pip
```bash
pip install osmsatlab
```

---

## Quick Start

The core of the library is the `OSMSatLab` facade class. It handles initialization and data loading automatically.

### 1. Basic Initialization
Initialize with a bounding box (minx, miny, maxx, maxy). This automatically downloads population data and OSM services.

```python
from osmsatlab.core import OSMSatLab

# Bounding box for Amsterdam
bbox = (4.85, 52.33, 4.95, 52.40) 

# Initialize lab (downloads data automatically)
lab = OSMSatLab(bbox=bbox, crs="EPSG:3857")
```

### 2. Calculate Metrics
Compute accessibility metrics for a specific service category (e.g., 'healthcare', 'education_school').

```python
# Calculate Accessibility (Euclidean, 1km threshold)
access_metrics = lab.calculate_accessibility_metrics('healthcare', threshold=1000, metric_type='euclidean')
print(f"Coverage Ratio: {access_metrics['coverage_stats']['coverage_ratio']:.2%}")

# Calculate Per-Capita Equity
equity_metrics = lab.calculate_per_capita_metrics('healthcare')
print(f"Services per 1k people: {equity_metrics['services_per_1000']:.4f}")
```

### 3. Visualization
Use the built-in visualization tools to generate maps instantly.

```python
from osmsatlab.viz import render_maps
import matplotlib.pyplot as plt

# Generate maps for healthcare access
render_maps(lab, "Amsterdam", service_category='healthcare')
plt.show()
```

---

## Project Structure

The library is organized into modular components:

*   **`osmsatlab.core`**: Contains the `OSMSatLab` facade class, the main entry point.
*   **`osmsatlab.io`**: Data fetching modules for OSM (`osm.py`) and WorldPop (`population.py`).
*   **`osmsatlab.metrics`**: Calculation logic for `accessibility` and `per_capita` metrics.
*   **`osmsatlab.spatial`**: Spatial operations and `index` (KDTree) management.
*   **`osmsatlab.viz`**: Visualization workflows, including `render_maps` and choropleth utilities.

## Methodology

OSMSatLab uses a raster-based population approach combined with vector-based service locations.
1.  **Population**: WorldPop 100m/1km resolution rasters are masked to the Area of Interest (AOI).
2.  **Services**: OSM Points of Interest (POIs) are fetched and spatially indexed.
3.  **Analysis**: For every population pixel centroid, the nearest service distance is calculated. The population count of pixels falling within the distance threshold is aggregated to determine total coverage.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

# OSMSatLab

**OSMSatLab** is a Python library designed for calculating accessibility and equity metrics using OpenStreetMap (OSM) data. It provides tools to download OSM data, process spatial information, and compute various metrics related to urban accessibility.

## key Features

- **Data Download**: Easily download OpenStreetMap data for any given bounding box.
- **Spatial Analysis**: Perform spatial operations using efficient indices (R-tree).
- **Accessibility Metrics**: Calculate distances to nearest services (e.g., hospitals, schools, parks).
- **Service Coverage**: Evaluate population coverage within specific distances of services.

## Installation

You can install `osmsatlab` using pip (once published):

```bash
pip install osmsatlab
```

Or using Poetry:

```bash
poetry add osmsatlab
```

## Usage

Here is a quick example of how to use `OSMSatLab`:

```python
from osmsatlab import OSMSatLab

# Initialize the library
lab = OSMSatLab()

# Example usage (adjust based on actual API)
# lab.download_data(bbox=...)
# metrics = lab.calculate_accessibility(...)
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

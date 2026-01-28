
import geopandas as gpd
from shapely.geometry import Polygon
import numpy as np
from osmsatlab.io.sentinel2 import get_sentinel2_imagery

# Define a triangle geometry (non-rectangular)
# Bounding box roughly: (-74.1, 4.7)
poly = Polygon([
    (-74.1, 4.7),       # point 1
    (-74.08, 4.7),      # point 2
    (-74.09, 4.72),     # point 3 (peak)
])

print("Creating Sentinel-2 cube with custom geometry (triangle)...")
cube = get_sentinel2_imagery(
    custom_geometry=poly,
    start_date="2023-01-01",
    end_date="2023-01-30",
    cloud_cover_max=50,
    bands=["B02"],
    resolution=100  # Low res for speed
)

print(f"Cube dims: {cube.dims}")
print("Computing...")
data = cube.compute()

# Check if we have NaNs (which indicate clipping happened outside the triangle but inside bbox)
nan_count = np.isnan(data).sum().item()
total_count = data.size
print(f"Total pixels: {total_count}")
print(f"NaN pixels: {nan_count}")

# We expect some NaNs because the bbox of the triangle is larger than the triangle itself
if nan_count > 0:
    print("SUCCESS: Clipping applied (NaNs found outside geometry).")
else:
    print("FAILURE: No NaNs found, clipping might not have worked.")

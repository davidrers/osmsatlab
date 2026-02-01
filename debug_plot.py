
import pandas as pd
from osmsatlab.io.sentinel2 import get_sentinel2_imagery
import dask.diagnostics

# Use a small test case
BBOX_BOGOTA_RESIDENTIAL = (-74.1255, 4.7195, -74.0825, 4.7565)
cube = get_sentinel2_imagery(
    bbox=BBOX_BOGOTA_RESIDENTIAL,
    start_date="2023-06-01",
    end_date="2023-06-10", # Short range
    cloud_cover_max=80
)

print("Computing cube...")
with dask.diagnostics.ProgressBar():
    data = cube.compute()

print(f"Data shape: {data.shape}")
print(f"Data dims: {data.dims}")
print(f"Data coords: {data.coords}")

# Simulate user loop
for t in data.time:
    try:
        rgb_slice = data.sel(time=t, band=["B04", "B03", "B02"])
        print(f"Time: {t.values}")
        print(f"Slice shape: {rgb_slice.shape}")
        print(f"Slice dims: {rgb_slice.dims}")
        
        # Check for scalar dimensions or missing bands
        if len(rgb_slice.shape) != 3:
             print("WARNING: Slice is not 3D!")
    except Exception as e:
        print(f"Error selecting bands: {e}")
        break  

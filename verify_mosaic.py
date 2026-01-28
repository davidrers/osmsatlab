
import pandas as pd
from osmsatlab.io.sentinel2 import get_sentinel2_imagery
import dask.diagnostics

# Bogota bounding box known to cross tile boundaries (or at least returned duplicates before)
BBOX_BOGOTA_RESIDENTIAL = (-74.1255, 4.7195, -74.0825, 4.7565)

print("Creating Sentinel-2 cube...")
cube = get_sentinel2_imagery(
    bbox=BBOX_BOGOTA_RESIDENTIAL,
    start_date="2023-06-01",
    end_date="2023-06-10",
    cloud_cover_max=80
)

print("Computing cube...")
with dask.diagnostics.ProgressBar():
    data = cube.compute()

# Check for duplicates in time dimension
time_values = data.time.values
unique_times = pd.unique(time_values)

print(f"Total time steps: {len(time_values)}")
print(f"Unique time steps: {len(unique_times)}")

if len(time_values) == len(unique_times):
    print("SUCCESS: No duplicate time steps found. Mosaicing worked.")
else:
    print(f"FAILURE: Found {len(time_values) - len(unique_times)} duplicates.")
    # Print them out
    print(pd.Timestamp(t) for t in time_values)

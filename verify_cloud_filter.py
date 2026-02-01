
import pandas as pd
from osmsatlab.io.sentinel2 import get_sentinel2_imagery
import dask.diagnostics

print("Starting Local Cloud Filter Verification...")

# Use a tight cloud threshold (e.g., 5%) to see if it aggressively filters scenes
# that might be 80% cloudy overall but clear locally.
try:
    cube = get_sentinel2_imagery(
        bbox=(-74.1255, 4.7195, -74.0825, 4.7565), # Bogota
        start_date="2023-05-01",
        end_date="2023-06-30",
        cloud_cover_max=10, # Strict local threshold
        bands=["B02"]
    )
    
    print("Filtering complete.")
    print(f"Final cube dimensions: {cube.dims}")
    print(f"Final time steps: {len(cube.time)}")
    
    if len(cube.time) > 0:
        print("Computing first frame to ensure data validity...")
        first_frame = cube.isel(time=0).compute()
        print("Compute successful.")
        
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()

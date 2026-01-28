
import os
import shutil
from shapely.geometry import box
from osmsatlab.io.sentinel2 import get_sentinel2_imagery
import pandas as pd
import numpy as np
import xarray as xr

# Define a small AOI in Bogota
BBOX = (-74.05, 4.60, -74.04, 4.61)

# specific time range
START_DATE = "2023-01-01"
END_DATE = "2023-01-10"

def run_test():
    print(f"\n--- Testing Cloud Masking ---")
    try:
        # Get raw data first to find a cloudy scene
        print("Fetching raw data...")
        raw_data = get_sentinel2_imagery(
            bbox=BBOX,
            start_date=START_DATE,
            end_date=END_DATE,
            cloud_cover_max=100,
            mask_clouds=False,
            add_ndvi=False
        )
        
        if len(raw_data.time) == 0:
            print("No scenes found to test.")
            return

        # Pick the cloudiest scene
        # We need SCL to know which is cloudy, but it might have been dropped.
        # Let's hope index 0 has some clouds or just run mask on all and check NaNs.
        
        print("Fetching masked data...")
        masked_data = get_sentinel2_imagery(
            bbox=BBOX,
            start_date=START_DATE,
            end_date=END_DATE,
            cloud_cover_max=100,
            mask_clouds=True,
            add_ndvi=False
        )
        
        # Verify NaNs
        print("\nVerifying NaNs in masked data:")
        for t in masked_data.time.values:
            ts = pd.Timestamp(t).strftime('%Y-%m-%d')
            
            # Get raw slice
            raw_slice = raw_data.sel(time=t, band="B04") # Assuming B04 exists
            
            # Get masked slice
            # Note: masked_data might have filtered out different scenes if cloud_cover_max was restrictive,
            # but here it is 100, so times should align.
            if t not in raw_data.time:
                continue
                
            masked_slice = masked_data.sel(time=t, band="B04")
            
            # Check for NaNs
            nan_count = masked_slice.isnull().sum().item()
            total_count = masked_slice.size
            nan_pct = (nan_count / total_count) * 100
            
            print(f"  Date: {ts}, NaNs: {nan_count}/{total_count} ({nan_pct:.2f}%)")
            
            # Basic sanity check: if it was masked, there should be NaNs (unless 100% clear)
            # And masked values should be different from raw values (unless raw was already NaN)
            
            # Select pixels that are NaN in masked but NOT NaN in raw
            # These are the pixels that were actively masked out
            actively_masked = masked_slice.isnull() & raw_slice.notnull()
            masked_count = actively_masked.sum().item()
            print(f"    -> Actively masked cloud pixels: {masked_count}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    run_test()

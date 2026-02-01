
import os
import sys
# import pyproj
from osmsatlab.io.sentinel2 import get_sentinel2_imagery
import dask.diagnostics

# Print original env before import (might be too late if script ran before but standard python execution it's fine)
# Actually, we want to see if import osmsatlab cleared it.
# We will print it after import (if it was cleared) or before if we really want to check.
# But since we import osmsatlab first thing in this script (after os/sys), the effect should be immediate.

print(f"PROJ_LIB before test: {os.environ.get('PROJ_LIB')}")

BBOX_BOGOTA_RESIDENTIAL = (-74.1255, 4.7195, -74.0825, 4.7565)
try:
    cube = get_sentinel2_imagery(
        bbox=BBOX_BOGOTA_RESIDENTIAL,
        start_date="2023-06-01",
        end_date="2023-06-30",
        cloud_cover_max=80
    )

    print("Cube created successfully.")
    
    with dask.diagnostics.ProgressBar():
        data = cube.compute()
    print("Computation successful.")

except Exception as e:
    print(f"Caught exception: {e}")
    # import traceback
    # traceback.print_exc()

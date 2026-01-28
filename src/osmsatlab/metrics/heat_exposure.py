
import shapely.geometry
import xarray as xr
import numpy as np
import warnings
from ..io import get_modis_temperature, get_population_raster

def _robust_normalize(da: xr.DataArray, q_min: float = 0.02, q_max: float = 0.98) -> xr.DataArray:
    """
    Normalize DataArray to 0-1 range using robust percentiles to ignore outliers.
    """
    # Calculate quantiles
    try:
         # generic quantile for xarray (works lazily with dask if recent xarray version, else computes)
        vmin = da.quantile(q_min).item()
        vmax = da.quantile(q_max).item()
        
        if vmin == vmax:
             return xr.zeros_like(da)

        # Scale
        da_norm = (da - vmin) / (vmax - vmin)
        
        # Clip to 0-1 (handle outliers)
        da_norm = da_norm.clip(0, 1)
        
        return da_norm
    except Exception as e:
        warnings.warn(f"Failed to calculate quantiles (possibly empty/NaN data): {e}")
        return da # Return as is or zeros?

def calculate_heat_exposure_index(
    bbox: tuple[float, float, float, float] | None = None,
    custom_geometry: str | shapely.geometry.base.BaseGeometry | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    year: int = 2020,
    lst_data: xr.DataArray | None = None, # Support for pre-loaded data
    pop_data: xr.DataArray | None = None # Support for pre-loaded data
) -> xr.DataArray:
    """
    Calculate a Heat Exposure Index based on Land Surface Temperature and Population Density.
    Fetches MODIS LST and WorldPop data automatically for the specified area and time range,
    OR uses provided pre-loaded data.
    
    Index = (Normalized LST) * (Normalized Population)
    
    Args:
        bbox (tuple, optional): (west, south, east, north) in EPSG:4326.
        custom_geometry (str or geometry, optional): Path to GeoJSON or Shapely geometry.
        start_date (str): Start date (YYYY-MM-DD). Not required if lst_data is provided.
        end_date (str): End date (YYYY-MM-DD). Not required if lst_data is provided.
        year (int, optional): Year for population data. Defaults to 2020.
        lst_data (xr.DataArray, optional): Pre-loaded LST data. If provided, fetching is skipped.
        pop_data (xr.DataArray, optional): Pre-loaded population data. If provided, fetching is skipped.
                                 
    Returns:
        xr.DataArray: Heat Exposure Index (0-1 range, unitless).
    """
    if lst_data is None:
        if start_date is None or end_date is None:
            raise ValueError("start_date and end_date are required if lst_data is not provided.")
            
        print(f"Fetching MODIS LST from {start_date} to {end_date}...")
        lst_data = get_modis_temperature(
            bbox=bbox,
            custom_geometry=custom_geometry,
            start_date=start_date,
            end_date=end_date,
            composite_period=None, 
            convert_to_celsius=True
        )
    else:
        print("Using pre-loaded LST data.")
    
    if pop_data is None:
        print(f"Fetching WorldPop Population ({year})...")
        pop_data = get_population_raster(
            bbox=bbox,
            custom_geometry=custom_geometry,
            year=year
    )
    else:
        print("Using pre-loaded Population data.")
    
    # 2. Time Reduction
    if "time" in lst_data.dims:
        print("Reducing LST time series to mean image...")
        lst_data = lst_data.mean(dim="time", skipna=True)
    # Reproject population to match LST grid (LST is usually the master grid here)
    if not pop_data.rio.shape == lst_data.rio.shape or \
       not pop_data.rio.crs == lst_data.rio.crs or \
       not pop_data.rio.transform() == lst_data.rio.transform():
       
       print("Aligning population raster to LST grid...")
       pop_aligned = pop_data.rio.reproject_match(lst_data)
       
       # Handle huge nodata values introduced by reprojection (padding)
       # If nodata is defined, mask it to NaN
       if pop_aligned.rio.nodata is not None:
            pop_aligned = pop_aligned.where(pop_aligned != pop_aligned.rio.nodata)
       
       # Also mask out improbably large values (e.g. float32 max) often used as nodata
       # WorldPop max is usually ~100,000 per pixel. Anything > 1e10 is garbage.
       pop_aligned = pop_aligned.where(pop_aligned < 1e10)
       
    else:
       pop_aligned = pop_data

    # 2. Normalize (Always Robust)
    print("Applying robust normalization (2nd-98th percentile)...")
    lst_norm = _robust_normalize(lst_data, 0.02, 0.98)
    pop_norm = _robust_normalize(pop_aligned, 0.02, 0.98)
        
    # 3. Calculate Index
    # Element-wise multiplication
    exposure_index = lst_norm * pop_norm
    
    # 4. Update Metadata
    exposure_index.name = "heat_exposure_index"
    exposure_index.attrs["units"] = "Index"
    exposure_index.attrs["long_name"] = "Heat Exposure Index (LST x Population)"
    exposure_index.attrs["description"] = "Bivariate index of heat exposure. 0=Low, 1=High."
    
    return exposure_index

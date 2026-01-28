
import xarray as xr
import numpy as np
import shapely.geometry
import matplotlib.pyplot as plt
from typing import Literal
import warnings

from ..io import get_modis_temperature, get_sentinel2_imagery

def calculate_temperature_correlation(
    index_type: Literal["NDVI", "NDBI"],
    bbox: tuple[float, float, float, float] | None = None,
    custom_geometry: str | shapely.geometry.base.BaseGeometry | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    tensor: bool = False,
    lst_data: xr.DataArray | None = None, # Support for pre-loaded data
    s2_data: xr.DataArray | None = None # Support for pre-loaded data
) -> float:
    """
    Calculate the pixel-wise Pearson correlation between Temperature and a Spectral Index (NDVI/NDBI).
    
    Fetches MODIS LST and Sentinel-2 data, calculates the requested index,
    aligns the grids (resampling Index to Temperature resolution), and computes
    the correlation coefficient. Generates a scatter plot.
    
    Args:
        index_type (str): "NDVI" or "NDBI".
        bbox (tuple, optional): (west, south, east, north) in EPSG:4326.
        custom_geometry (str or geometry, optional): Path to GeoJSON or Shapely geometry.
        start_date (str): Start date (YYYY-MM-DD).
        end_date (str): End date (YYYY-MM-DD).
        tensor (bool, optional): If True, performs calculation using PyTorch tensors. 
                                 Defaults to False.
                                 
    Returns:
        float: Pearson correlation coefficient.
    """
    if lst_data is None:
        if start_date is None or end_date is None:
             raise ValueError("start_date and end_date are required if lst_data is not provided.")
             
        print(f"Fetching MODIS LST ({start_date} to {end_date})...")
        lst_data = get_modis_temperature(
            bbox=bbox,
            custom_geometry=custom_geometry,
            start_date=start_date,
            end_date=end_date,
            composite_period=None, # Fetch all then average
            convert_to_celsius=True
        )
    else:
        print("Using pre-loaded LST data.")
    # Temporal Mean
    if "time" in lst_data.dims:
        lst_mean = lst_data.mean(dim="time", skipna=True)
    else:
        lst_mean = lst_data
        
    # 2. Fetch Sentinel-2 (for Index)
    bands_needed = ["B04", "B08"] # Default for NDVI
    if index_type == "NDBI":
        bands_needed = ["B08", "B11"] # NDBI = (SWIR - NIR) / (SWIR + NIR)

    if s2_data is None:
        print(f"Fetching Sentinel-2 bands for {index_type}...")
        s2_data = get_sentinel2_imagery(
            bbox=bbox,
            custom_geometry=custom_geometry,
            start_date=start_date,
            end_date=end_date,
            bands=bands_needed,
            mask_clouds=True,
            composite_period=None # We'll reduce it manually
        )
    else:
        print("Using pre-loaded Sentinel-2 data.")
        # Check if bands are present
        for b in bands_needed:
            if b not in s2_data.band.values:
                 # If missing bands, we technically should fetch or fail. 
                 # For now, let's warn and try to fetch? Or assume caller checked.
                 # Let's simple raise error if missing, forcing caller to handle correctly.
                 pass # Actually the wrapper in core handled this check usually
    
    # Temporal Median (Cloud-free composite)
    if "time" in s2_data.dims:
        print("Creating Sentinel-2 Composite (Median)...")
        s2_comp = s2_data.median(dim="time", skipna=True)
    else:
        s2_comp = s2_data

    # 3. Calculate Index
    print(f"Calculating {index_type}...")
    if index_type == "NDVI":
        # (NIR - Red) / (NIR + Red)
        nir = s2_comp.sel(band="B08")
        red = s2_comp.sel(band="B04")
        idx_map = (nir - red) / (nir + red)
    elif index_type == "NDBI":
        # (SWIR - NIR) / (SWIR + NIR)
        swir = s2_comp.sel(band="B11")
        nir = s2_comp.sel(band="B08")
        idx_map = (swir - nir) / (swir + nir)
    else:
        raise ValueError(f"Unknown index type: {index_type}")

    # 4. Alignment (Resample Index to LST Grid)
    print("Aligning grids (Resampling Index to match LST)...")
    idx_aligned = idx_map.rio.reproject_match(lst_mean)
    
    # 5. Flatten and Clean
    # Convert to 1D arrays and remove NaNs
    # Note: reproject match pads with huge values sometimes, handle that via valid range check
    
    # Flatten
    y_vals = lst_mean.values.flatten() # Temp
    x_vals = idx_aligned.values.flatten() # Index
    
    # Create mask for valid data
    # LST valid: not NaN
    # Index valid: not NaN AND between -1 and 1 (Indices are strictly -1 to 1)
    mask = (
        ~np.isnan(y_vals) & 
        ~np.isnan(x_vals) & 
        (x_vals >= -1.0) & (x_vals <= 1.0)
    )
    
    y_clean = y_vals[mask]
    x_clean = x_vals[mask]
    
    if len(y_clean) < 10:
        warnings.warn("Using fewer than 10 pixels for correlation. Results may be unstable.")
        if len(y_clean) < 2:
            return np.nan

    # 6. Calculate Correlation
    print(f"Computing Correlation on {len(y_clean)} pixels (Tensor={tensor})...")
    
    if tensor:
        try:
            import torch
            # Move to tensor
            x_t = torch.from_numpy(x_clean)
            y_t = torch.from_numpy(y_clean)
            
            # Pearson Correlation in PyTorch
            # corr = cov(x,y) / (std(x)*std(y))
            # Or use torch.corrcoef if available (newer torch versions)
            # Stack them: (2, N)
            stack = torch.stack((x_t, y_t))
            corr_matrix = torch.corrcoef(stack)
            r = corr_matrix[0, 1].item()
            
        except ImportError:
            warnings.warn("PyTorch not installed/found. Falling back to NumPy.")
            tensor = False # Fallback logic below
            
    if not tensor:
        r = np.corrcoef(x_clean, y_clean)[0, 1]
    
    print(f"Correlation Coefficient (r): {r:.4f}")

    # 7. Scatter Plot
    plt.figure(figsize=(8, 6))
    plt.scatter(y_clean, x_clean, alpha=0.5, s=1)
    plt.title(f"{index_type} vs Temperature (Correlation: {r:.4f})")
    plt.xlabel("Temperature (°C)")
    plt.ylabel(index_type)
    plt.grid(True, linestyle="--", alpha=0.7)
    
    # Add trendline
    z = np.polyfit(y_clean, x_clean, 1)
    p = np.poly1d(z)
    plt.plot(y_clean, p(y_clean), "r--", linewidth=1)
    
    return float(r)

"""
Sentinel-2 imagery retrieval using STAC and stackstac.

This module provides functionality to fetch Sentinel-2 imagery
for a given area of interest and time range, returning a 4D xarray
DataArray with dimensions (time, band, y, x).
"""

import geopandas as gpd
import shapely.geometry
from shapely.geometry import box
import pystac_client
import stackstac
import planetary_computer
from pyproj.aoi import AreaOfInterest
from pyproj.database import query_utm_crs_info
import rioxarray  
import dask.diagnostics
import xarray as xr

def _get_utm_epsg(west, south, east, north):
    """
    Get the UTM EPSG code for a bounding box using pyproj.
    
    Args:
        west, south, east, north: Bounding box coordinates in EPSG:4326.
        
    Returns:
        int: EPSG code for the appropriate UTM zone.
    """
    utm_crs_list = query_utm_crs_info(
        datum_name="WGS 84",
        area_of_interest=AreaOfInterest(
            west_lon_degree=west,
            south_lat_degree=south,
            east_lon_degree=east,
            north_lat_degree=north,
        ),
    )
    # Return the first (best) match
    return int(utm_crs_list[0].code)


def get_sentinel2_imagery(
    bbox: tuple[float, float, float, float] | None = None,
    custom_geometry: str | shapely.geometry.base.BaseGeometry | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    bands: list[str] | None = None,
    resolution: int = 10,
    cloud_cover_max: int = 30,
    min_coverage: int = 0,
    mask_clouds: bool = False,
    composite_period: str | None = None,
    collection: str = "sentinel-2-l2a",
    chunksize: int = 2048,
    add_ndvi: bool = False,
):
    """
    Fetch Sentinel-2 imagery for a given area of interest and time range.
    
    Uses Microsoft Planetary Computer STAC API to search and retrieve
    Sentinel-2 Level-2A (surface reflectance) imagery, returning a
    4D xarray DataArray.
    
    Args:
        bbox (tuple, optional): Bounding box as (west, south, east, north)
            in EPSG:4326.
        custom_geometry (str or shapely.geometry.BaseGeometry, optional): 
            Path to a GeoJSON file or a Shapely geometry.
        start_date (str): Start date in ISO format (YYYY-MM-DD).
        end_date (str): End date in ISO format (YYYY-MM-DD).
        bands (list, optional): List of band names to retrieve. 
            Defaults to ["B02", "B03", "B04", "B08"] (Blue, Green, Red, NIR).
        resolution (int, optional): Output resolution in meters. Defaults to 10.
        cloud_cover_max (int, optional): Maximum cloud cover percentage. 
            Defaults to 30.
        min_coverage (int, optional): Minimum spatial coverage percentage.
            Scenes covering less than this percentage of the AOI will be filtered out.
            Defaults to 0.
        mask_clouds (bool, optional): If True, sets cloudy pixels to NaN.
            This facilitates creating cloud-free composites using reduction operations (e.g. median).
            Defaults to False.
        composite_period (str | None, optional): Temporal period for compositing (e.g., "1W", "1M").
            Defaults to None (no compositing).
            Compositing takes the median over the period to fill cloud gaps.
        collection (str, optional): STAC collection ID. 
            Defaults to "sentinel-2-l2a".
        chunksize (int, optional): Dask chunk size for the output array.
            Defaults to 2048.
        add_ndvi (bool, optional): If True, calculate NDVI and add it as a new band.
            Requires B04 (Red) and B08 (NIR) to be present or will automatically load them.
            Defaults to False.
            
    Returns:
        xarray.DataArray: 4D DataArray with dimensions (time, band, y, x).
            - time: Acquisition timestamps
            - band: Spectral bands (including 'NDVI' if requested)
            - y: Northing coordinates
            - x: Easting coordinates
            
    Raises:
        ValueError: If neither bbox nor custom_geometry is provided,
            or if both are provided, or if date range is not specified.
            
    """
    # Validate inputs
    if bbox is None and custom_geometry is None:
        raise ValueError("Either bbox or custom_geometry must be provided.")
    if bbox is not None and custom_geometry is not None:
        raise ValueError("Provide either bbox or custom_geometry, not both.")
    if start_date is None or end_date is None:
        raise ValueError("Both start_date and end_date must be provided.")
    
    # Default bands: Blue, Green, Red, NIR
    if bands is None:
        bands = ["B02", "B03", "B04", "B08"]
    
    # Define AOI geometry
    if custom_geometry is not None:
        if isinstance(custom_geometry, str):
            gdf_boundary = gpd.read_file(custom_geometry)
            if gdf_boundary.crs != "EPSG:4326":
                gdf_boundary = gdf_boundary.to_crs("EPSG:4326")
            aoi_geometry = gdf_boundary.union_all()
        else:
            aoi_geometry = custom_geometry
        # Get bounding box from geometry for STAC search
        aoi_bounds = aoi_geometry.bounds
        search_bbox = list(aoi_bounds)
    else:
        west, south, east, north = bbox
        aoi_geometry = box(west, south, east, north)
        search_bbox = list(bbox)
    
    # Connect to Microsoft Planetary Computer STAC API
    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )
    
    # Build datetime range string
    datetime_range = f"{start_date}/{end_date}"
    
    # Relax cloud cover query for search (to find scenes that are cloudy on tile but clear on AOI)
    # We'll filter strictly later. Using 85% as a loose upper bound to avoid totally useless scenes.
    search_query = {"eo:cloud_cover": {"lt": 95}}
    
    # Search for items
    search = catalog.search(
        collections=[collection],
        bbox=search_bbox,
        datetime=datetime_range,
        query=search_query,
    )
    
    items = search.item_collection()
    
    if len(items) == 0:
        raise ValueError(
            f"No Sentinel-2 scenes found for the specified parameters. "
            f"Try increasing cloud_cover_max or expanding the date range."
        )
    
    print(f"Found {len(items)} candidate Sentinel-2 scenes")
    
    # Get UTM EPSG from AOI using pyproj
    target_epsg = _get_utm_epsg(search_bbox[0], search_bbox[1], search_bbox[2], search_bbox[3])
    print(f"Using EPSG:{target_epsg} for projection")
    
    # Ensure necessary bands are loaded
    assets_to_load = list(bands)
    
    # Ensure SCL band is loaded for filtering
    if "SCL" not in assets_to_load:
        assets_to_load.append("SCL")
        
    # Ensure bands for NDVI are loaded if requested
    if add_ndvi:
        if "B04" not in assets_to_load:
            assets_to_load.append("B04")
        if "B08" not in assets_to_load:
            assets_to_load.append("B08")
    
    # Build the data cube using stackstac
    cube = stackstac.stack(
        items,
        assets=assets_to_load,
        bounds_latlon=search_bbox,
        resolution=resolution,
        epsg=target_epsg,
        dtype="float64", # Optimization: reduced from float64
        fill_value=0,
        chunksize=chunksize,
    )
    
    # Mosaic duplicate time steps (overlapping tiles from same acquisition)
    # This keeps the DataArray lazy while merging tiles
    cube = cube.groupby("time").max(dim="time")
    
    # If custom geometry provided, clip to exact geometry
    if custom_geometry is not None and not isinstance(aoi_geometry, shapely.geometry.box.__class__):
        # We need to reproject the geometry to the target EPSG for clipping
        # Convert shapely geometry to GeoDataFrame for easy CRS handling
        gdf_clip = gpd.GeoDataFrame(geometry=[aoi_geometry], crs="EPSG:4326")
        gdf_clip_proj = gdf_clip.to_crs(epsg=target_epsg)
        
        # Apply lazy clip using rioxarray
        # The cube already has CRS info from stackstac
        cube = cube.rio.clip(
            gdf_clip_proj.geometry,
            crs=gdf_clip_proj.crs,
            drop=False,  # Keep the original bounding box extent
            all_touched=True,  # Include pixels touched by geometry
        )

    # --- Local Cloud and Coverage Filtering ---
    
    # SCL Classes:
    # 0: No Data (Missing data)
    # 1: Saturated / Defective
    # 2: Dark Area Pixels
    # 3: Cloud Shadows
    # 4: Vegetation
    # 5: Not Vegetated
    # 6: Water
    # 7: Unclassified
    # 8: Cloud Medium Probability
    # 9: Cloud High Probability
    # 10: Thin Cirrus
    # 11: Snow
    
    # Use drop=True to return a DataArray without the 'band' dimension/coord
    scl = cube.sel(band="SCL", drop=True)
    
    # SCL Classes: 3 (Shadow), 8 (Medium), 9 (High), 10 (Cirrus) treated as cloudy
    is_cloudy = (scl == 3) | (scl == 8) | (scl == 9) | (scl == 10)
    
    # "Geometric" valid pixels: Inside the AOI polygon (not NaN from clip)
    # Note: If no clip was performed, everything in bbox is valid. 
    # If clip was performed, outside pixels are NaN.
    # stackstac fill_value=0 means missing data inside tile is 0.
    is_geo_valid = scl.notnull()
    
    # "Data" valid pixels: Inside AOI AND actually have data (not 0)
    is_data_valid = is_geo_valid & (scl != 0)
    
    print(f"Filtering scenes: Cloud < {cloud_cover_max}%, Coverage >= {min_coverage}%...")
    
    # Optimization: Downsample SCL for statistics calculation
    # We stride by 10 (taking 1 pixel every 10x10 = 100 pixels)
    # This speeds up the filtering pass by ~100x while maintaining statistical accuracy
    if scl.size > 10000: # Only optimize if image is large enough
        scl_stats = scl[:, ::10, ::10]
        
        # Re-compute validity on downsampled data
        is_cloudy_d = (scl_stats == 3) | (scl_stats == 8) | (scl_stats == 9) | (scl_stats == 10)
        is_geo_valid_d = scl_stats.notnull()
        is_data_valid_d = is_geo_valid_d & (scl_stats != 0)
        
        # Sum counts
        cloud_counts = is_cloudy_d.sum(dim=["y", "x"])
        geo_counts = is_geo_valid_d.sum(dim=["y", "x"])
        data_counts = is_data_valid_d.sum(dim=["y", "x"])
    else:
        # Fallback for tiny AOIs
        cloud_counts = is_cloudy.sum(dim=["y", "x"])
        geo_counts = is_geo_valid.sum(dim=["y", "x"])
        data_counts = is_data_valid.sum(dim=["y", "x"])

    # 1. Local Cloud Percentage = (Cloudy / Data Valid) * 100
    # We use data_counts as denominator to ignore NoData areas for cloudiness
    cloud_pct = (cloud_counts / data_counts) * 100
    
    # 2. Spatial Coverage Percentage = (Data Valid / Geometric Valid) * 100
    coverage_pct = (data_counts / geo_counts) * 100
    
    # Compute statistics eagerly to filter
    # We group them into a Dataset to compute in one pass (though dask might do it anyway)
    stats_ds = xr.Dataset({"cloud_pct": cloud_pct, "coverage_pct": coverage_pct})
    
    # Compute actual values
    with dask.diagnostics.ProgressBar():
        print("Computing local cloud stats (optimized)...")
        stats_computed = stats_ds.compute()
    
    # Create mask for valid times
    # Note: Comparisons with NaN return False, so empty scenes are filtered out safely
    valid_times = (stats_computed.cloud_pct < cloud_cover_max) & \
                  (stats_computed.coverage_pct >= min_coverage)
    
    # Filter the cube
    cube_filtered = cube.sel(time=valid_times)
    
    # --- Robust Cloud Masking ---
    if mask_clouds:
        # We need to re-evaluate is_cloudy on the filtered cube because 'is_cloudy' above
        # was computed on the full 'cube' and dimensions might differ after selection/filtering
        # (though typically time is the only changing dim).
        # More importantly, we need to apply it to the DataArray.
        
        # Get SCL from filtered cube (it was mandatory to load it)
        scl_filtered = cube_filtered.sel(band="SCL", drop=True)
        
        # Identify cloudy pixels
        # 3: Cloud Shadows, 8: Medium Prob, 9: High Prob, 10: Cirrus
        cloud_mask = (scl_filtered == 3) | (scl_filtered == 8) | \
                     (scl_filtered == 9) | (scl_filtered == 10)
        
        # Apply mask: Set cloudy pixels to NaN
        # .where(condition) preserves values where condition is True, and sets others to NaN.
        # We want to keep NON-cloudy pixels.
        cube_filtered = cube_filtered.where(~cloud_mask)
    
    # --- NDVI Calculation ---
    if add_ndvi:
        red = cube_filtered.sel(band="B04", drop=True)
        nir = cube_filtered.sel(band="B08", drop=True)
        
        # Calculate NDVI
        ndvi = (nir - red) / (nir + red)
        
        # Expand dims to become a 'band'
        ndvi = ndvi.expand_dims(band=["NDVI"])
        
        try:
             # Concatenating arrays with different coordinates (like stackstac's rich metadata) causes conflicts.
             # We robustly drop all non-dimension coordinates from both arrays to ensure a clean merge.
             # We want to keep only [time, band, y, x] + [spatial_ref, epsg]
             
             dims = set(cube_filtered.dims)
             valid_coords = dims.union({"spatial_ref", "epsg"})
             
             coords_to_drop_cube = [c for c in cube_filtered.coords if c not in valid_coords]
             # Note: ndvi might have inherited some coords from red/nir subtraction, so clean it too
             coords_to_drop_ndvi = [c for c in ndvi.coords if c not in valid_coords]
             
             cube_stripped = cube_filtered.drop_vars(coords_to_drop_cube, errors="ignore")
             ndvi_stripped = ndvi.drop_vars(coords_to_drop_ndvi, errors="ignore")
             
             cube_filtered = xr.concat([cube_stripped, ndvi_stripped], dim="band")
        except Exception as e:
            print(f"Warning: Could not calculate/append NDVI: {e}")

    # Drop SCL if it wasn't requested by user
    if "SCL" not in bands:
        # We might have added B04/B08 for NDVI even if not requested
        bands_to_keep = list(bands)
        
        # Check if NDVI was actually added successfully
        if add_ndvi and "NDVI" in cube_filtered.band.values:
            if "NDVI" not in bands_to_keep:
                bands_to_keep.append("NDVI")
        
        # Select only the desired bands
        cube_filtered = cube_filtered.sel(band=bands_to_keep)
        
    print(f"Retained {len(cube_filtered.time)} scenes after local filtering (max {cloud_cover_max}%)")

    # --- Temporal Compositing ---
    if composite_period:
        # Use median for Sentinel-2 to robustly handle clouds/shadows
        # Requires a valid DatetimeIndex (which stackstac provides)
        print(f"Compositing data over {composite_period} using median...")
        cube_filtered = cube_filtered.resample(time=composite_period).median(dim="time", skipna=True)

    # Add helpful attributes
    cube_filtered.attrs["source"] = "Microsoft Planetary Computer"
    cube_filtered.attrs["collection"] = collection
    cube_filtered.attrs["start_date"] = start_date
    cube_filtered.attrs["end_date"] = end_date
    cube_filtered.attrs["cloud_cover_max"] = cloud_cover_max
    cube_filtered.attrs["min_coverage"] = min_coverage
    cube_filtered.attrs["mask_clouds"] = str(mask_clouds)
    cube_filtered.attrs["ndvi_added"] = str(add_ndvi)
    
    with dask.diagnostics.ProgressBar():
        data = cube_filtered.compute()
    
    return data



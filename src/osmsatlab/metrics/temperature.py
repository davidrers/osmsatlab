
import xarray as xr
import shapely.geometry
import warnings
from ..io import get_modis_temperature

def calculate_temporal_median_temperature(
    bbox: tuple[float, float, float, float] | None = None,
    custom_geometry: str | shapely.geometry.base.BaseGeometry | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    aggregation: str = "1W",
    lst_data: xr.DataArray | None = None # Support for pre-loaded data
) -> xr.DataArray:
    """
    Calculate the temporal median temperature over aggregated periods.
    
    Examines the temperature trends by aggregating daily MODIS LST data 
    into temporal bins (e.g., weekly) using the median statistic to ignore outliers.
    
    Args:
        bbox (tuple, optional): (west, south, east, north) in EPSG:4326.
        custom_geometry (str or geometry, optional): Path to GeoJSON or Shapely geometry.
        start_date (str): Start date (YYYY-MM-DD).
        end_date (str): End date (YYYY-MM-DD).
        aggregation (str, optional): Temporal aggregation frequency (e.g., '1W', '2W', '1M'). 
                                     Defaults to '1W'.
                                 
    Returns:
        xr.DataArray: Aggregated Temperature DataArray with median values.
                      Dimensions: (time, y, x) where 'time' corresponds to the bin labels.
    """
    if lst_data is None:
        if start_date is None or end_date is None:
            raise ValueError("start_date and end_date are required if lst_data is not provided.")
            
        print(f"Fetching MODIS LST from {start_date} to {end_date}...")
        
        # 1. Fetch Daily Data
        # composite_period=None ensures we get the raw scenes (or as raw as STAC gives us)
        # We will handle the aggregation here explicitly.
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
    
    if "time" not in lst_data.dims:
        warnings.warn("Returned data has no time dimension. Aggregation is not possible.")
        return lst_data

    # 2. Resample and Calculate Median
    # Use 'time' as the dimension to resample
    print(f"Aggregating temperature data: {aggregation} Median...")
    
    # Ensure time index is sorted
    lst_data = lst_data.sortby("time")
    
    # Resample
    # Note: starting with xarray 2023+, .resample().median() is standard.
    # We use skipna=True to handle clouds/gaps robustly.
    lst_agg = lst_data.resample(time=aggregation).median(dim="time", skipna=True)
    
    # Update Metadata
    lst_agg.name = "median_temperature"
    lst_agg.attrs["aggregation"] = aggregation
    lst_agg.attrs["start_date"] = start_date
    lst_agg.attrs["end_date"] = end_date
    lst_agg.attrs["units"] = "Celsius"
    
    return lst_agg

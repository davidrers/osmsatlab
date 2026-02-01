from __future__ import annotations
import numpy as np
import geopandas as gpd
import xarray as xr
from rasterio.features import rasterize
from typing import Iterable, Literal


ZonalStat = Literal["mean", "median", "min", "max", "count"]
ReduceFn = Literal["mean", "median", "min", "max"]


def _ensure_same_crs(units: gpd.GeoDataFrame, da: xr.DataArray) -> gpd.GeoDataFrame:
    if units.crs is None:
        raise ValueError("Units GeoDataFrame has no CRS.")
    if not hasattr(da, "rio") or da.rio.crs is None:
        raise ValueError("DataArray has no CRS (.rio.crs). Ensure it was loaded with rioxarray/stackstac.")
    if str(units.crs) != str(da.rio.crs):
        return units.to_crs(da.rio.crs)
    return units


def _reduce_to_2d(
    da: xr.DataArray,
    *,
    reduce_time: ReduceFn = "mean",
    band: str | int | None = None,
) -> xr.DataArray:
    """
    Convert DataArray to 2D (y, x) by:
      - selecting a band if 'band' dim exists
      - reducing 'time' if 'time' dim exists
    """
    out = da

    # Handle band dimension
    if "band" in out.dims:
        if band is None:
            # default: first band
            out = out.isel(band=0)
        else:
            if isinstance(band, int):
                out = out.isel(band=band)
            else:
                # band is str
                out = out.sel(band=band)

    # Handle time dimension
    if "time" in out.dims:
        if reduce_time == "mean":
            out = out.mean(dim="time", skipna=True)
        elif reduce_time == "median":
            out = out.median(dim="time", skipna=True)
        elif reduce_time == "min":
            out = out.min(dim="time", skipna=True)
        elif reduce_time == "max":
            out = out.max(dim="time", skipna=True)
        else:
            raise ValueError(f"Unknown reduce_time='{reduce_time}'")

    # Squeeze any leftover length-1 dims
    out = out.squeeze(drop=True)

    if set(out.dims) != {"y", "x"}:
        raise ValueError(
            f"zonal_stats needs (y, x) after reduction, got dims={out.dims}. "
            "Tip: pass band='NDVI' or band=0, and/or reduce_time='mean'."
        )

    return out


def rasterize_units_to_match(
    units: gpd.GeoDataFrame,
    da_2d: xr.DataArray,
    unit_id_col: str = "unit_id",
    fill: int = -1,
) -> xr.DataArray:
    """
    Rasterize polygon unit IDs onto the grid of a 2D DataArray (y, x).
    Returns an xr.DataArray (y, x) of unit_id values aligned to `da_2d`.
    """
    units = _ensure_same_crs(units, da_2d)
    if unit_id_col not in units.columns:
        raise ValueError(f"Units missing required column '{unit_id_col}'.")

    transform = da_2d.rio.transform()
    height = da_2d.sizes["y"]
    width = da_2d.sizes["x"]

    shapes = ((geom, int(uid)) for geom, uid in zip(units.geometry, units[unit_id_col]))
    arr = rasterize(
        shapes=shapes,
        out_shape=(height, width),
        fill=fill,
        transform=transform,
        dtype="int32",
        all_touched=True,
    )

    unit_raster = xr.DataArray(
        arr,
        dims=("y", "x"),
        coords={"y": da_2d["y"], "x": da_2d["x"]},
        name="unit_id_raster",
    )
    unit_raster.rio.write_crs(da_2d.rio.crs, inplace=True)
    unit_raster.rio.write_transform(transform, inplace=True)
    return unit_raster


def zonal_stats(
    units: gpd.GeoDataFrame,
    da: xr.DataArray,
    stats: Iterable[ZonalStat] = ("mean", "median", "count"),
    unit_id_col: str = "unit_id",
    fill: int = -1,
    drop_fill: bool = True,
    # NEW:
    reduce_time: ReduceFn = "mean",
    band: str | int | None = None,
    out_prefix: str | None = None,
) -> gpd.GeoDataFrame:
    """
    Compute zonal stats for a raster DataArray over polygon units.

    Works with da dims:
      - (y, x)
      - (time, y, x)
      - (time, band, y, x)
      - (band, y, x)

    Returns a copy of units with new columns like:
      - <prefix>_mean, <prefix>_median, <prefix>_count, etc.
    """
    da_2d = _reduce_to_2d(da, reduce_time=reduce_time, band=band)

    prefix = out_prefix or (da_2d.name or da.name or "raster")
    units_out = units.copy()

    unit_raster = rasterize_units_to_match(units_out, da_2d, unit_id_col=unit_id_col, fill=fill)

    # Flatten and mask
    v = da_2d.values.astype("float64").ravel()
    u = unit_raster.values.ravel()

    valid = ~np.isnan(v)
    if drop_fill:
        valid = valid & (u != fill)

    v = v[valid]
    u = u[valid]

    if v.size == 0:
        for s in stats:
            units_out[f"{prefix}_{s}"] = np.nan
        return units_out

    out_maps: dict[str, dict[int, float]] = {}
    unique_ids = np.unique(u)

    for uid in unique_ids:
        vals = v[u == uid]
        if vals.size == 0:
            continue

        for s in stats:
            col = f"{prefix}_{s}"
            out_maps.setdefault(col, {})

            if s == "mean":
                out_maps[col][int(uid)] = float(np.mean(vals))
            elif s == "median":
                out_maps[col][int(uid)] = float(np.median(vals))
            elif s == "min":
                out_maps[col][int(uid)] = float(np.min(vals))
            elif s == "max":
                out_maps[col][int(uid)] = float(np.max(vals))
            elif s == "count":
                out_maps[col][int(uid)] = float(vals.size)
            else:
                raise ValueError(f"Unknown stat: {s}")

    for col, mapping in out_maps.items():
        units_out[col] = units_out[unit_id_col].map(mapping).astype("float64")

    return units_out

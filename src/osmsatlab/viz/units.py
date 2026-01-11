"""
Analysis unit creation for spatial analysis.
Provides LAU administrative boundaries for Netherlands and grid cells for other regions.
"""

import numpy as np
import geopandas as gpd
from shapely.geometry import box

from osmsatlab.io.population import get_country_iso3


# GISCO LAU (Local Administrative Units) dataset
LAU_GISCO_2021_4326 = "https://gisco-services.ec.europa.eu/distribution/v2/lau/geojson/LAU_RG_01M_2021_4326.geojson"


def aoi_geometry(lab, crs="EPSG:4326"):
    """
    Extract AOI geometry from OSMSatLab instance.
    
    Parameters
    
    lab : OSMSatLab
        OSMSatLab instance with bbox or custom_geometry
    crs : str, optional
        Target CRS for the output geometry
        
    Returns
    
    shapely.geometry
        AOI geometry in the requested CRS
    """
    if lab.custom_geometry is not None:
        if isinstance(lab.custom_geometry, str):
            g = gpd.read_file(lab.custom_geometry)
            if g.crs is None:
                g = g.set_crs("EPSG:4326")
            return g.to_crs(crs).union_all()
        return gpd.GeoSeries([lab.custom_geometry], crs="EPSG:4326").to_crs(crs).iloc[0]

    if lab.bbox is not None:
        west, south, east, north = lab.bbox
        return gpd.GeoSeries([box(west, south, east, north)], crs="EPSG:4326").to_crs(crs).iloc[0]

    raise ValueError("No AOI found on OSMSatLab (bbox/custom_geometry).")


def _aoi_intersects_netherlands(aoi_4326):
    """
    Check if AOI intersects with Netherlands boundaries.
    
    This handles border cases like Enschede where the bbox might extend into Germany.
    
    Parameters
    
    aoi_4326 : shapely.geometry
        AOI geometry in EPSG:4326
        
    Returns
    
    bool
        True if AOI intersects Netherlands
    """
    from osmsatlab.io.population import get_world_boundaries

    world = get_world_boundaries()
    world = world.to_crs("EPSG:4326")

    # Natural Earth datasets have different column names for ISO codes
    candidates = []
    for col in ["ISO_A3", "ADM0_A3", "iso_a3"]:
        if col in world.columns:
            candidates.append(col)

    if not candidates:
        return False

    iso_col = candidates[0]
    nld = world[world[iso_col] == "NLD"]
    if nld.empty:
        return False

    nld_geom = nld.union_all()
    return aoi_4326.intersects(nld_geom)


def nl_lau_units(lab):
    """
    Create analysis units from Netherlands LAU administrative boundaries.
    
    Parameters
    
    lab : OSMSatLab
        OSMSatLab instance
        
    Returns
    
    tuple
        (units_gdf, aoi_geometry, iso3_code)
    """
    aoi_4326 = aoi_geometry(lab, crs="EPSG:4326")
    iso3 = get_country_iso3(aoi_4326)

    lau = gpd.read_file(LAU_GISCO_2021_4326)
    lau = lau[lau["CNTR_CODE"] == "NL"].copy()

    aoi_proj = aoi_geometry(lab, crs=lab.target_crs)
    aoi_gdf = gpd.GeoDataFrame(geometry=[aoi_proj], crs=lab.target_crs)

    lau = lau.to_crs(lab.target_crs)
    lau_clip = gpd.overlay(lau, aoi_gdf, how="intersection")

    if lau_clip.empty:
        raise ValueError("AOI does not intersect LAU units (NL).")

    lau_clip["unit_id"] = np.arange(len(lau_clip))
    lau_clip["unit_name"] = lau_clip.get("LAU_NAME", lau_clip["unit_id"].astype(str))

    return lau_clip[["unit_id", "unit_name", "geometry"]], aoi_proj, iso3


def grid_units(lab, cell_m=1000):
    """
    Create analysis units from a regular grid clipped to AOI.
    
    Parameters
    
    lab : OSMSatLab
        OSMSatLab instance
    cell_m : int, optional
        Grid cell size in meters
        
    Returns
    
    tuple
        (units_gdf, aoi_geometry, iso3_code)
    """
    aoi_4326 = aoi_geometry(lab, crs="EPSG:4326")
    iso3 = get_country_iso3(aoi_4326)

    geom = aoi_geometry(lab, crs=lab.target_crs)
    minx, miny, maxx, maxy = geom.bounds

    xs = np.arange(minx, maxx + cell_m, cell_m)
    ys = np.arange(miny, maxy + cell_m, cell_m)

    cells = [box(xs[i], ys[j], xs[i+1], ys[j+1])
             for i in range(len(xs) - 1)
             for j in range(len(ys) - 1)]

    grid = gpd.GeoDataFrame({"unit_id": np.arange(len(cells))}, geometry=cells, crs=lab.target_crs)
    grid = grid[grid.intersects(geom)].copy()
    grid["geometry"] = grid.geometry.intersection(geom)
    grid = grid[~grid.is_empty].copy()

    grid["unit_id"] = np.arange(len(grid))
    grid["unit_name"] = grid["unit_id"].astype(str)

    return grid[["unit_id", "unit_name", "geometry"]], geom, iso3


def analysis_units(lab, grid_cell_m=1000):
    """
    Create analysis units appropriate for the location.
    
    Returns LAU municipality polygons for Netherlands, otherwise creates a clipped grid.
    
    Parameters
    
    lab : OSMSatLab
        OSMSatLab instance
    grid_cell_m : int, optional
        Grid cell size in meters (used for non-NL regions)
        
    Returns
    
    tuple
        (units_gdf, aoi_geometry, iso3_code)
    """
    aoi_4326 = aoi_geometry(lab, crs="EPSG:4326")
    
    if _aoi_intersects_netherlands(aoi_4326):
        return nl_lau_units(lab)
    
    return grid_units(lab, cell_m=grid_cell_m)

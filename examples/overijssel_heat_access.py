import geopandas as gpd
import requests
from shapely.geometry import shape as shp_shape
from osmsatlab.core import OSMSatLab
from osmsatlab.viz.units import analysis_units
from osmsatlab.viz.choropleth import plot_choropleth
import matplotlib.pyplot as plt

# Overijssel boundary
overijssel_url = "https://apitestbed.geonovum.nl/joins_pygeoapi/collections/nl-provinces/items/b7805978-1c97-5152-a6a4-46e8d8f37c1c?f=json"
overijssel_geojson = requests.get(overijssel_url).json()
overijssel_geom = shp_shape(overijssel_geojson["geometry"])

# Lab setup
lab = OSMSatLab(custom_geometry=overijssel_geom, crs="EPSG:28992", load_population_year=2020, load_services=False)

# Fetch a service category for access (choose one)
lab.fetch_services(tags={"amenity": ["hospital", "clinic", "doctors", "pharmacy"]}, category_name="healthcare")

# Units (LAU in NL)
units, aoi, iso3 = analysis_units(lab, grid_cell_m=1000)

# Time window
start_date = "2023-06-01"
end_date = "2023-06-30"

# Compute combined score
out_units = lab.calculate_heat_access_vulnerability(
    units_gdf=units,
    service_category="healthcare",
    start_date=start_date,
    end_date=end_date,
    threshold=1000,
    metric_type="euclidean",
    year=2020,
    weights=(0.5, 0.4, 0.1),
    use_torch=True,
)

print(out_units[["unit_id", "unit_name", "heat_exposure_index_mean", "access_median", "population_sum", "vulnerability_score"]].head())

# Plot vulnerability as choropleth
plot_choropleth(
    out_units,
    column="vulnerability_score",
    title=f"Heat-Access Priority Index - Overijssel ({start_date} to {end_date})",
    aoi=aoi,
    log1p=False
)

# Save outputs
out_units.to_file("Heat-Access Priority Index.geojson", driver="GeoJSON")
plt.savefig("Heat-Access Priority Index.png", dpi=200, bbox_inches="tight")
plt.show()

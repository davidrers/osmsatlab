"""
Example: Healthcare accessibility analysis for Overijssel (NL), Enschede (NL), and Soacha (COL)

This script demonstrates the complete visualization workflow including:
1. Population choropleth map
2. Service locations choropleth map
3. Pairwise scatter plot (population vs services)
4. Distance distribution histogram
5. Coverage threshold sensitivity analysis
6. Interactive web-based accessibility map
"""

from shapely.geometry import shape as shp_shape
from osmsatlab.core import OSMSatLab
from osmsatlab.viz import render_maps
import matplotlib.pyplot as plt


# Example 1: Overijssel Province, Netherlands
# Regional analysis using actual administrative boundary

print("=" * 70)
print("OVERIJSSEL PROVINCE, NETHERLANDS - REGIONAL HEALTHCARE ACCESSIBILITY")
print("=" * 70)

# Fetch the province boundary from Dutch administrative API
import requests
import geopandas as gpd

overijssel_url = "https://apitestbed.geonovum.nl/joins_pygeoapi/collections/nl-provinces/items/b7805978-1c97-5152-a6a4-46e8d8f37c1c?f=json"
response = requests.get(overijssel_url)
overijssel_geojson = response.json()

# Extract the geometry
overijssel_geom = shp_shape(overijssel_geojson["geometry"])

# Calculate area in km²
overijssel_gdf = gpd.GeoDataFrame([1], geometry=[overijssel_geom], crs="EPSG:4326")
area_km2 = overijssel_gdf.to_crs("EPSG:28992").area.iloc[0] / 1_000_000

print(f"Province area: {area_km2:.0f} km²")
print("Downloading population and healthcare data...")

lab_overijssel = OSMSatLab(
    custom_geometry=overijssel_geom,
    crs="EPSG:28992"  # RD New (Dutch national projection in meters)
)

overijssel_out = render_maps(
    lab_overijssel,
    place_label="Overijssel Province (NL)",
    service_category="healthcare",
    grid_cell_m=1000,
    threshold_m=1000
)

print(f"ISO3: {overijssel_out['iso3']}")
print(f"Number of units: {len(overijssel_out['units'])}")
print(f"Total population: {overijssel_out['pop_units']['population'].sum():,.0f}")
print(f"Total healthcare facilities: {overijssel_out['svc_units']['service_count'].sum():.0f}")
print(f"Coverage at 1000m: {overijssel_out['acc']['coverage_stats']['coverage_ratio']:.1%}")

"""
# Example 2: Enschede, Netherlands
# Will use LAU municipality boundaries

print("=" * 70)
print("ENSCHEDE, NETHERLANDS - HEALTHCARE ACCESSIBILITY ANALYSIS")
print("=" * 70)

bbox_enschede = (6.7470, 52.1610, 7.0460, 52.3210)
lab_enschede = OSMSatLab(bbox=bbox_enschede, crs="EPSG:3857")

enschede_out = render_maps(
    lab_enschede,
    place_label="Enschede (NL)",
    service_category="healthcare",
    grid_cell_m=1000,
    threshold_m=1000
)

print(f"ISO3: {enschede_out['iso3']}")
print(f"Number of units: {len(enschede_out['units'])}")
print(f"Unit type: {enschede_out['units'].geometry.iloc[0].geom_type}")


# Example 3: Soacha, Colombia
# Will use grid cells

print("\n" + "=" * 70)
print("SOACHA, COLOMBIA - HEALTHCARE ACCESSIBILITY ANALYSIS")
print("=" * 70)

SOACHA_GEOJSON = {
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-74.2442080279905, 4.557198840410862],
                [-74.23738287673807, 4.559329364586489],
                [-74.23253413312355, 4.559932161882344],
                [-74.21152247548973, 4.550761761617366],
                [-74.18239508634338, 4.5612483523476754],
                [-74.17838725121939, 4.567071962768566],
                [-74.18010643545456, 4.570218456320106],
                [-74.17595445936908, 4.571723754325916],
                [-74.17550761084297, 4.5750175378968265],
                [-74.17780707527122, 4.57740526059041],
                [-74.17975242142822, 4.57725626894576],
                [-74.1818707200668, 4.590246318386107],
                [-74.18373797770683, 4.595733829660205],
                [-74.20554288227699, 4.601050215768822],
                [-74.21752533368472, 4.614959228521641],
                [-74.22495833608578, 4.6140574472301665],
                [-74.23464657099514, 4.605895589792311],
                [-74.24601388731183, 4.585475802858397],
                [-74.2502773732052, 4.580340162241683],
                [-74.24891004468158, 4.575500090733755],
                [-74.24496154544975, 4.570207159420178],
                [-74.24526682635562, 4.562342888560451],
                [-74.2442080279905, 4.557198840410862]
            ]]
        }
    }]
}

soacha_poly = shp_shape(SOACHA_GEOJSON["features"][0]["geometry"])
lab_soacha = OSMSatLab(custom_geometry=soacha_poly, crs="EPSG:3857")

soacha_out = render_maps(
    lab_soacha,
    place_label="Soacha (COL)",
    service_category="healthcare",
    grid_cell_m=1000,
    threshold_m=1000
)

print(f"ISO3: {soacha_out['iso3']}")
print(f"Number of units: {len(soacha_out['units'])}")
print(f"Unit type: {soacha_out['units'].geometry.iloc[0].geom_type}")
"""

# Display all matplotlib plots

print("\n" + "=" * 70)
print("Displaying all static plots (5 matplotlib figures per location)")
print("Interactive maps saved as HTML files")
print("Close plot windows to end the script")
print("=" * 70)

plt.show()

"""
Example: Healthcare accessibility analysis for Enschede (NL) and Soacha (COL)
"""

from shapely.geometry import shape as shp_shape
from osmsatlab.core import OSMSatLab
from osmsatlab.viz import (
    render_maps,
    plot_coverage_threshold_analysis,
    plot_interactive_accessibility_map,
    analysis_units
)
import matplotlib.pyplot as plt


# Example 1: Enschede, Netherlands
print("=== Enschede, Netherlands ===")
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

# Threshold analysis
thresholds = [250, 500, 1000, 1500, 2000]
fig, ax, coverage = plot_coverage_threshold_analysis(
    lab_enschede,
    service_category="healthcare",
    thresholds=thresholds,
    place_label="Enschede (NL)"
)
print(f"Coverage by threshold: {coverage}")

# Interactive map
units, aoi, iso3 = analysis_units(lab_enschede, grid_cell_m=1000)
map_enschede = plot_interactive_accessibility_map(
    lab_enschede,
    units=units,
    aoi=aoi,
    service_category="healthcare",
    threshold_m=1000
)
map_enschede.save("enschede_accessibility.html")
print("Interactive map saved: enschede_accessibility.html")


# Example 2: Soacha, Colombia
print("\n=== Soacha, Colombia ===")
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

# Interactive map
units_s, aoi_s, iso3_s = analysis_units(lab_soacha, grid_cell_m=1000)
map_soacha = plot_interactive_accessibility_map(
    lab_soacha,
    units=units_s,
    aoi=aoi_s,
    service_category="healthcare",
    threshold_m=1000
)
map_soacha.save("soacha_accessibility.html")
print("Interactive map saved: soacha_accessibility.html")

plt.show()

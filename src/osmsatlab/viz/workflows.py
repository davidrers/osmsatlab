"""
Workflow functions for complete spatial analysis.
"""

from .units import analysis_units
from .aggregation import sum_population_to_units, count_services_to_units
from .choropleth import plot_choropleth, plot_interactive_accessibility_map
from .plot import plot_distribution, plot_pairwise, plot_coverage_threshold_analysis


def render_maps(lab, place_label, service_category="healthcare", grid_cell_m=1000, threshold_m=1000):
    """
    Generate all maps and metrics for a given location.
    
    Creates population choropleth, service choropleth, and accessibility distribution plots.
    
    Parameters
    
    lab : OSMSatLab
        OSMSatLab instance with loaded population and services
    place_label : str
        Label for the location (used in plot titles)
    service_category : str, optional
        Service category to analyze (e.g., 'healthcare', 'education')
    grid_cell_m : int, optional
        Grid cell size in meters (for non-NL regions)
    threshold_m : int, optional
        Distance threshold in meters for accessibility metrics
        
    Returns
    
    dict
        Dictionary containing:
        - iso3: ISO3 country code
        - units: Analysis units GeoDataFrame
        - pop_units: Population aggregated to units
        - svc_units: Services aggregated to units
        - acc: Accessibility metrics from OSMSatLab
    """
    units, aoi, iso3 = analysis_units(lab, grid_cell_m=grid_cell_m)

    # Plot 1: Population choropleth
    pop_units = sum_population_to_units(lab.population, units, pop_col="population")
    plot_choropleth(
        pop_units,
        column="population",
        title=f"Population Distribution — {place_label}",
        aoi=aoi,
        log1p=False
    )

    # Plot 2: Service locations choropleth
    svc_units = count_services_to_units(lab.services[service_category], units)
    plot_choropleth(
        svc_units,
        column="service_count",
        title=f"{service_category.replace('_',' ').title()} Services — {place_label}",
        aoi=aoi,
        log1p=False
    )

    # Plot 3: Pairwise scatter plot
    plot_pairwise(
        pop_units,
        svc_units,
        title=f"Population vs {service_category.replace('_',' ').title()} Services — {place_label}",
        log1p=False
    )
    
    # Plot 4: Distance distribution
    acc = lab.calculate_accessibility_metrics(service_category, threshold=threshold_m)
    plot_distribution(
        acc["population_gdf"]["nearest_dist"],
        title=f"Distance to nearest {service_category.replace('_',' ')} — {place_label}",
        bins=60,
        log10=False,
        x_label=f"Distance to nearest {service_category.replace('_',' ')} (meters)"
    )

    # Plot 5: Coverage threshold sensitivity analysis
    thresholds = [250, 500, 1000, 1500, 2000]
    fig, ax, coverage = plot_coverage_threshold_analysis(
        lab,
        service_category=service_category,
        thresholds=thresholds,
        place_label=place_label
    )
    print(f"\nCoverage by threshold for {place_label}:")
    for t, c in coverage.items():
        print(f"  {t}m: {c*100:.1f}%")

    # Plot 6: Interactive accessibility map
    interactive_map = plot_interactive_accessibility_map(
        lab,
        units=units,
        aoi=aoi,
        service_category=service_category,
        threshold_m=threshold_m
    )
    map_filename = f"{place_label.replace(' ', '_').replace('(', '').replace(')', '').lower()}_accessibility.html"
    interactive_map.save(map_filename)
    print(f"Interactive map saved: {map_filename}\n")
    
    return {"iso3": iso3, "units": units, "pop_units": pop_units, "svc_units": svc_units, "acc": acc}

# Accessibility & Equity Metrics

Core functions for measuring urban accessibility and service distribution fairness.

## Facade Methods
These methods are the primary way to access functionality through the `OSMSatLab` class.

### Calculate Accessibility
::: osmsatlab.core.OSMSatLab.calculate_accessibility_metrics

### Calculate Per-Capita Equity
::: osmsatlab.core.OSMSatLab.calculate_per_capita_metrics

---

## Underlying Logic
Direct access to the calculation functions for advanced usage.

### Accessibility Logic
::: osmsatlab.metrics.accessibility
    options:
      members:
        - calculate_nearest_service_distance
        - calculate_network_distance
        - calculate_coverage

### Per-Capita Logic
::: osmsatlab.metrics.per_capita
    options:
      members:
        - calculate_services_per_capita
        - calculate_population_per_service

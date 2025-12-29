from osmsatlab import OSMSatLab
import warnings

# Suppress CRS warnings for cleaner output in example
warnings.filterwarnings('ignore', category=UserWarning)

def main():
    print("=== OSMSatLab: Accessibility Analysis Example ===")
    
    # Define area (University of Twente / Enschede Technology Park)
    # Using a small box for speed
    bbox = (6.83, 52.23, 6.86, 52.25)
    
    # Target CRS: Amersfoort / RD New (EPSG:28992) for Netherlands (meters)
    # Or UTM 31N (EPSG:32631)
    target_crs = "EPSG:28992"
    
    print(f"1. Initializing Analysis for bbox: {bbox}")
    lab = OSMSatLab(bbox=bbox, crs=target_crs)
    
    print("2. Loading Population Data (WorldPop 1km)...")
    try:
        lab.load_population(year=2020)
        print(f"   Loaded {len(lab.population)} population points.")
        print(f"   Total Population: {lab.population['population'].sum():.1f}")
    except Exception as e:
        print(f"   Failed to load population: {e}")
        return

    print("3. Fetching Healthcare Services (Hospitals/Clinics)...")
    try:
        # OSM tags for healthcare
        tags = {'amenity': ['hospital', 'clinic', 'doctors', 'pharmacy']}
        lab.fetch_services(tags, 'healthcare')
        print(f"   Found {len(lab.services['healthcare'])} healthcare facilities.")
    except Exception as e:
        print(f"   Failed to fetch services: {e}")
        return
        
    if lab.services['healthcare'].empty:
        print("   No services found. Skipping metrics.")
        return

    print("4. Calculating Accessibility Metrics...")
    # Coverage within 1km (1000m)
    acc = lab.calculate_accessibility_metrics('healthcare', threshold=1000)
    stats = acc['coverage_stats']
    print(f"   - Average Distance to nearest service: {acc['population_gdf']['nearest_dist'].mean():.1f} meters")
    print(f"   - Population covered within 1km: {stats['covered_population']:.1f} ({stats['coverage_ratio']*100:.1f}%)")
    
    print("5. Calculating Equity Metrics...")
    eq = lab.calculate_equity_metrics('healthcare')
    print(f"   - Facilities per 1,000 people: {eq['services_per_1000']:.2f}")
    print(f"   - Population per facility: {eq['people_per_service']:.1f}")
    
    print("=== Analysis Complete ===")

if __name__ == "__main__":
    main()

from osmsatlab.io.population import get_population_data
import shapely.geometry
import geopandas as gpd

def main():
    # Small area in The Netherlands (Enschede area, university campus roughly)
    # bbox = (6.84, 52.23, 6.86, 52.25) 
    # Let's use a very small bbox to avoid large processing if possible, 
    # but WorldPop files are per country, so it will download the whole NLD file (smallish country).
    
    # Using a small bounding box
    bbox = (6.850, 52.238, 6.855, 52.242)
    
    print(f"Fetching population for bbox: {bbox}")
    try:
        gdf = get_population_data(bbox=bbox, year=2020)
        print("Success!")
        print(f"Number of points: {len(gdf)}")
        if not gdf.empty:
            print(f"Total population in bbox: {gdf['population'].sum()}")
            print(gdf.head())
        else:
            print("No population found (expected if area is empty).")
            
    except Exception as e:
        print(f"Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

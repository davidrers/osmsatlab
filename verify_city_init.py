from osmsatlab import OSMSatLab
from shapely.geometry.base import BaseGeometry
import time

def verify_city_init():
    print("Testing valid city initialization...")
    try:
        lab = OSMSatLab(city="Bogota", load_services=False, load_population_year=None)
        if isinstance(lab.custom_geometry, BaseGeometry):
            print("SUCCESS: 'Bogota' geometry loaded correctly.")
        else:
            print("FAILURE: 'Bogota' geometry is not a valid Shapely geometry.")
    except Exception as e:
        print(f"FAILURE: Initializing with 'Bogota' raised an exception: {e}")

    print("\nTesting invalid city initialization...")
    try:
        lab = OSMSatLab(city="NonExistentCity12345", load_services=False, load_population_year=None)
        print("FAILURE: Initializing with 'NonExistentCity12345' did NOT raise an exception.")
    except ValueError as e:
        print(f"SUCCESS: Caught expected ValueError: {e}")
    except Exception as e:
        print(f"FAILURE: Caught unexpected exception: {e}")

if __name__ == "__main__":
    verify_city_init()

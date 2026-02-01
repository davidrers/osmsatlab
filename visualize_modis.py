
import matplotlib.pyplot as plt
from osmsatlab.io.modis import get_modis_temperature

# 1. Fetch Data
print("Fetching MODIS data...")
data = get_modis_temperature(
    bbox=(-74.05, 4.60, -74.04, 4.61), # Bogota
    start_date="2023-01-01",
    end_date="2023-01-10",
    convert_to_celsius=True
)

# 2. Plotting a Single Map (First Time Step)
plt.figure(figsize=(10, 8))
# isel(time=0) selects the first time step
# squeeze() removes single-dimensional entries (like band=1) for cleaner plotting
data.isel(time=0).squeeze().plot(cmap="magma", cbar_kwargs={'label': 'Temperature (°C)'})
plt.title(f"MODIS LST - Bogota - {str(data.time[0].values)[:10]}")
plt.savefig("modis_map.png")
print("Saved map to modis_map.png")

# 3. Plotting a Time Series (Mean over AOI)
plt.figure(figsize=(10, 5))
# mean(dim=["x", "y"]) calculates average temp over the area for each time step
# squeeze() to remove the 'band' dimension since we only have one layer
data.mean(dim=["x", "y"]).squeeze().plot.line(marker="o")
plt.title("Mean Land Surface Temperature over Time")
plt.ylabel("Temperature (°C)")
plt.grid(True)
plt.savefig("modis_timeseries.png")
print("Saved time series to modis_timeseries.png")

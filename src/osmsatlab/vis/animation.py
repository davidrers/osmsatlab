
"""
Visualization module for satellite data.
"""

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import xarray as xr
import numpy as np
import os
from typing import List, Optional

def create_timelapse(
    data: xr.DataArray,
    output_path: str = "timelapse.gif",
    fps: int = 5,
    bands: Optional[List[str]] = None,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    cmap: Optional[str] = "viridis",
    add_text: bool = True,
    figsize: tuple = (10, 10),
    dpi: int = 100
):
    """
    Create a timelapse animation (GIF) from an xarray DataArray.

    Args:
        data (xr.DataArray): Input data with a 'time' dimension. 
                             Can be (time, y, x) or (time, band, y, x).
        output_path (str, optional): Output path for the GIF. Defaults to "timelapse.gif".
        fps (int, optional): Frames per second. Defaults to 5.
        bands (List[str], optional): For RGB visualization, list of [Red, Green, Blue] band names. 
                                     Only used if data has a 'band' dimension. 
                                     Defaults to None (uses cmap on first band/layer).
        vmin (float, optional): Min value for colormap scaling. Defaults to data min.
        vmax (float, optional): Max value for colormap scaling. Defaults to data max.
        cmap (str, optional): Matplotlib colormap name. Defaults to "viridis". Ignored for RGB.
        add_text (bool, optional): If True, adds the date to the image. Defaults to True.
        figsize (tuple, optional): Figure size. Defaults to (10, 10).
        dpi (int, optional): DPI of the output. Defaults to 100.
    """
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Prepare plotting data
    is_rgb = False
    
    # Check dimensions
    dims = data.dims
    if "time" not in dims:
        raise ValueError("DataArray must have a 'time' dimension.")

    if "band" in dims:
        if bands and len(bands) == 3:
            # RGB Mode
            is_rgb = True
            try:
                # Select RGB bands
                plot_data = data.sel(band=bands)
                # Normalize for RGB display (0-1)
                # Simple normalization based on vmin/vmax or percentiles if not provided
                if vmin is None: 
                    vmin = plot_data.as_numpy().quantile(0.02)
                if vmax is None:
                    vmax = plot_data.as_numpy().quantile(0.98)
                
                # Clip and scale
                plot_data = (plot_data - vmin) / (vmax - vmin)
                plot_data = plot_data.clip(0, 1)
                
                # Transpose to (time, y, x, band) for matplotlib
                plot_data = plot_data.transpose("time", "y", "x", "band")
            except KeyError:
                print(f"Warning: Specified bands {bands} not found. Falling back to single band.")
                plot_data = data.isel(band=0)
        else:
            # Single Band Mode - take first band if not specified
            if bands:
               plot_data = data.sel(band=bands[0])
            else:
               plot_data = data.isel(band=0)
    else:
        # 3D array (time, y, x)
        plot_data = data

    # Setup Figure
    fig, ax = plt.subplots(figsize=figsize)
    ax.axis('off')
    
    # Initial Frame
    times = data.time.values
    
    if vmin is None and not is_rgb:
         vmin = float(plot_data.min())
    if vmax is None and not is_rgb:
         vmax = float(plot_data.max())

    if is_rgb:
        im = ax.imshow(plot_data.isel(time=0).values, interpolation='nearest')
    else:
        im = ax.imshow(plot_data.isel(time=0).values, cmap=cmap, vmin=vmin, vmax=vmax, interpolation='nearest')
        if not is_rgb:
             cbar = plt.colorbar(im, ax=ax, fraction=0.035, pad=0.04)
        
    if add_text:
        title = ax.set_title(str(times[0])[:10], fontsize=16)

    def update(frame):
        if is_rgb:
            im.set_data(plot_data.isel(time=frame).values)
        else:
            im.set_data(plot_data.isel(time=frame).values)
        
        if add_text:
            title.set_text(str(times[frame])[:10])
        return im,

    print(f"Generating animation with {len(times)} frames...")
    ani = animation.FuncAnimation(
        fig, 
        update, 
        frames=len(times), 
        interval=1000/fps, 
        blit=False # blit=True can cause issues with title updates sometimes
    )
    
    ani.save(output_path, writer='pillow', dpi=dpi)
    plt.close(fig)
    print(f"Saved animation to {output_path}")


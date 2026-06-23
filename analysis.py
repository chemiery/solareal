import requests
import rasterio
import numpy as np
import tempfile
import os
from shapely.geometry import shape
from shapely.ops import transform
import pyproj
from rasterio.mask import mask


WCS_URL = "https://api.dataforsyningen.dk/dhm_wcs_DAF?token=XXXXXXXXXXXXXXXXXXX"


# ------------------------------------------------------
# Reprojection
# ------------------------------------------------------
def reproject_geom(geom, src="EPSG:4326", dst="EPSG:25832"):
    project = pyproj.Transformer.from_crs(src, dst, always_xy=True).transform
    return transform(project, geom)


def get_bbox(geom):
    return geom.bounds


def buffer_geom(geom, buffer_m=1):
    return geom.buffer(buffer_m)


# ------------------------------------------------------
# Sikrer minimum bbox størrelse
# ------------------------------------------------------
def expand_bbox(bbox, min_size=20):
    minx, miny, maxx, maxy = bbox

    width = maxx - minx
    height = maxy - miny

    if width < min_size:
        mid = (minx + maxx) / 2
        minx = mid - min_size / 2
        maxx = mid + min_size / 2

    if height < min_size:
        mid = (miny + maxy) / 2
        miny = mid - min_size / 2
        maxy = mid + min_size / 2

    return minx, miny, maxx, maxy


# ------------------------------------------------------
# WCS download
# ------------------------------------------------------
def download_wcs(bbox, outfile):
    minx, miny, maxx, maxy = bbox

    res = 0.4

    width = max(50, int((maxx - minx) / res))
    height = max(50, int((maxy - miny) / res))

    params = {
        "SERVICE": "WCS",
        "REQUEST": "GetCoverage",
        "VERSION": "1.0.0",
        "COVERAGE": "dhm_overflade",
        "CRS": "EPSG:25832",
        "BBOX": f"{minx},{miny},{maxx},{maxy}",
        "FORMAT": "GTiff",
        "WIDTH": width,
        "HEIGHT": height
    }

    r = requests.get(WCS_URL, params=params, stream=True)

    print("WCS URL:", r.url)
    print("Status:", r.status_code)
    print("Content-Type:", r.headers.get("Content-Type"))

    r.raise_for_status()

    with open(outfile, "wb") as f:
        for chunk in r.iter_content(1024):
            f.write(chunk)

    if os.path.getsize(outfile) < 2000:
        raise Exception("WCS returnerede ikke raster")


# ------------------------------------------------------
# Analyse
# ------------------------------------------------------
def run_analysis(geojson):

    geom = shape(geojson["geometry"])  
    # reprojicer til UTM
    geom_utm = reproject_geom(geom)

    # buffer til WCS
    geom_buffer = buffer_geom(geom_utm, 1)
    bbox = expand_bbox(get_bbox(geom_buffer))

    temp_dir = tempfile.mkdtemp()
    raw_tif = os.path.join(temp_dir, "dhm.tif")

    download_wcs(bbox, raw_tif)

    # ---------------------------
    # MASK + beregninger
    # ---------------------------
    with rasterio.open(raw_tif) as src:
    

        # mask til polygon
        geom_geojson = [geom_utm.__geo_interface__]
        out_image, _ = mask(src, geom_geojson, crop=True)

        elevation = out_image[0].astype(float)

        nodata = src.nodata
        if nodata is not None:
            elevation[elevation == nodata] = np.nan

        elevation[~np.isfinite(elevation)] = np.nan

        if np.all(np.isnan(elevation)):
            raise Exception("Raster indeholder kun nodata")

        px, py = src.res

        # ---------------------------
        # Gradient → slope
        # ---------------------------
        gy, gx = np.gradient(elevation, py, px)

        slope = np.sqrt(gx**2 + gy**2)
        slope_deg = np.degrees(np.arctan(slope))

        slope_clean = slope_deg[np.isfinite(slope_deg)]

        # fjern ekstreme artefakter
        slope_clean = slope_clean[(slope_clean >= 0) & (slope_clean <= 70)]

        if slope_clean.size == 0:
            raise Exception("Ingen valide hældningsværdier")

        # ---------------------------
        # Statistik 
        # ---------------------------
        mean = float(np.mean(slope_clean))
        median = float(np.median(slope_clean))
        max_val = float(np.max(slope_clean))

        # ---------------------------
        # Tagflade Aspect (retning)
        # ---------------------------
        aspect = np.degrees(np.arctan2(-gx, gy))
        aspect = np.mod(aspect + 360, 360)

        aspect_clean = aspect[np.isfinite(aspect)]
        aspect_clean = aspect_clean[(aspect_clean >= 0) & (aspect_clean <= 360)]

        aspect_median = float(np.median(aspect_clean))

        # ---------------------------
        # Areal
        # ---------------------------
        area_2d = geom_utm.area

        # 3D areal baseret på median
        median_slope = max(0, min(median, 70))
        theta_rad = np.radians(median_slope)

        area_3d = area_2d / np.cos(theta_rad)

        area_gain = (area_3d / area_2d - 1) * 100
        
        # ---------------------------
        # Sol / energi (generiske gennemsnitsværdier. Korrigér her for brugerdefineret beregning. )
        # ---------------------------

        irradiation = 1000
        efficiency = 0.18
        optimal_tilt = 35

        def orientation_factor(aspect):
            diff = abs(aspect - 180)
            return max(0, np.cos(np.radians(diff)))

        def tilt_factor(slope):
            diff = abs(slope - optimal_tilt)
            return max(0, np.cos(np.radians(diff)))

        orient_f = orientation_factor(aspect_median)
        tilt_f = tilt_factor(median)

        solar_factor = orient_f * tilt_f

        energy = area_3d * irradiation * solar_factor * efficiency



        # ---------------------------
        # Typetal
        # ---------------------------
        slope_filtered = slope_clean[slope_clean >= 5]

        if slope_filtered.size == 0:
            slope_filtered = slope_clean

        binned = np.round(slope_filtered).astype(int)

        values, counts = np.unique(binned, return_counts=True)
        sorted_idx = np.argsort(counts)[::-1]

        top_values = values[sorted_idx][:3]
        top_values = list(top_values) + [None] * (3 - len(top_values))

        primary = int(top_values[0]) if top_values[0] is not None else None
        secondary = int(top_values[1]) if top_values[1] is not None else None
        tertiary = int(top_values[2]) if top_values[2] is not None else None

    return {
       
        "median": round(median, 0),
       

        "aspect_median": round(aspect_median, 1),

        "area_2d": round(area_2d, 1),
        "area_3d": round(area_3d, 1),

        "mode_primary": primary,
        "mode_secondary": secondary,
        "mode_tertiary": tertiary,

        "energy_kwh": round(energy, 0),
        "solar_factor": round(solar_factor, 2)
    }

import io
import time
import requests
import pandas as pd
import geopandas as gpd
import urllib3

urllib3.disable_warnings()

API_KEY = "Your LINZ Api Key"

# NZTM2000 (EPSG:2193) bounding box covering the entire Waipā District with buffer
# Format: (min_easting, min_northing, max_easting, max_northing)
WAIPA_BBOX = "1775000,5765000,1840000,5815000"

BASE_URL = f"https://data.linz.govt.nz/services;key={API_KEY}/wfs"

BATCH_SIZE = 10000  # Recommended LINZ WFS batch size (max 10,000 features per request)
start_index = 0
gdfs = []

print("Starting download for the entire Waipā District...")

while True:
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": "layer-50772",
        "outputFormat": "application/json",
        "srsName": "EPSG:2193",
        "bbox": f"{WAIPA_BBOX},EPSG:2193",
        "startIndex": start_index,
        "count": BATCH_SIZE,
    }

    r = requests.get(BASE_URL, params=params, verify=False, timeout=120)

    if r.status_code != 200:
        print(f"Error occurred (Status {r.status_code}): {r.text[:1000]}")
        raise Exception("Download failed")

    batch_gdf = gpd.read_file(io.BytesIO(r.content))
    fetched_count = len(batch_gdf)
    print(f"Downloaded: {start_index} to {start_index + fetched_count} (Batch count: {fetched_count})")

    if fetched_count == 0:
        break

    gdfs.append(batch_gdf)

    # Stop pagination if fetched count is less than batch size (last page reached)
    if fetched_count < BATCH_SIZE:
        break

    start_index += BATCH_SIZE
    time.sleep(0.5)  # Short pause to avoid overloading the server

# Merge all batches and remove duplicates
if gdfs:
    full_gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs="EPSG:2193")
    if "id" in full_gdf.columns:
        full_gdf = full_gdf.drop_duplicates(subset=["id"])

    print(f"\nMerge complete! Total features: {len(full_gdf)}")
    print(full_gdf.head())

    # Save to local file (GeoPackage recommended)
    output_filename = "waipa_primary_parcels.gpkg"
    full_gdf.to_file(output_filename, driver="GPKG")
    print(f"File saved successfully: {output_filename}")
else:
    print("No data found.")

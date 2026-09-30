"""
Spatial Alignment and Distance Calculation Module for Objective 2.
Computes Haversine distances, landslide densities around stations, and attaches district context.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from src.config import CLEANED_DIR

def haversine_vectorized(lat1: float, lon1: float, lat2_arr: np.ndarray, lon2_arr: np.ndarray) -> np.ndarray:
    """Computes the great-circle distances in kilometers between a point and an array of points."""
    R = 6371.0  # Earth's radius in kilometers
    
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2_arr)
    delta_phi = np.radians(lat2_arr - lat1)
    delta_lambda = np.radians(lon2_arr - lon1)
    
    a = np.sin(delta_phi / 2.0)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2.0)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

def compute_station_landslide_features(stations_df: pd.DataFrame, landslides_df: pd.DataFrame) -> pd.DataFrame:
    """Computes spatial landslide density and nearest proximity features for each unique monitoring station."""
    land_lats = landslides_df["latitude"].values
    land_lons = landslides_df["longitude"].values
    
    unique_stations = stations_df[["station", "latitude", "longitude", "district"]].drop_duplicates().copy()
    
    min_distances = []
    count_5km = []
    count_10km = []
    
    for _, st in unique_stations.iterrows():
        st_lat = st["latitude"]
        st_lon = st["longitude"]
        
        if pd.isna(st_lat) or pd.isna(st_lon):
            min_distances.append(np.nan)
            count_5km.append(0)
            count_10km.append(0)
            continue
            
        dists = haversine_vectorized(st_lat, st_lon, land_lats, land_lons)
        min_distances.append(round(float(np.min(dists)), 2))
        count_5km.append(int(np.sum(dists <= 5.0)))
        count_10km.append(int(np.sum(dists <= 10.0)))
        
    unique_stations["dist_to_nearest_landslide_km"] = min_distances
    unique_stations["landslide_count_5km"] = count_5km
    unique_stations["landslide_count_10km"] = count_10km
    unique_stations["is_landslide_hotspot"] = (unique_stations["landslide_count_10km"] >= 5).astype(int)
    
    return unique_stations

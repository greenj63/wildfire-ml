# scripts/process_wildfire_drought_data.py
"""Combine wildfires with the drought/weather data of their county.

Plan and reasoning: docs/wildfire_drought_merge_plan.md

Needs these files first (see data/README.md):
    data/processed/wildfire/wildfire_clean.csv
    data/processed/droughts/drought_clean.csv
    data/raw/county_centroids/2020_Gaz_counties_national.txt
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from shared.data_loader import get_dataset_dir

OUTPUT_NAME = "wildfire_drought"
OUTPUT_FILENAME = "wildfire_drought.csv"

FIRST_YEAR = 2000  # the drought data covers 2000-2020
LAST_YEAR = 2020
BOX_MARGIN_KM = 25  # how generous each county's lat/long box is
# A fire's own FIPS county only counts if the fire is within this many box
# half-widths of its center. Farther than that, the FIPS code is probably wrong.
OWN_COUNTY_RANGE_FACTOR = 2
SCORE_LOOKBACK_DAYS = 7  # the drought score is weekly
MAX_ROWS = 100_000
SEED = 42

KM_PER_DEGREE = 111.32
EARTH_RADIUS_KM = 6371.0
DROUGHT_CHUNK_ROWS = 2_000_000
FIRE_CHUNK_ROWS = 2_000


def load_fires() -> pd.DataFrame:
    path = get_dataset_dir("wildfire", processed=True) / "wildfire_clean.csv"
    fires = pd.read_csv(path, low_memory=False)
    fires = fires[fires["FIRE_YEAR"].between(FIRST_YEAR, LAST_YEAR)]
    fires = fires.dropna(subset=["LATITUDE", "LONGITUDE"]).reset_index(drop=True)
    fires["DISCOVERY_DATE"] = pd.to_datetime(fires["DISCOVERY_DATE"], format="%m/%d/%Y")
    fires["FIPS_CODE"] = fires["FIPS_CODE"].astype("Int64")
    return fires


def load_counties() -> pd.DataFrame:
    """County center points and box sizes.

    Alaska, Hawaii, and Puerto Rico aren't in the drought data; pairs with those
    counties are dropped later, when no drought row is found for them.
    """
    path = get_dataset_dir("county_centroids") / "2020_Gaz_counties_national.txt"
    counties = pd.read_csv(path, sep="\t", dtype={"GEOID": int})
    counties.columns = counties.columns.str.strip()  # last header has trailing spaces

    # Box half-width: half the side of a square with the county's land area + margin
    land_km2 = counties["ALAND"] / 1_000_000
    counties["HALF_WIDTH_KM"] = 0.5 * np.sqrt(land_km2) + BOX_MARGIN_KM
    counties["LAT_RANGE"] = counties["HALF_WIDTH_KM"] / KM_PER_DEGREE
    # Longitude degrees get narrower further north, so widen the box to match
    counties["LON_RANGE"] = counties["HALF_WIDTH_KM"] / (
        KM_PER_DEGREE * np.cos(np.radians(counties["INTPTLAT"]))
    )
    return counties


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = (
        np.sin((lat2 - lat1) / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def find_latlon_candidates(fires: pd.DataFrame, counties: pd.DataFrame) -> pd.DataFrame:
    """Every (fire, county) pair where the fire is inside the county's box."""
    c_lat = counties["INTPTLAT"].to_numpy()
    c_lon = counties["INTPTLONG"].to_numpy()
    c_lat_range = counties["LAT_RANGE"].to_numpy()
    c_lon_range = counties["LON_RANGE"].to_numpy()

    pairs = []
    for start in range(0, len(fires), FIRE_CHUNK_ROWS):
        chunk = fires.iloc[start : start + FIRE_CHUNK_ROWS]
        f_lat = chunk["LATITUDE"].to_numpy()[:, None]
        f_lon = chunk["LONGITUDE"].to_numpy()[:, None]
        inside = (np.abs(f_lat - c_lat) <= c_lat_range) & (
            np.abs(f_lon - c_lon) <= c_lon_range
        )
        fire_idx, county_idx = np.nonzero(inside)
        pairs.append(
            pd.DataFrame({"fire_idx": fire_idx + start, "county_idx": county_idx})
        )
    pairs = pd.concat(pairs, ignore_index=True)
    pairs["DROUGHT_FIPS"] = counties["GEOID"].to_numpy()[pairs["county_idx"]]
    pairs["MATCH_METHOD"] = "latlon"
    return pairs.drop(columns="county_idx")


def find_fips_candidates(
    fires: pd.DataFrame, latlon_pairs: pd.DataFrame, counties: pd.DataFrame
) -> pd.DataFrame:
    """A fire's own FIPS county is a candidate, even if the fire is outside its box.

    Without this, a fire far from the center of a long county can miss its own
    county's box and get matched to a neighbor. The county is skipped when the fire
    is more than OWN_COUNTY_RANGE_FACTOR box half-widths from its center, since the
    FIPS code is then probably wrong. Pairs already found by lat/long are also
    skipped, so MATCH_METHOD is "fips" only when the county wasn't in range.
    """
    own = fires["FIPS_CODE"].dropna()
    own_pairs = pd.DataFrame(
        {
            "fire_idx": own.index,
            "DROUGHT_FIPS": own.astype(int).to_numpy(),
            "MATCH_METHOD": "fips",
        }
    )
    centers = counties.set_index("GEOID")[["INTPTLAT", "INTPTLONG", "HALF_WIDTH_KM"]]
    own_pairs = own_pairs[own_pairs["DROUGHT_FIPS"].isin(centers.index)]
    center = centers.loc[own_pairs["DROUGHT_FIPS"]]
    fire = fires.loc[own_pairs["fire_idx"]]
    distance_km = haversine_km(
        fire["LATITUDE"].to_numpy(),
        fire["LONGITUDE"].to_numpy(),
        center["INTPTLAT"].to_numpy(),
        center["INTPTLONG"].to_numpy(),
    )
    max_km = OWN_COUNTY_RANGE_FACTOR * center["HALF_WIDTH_KM"].to_numpy()
    own_pairs = own_pairs[distance_km <= max_km]

    already = own_pairs.merge(
        latlon_pairs[["fire_idx", "DROUGHT_FIPS"]], how="left", indicator=True
    )["_merge"].eq("both")
    return own_pairs[~already.to_numpy()]


def day_key(fips, dates: pd.Series) -> np.ndarray:
    """One integer per (county, day), so rows can be filtered quickly with isin."""
    days = (dates - pd.Timestamp("1970-01-01")).dt.days.to_numpy()
    return np.asarray(fips, dtype=np.int64) * 100_000 + days


def load_drought_rows(pairs: pd.DataFrame, fires: pd.DataFrame):
    """Read the big drought file in chunks, keeping only the rows some pair needs.

    Returns (weather rows on discovery dates, score rows in the look-back window).
    """
    discovery = fires.loc[pairs["fire_idx"], "DISCOVERY_DATE"].reset_index(drop=True)
    weather_keys = day_key(pairs["DROUGHT_FIPS"], discovery)
    score_keys = np.unique(
        np.concatenate([weather_keys - k for k in range(SCORE_LOOKBACK_DAYS + 1)])
    )
    weather_keys = np.unique(weather_keys)

    path = get_dataset_dir("droughts", processed=True) / "drought_clean.csv"
    weather_parts, score_parts = [], []
    for chunk in pd.read_csv(path, chunksize=DROUGHT_CHUNK_ROWS):
        chunk["date"] = pd.to_datetime(chunk["date"], format="%Y-%m-%d")
        keys = day_key(chunk["fips"], chunk["date"])
        weather_parts.append(chunk[np.isin(keys, weather_keys)])
        scored = chunk[np.isin(keys, score_keys) & chunk["score"].notna()]
        score_parts.append(scored[["fips", "date", "score"]])
        print(f"  read {chunk.index[-1] + 1:,} drought rows")

    weather = pd.concat(weather_parts, ignore_index=True)
    scores = pd.concat(score_parts, ignore_index=True)
    return weather, scores


def attach_drought(pairs, fires, weather, scores) -> pd.DataFrame:
    """Add weather (discovery day) and the latest score (look-back window) to pairs."""
    pairs = pairs.copy()
    pairs["DISCOVERY_DATE"] = fires.loc[pairs["fire_idx"], "DISCOVERY_DATE"].to_numpy()

    weather = weather.drop(columns="score").rename(
        columns={"fips": "DROUGHT_FIPS", "date": "DISCOVERY_DATE"}
    )
    pairs = pairs.merge(weather, on=["DROUGHT_FIPS", "DISCOVERY_DATE"], how="inner")

    scores = scores.rename(
        columns={"fips": "DROUGHT_FIPS", "date": "SCORE_DATE", "score": "SCORE"}
    )
    pairs = pd.merge_asof(
        pairs.sort_values("DISCOVERY_DATE"),
        scores.sort_values("SCORE_DATE"),
        left_on="DISCOVERY_DATE",
        right_on="SCORE_DATE",
        by="DROUGHT_FIPS",
        direction="backward",
        tolerance=pd.Timedelta(days=SCORE_LOOKBACK_DAYS),
    )
    return pairs.dropna(subset=["SCORE"]).drop(columns="DISCOVERY_DATE")


def pick_best_match(pairs, fires, counties) -> pd.DataFrame:
    """One county per fire.

    Weather is always taken on the discovery date, so every candidate ties on date.
    Ties go to the county with the fire's own FIPS code, then the nearest center.
    """
    centers = counties.set_index("GEOID")[["INTPTLAT", "INTPTLONG"]]
    fire_rows = fires.loc[pairs["fire_idx"]]
    pairs["MATCH_DISTANCE_KM"] = haversine_km(
        fire_rows["LATITUDE"].to_numpy(),
        fire_rows["LONGITUDE"].to_numpy(),
        centers.loc[pairs["DROUGHT_FIPS"], "INTPTLAT"].to_numpy(),
        centers.loc[pairs["DROUGHT_FIPS"], "INTPTLONG"].to_numpy(),
    )
    pairs["SAME_FIPS"] = (
        fire_rows["FIPS_CODE"].fillna(-1).astype(int).to_numpy()
        == pairs["DROUGHT_FIPS"].to_numpy()
    )
    pairs = pairs.sort_values(
        ["fire_idx", "SAME_FIPS", "MATCH_DISTANCE_KM"], ascending=[True, False, True]
    )
    return pairs.drop_duplicates("fire_idx").drop(columns="SAME_FIPS")


def limit_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Keep at most MAX_ROWS, with the same mix of fire size classes as before."""
    if len(df) <= MAX_ROWS:
        return df
    sample, _ = train_test_split(
        df,
        train_size=MAX_ROWS,
        stratify=df["FIRE_SIZE_CLASS"],
        random_state=SEED,
    )
    return sample.sort_values("FOD_ID")


def main() -> None:
    print("Loading fires and county centers...")
    fires = load_fires()
    counties = load_counties()
    print(
        f"{len(fires):,} fires in {FIRST_YEAR}-{LAST_YEAR}, {len(counties):,} counties"
    )

    latlon_pairs = find_latlon_candidates(fires, counties)
    fips_pairs = find_fips_candidates(fires, latlon_pairs, counties)
    pairs = pd.concat([latlon_pairs, fips_pairs], ignore_index=True)
    print(
        f"{latlon_pairs['fire_idx'].nunique():,} fires inside a county box "
        f"({len(latlon_pairs):,} candidate pairs), "
        f"{len(fips_pairs):,} own-county FIPS candidates outside their box"
    )

    print("Reading drought data (this takes a few minutes)...")
    weather, scores = load_drought_rows(pairs, fires)
    pairs = attach_drought(pairs, fires, weather, scores)
    best = pick_best_match(pairs, fires, counties)

    # Only fires that have drought data are kept
    df = fires.loc[best["fire_idx"]].reset_index(drop=True)
    df = pd.concat([df, best.drop(columns="fire_idx").reset_index(drop=True)], axis=1)
    print(f"{len(df):,} fires matched to drought data")
    print(df["MATCH_METHOD"].value_counts())

    df = limit_rows(df)

    out_dir = get_dataset_dir(OUTPUT_NAME, processed=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / OUTPUT_FILENAME
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df):,} rows to {out_path}")


if __name__ == "__main__":
    main()

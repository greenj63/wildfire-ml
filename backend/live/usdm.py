"""US Drought Monitor: weekly county drought coverage, turned into the model's SCORE."""

from datetime import date, datetime, timedelta

from backend.live.http import ApiError, get_text

URL = (
    "https://usdmdataservices.unl.edu/api/CountyStatistics/"
    "GetDroughtSeverityStatisticsByAreaPercent"
)


def drought_score_from_row(row: dict) -> float:
    """Cumulative percent of the county in D0..D4, summed and divided by 100.

    That is the Drought Severity and Coverage Index (0-500) scaled to 0-5, the same
    scale as the training SCORE (a county fully in D0 and 10% in D1 scores 1.10).
    """
    return sum(float(row[level]) for level in ("D0", "D1", "D2", "D3", "D4")) / 100


def fetch_drought_score(fips: str, on: date) -> tuple[float, date]:
    """(score, map date) from the newest weekly map on or before `on`."""
    text = get_text(
        URL,
        {
            "aoi": fips,
            "startdate": f"{(on - timedelta(days=28)):%m/%d/%Y}",
            "enddate": f"{on:%m/%d/%Y}",
            "statisticsType": 1,  # cumulative: D0 includes D1-D4
        },
    )
    lines = [line for line in text.strip().splitlines() if line]
    if len(lines) < 2:
        raise ApiError(f"No drought data for county {fips} up to {on}")
    header = lines[0].split(",")
    rows = [dict(zip(header, line.split(","), strict=False)) for line in lines[1:]]
    newest = max(rows, key=lambda r: r["MapDate"])
    map_date = datetime.strptime(newest["MapDate"], "%Y%m%d").date()
    return drought_score_from_row(newest), map_date

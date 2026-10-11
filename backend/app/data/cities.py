"""Built-in city coordinates.

Kerykeion can calculate a chart from latitude, longitude, and a time zone.
Looking up a city name online would call GeoNames. This prototype uses a
fixed list instead, so the chart stays on this computer.

The list is a testing set of major cities, not a world gazetteer.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CityLocation:
    name: str
    latitude: float
    longitude: float
    timezone: str


def _city(
    name: str,
    latitude: float,
    longitude: float,
    timezone: str,
) -> tuple[str, CityLocation]:
    return (name.lower(), CityLocation(name, latitude, longitude, timezone))


# Keys are lowercase city names. Coordinates are city-center values.
_CITY_ROWS: tuple[tuple[str, CityLocation], ...] = (
    _city("seattle", 47.6062, -122.3321, "America/Los_Angeles"),
    _city("portland", 45.5152, -122.6784, "America/Los_Angeles"),
    _city("san francisco", 37.7749, -122.4194, "America/Los_Angeles"),
    _city("los angeles", 34.0522, -118.2437, "America/Los_Angeles"),
    _city("san diego", 32.7157, -117.1611, "America/Los_Angeles"),
    _city("las vegas", 36.1699, -115.1398, "America/Los_Angeles"),
    _city("phoenix", 33.4484, -112.0740, "America/Phoenix"),
    _city("denver", 39.7392, -104.9903, "America/Denver"),
    _city("salt lake city", 40.7608, -111.8910, "America/Denver"),
    _city("austin", 30.2672, -97.7431, "America/Chicago"),
    _city("dallas", 32.7767, -96.7970, "America/Chicago"),
    _city("houston", 29.7604, -95.3698, "America/Chicago"),
    _city("san antonio", 29.4241, -98.4936, "America/Chicago"),
    _city("chicago", 41.8781, -87.6298, "America/Chicago"),
    _city("minneapolis", 44.9778, -93.2650, "America/Chicago"),
    _city("new orleans", 29.9511, -90.0715, "America/Chicago"),
    _city("nashville", 36.1627, -86.7816, "America/Chicago"),
    _city("new york", 40.7128, -74.0060, "America/New_York"),
    _city("boston", 42.3601, -71.0589, "America/New_York"),
    _city("philadelphia", 39.9526, -75.1652, "America/New_York"),
    _city("washington", 38.9072, -77.0369, "America/New_York"),
    _city("miami", 25.7617, -80.1918, "America/New_York"),
    _city("atlanta", 33.7490, -84.3880, "America/New_York"),
    _city("detroit", 42.3314, -83.0458, "America/Detroit"),
    _city("honolulu", 21.3069, -157.8583, "Pacific/Honolulu"),
    _city("anchorage", 61.2181, -149.9003, "America/Anchorage"),
    _city("toronto", 43.6532, -79.3832, "America/Toronto"),
    _city("vancouver", 49.2827, -123.1207, "America/Vancouver"),
    _city("mexico city", 19.4326, -99.1332, "America/Mexico_City"),
    _city("london", 51.5074, -0.1278, "Europe/London"),
    _city("dublin", 53.3498, -6.2603, "Europe/Dublin"),
    _city("paris", 48.8566, 2.3522, "Europe/Paris"),
    _city("berlin", 52.5200, 13.4050, "Europe/Berlin"),
    _city("rome", 41.9028, 12.4964, "Europe/Rome"),
    _city("madrid", 40.4168, -3.7038, "Europe/Madrid"),
    _city("amsterdam", 52.3676, 4.9041, "Europe/Amsterdam"),
    _city("tokyo", 35.6762, 139.6503, "Asia/Tokyo"),
    _city("seoul", 37.5665, 126.9780, "Asia/Seoul"),
    _city("beijing", 39.9042, 116.4074, "Asia/Shanghai"),
    _city("shanghai", 31.2304, 121.4737, "Asia/Shanghai"),
    _city("hong kong", 22.3193, 114.1694, "Asia/Hong_Kong"),
    _city("singapore", 1.3521, 103.8198, "Asia/Singapore"),
    _city("mumbai", 19.0760, 72.8777, "Asia/Kolkata"),
    _city("delhi", 28.7041, 77.1025, "Asia/Kolkata"),
    _city("dubai", 25.2048, 55.2708, "Asia/Dubai"),
    _city("sydney", -33.8688, 151.2093, "Australia/Sydney"),
    _city("sao paulo", -23.5558, -46.6396, "America/Sao_Paulo"),
)

CITIES: dict[str, CityLocation] = dict(_CITY_ROWS)

_ALIASES = {
    "nyc": "new york",
    "new york city": "new york",
    "washington dc": "washington",
    "washington d c": "washington",
    "sf": "san francisco",
    "la": "los angeles",
    "l a": "los angeles",
}


def lookup_city(name: str) -> CityLocation | None:
    """Return coordinates for a known city, ignoring state text after a comma."""

    key = name.lower().replace(".", "").split(",")[0].strip()
    key = " ".join(key.split())
    key = _ALIASES.get(key, key)
    return CITIES.get(key)

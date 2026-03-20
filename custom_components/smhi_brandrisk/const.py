"""Constants for SMHI Brandrisk integration."""

DOMAIN = "smhi_brandrisk"

# API endpoints – FWI brandrisk (säsongsbaserat, fwiindex=-1 utanför säsong)
API_BASE_FORECAST_DAILY = (
    "https://opendata-download-metfcst.smhi.se/api/category/fwif1g/version/1/daily"
    "/geotype/point/lon/{lon}/lat/{lat}/data.json"
)
API_BASE_FORECAST_HOURLY = (
    "https://opendata-download-metfcst.smhi.se/api/category/fwif1g/version/1/hourly"
    "/geotype/point/lon/{lon}/lat/{lat}/data.json"
)

# API endpoint – SNOW1g fruset nederbördsindex (år-runt, punktbaserat)
API_SNOW1G_HOURLY = (
    "https://opendata-download-metfcst.smhi.se/api/category/snow1g/version/1"
    "/geotype/point/lon/{lon}/lat/{lat}/data.json"
)

# API endpoint – IBW vädervarningar (år-runt, nationell nivå)
API_IBW_ALERTS = (
    "https://opendata-download-warnings.smhi.se/ibww/api/version/1/alerts.json"
)

# Update interval in minutes
DEFAULT_SCAN_INTERVAL = 60

# Config keys
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
CONF_NAME = "name"

# FWI Index classes (1–6) with Swedish labels and colors
FWI_INDEX_MAP = {
    1: {"label": "Mycket låg", "icon": "mdi:fire-off", "color": "green"},
    2: {"label": "Låg",        "icon": "mdi:fire-off", "color": "lightgreen"},
    3: {"label": "Medel",      "icon": "mdi:fire",     "color": "yellow"},
    4: {"label": "Hög",        "icon": "mdi:fire",     "color": "orange"},
    5: {"label": "Mycket hög", "icon": "mdi:fire-alert","color": "red"},
    6: {"label": "Extrem",     "icon": "mdi:fire-alert","color": "darkred"},
}

# IBW vädervarningar – allvarlighetsgrad
IBW_SEVERITY = {"GREEN": 0, "YELLOW": 1, "ORANGE": 2, "RED": 3}

IBW_SEVERITY_LABEL = {
    0: "Ingen varning",
    1: "Gul varning",
    2: "Orange varning",
    3: "Röd varning",
}

IBW_SEVERITY_ICON = {
    0: "mdi:shield-check",
    1: "mdi:shield-alert-outline",
    2: "mdi:shield-alert",
    3: "mdi:shield-alert",
}

# Svenska händelsetyp-etiketter för IBW
IBW_EVENT_LABELS = {
    "WIND": "Vind",
    "SNOW": "Snö",
    "ICE": "Is",
    "RAIN": "Regn",
    "THUNDER": "Åska",
    "FOG": "Dimma",
    "HEAT": "Värme",
    "COLD": "Kyla",
    "FOREST_FIRE": "Skogsbrand",
    "FLOOD": "Översvämning",
    "HIGH_WATER": "Högt vattenflöde",
    "LOW_WATER": "Lågt vattenflöde",
    "AVALANCHE": "Lavinfara",
    "STORM_SURGE": "Stormflod",
    "WAVE": "Höga vågor",
}

# Fruset nederbörds-risk (probability_of_frozen_precipitation, 0.0–1.0)
# Lista av (max_exklusivt, label, icon, color)
FROZEN_PRECIP_RISK_MAP = [
    (0.10, "Mycket låg",  "mdi:snowflake-off",         "green"),
    (0.25, "Låg",         "mdi:snowflake-variant",      "lightgreen"),
    (0.50, "Måttlig",     "mdi:weather-snowy",          "yellow"),
    (0.75, "Hög",         "mdi:weather-snowy-heavy",    "orange"),
    (1.01, "Mycket hög",  "mdi:weather-snowy-heavy",    "red"),
]

# Sensor definitions: (parameter_name, friendly_name, unit, icon)
SENSOR_DEFINITIONS = [
    ("fwiindex",  "Brandrisk (FWI-klass)",    "",       "mdi:fire"),
    ("fwi",       "FWI-index",                "",       "mdi:fire"),
    ("ffmc",      "FFMC (fuktighet – finbränsle)", "",  "mdi:leaf"),
    ("dmc",       "DMC (fuktighet – medium)",  "",      "mdi:leaf"),
    ("dc",        "DC (torka – djupt)",        "",      "mdi:weather-sunny-alert"),
    ("isi",       "ISI (spridningshastighet)", "",      "mdi:weather-windy"),
    ("bui",       "BUI (bränsletillgång)",     "",      "mdi:pine-tree-fire"),
    ("gfwi",      "Gräsbrandsrisk (klass)",    "",      "mdi:grass"),
]

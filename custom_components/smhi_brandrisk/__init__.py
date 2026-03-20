"""SMHI Brandrisk – Home Assistant Integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    API_BASE_FORECAST_DAILY,
    API_BASE_FORECAST_HOURLY,
    API_SNOW1G_HOURLY,
    API_IBW_ALERTS,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    IBW_SEVERITY,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SMHI Brandrisk from a config entry."""
    lat = entry.data[CONF_LATITUDE]
    lon = entry.data[CONF_LONGITUDE]
    session = async_get_clientsession(hass)

    coordinator = SMHIBrandRiskCoordinator(hass, session, lat, lon)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


class SMHIBrandRiskCoordinator(DataUpdateCoordinator):
    """Hämtar brandrisk- och vinterriskdata från SMHI:s öppna API:er."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: aiohttp.ClientSession,
        lat: float,
        lon: float,
    ) -> None:
        self.lat = lat
        self.lon = lon
        self.session = session

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{lat}_{lon}",
            update_interval=timedelta(minutes=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict:
        """Hämta data från SMHI FWI-, SNOW1g- och IBW-API:er."""
        # SMHI:s API accepterar max ~6 decimaler — avrunda för att undvika 404
        lat = round(self.lat, 4)
        lon = round(self.lon, 4)

        url_daily = API_BASE_FORECAST_DAILY.format(lat=lat, lon=lon)
        url_hourly = API_BASE_FORECAST_HOURLY.format(lat=lat, lon=lon)
        url_snow = API_SNOW1G_HOURLY.format(lat=lat, lon=lon)

        # --- FWI dagsprognos (kritisk) ---
        try:
            async with asyncio.timeout(15):
                resp_daily = await self.session.get(url_daily)
                resp_daily.raise_for_status()
                data_daily = await resp_daily.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Fel vid anrop mot SMHI FWI API: {err}") from err
        except TimeoutError as err:
            raise UpdateFailed(f"Timeout mot SMHI FWI API: {err}") from err

        # --- FWI timprognos (icke-kritisk, används bara för timprognos_idag-attribut) ---
        data_hourly: dict = {}
        try:
            async with asyncio.timeout(15):
                resp_hourly = await self.session.get(url_hourly)
                resp_hourly.raise_for_status()
                data_hourly = await resp_hourly.json()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("FWI timprognos misslyckades (icke-kritisk): %s", err)

        # --- SNOW1g fruset nederbördsindex (icke-kritisk) ---
        data_snow: dict = {}
        try:
            async with asyncio.timeout(15):
                resp_snow = await self.session.get(url_snow)
                resp_snow.raise_for_status()
                data_snow = await resp_snow.json()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("SNOW1g-hämtning misslyckades: %s – url: %s", err, url_snow)

        # --- IBW vädervarningar (icke-kritisk) ---
        data_ibw: list = []
        try:
            async with asyncio.timeout(10):
                resp_ibw = await self.session.get(API_IBW_ALERTS)
                if resp_ibw.status == 200:
                    data_ibw = await resp_ibw.json()
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("IBW-varningshämtning misslyckades (icke-kritisk): %s", err)

        # --- Säsongsdetektering ---
        daily_parsed = self._parse_timeseries(data_daily)
        fwiindex_today = daily_parsed[0].get("fwiindex") if daily_parsed else None
        # fwiindex == -1.0 är SMHIs sentinel-värde för "utanför brandsäsong"
        fire_season_active = (
            fwiindex_today is not None and float(fwiindex_today) >= 1.0
        )

        return {
            "daily": daily_parsed,
            "hourly": self._parse_timeseries(data_hourly) if data_hourly else [],
            "snow_hourly": self._parse_timeseries(data_snow) if data_snow else [],
            "ibw_alerts": self._parse_ibw_alerts(data_ibw),
            "fire_season_active": fire_season_active,
            "reference_time": data_daily.get("referenceTime"),
            "approved_time": data_daily.get("approvedTime"),
            "grid_lat": data_daily.get("geometry", {}).get("coordinates", [[None]])[0][1],
            "grid_lon": data_daily.get("geometry", {}).get("coordinates", [[None]])[0][0],
        }

    def _parse_timeseries(self, data: dict) -> list[dict]:
        """Omvandla SMHI:s timeSeries-struktur till en enkel lista med dicts."""
        result = []
        for entry in data.get("timeSeries", []):
            row = {"validTime": entry.get("validTime")}
            for param in entry.get("parameters", []):
                name = param.get("name", "")
                values = param.get("values", [])
                row[name] = values[0] if values else None
            result.append(row)
        return result

    def _parse_ibw_alerts(self, data) -> list[dict]:
        """Parsa IBW-varningslistan till en enkel struktur."""
        if isinstance(data, list):
            alerts = data
        elif isinstance(data, dict):
            # Hantera GeoJSON-format eller wrapper-objekt
            alerts = data.get("alerts", data.get("features", []))
        else:
            return []

        result = []
        for alert in alerts:
            # Stöd för både flat dict och GeoJSON med properties-nyckel
            props = alert.get("properties", alert)
            event = props.get("event", {})
            level = props.get("warningLevel", {})
            severity_code = level.get("code", "GREEN")

            result.append({
                "event_code": event.get("code", ""),
                "event_sv": event.get("sv", event.get("en", "")),
                "severity_code": severity_code,
                "severity": IBW_SEVERITY.get(severity_code, 0),
                "description": props.get("description", ""),
                "sent": props.get("sent", ""),
            })

        return result

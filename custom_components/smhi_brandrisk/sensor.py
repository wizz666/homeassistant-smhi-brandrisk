"""Sensorer för SMHI Brandrisk."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SMHIBrandRiskCoordinator
from .const import (
    DOMAIN,
    CONF_NAME,
    SENSOR_DEFINITIONS,
    FWI_INDEX_MAP,
    IBW_SEVERITY_LABEL,
    IBW_SEVERITY_ICON,
    IBW_EVENT_LABELS,
    FROZEN_PRECIP_RISK_MAP,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Lägg till sensorer för denna konfigurationspost."""
    coordinator: SMHIBrandRiskCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data[CONF_NAME]

    entities: list[CoordinatorEntity] = []

    # Befintliga FWI-sensorer (en per parameter)
    for param_name, friendly_name, unit, icon in SENSOR_DEFINITIONS:
        entities.append(
            SMHIBrandRiskSensor(
                coordinator=coordinator,
                entry_id=entry.entry_id,
                location_name=name,
                param_name=param_name,
                friendly_name=friendly_name,
                unit=unit,
                icon=icon,
            )
        )

    # FWI-sammanfattning (text)
    entities.append(
        SMHIBrandRiskSummary(
            coordinator=coordinator,
            entry_id=entry.entry_id,
            location_name=name,
        )
    )

    # Ny: Aktiv säsong
    entities.append(
        SMHISeasonSensor(
            coordinator=coordinator,
            entry_id=entry.entry_id,
            location_name=name,
        )
    )

    # Ny: Vinterrisk – fruset nederbördsindex (SNOW1g)
    entities.append(
        SMHIWinterRiskSensor(
            coordinator=coordinator,
            entry_id=entry.entry_id,
            location_name=name,
        )
    )

    # Ny: Vädervarning (IBW)
    entities.append(
        SMHIWeatherWarningSensor(
            coordinator=coordinator,
            entry_id=entry.entry_id,
            location_name=name,
        )
    )

    async_add_entities(entities, update_before_add=True)


def _device_info(domain_key: str, location_name: str) -> DeviceInfo:
    """Gemensam DeviceInfo för alla sensorer på samma plats."""
    return DeviceInfo(
        identifiers={(DOMAIN, domain_key)},
        name=f"SMHI Brandrisk – {location_name}",
        manufacturer="SMHI / MSB",
        model="Fire Weather Index (FWI) + SNOW1g + IBW",
        entry_type=DeviceEntryType.SERVICE,
    )


def _frozen_precip_info(prob_fraction: float | None) -> tuple[str, str, str]:
    """Returnera (label, icon, color) för ett sannolikhetsvärde 0.0–1.0."""
    if prob_fraction is None:
        return "Okänd", "mdi:snowflake-off", "gray"
    for max_val, label, icon, color in FROZEN_PRECIP_RISK_MAP:
        if prob_fraction < max_val:
            return label, icon, color
    return "Mycket hög", "mdi:weather-snowy-heavy", "red"


# ---------------------------------------------------------------------------
# Befintliga sensorer (oförändrade)
# ---------------------------------------------------------------------------

class SMHIBrandRiskSensor(CoordinatorEntity, SensorEntity):
    """En sensor för ett specifikt brandriskparameter (dygn, första värdet = idag)."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SMHIBrandRiskCoordinator,
        entry_id: str,
        location_name: str,
        param_name: str,
        friendly_name: str,
        unit: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator)
        self._param_name = param_name
        self._location_name = location_name
        self._entry_id = entry_id
        self._attr_name = friendly_name
        self._attr_native_unit_of_measurement = unit if unit else None
        self._attr_icon = icon
        self._attr_unique_id = f"{entry_id}_{param_name}"

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry_id, self._location_name)

    @property
    def native_value(self) -> Any:
        """Returnera dagens värde (första posten i dygnsprognosen)."""
        daily = self.coordinator.data.get("daily", [])
        if not daily:
            return None
        val = daily[0].get(self._param_name)
        # gfwi beräknas inte i djup vinter — returnera 0 (ingen gräsbrandsrisk)
        if val is None and self._param_name == "gfwi":
            return 0
        return val

    @property
    def extra_state_attributes(self) -> dict:
        """Lägg till prognos för kommande dagar som extra attribut."""
        daily = self.coordinator.data.get("daily", [])
        forecast = []
        for entry in daily:
            val = entry.get(self._param_name)
            if val is not None:
                row = {"time": entry.get("validTime"), "value": val}
                if self._param_name == "fwiindex":
                    info = FWI_INDEX_MAP.get(int(val), {})
                    row["label"] = info.get("label", "")
                    row["color"] = info.get("color", "")
                forecast.append(row)

        attrs = {
            "prognos_dygn": forecast,
            "referenstid": self.coordinator.data.get("reference_time"),
            "godkänd_tid": self.coordinator.data.get("approved_time"),
            "närmaste_gitterpunkt_lat": self.coordinator.data.get("grid_lat"),
            "närmaste_gitterpunkt_lon": self.coordinator.data.get("grid_lon"),
            "källa": "SMHI / MSB – brandrisk.smhi.se",
        }

        if self._param_name == "fwiindex" and self.native_value is not None:
            info = FWI_INDEX_MAP.get(int(self.native_value), {})
            attrs["risknivå"] = info.get("label", "")
            attrs["färg"] = info.get("color", "")

        return attrs

    @property
    def icon(self) -> str:
        """Välj ikon baserat på FWI-klass om tillämpligt."""
        if self._param_name == "fwiindex" and self.native_value is not None:
            info = FWI_INDEX_MAP.get(int(self.native_value), {})
            return info.get("icon", self._attr_icon)
        return self._attr_icon


class SMHIBrandRiskSummary(CoordinatorEntity, SensorEntity):
    """En sammanfattningssensor som visar brandriskens textbeskrivning direkt."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SMHIBrandRiskCoordinator,
        entry_id: str,
        location_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._location_name = location_name
        self._entry_id = entry_id
        self._attr_name = "Brandrisk idag (text)"
        self._attr_unique_id = f"{entry_id}_summary"

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry_id, self._location_name)

    @property
    def native_value(self) -> str | None:
        """Returnera textbeskrivning av brandriskklassen."""
        daily = self.coordinator.data.get("daily", [])
        if not daily:
            return None
        fwiindex = daily[0].get("fwiindex")
        if fwiindex is None:
            return None
        if float(fwiindex) < 0:
            return "Utanför brandsäsong"
        info = FWI_INDEX_MAP.get(int(fwiindex), {})
        return info.get("label", f"Klass {fwiindex}")

    @property
    def icon(self) -> str:
        daily = self.coordinator.data.get("daily", [])
        if not daily:
            return "mdi:fire"
        fwiindex = daily[0].get("fwiindex")
        if fwiindex is None:
            return "mdi:fire"
        if float(fwiindex) < 0:
            return "mdi:snowflake"
        info = FWI_INDEX_MAP.get(int(fwiindex), {})
        return info.get("icon", "mdi:fire")

    @property
    def extra_state_attributes(self) -> dict:
        daily = self.coordinator.data.get("daily", [])
        hourly = self.coordinator.data.get("hourly", [])

        today_data = daily[0] if daily else {}
        fwiindex = today_data.get("fwiindex")
        info = FWI_INDEX_MAP.get(int(fwiindex), {}) if fwiindex is not None else {}

        hourly_today = [
            {"tid": e.get("validTime"), "fwiindex": e.get("fwiindex"), "fwi": e.get("fwi")}
            for e in hourly[:24]
        ]

        return {
            "fwiindex": fwiindex,
            "fwi": today_data.get("fwi"),
            "ffmc": today_data.get("ffmc"),
            "dmc": today_data.get("dmc"),
            "dc": today_data.get("dc"),
            "isi": today_data.get("isi"),
            "bui": today_data.get("bui"),
            "gräsbrandsrisk_klass": today_data.get("gfwi"),
            "risknivå": info.get("label", ""),
            "färg": info.get("color", ""),
            "timprognos_idag": hourly_today,
            "källa": "SMHI / MSB – brandrisk.smhi.se",
        }


# ---------------------------------------------------------------------------
# Nya sensorer – år-runt-funktionalitet
# ---------------------------------------------------------------------------

class SMHISeasonSensor(CoordinatorEntity, SensorEntity):
    """Visar aktuell risksäsong: Brandsäsong eller Utanför brandsäsong."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SMHIBrandRiskCoordinator,
        entry_id: str,
        location_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._location_name = location_name
        self._attr_name = "Aktiv säsong"
        self._attr_unique_id = f"{entry_id}_season"

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry_id, self._location_name)

    @property
    def native_value(self) -> str:
        fire_active = self.coordinator.data.get("fire_season_active", False)
        return "Brandsäsong" if fire_active else "Utanför brandsäsong"

    @property
    def icon(self) -> str:
        return "mdi:fire" if self.coordinator.data.get("fire_season_active") else "mdi:snowflake"

    @property
    def extra_state_attributes(self) -> dict:
        daily = self.coordinator.data.get("daily", [])
        fwiindex = daily[0].get("fwiindex") if daily else None
        return {
            "brandsäsong_aktiv": self.coordinator.data.get("fire_season_active", False),
            "fwiindex_råvärde": fwiindex,
            "källa": "SMHI FWI (fwiindex >= 1 = brandsäsong aktiv)",
        }


class SMHIWinterRiskSensor(CoordinatorEntity, SensorEntity):
    """Visar risk för fruset nederbörd (snö/is) baserat på SMHI SNOW1g.

    Värdet är sannolikheten (0–100 %) för fruset nederbörd under kommande timme.
    Sensorn är aktiv hela året – mest relevant november–april.
    """

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "%"

    def __init__(
        self,
        coordinator: SMHIBrandRiskCoordinator,
        entry_id: str,
        location_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._location_name = location_name
        self._attr_name = "Vinterrisk (fruset nederbörd)"
        self._attr_unique_id = f"{entry_id}_winter_risk"

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry_id, self._location_name)

    @property
    def native_value(self) -> int | None:
        """Returnera sannolikhet i procent (0–100)."""
        snow = self.coordinator.data.get("snow_hourly", [])
        if not snow:
            return None
        prob = snow[0].get("probability_of_frozen_precipitation")
        if prob is None:
            return None
        return round(float(prob) * 100)

    @property
    def icon(self) -> str:
        val = self.native_value
        prob = val / 100 if val is not None else None
        _, icon, _ = _frozen_precip_info(prob)
        return icon

    @property
    def extra_state_attributes(self) -> dict:
        snow = self.coordinator.data.get("snow_hourly", [])

        # Prognos kommande 48 timmar
        forecast_48h = []
        for entry in snow[:48]:
            prob = entry.get("probability_of_frozen_precipitation")
            if prob is not None:
                p = round(float(prob) * 100)
                label, _, color = _frozen_precip_info(float(prob))
                forecast_48h.append({
                    "tid": entry.get("validTime"),
                    "sannolikhet_procent": p,
                    "risknivå": label,
                    "färg": color,
                })

        val = self.native_value
        prob_fraction = val / 100 if val is not None else None
        risk_label, _, risk_color = _frozen_precip_info(prob_fraction)

        return {
            "risknivå": risk_label,
            "färg": risk_color,
            "prognos_48h": forecast_48h,
            "källa": "SMHI SNOW1g – probability_of_frozen_precipitation",
        }


class SMHIWeatherWarningSensor(CoordinatorEntity, SensorEntity):
    """Visar aktiva SMHI vädervarningar (IBW – Impact-Based Warnings).

    Visar den högsta aktiva allvarlighetsgraden för Sverige.
    Täckning: Nationell nivå (ej filtrerat per koordinat i v1).
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SMHIBrandRiskCoordinator,
        entry_id: str,
        location_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._location_name = location_name
        self._attr_name = "Vädervarning"
        self._attr_unique_id = f"{entry_id}_ibw_warning"

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry_id, self._location_name)

    @property
    def native_value(self) -> str:
        alerts = self.coordinator.data.get("ibw_alerts", [])
        if not alerts:
            return IBW_SEVERITY_LABEL[0]
        max_severity = max(a.get("severity", 0) for a in alerts)
        return IBW_SEVERITY_LABEL.get(max_severity, IBW_SEVERITY_LABEL[0])

    @property
    def icon(self) -> str:
        alerts = self.coordinator.data.get("ibw_alerts", [])
        if not alerts:
            return IBW_SEVERITY_ICON[0]
        max_severity = max(a.get("severity", 0) for a in alerts)
        return IBW_SEVERITY_ICON.get(max_severity, IBW_SEVERITY_ICON[0])

    @property
    def extra_state_attributes(self) -> dict:
        alerts = self.coordinator.data.get("ibw_alerts", [])
        max_severity = max((a.get("severity", 0) for a in alerts), default=0)

        # Unika aktiva varningstyper (svenska etiketter)
        active_types = sorted({
            IBW_EVENT_LABELS.get(a["event_code"], a["event_code"])
            for a in alerts
        })

        return {
            "antal_varningar": len(alerts),
            "allvarlighetsgrad_nivå": max_severity,
            "aktiva_varningstyper": active_types,
            "varningar": [
                {
                    "typ": IBW_EVENT_LABELS.get(a["event_code"], a["event_code"]),
                    "nivå": IBW_SEVERITY_LABEL.get(a["severity"], ""),
                    "skickat": a["sent"],
                }
                for a in alerts
            ],
            "täckning": "Hela Sverige (nationell nivå)",
            "källa": "SMHI Impact-Based Warnings (IBW)",
        }

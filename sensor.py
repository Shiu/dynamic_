"""Sensor platform for Dynamic Presence integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime, LIGHT_LUX
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
)
from .coordinator import DynamicPresenceCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator: DynamicPresenceCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        DynamicPresenceSensor(
            coordinator=coordinator,
            device_class=SensorDeviceClass.DURATION,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTime.SECONDS,
            unique_id=f"{entry.entry_id}_occupancy_duration",
            key="occupancy_duration",
        ),
        DynamicPresenceSensor(
            coordinator=coordinator,
            device_class=SensorDeviceClass.DURATION,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTime.SECONDS,
            unique_id=f"{entry.entry_id}_absence_duration",
            key="absence_duration",
        ),
        ManualStatesSensor(
            coordinator=coordinator,
            is_night_mode=False,
        ),
    ]

    # Only add night mode sensor if night lights are configured
    if coordinator.has_night_mode:
        entities.append(
            ManualStatesSensor(
                coordinator=coordinator,
                is_night_mode=True,
            )
        )

    if coordinator.has_light_sensor:
        entities.append(
            DynamicPresenceSensor(
                coordinator=coordinator,
                device_class=SensorDeviceClass.ILLUMINANCE,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=LIGHT_LUX,
                unique_id=f"{entry.entry_id}_light_level",
                key="light_level",
            )
        )

    async_add_entities(entities)


class DynamicPresenceSensor(
    CoordinatorEntity[DynamicPresenceCoordinator], SensorEntity
):
    """Base sensor for Dynamic Presence."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: DynamicPresenceCoordinator,
        device_class: SensorDeviceClass | None,
        state_class: SensorStateClass,
        unique_id: str,
        key: str,
        native_unit_of_measurement: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_unique_id = unique_id
        self._attr_suggested_object_id = key
        self._attr_translation_key = key
        self._key = key
        self._attr_native_unit_of_measurement = native_unit_of_measurement
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> int | float | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(f"sensor_{self._key}", 0)


class ManualStatesSensor(CoordinatorEntity[DynamicPresenceCoordinator], SensorEntity):
    """Sensor for tracking manual states."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: DynamicPresenceCoordinator,
        is_night_mode: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._is_night_mode = is_night_mode

        # Set unique_id and entity_id
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_"
            f"{'night' if is_night_mode else 'main'}_manual_states"
        )
        self.entity_id = (
            f"sensor.{coordinator.room_name}_"
            f"{'night' if is_night_mode else 'main'}_manual_states"
        ).lower()

        # Set name based on mode
        self._attr_translation_key = (
            "night_manual_states" if is_night_mode else "main_manual_states"
        )
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        states = self.coordinator.manual_states
        mode_states = states["night" if self._is_night_mode else "main"]

        # Format each light state as "Light Name: ON/OFF"
        formatted_states = []
        for entity_id, is_on in mode_states.items():
            # Extract light name from entity_id (e.g., "light.kitchen" -> "Kitchen")
            light_name = entity_id.split(".")[-1].replace("_", " ").title()
            state_str = "ON" if is_on else "OFF"
            formatted_states.append(f"{light_name}: {state_str}")

        # Join all states with commas
        return ", ".join(formatted_states) if formatted_states else "No lights"

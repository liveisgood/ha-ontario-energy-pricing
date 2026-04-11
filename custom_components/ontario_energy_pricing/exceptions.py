"""Custom exceptions for the Ontario Energy Pricing integration."""

from __future__ import annotations

# type: ignore[import]  # noqa: E501,F401
# Home Assistant imports - unavailable outside HA runtime
from homeassistant.exceptions import (  # type: ignore[import]  # noqa: E501  # pylint: disable=import-error
    ConfigEntryError,
    HomeAssistantError,
)


class OntarioEnergyPricingError(HomeAssistantError):
    """Base exception for Ontario Energy Pricing errors."""

    def __init__(
        self,
        message: str,
        translation_key: str | None = None,
        translation_placeholders: dict[str, str] | None = None,
    ) -> None:
        """Initialize the exception."""
        super().__init__(message)
        self.message = message
        self.translation_key = translation_key
        self.translation_placeholders = translation_placeholders or {}


class GridStatusAuthError(ConfigEntryError):
    """Exception raised when GridStatus API authentication fails."""

    def __init__(self, message: str = "Authentication failed") -> None:
        """Initialize the exception."""
        super().__init__(message)
        self.translation_key = "auth_error"


class GridStatusAPIError(OntarioEnergyPricingError):
    """Exception raised when GridStatus API returns an error."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
    ) -> None:
        """Initialize the exception."""
        super().__init__(
            message=message,
            translation_key="api_error",
            translation_placeholders={
                "status_code": str(status_code) if status_code else "unknown"
            },
        )
        self.status_code = status_code


class GridStatusConnectionError(OntarioEnergyPricingError):
    """Exception raised when connection to GridStatus API fails."""

    def __init__(self, message: str = "Failed to connect to GridStatus API") -> None:
        """Initialize the exception."""
        super().__init__(
            message=message,
            translation_key="connection_error",
        )


class IESOXMLParseError(OntarioEnergyPricingError):
    """Exception raised when IESO XML parsing fails."""

    def __init__(
        self,
        message: str = "Failed to parse IESO XML response",
        xml_snippet: str | None = None,
    ) -> None:
        """Initialize the exception."""
        super().__init__(
            message=message,
            translation_key="xml_parse_error",
        )
        self.xml_snippet = xml_snippet


class ZoneNotFoundError(OntarioEnergyPricingError):
    """Exception raised when no matching zone is found for a location."""

    def __init__(
        self,
        location: str,
        available_zones: list[str] | None = None,
    ) -> None:
        """Initialize the exception."""
        message = f"No zone found for location: {location}"
        super().__init__(
            message=message,
            translation_key="zone_not_found",
            translation_placeholders={"location": location},
        )
        self.location = location
        self.available_zones = available_zones or []

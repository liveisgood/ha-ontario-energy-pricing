"""Custom exceptions for the Ontario Energy Pricing integration."""

from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError


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


class IESOLMPError(OntarioEnergyPricingError):
    """Exception raised when IESO LMP fetch or parse fails."""

    def __init__(
        self,
        message: str = "Failed to fetch IESO LMP data",
        xml_snippet: str | None = None,
    ) -> None:
        """Initialize the exception."""
        super().__init__(
            message=message,
            translation_key="lmp_fetch_error",
        )
        self.xml_snippet = xml_snippet


class IESOConnectionError(OntarioEnergyPricingError):
    """Exception raised when connection to IESO fails."""

    def __init__(self, message: str = "Failed to connect to IESO") -> None:
        """Initialize the exception."""
        super().__init__(
            message=message,
            translation_key="ieso_connection_error",
        )

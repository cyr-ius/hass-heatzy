"""Test the livebox config flow."""

from unittest.mock import AsyncMock, patch

import pytest
from heatzypy.exception import AuthenticationFailed, HeatzyException, HttpRequestFailed
from homeassistant import config_entries, setup
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.heatzy.const import DOMAIN

from .const import MOCK_USER_INPUT


@pytest.fixture(autouse=True)
def mock_setup_entry():
    """Override async_setup_entry."""
    with patch("custom_components.heatzy.async_setup_entry", return_value=True):
        yield


async def test_form_success(hass: HomeAssistant, HeatzyClient: AsyncMock) -> None:
    """Test a successful setup flow."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    with patch("custom_components.heatzy.config_flow.HeatzyClient") as mock:
        # Simulate a successful connection and info retrieval
        mock.return_value = HeatzyClient

        # Start the config flow
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert not result.get("errors")

        # Simulate user submitting the form
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_USER_INPUT,
        )
        await hass.async_block_till_done()

        # Assert the flow finished and created an entry
        assert result2["type"] == FlowResultType.CREATE_ENTRY
        assert result2["title"] == "heatzy (xx@yy.zz)"  # From INFO fixture
        assert result2["data"] == MOCK_USER_INPUT  # From INFO fixture


async def test_form_cannot_connect(hass: HomeAssistant, HeatzyClient: AsyncMock) -> None:
    """Test the flow handles connection errors."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    with patch("custom_components.heatzy.config_flow.HeatzyClient") as mock:
        # Simulate a successful connection and info retrieval
        mock.return_value = HeatzyClient
        mock.return_value.async_bindings.side_effect = HttpRequestFailed(
            "Connection failed"
        )

        # Start the flow and submit data
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=MOCK_USER_INPUT,
        )

        # Assert the form is shown again with a connection error
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


async def test_form_invalid_auth(hass: HomeAssistant, HeatzyClient: AsyncMock) -> None:
    """Test the flow handles invalid authentication."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    with patch("custom_components.heatzy.config_flow.HeatzyClient") as mock:
        # Simulate an authentication error
        mock.return_value = HeatzyClient
        mock.return_value.async_bindings.side_effect = AuthenticationFailed(
            "Login error"
        )

        # Start the flow and submit data
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=MOCK_USER_INPUT,
        )

        # Assert the form is shown again with an auth error
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_auth"}


async def test_form_unknown(hass: HomeAssistant, HeatzyClient: AsyncMock) -> None:
    """Test the flow handles invalid authentication."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    with patch("custom_components.heatzy.config_flow.HeatzyClient") as mock:
        # Simulate an authentication error
        mock.return_value = HeatzyClient
        mock.return_value.async_bindings.side_effect = HeatzyException(
            "Unknown error"
        )

        # Start the flow and submit data
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=MOCK_USER_INPUT,
        )

        # Assert the form is shown again with an auth error
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "unknown"}


async def test_form_already_configured(hass: HomeAssistant, HeatzyClient: AsyncMock) -> None:
    """Test the flow aborts if the device is already configured."""
    # Create a mock entry to simulate existing configuration
    MockConfigEntry(
        domain=DOMAIN, unique_id="012345678901234", data=MOCK_USER_INPUT
    ).add_to_hass(hass)

    with patch("custom_components.heatzy.config_flow.HeatzyClient") as mock:
        # Simulate a successful connection and info retrieval
        mock.return_value = HeatzyClient

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Simulate user submitting the form
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_USER_INPUT,
        )
        await hass.async_block_till_done()

        # Assert the flow is aborted
        assert result2["type"] == FlowResultType.ABORT
        assert result2["reason"] == "already_configured"

"""Test the Heatzy config flow."""

from unittest.mock import AsyncMock, patch

from heatzypy.exception import AuthenticationFailed, HeatzyException, HttpRequestFailed
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.heatzy.const import DOMAIN
from homeassistant import config_entries, setup
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

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


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (HttpRequestFailed("Connection failed"), "cannot_connect"),
        (AuthenticationFailed("Login error"), "invalid_auth"),
        (HeatzyException("Unknown error"), "unknown"),
    ],
)
async def test_form_error_then_recover(
    hass: HomeAssistant, HeatzyClient: AsyncMock, error: Exception, reason: str
) -> None:
    """Show the error on the form, then create the entry once it is fixed."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    with patch("custom_components.heatzy.config_flow.HeatzyClient") as mock:
        mock.return_value = HeatzyClient
        mock.return_value.async_bindings.side_effect = error

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=MOCK_USER_INPUT,
        )
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": reason}

        mock.return_value.async_bindings.side_effect = None
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MOCK_USER_INPUT
        )
        await hass.async_block_till_done()

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"] == MOCK_USER_INPUT


async def test_form_already_configured(
    hass: HomeAssistant, HeatzyClient: AsyncMock
) -> None:
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


async def test_reauth_error_then_recover(
    hass: HomeAssistant, HeatzyClient: AsyncMock
) -> None:
    """Ask for the new password, refuse a wrong one, then store the right one."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_INPUT)
    entry.add_to_hass(hass)

    with patch("custom_components.heatzy.config_flow.HeatzyClient") as mock:
        mock.return_value = HeatzyClient
        result = await entry.start_reauth_flow(hass)
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"

        mock.return_value.async_bindings.side_effect = AuthenticationFailed("Login")
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "wrong"}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_auth"}

        mock.return_value.async_bindings.side_effect = None
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "new_password"}
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] == "new_password"

# Heatzy

This a _custom component_ for [Home Assistant](https://www.home-assistant.io/).

![GitHub release](https://img.shields.io/github/release/Cyr-ius/hass-heatzy)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
![downloads](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.heatzy.total)

## Description

[Heatzy](https://heatzy.com/) modules drive electric heaters through their pilot wire
and are controlled from the Heatzy app. This integration connects to your Heatzy
cloud account and brings every module of the account into Home Assistant:

- a climate entity per module, with preset modes (comfort, eco, away...) and
  automatic mode (the module schedule);
- switches to lock the module buttons, and the window and presence modes on
  Pilote Pro;
- number entities to set the boost and vacation durations, and the temperature
  calibration on Glow, Onyx and Inea;
- binary sensors for the cloud connectivity of each module, and presence
  detection on Pilote Pro.

State changes are pushed by the Heatzy cloud over a websocket; the integration
also polls the cloud every minute as a fallback.

## Supported Devices

- Heatzy Pilot 1 & 2 & 3
- Acova Heatzy Elec'Pro
- Glow by Heatzy
- Onyx by Heatzy
- Bloom by Heatzy
- Sauter Orosi
- Pilote Pro

## Installation

1. Install [HACS](https://hacs.xyz/) if it is not already installed.
2. Add this repository in HACS and download the **Heatzy** integration:

   [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=cyr-ius&repository=hass-heatzy&category=integration)

3. Restart Home Assistant.
4. Go to **Settings > Devices & services > Add integration**, search for
   **Heatzy**, and enter your account details:

   [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=heatzy)

### Configuration parameters

| Parameter | Description                                                                |
| --------- | -------------------------------------------------------------------------- |
| Email     | The email address of your Heatzy account (the one used in the Heatzy app). |
| Password  | The password of your Heatzy account.                                       |

The integration has no options. Each Heatzy account can be added once.

## Actions

The actions target Heatzy climate entities.

| Action            | Fields                    | Description                                                                |
| ----------------- | ------------------------- | -------------------------------------------------------------------------- |
| `heatzy.boost`    | `delay`: 1 to 255 minutes | Heat in comfort mode for the given time, then return to the previous mode. |
| `heatzy.vacation` | `delay`: 1 to 255 days    | Keep the heater in frost protection for the given number of days.          |
| `heatzy.presence` | none                      | Enable presence detection mode (Pilote Pro).                               |

Example:

```yaml
action: heatzy.boost
target:
  entity_id: climate.living_room
data:
  delay: 60
```

## Removal

1. Go to **Settings > Devices & services**, select **Heatzy**, open the menu of
   the account entry and select **Delete**.
2. To remove the integration files as well, open HACS, select **Heatzy** and
   choose **Remove**, then restart Home Assistant.

Removing the integration does not change anything on the Heatzy modules or in
your Heatzy account.

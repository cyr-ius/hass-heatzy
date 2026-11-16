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

## Supported functions

| Model (family)                                                                  | Presets                                                   | Temperatures                                 | Switches                    | Other entities                     |
| ------------------------------------------------------------------------------- | --------------------------------------------------------- | -------------------------------------------- | --------------------------- | ---------------------------------- |
| Heatzy Pilote 1 (`PILOTE_V1`)                                                   | comfort, eco, away                                        | —                                            | —                           | —                                  |
| Heatzy Pilote 2, Elec'Pro (`PILOTE_V2`), Pilote SoC, Elec'Pro SoC (`PILOTE_V3`) | comfort, eco, away, boost, vacation                       | —                                            | lock                        | boost and vacation durations       |
| Elec'Pro BLE, Sauter (`PILOTE_V4`)                                              | comfort, comfort 1, comfort 2, eco, away, boost, vacation | —                                            | lock                        | boost and vacation durations       |
| Glow, Onyx, Inea, Glow BLU (`GLOW`)                                             | comfort, comfort 1, comfort 2, eco, away, boost, vacation | current, comfort and eco setpoints           | lock                        | durations, temperature calibration |
| Bloom (`BLOOM`)                                                                 | comfort, comfort 1, comfort 2, eco, away, boost, vacation | current, comfort and eco setpoints           | lock                        | boost and vacation durations       |
| Pilote Pro (`PILOTE_PRO_V1`)                                                    | comfort, comfort 1, comfort 2, eco, away, boost, vacation | current, comfort and eco setpoints, humidity | lock, window, presence mode | durations, presence detection      |

Every module also has a **connectivity** binary sensor, and a climate entity with
the `heat`, `off` and `auto` (module schedule) modes.

## Data updates

The Heatzy cloud pushes every change over a websocket. Every minute, the
integration also reads the cloud API when the websocket has no recent data, and
every 30 minutes it reads the full list of modules of the account: a module
added to the account then appears without reloading, and a module removed from
the account is removed from Home Assistant.

## Use cases

- Switch the whole house to eco at night or when everybody is away, and back to
  comfort in the morning.
- Start a boost when you come home earlier than planned.
- Put the heaters in vacation mode for the length of a trip.
- Get a notification when a module goes offline (connectivity binary sensor).

## Automation examples

Eco when the house is empty:

```yaml
triggers:
  - trigger: state
    entity_id: zone.home
    to: "0"
actions:
  - action: climate.set_preset_mode
    target:
      entity_id: all
    data:
      preset_mode: eco
```

Notify when a module is offline for 10 minutes:

```yaml
triggers:
  - trigger: state
    entity_id: binary_sensor.living_room_connectivity
    to: "off"
    for: "00:10:00"
actions:
  - action: notify.notify
    data:
      message: "The Heatzy module of the living room is offline."
```

## Known limitations

- The integration needs the Heatzy cloud: without internet access, the modules
  cannot be controlled from Home Assistant.
- Heatzy Pilote 1 only supports the comfort, eco and away presets, without
  temperatures, boost or vacation.
- Pilot-wire modules (Pilote 2, 3, Elec'Pro, Sauter) have no temperature sensor:
  the setpoint is the one of the heater.
- Boost and vacation durations go from 1 to 255 (minutes or days).
- The window and presence modes only exist on the Pilote Pro, the temperature
  calibration only on the Glow family.

## Troubleshooting

- **Home Assistant asks to reauthenticate**: the password of the Heatzy account
  changed. Enter the new one; to change it yourself, use **Reconfigure** on the
  integration entry.
- **Entities are unavailable**: check the connectivity binary sensor. If it is
  off, the module is offline in the Heatzy app as well; check its power and Wi-Fi.
- **An action fails with "Command to … failed"**: the Heatzy cloud refused the
  command or the module is offline; try again from the Heatzy app.
- **Report an issue**: download the diagnostics of the integration entry
  (passwords and identifiers are redacted) and attach them to a
  [GitHub issue](https://github.com/cyr-ius/hass-heatzy/issues). If you also
  enable debug logs, check them for tokens or passwords before sharing them.

## Removal

1. Go to **Settings > Devices & services**, select **Heatzy**, open the menu of
   the account entry and select **Delete**.
2. To remove the integration files as well, open HACS, select **Heatzy** and
   choose **Remove**, then restart Home Assistant.

Removing the integration does not change anything on the Heatzy modules or in
your Heatzy account.

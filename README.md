# Crestron TSW for Home Assistant

A local-push Home Assistant custom integration that replaces a separate Crestron
control processor or MQTT bridge for a TSW-750. Home Assistant listens for the
panel's native CIP connection and exposes its joins as named event entities and
device automation triggers.

## Installation with HACS

1. In HACS, open **Custom repositories**.
2. Add `https://github.com/Jugrnot/home-assistant-crestron-tsw` as an
   **Integration** repository.
3. Install **Crestron TSW** and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration** and select
   **Crestron TSW**.
5. Keep the defaults: listen address `0.0.0.0`, port `41794`, and IP ID `64`
   (Crestron `40` hex).

## Point the panel at Home Assistant

Open the TSW-750 setup screen by pressing side keys 1, 2, 3, 4 twice within five
seconds. In **IP Table Setup**, change IP ID `40` to the IP address of the Home
Assistant host. The panel initiates the TCP connection; do not enter the panel's
own IP address in the integration.

Stop the old laptop bridge before changing the IP table. Only one processor
endpoint should be active.

## Using button presses

The integration creates event entities and device triggers for:

| Join | Button |
|---:|---|
| 101 | Watch TV |
| 102 | Apple TV |
| 103 | System On |
| 104 | Display / Input |
| 105 | All Off |
| 106 | Game Console |
| 107 | Volume Up |
| 108 | Volume Down |
| 109 | Mute |
| 110 | Music |
| 111 | Play / Pause |

In an automation, choose **Device**, select the Crestron TSW-750, and choose the
named button trigger. Raw events are also fired as `crestron_tsw_join` and
`crestron_tsw_button`.

Example YAML:

```yaml
triggers:
  - trigger: event
    event_type: crestron_tsw_button
    event_data:
      join: 102
      pressed: true
actions:
  - action: media_player.select_source
    target:
      entity_id: media_player.living_room_receiver
    data:
      source: Apple TV
```

## Feedback to the panel

Three actions are provided. Values are cached and replayed when the panel
reconnects:

- `crestron_tsw.set_digital_feedback`
- `crestron_tsw.set_analog_feedback`
- `crestron_tsw.set_serial_feedback`

## Network note

The TSW-750 runs legacy embedded firmware. Keep it on an isolated IoT VLAN and
allow TCP 41794 only between the panel and Home Assistant.

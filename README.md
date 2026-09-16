# OpenAir

**Native Max For Live GUIs for Airwindows Plugins**

OpenAir brings the bare-metal C++ DSP of [Airwindows](https://www.airwindows.com/) directly into the Ableton Live and Max/MSP ecosystem as native Max for Live (M4L) devices with custom-built user interfaces, parameter controls, gain staging, and metering.

Authored by **macchinette** • Current Pre-release: `v0.0.1`

---

## Included Devices (v0.0.1 Pre-Release)

| Device | DSP Object | Description |
|---|---|---|
| **OA_Air4.amxd** | `airfx.air4~` | High-frequency air band exciter and presence shaper. |
| **OA_BassKit.amxd** | `airfx.basskit~` | Sub-bass synthesis and low-end reinforcement with sub & voicing controls. |
| **OA_clipsoftly.amxd** | `airfx.clipsoftly~` | Transparent analog-style soft-clipping saturation limiter. |
| **OA_console0channel.amxd** | `airfx.console0channel~` | Console0 nonlinear channel-encoding strip (insert on individual tracks). |
| **OA_console0bus.amxd** | `airfx.console0buss~` | Console0 complementary decoding summing bus (insert on group/master). |
| **OA_distance3.amxd** | `airfx.distance3~` | Psychoacoustic depth and spatial distance placement. |
| **OA_galactic.amxd** | `airfx.galactic~` | Lush, expansive ambient reverb with detune, brightness, and replace controls. |
| **OA_purestconsolechannel2.amxd** | `airfx.purestconsole2channel~` | PurestConsole2 channel-encoding stage for pristine analog summing. |
| **OA_purestconsolebus.amxd** | `airfx.purestconsole2buss~` | PurestConsole2 summing bus decode stage. |
| **OA_totape8.amxd** | `airfx.totape8~` | Flagship analog tape emulation with head bump frequency, bias, flutter, and tilt. |

---

## Installation Guide

OpenAir is distributed as a **Standard Max Package**. Once placed in your Max Packages folder, Ableton Live and Max/MSP will automatically index the devices and native C++ externals.

### Step 1: Install the Package

Extract the `OpenAir` folder from the download `.zip` and place it into your Max Packages directory:

- **macOS**:
  ```text
  ~/Documents/Max 8/Packages/OpenAir
  ```
  *(or `~/Documents/Max 9/Packages/OpenAir` if using Max 9)*

- **Windows**:
  ```text
  Documents\Max 8\Packages\OpenAir
  ```
  *(or `Documents\Max 9\Packages\OpenAir` if using Max 9)*

*Alternatively, you can also place or drag the `.amxd` devices from `patchers/` directly into your Ableton Live User Library (`User Library/Presets/Audio Effects/Max Audio Effect/`).*

---

### Step 2: macOS Security Notice (Gatekeeper / Quarantine)

Because the native `.mxo` externals are downloaded from the web (e.g. Patreon) and are not notarized by Apple's automated cloud service, macOS Gatekeeper may block them from loading by default.

To authorize OpenAir on macOS, open the **Terminal** app and run this one-line command:

```bash
xattr -cr ~/Documents/Max\ 8/Packages/OpenAir
```
*(If using Max 9, replace `Max\ 8` with `Max\ 9`)*

Alternatively, if prompted by macOS when loading a device, open **System Settings -> Privacy & Security**, scroll down to the Security section, and click **"Allow Anyway"** for the blocked external.

---

## Console Workflow Guide

Airwindows console emulations (`Console0` and `PurestConsole2`) operate in complementary encode/decode pairs to recreate the sound of large-format analog mixing consoles:

1. **Channel Devices** (`OA_console0channel.amxd` or `OA_purestconsolechannel2.amxd`):
   - Place as the **final insert effect** on every individual audio track.
2. **Buss Devices** (`OA_console0bus.amxd` or `OA_purestconsolebus.amxd`):
   - Place as the **first insert effect** on your master or subgroup bus.
3. **Gain Staging**:
   - Keep your track volume faders around 0 dB (unity gain) for accurate mathematical decoding. Use the input/drive controls on the channel devices to balance levels into the summing bus.

---

## Requirements
- **macOS**: macOS 10.15 Catalina or newer (native Universal binary: Apple Silicon M1/M2/M3/M4 & Intel).
- **Windows**: Windows 10 or 11 (64-bit).
- **Host**: Ableton Live 10, 11, or 12 with Max for Live (Max 8 or Max 9).

---

## Credits & Acknowledgements
- **DSP Algorithms**: Ported from the incredible open-source DSP work of Chris Johnson ([Airwindows](https://www.airwindows.com/)).
- **Max for Live Ports & GUIs**: Authored by **macchinette**.

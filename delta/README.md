# OA_Delta — Comparative Delta Analyzer & Audition Device (`macchinette`)

**OA_Delta** (`delta/OA_Delta.amxd`) is a native Max for Live (`MaxMSP` binary `.amxd`) diagnostic audio effect (`248 x 169 px`, 100% vanilla M4L objects, zero JS) that compares an upstream/external reference tap (**Tap**) against the device's own insert position, displaying a real-time **EQ-Eight-balanced Spectrum** comparison with full dynamic Ableton theme coloring (`themecolor.*`) and one-click **Delta (`Δ`)** audition.

> **Version Backups**:
> - `delta/OA_Delta_v0.amxd` (`delta/generate_delta_v0.py`): Preserved `v0` baseline.
> - `delta/OA_Delta.amxd` (`delta/generate_delta.py`): Streamlined single-view Spectrum & Delta Audition layout (`248 x 169 px`) with balanced paddings and dynamic Ableton theme tokens.

---

## Layout, Paddings & Dynamic Ableton Theming (`248 x 169 px`)

- **Symmetric Paddings & Inset Frame**:
  - `6 px` left/right outer margins (`x = 6..242 px`) and symmetric `28 px` top/bottom control bars (`y = 0..28 px` and `y = 141..169 px`).
  - Central spectrum viewport (`x = 6, y = 28, w = 236, h = 113 px`) sits cleanly inside a `1 px` `live_lcd_frame` bezel with `5.5–6.0 px` vertical breathing room from the top dropdowns (`umenu` actual Max 9 height `17.5 px` at `y = 5.0..22.5 px`) and bottom controls (`y = 147.0..163.0 px`).
- **100% Dynamic Ableton Theme Tokens (`saved_attribute_attributes` -> `themecolor.*`)**:
  - Device surface: `live_surface_bg`
  - Labels (`Tap`, `Gain`, `Delay`): `live_control_fg` (`Ableton Sans Small Bold`, `10.0 pt`)
  - Dropdowns (`umenu`) & Numboxes (`live.numbox`): `live_control_bg`, `live_control_fg`, `live_control_text_selection`, `live_focus_frame`, `live_value_arc`
  - Spectrum (`spectroscope~`):
    - Foreground Delta (`Δ`) curve: `live_spectrum_default_color` (with `curvecolor` alias omitted so `fgcolor` dynamic theme binding persists)
    - Background Reference (`Out`) silhouette: `live_spectrum_alternative_color`
    - Grid lines: `live_spectrum_grid_lines`
    - LCD background & frame: `live_lcd_bg` & `live_lcd_frame`
  - Audition toggle (`live.text` + `headphones.svg` with `remapsvgcolors = 1`): `live_control_bg`, `live_lcd_bg`, `live_control_fg_off`, `live_control_fg_on`, `live_lcd_control_fg_alt`

### 1. Top Row (`y = 0..28 px`) — Tap Setter
- **`Tap` Track & Tap-Point Dropdowns** (`y = 5.0 px`):
  - Track selector (`umenu`, `No Input` / Live tracks) and Tap Point selector (`Pre FX` / `Post FX` / `Post Mixer`) driven directly by `live.routing`.
  - Pure-Max 2-click dropdown close controller (`hover` + `mousestate` + `timer` + `delay` + `key` -> `ignoreclick 1/0`) so clicking a second time onto an open dropdown box cleanly dismisses the popup without re-opening it.
  - Selecting any valid track immediately activates the `B - A` phase-cancellation delta chain.

### 2. Center Spectrum (`x = 6, y = 28, w = 236, h = 113 px`) — EQ-Eight-Balanced Analyzer
- **Dual-Layer `spectroscope~`**:
  - Foreground curve (`live_spectrum_default_color`) shows the real-time **Delta (`Δ`)** signal; background silhouette (`live_spectrum_alternative_color`) shows the **Reference (`Out`)** signal.
- **Midrange-Focused Spectral Balance**:
  - Sample-rate-independent 2-stage `onepole~` pre-emphasis tilt network on the visual analyzer feeds tames low-end dominance (`< 260 Hz`) and tilts mids/highs (`+4.5 dB/oct` around `500 Hz – 4 kHz`).
  - Cropped 3-decade logarithmic viewport (`bpatcher`, `x0 = 0.28`) removes `spectroscope~`'s dead `0..25 Hz` first decade so `500 Hz – 1 kHz` sits in the center of the graph like Ableton EQ Eight.

### 3. Bottom Row (`y = 141..169 px`) — Audition, Gain & Delay
- **`[ 🎧 ]` Audition Toggle** (`y = 147.0 px, h = 16.0 px`):
  - **OFF**: Normal track audio flows through `plugout~ 1/2` untouched while the spectrum analyzes `Δ`.
  - **ON**: Solos the phase-cancelled $\Delta = \text{Device Pos} - \text{Tap}$ signal through the output.
- **`Gain`**: Draggable dB boost (`0.0` to `+36.0 dB`) feeding a safety peak limiter (`omx.peaklim~`).
- **`Delay`**: Millisecond delay alignment (`0.00` to `50.0 ms`, `mstosamps~` -> `delay~`) applied to the Tap signal.

---

## Rebuilding from Source

```powershell
python delta/generate_delta.py
```

# OA_Delta — Comparative Delta Analyzer & Audition Device (`macchinette`)

**OA_Delta** (`delta/OA_Delta.amxd`) is a native Max for Live (`MaxMSP` binary `.amxd`) horizontal diagnostic audio effect (`320 x 169 px`) that compares an upstream/external reference tap (**TAP A**) against the device's own insert position, displaying real-time **Spectrum**, **Phase**, and **Level** comparisons and allowing one-click **Delta (`Δ`)** audition.

> **Version Backups**:
> - `delta/OA_Delta_v0.amxd` (`delta/generate_delta_v0.py`): Preserved `v0` baseline with the 3-tab Setup/Spectrum/Phase layout.
> - `delta/OA_Delta.amxd` (`delta/generate_delta.py`): Current horizontal visualizer-first layout with expandable `Tap A` side panel, lit/greyed `[ Δ ]` audition icon, bottom control strip, and smart `Levels` comparison tab.

---

## Layout & Workflow (`320 x 169 px` Horizontal Plugin)

### 1. Expandable `Tap A` Panel (`[ ▸ Tap A / ▾ Tap A ]`)
- Located in the top-left header in standard Ableton Live sidechain-panel style.
- **Expanded (`▾ Tap A`)**: Reveals the **`AUDIO FROM (A)`** track selector and **`TAP POINT`** (`Pre FX / Post FX / Post Mixer`) dropdown on the left while keeping the active visualizer visible alongside it.
- **Collapsed (`▸ Tap A`)**: Hides the side panel and **dynamically stretches** the active visualizer (`Spectrum`, `Phase`, or `Levels`) across the full `320 px` width of the device.
- **Automatic Spectrum Activation**: As soon as a valid track is selected in **Tap A**, the `B - A` subtraction chain activates and starts feeding the **Spectrum** analyzer immediately.

### 2. Three Visualizer Tabs (`[ Spectrum | Phase | Levels ]`)
- **`Spectrum` (Default Starting View)**:
  - Horizontal log-frequency `spectroscope~` with a compact header source switch **`[ Δ | A | B ]`**.
- **`Phase`**:
  - XY Lissajous Goniometer (`scope~`) + real-time **Phase Correlation (`-1.0` to `+1.0`)** readout for the Delta signal.
- **`Levels` (Smart Level Comparison)**:
  - Side-by-side stereo meters and dB readouts for **`TAP A`**, **`OUT`** (device position), and **`DELTA Δ`** (null depth in dB), plus a real-time **`GAIN DIFF`** (`Out - Tap A` in dB) indicator.

### 3. Persistent Bottom Control Strip (Replaces Bottom Meters)
- **`[ Δ ]` Audition Icon**:
  - **Greyed out (`OFF`)**: Normal track audio flows through `plugout~ 1/2` untouched while visualizers analyze `Δ`.
  - **Lit (`ON`)**: Solos the carved $\Delta = \text{Device Pos} - \text{Tap A}$ signal through the output.
- **`GAIN`**: Draggable dB boost (`0.0` to `+36.0 dB`) feeding a brickwall safety limiter (`omx.peaklim~`) for inspecting low-level artifacts.
- **`DELAY`**: Sample-accurate alignment (`-10`, `-1`, draggable `0..2048 smp`, `+1`, `+10`) applied to **Tap A** while watching the Spectrum or Null Depth in real time.

---

## Rebuilding from Source

```powershell
python delta/generate_delta.py
```

# OpenAir dEQ Eight (`dEQ Eight.amxd`)

**Author**: macchinette  
**Version**: v1.0.0 (Production Candidate)  
**Format**: Max for Live Audio Effect (`.amxd`)  
**Target Host**: Ableton Live 11 / 12 (Windows & macOS)

---

## 1. Overview

**dEQ Eight** is a production-grade 8-band dynamic parametric equalizer for Ableton Live. It bridges the native workflow and aesthetics of **Ableton EQ Eight** with the surgical power of modern dynamic equalizers like **FabFilter Pro-Q 3**, powered by **Andrew Simper's (Cytomic) 64-bit Zero-Delay Feedback (ZDF) State-Variable Filter** topology.

Every band can function as a traditional static filter, a dynamic compressor (ducking/taming frequencies on transients), or an upward/downward dynamic expander. Sidechain triggers can be evaluated internally or routed from any external Ableton track with dedicated tap-point selection (`Pre FX`, `Post FX`, `Post Mixer`).

---

## 2. Key Features & Innovations

### 1:1 Ableton EQ Eight Aesthetic & Geometric Alignment
- **Logarithmic Frequency Grid**: Spans **12 Hz to 22 kHz**, aligning the `100 Hz`, `1 kHz`, and `10 kHz` grid lines with Ableton EQ Eight. The `100 Hz` grid line falls right behind the 3rd band selector card.
- **Native Typography**: Control titles and labels use **`Ableton Sans Small Bold`**, while numeric readouts and menus use **`Ableton Sans Medium`**, providing clean contrast and readability.
- **Uniform 16 px Box Heights**: All sliders and numeric boxes (`dyn_scale`, `out_gain`, `band_dyndepth`, `band_thresh`, `band_attack`, `band_release`) share an identical 16 px height.
- **Native `live.menu` Dropdowns**: Filter curve selectors utilize native menus with custom vector SVGs (`eq8_*.svg`, 23x11 px), replacing legacy JavaScript popups with native Ableton menus.

### 64-Bit Cytomic ZDF Trapezoidal SVF Engine (`gen~`)
- **Topology-Preserving Transform (TPT)**: Uses bilinear-transformed state-variable integrators with instantaneous zero-delay feedback, completely eliminating zipper noise under audio-rate parameter changes.
- **Nyquist Bandwidth Decramping**: Features $\cos(\omega_0/2)$ compensation across all filters, preserving natural analog bell curves and shelving slopes up to 20 kHz without cramming near the Nyquist limit.
- **8 Filter Shapes**:
  1. `Low Cut 48` (4-pole 48 dB/oct highpass)
  2. `Low Cut 12` (2-pole 12 dB/oct highpass)
  3. `Low Shelf` (bipolar shelving filter with dynamic boost/cut)
  4. `Bell` (peaking parametric bell with dynamic range)
  5. `Notch` (narrow band-reject notch)
  6. `High Shelf` (bipolar high shelf with dynamic boost/cut)
  7. `High Cut 12` (2-pole 12 dB/oct lowpass)
  8. `High Cut 48` (4-pole 48 dB/oct lowpass)

### High-Resolution 4096-Point FFT RTA Spectrum Analyzer
- **Native Real-Time FFT**: Reads 2048 Hann-windowed bins directly from native C++ Max DSP (`fft~ 4096 4096 0` -> `poke~ ---rta_fft`), incurring zero JS processing latency.
- **Peak-Preserving Sub-Bin Interpolation**: Below 450 Hz, sub-bin fractional quadratic interpolation resolves individual low-frequency bass fundamentals and harmonics crisply.
- **Single-Color Dynamic Shading**: Plotted with theme-linked `live_spectrum_default_color` without artificial border lines.

### Dynamic Live 12 Theme Color Reactivity
- **Zero Hardcoded Colors**: Uses dynamic color tokens routed via `live.colors`.
- Automatically responds when changing Live 12 / 11 themes (Default Dark, Light, Mid Dark, Mid Light, Custom skins).
- Graph background (`live_lcd_bg`), scale text (`live_display_scale_text`), filter curves (`live_lcd_control_fg_alt`), band handles (`live_display_handle_one`), and device surface (`live_surface_bg`) update live.

### Dual Expandable Drawers & Dynamic Device Resizing
- **Left Sidechain Drawer (`+154 px`)**: Expands to reveal dual external sidechain routing panels (`Ext. A` and `Ext. B`) with track choosers, tap points, gain trim, and mix controls via `live.routing`.
- **Right Dynamics Drawer (`+136 px`)**: Expands to reveal per-band dynamic parameters: `Dyn Range` (-15 to +15 dB), `Threshold` (-60 to 0 dB), `Attack` (0.1 to 250 ms), `Release` (5 to 1000 ms), and detector source (`Int`, `SC A`, `SC B`).
- Seamless rack resizing from **495 px** up to **785 px** via `live.thisdevice` (`setwidth`), preserving the central EQ graph.

### Robust M4L State Persistence
- All 8 band parameters, dynamics states, UI drawer states, and selections are serialized into a binary/blob state managed by `pattr eq_state`.
- **Zero Reset Bug**: Opening/closing the Max editor or saving/loading Live sets retains the exact state without resetting values.

---

## 3. Directory Contents

```
dynamic eq/v1/
├── dEQ Eight.amxd             # Production Max for Live Audio Effect
├── build_deq_eight.py         # Automated Python build script
├── deq_eight_lom.js           # Native component controller, theme router & state manager
├── deq_eight_ui.js            # 4096-pt FFT RTA analyzer & interactive EQ curve canvas
├── dEQ_HQ_169.mov             # 16:9 High-Quality video presentation asset
├── ableton_*.svg              # 12 Ableton UI vector icons (drawers, solo, RTA, dyn rings)
├── eq8_*.svg                  # 8 Filter curve vector icons (LC48, LC12, LS, Bell, Notch, HS, HC12, HC48)
└── README.md                  # This documentation
```

---

## 4. Rebuilding from Source

To regenerate `dEQ Eight.amxd` and all embedded SVG vector icons:

```bash
cd "dynamic eq/v1"
python build_deq_eight.py
```


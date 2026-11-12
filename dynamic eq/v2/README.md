# OpenAir dEQ Eight (Alpha v0.03 / v2 Development Edition)

**Author**: `macchinette`  
**Devices**: `dEQ Eight dev.amxd` (unfrozen dev) / `dEQ Eight Alpha v0.03.amxd` (frozen single-file release)  
**Folder**: `dynamic eq/v2/`  

---

## 1. Alpha v0.03 Architecture Highlights

### A. True Band-Specific Multiband Dynamics (`Int` Mode)
- **6th-Order (`36 dB/octave`) Stereo ZDF Band Isolator**: When a band's dynamic source is set to **`Int`** (`b_source == 0`), its detector runs 3 cascaded 2-pole Cytomic Trapezoidal SVF stages matched to the band's filter topology:
  - **Low Shelf / High Cut (`types 2, 6, 7`)**: 6th-order ZDF **Low-Pass** (`-3 dB` aligned to `fc`, `0 dB` passband ripple across sub-bass).
  - **Bell / Notch (`types 3, 4`)**: 6th-order ZDF **Band-Pass** (`Q` cascade-compensated via `0.35 + 0.52 * Q` for `>50 dB` sub-bass rejection at 1 decade while preserving surgical high-`Q` accuracy).
  - **High Shelf / Low Cut (`types 5, 0, 1`)**: 6th-order ZDF **High-Pass** (`-3 dB` aligned to `fc`, `0 dB` passband ripple up to Nyquist).
- **Soft-Knee 1:1 Multiband Compressor Gain Computer**: Smooth `3 dB` quadratic knee around `Threshold` driving a `1:1` hyperbolic range saturator (`norm / sqrt(1 + norm^2)`) scaled by `Dyn Range`.

### B. Broadband Signal-Follower External Sidechains (`SC A` / `SC B`)
- When a band's dynamic source is set to **`SC A`** or **`SC B`** (`b_source == 1, 2`), the detector bypasses the band-isolation filter on the external sidechain (`Mix = 100%`) and follows `max(|SC_L|, |SC_R|)` directly across the full spectrum (e.g., a `50 Hz` kick drum cleanly ducks a `2.5 kHz` vocal presence band).
- At intermediate `Mix` values (`0% < Mix < 100%`), `gen~` blends the band-isolated internal level with the broadband external sidechain follower.

### C. Lightweight CPU & De-Bloated Max Patcher
- **Zero-Gain Static Band Bypass**: Enabled Bell/Shelf bands sitting at `0.00 dB` with dynamics off skip per-sample SVF state updates (`0.00%` idle EQ CPU).
- **`History` Dirty-Checking**: Per-sample `tan()`, `cos()`, `exp()`, and `pow()` transcendental calls are eliminated on steady audio frames; coefficients recompute only when smoothed parameters or sample rate change.
- **`mute~`-Gated 4096-Point FFT RTA (`p rta_engine`)**: Turning off the RTA button disables 100% of FFT DSP via `mute~` and pauses `qmetro 33` when no dynamic bands are active.
- **Shared Gain-Reduction Buffer (`buffer~ ---deq_gr`)**: Replaces 8 audio-rate `gen~` outlets + 8 `snapshot~` timers + `pack`, isolating multi-instance memory cleanly via M4L `---` naming.
- **Real-Time Sample Rate Sync (`dspstate~`)**: Synchronizes `deq_eight_ui_dev.js` FFT bin mapping and SVF curves across `44.1 kHz`, `48 kHz`, `88.2 kHz`, `96 kHz`, and `192 kHz`.

---

## 2. Minimal SVG Asset Footprint (`remapsvgcolors = 1`)

All 13 embedded vector icons (`headphones.svg`, `rta_bars.svg`, `dyn_ring.svg`, `tri_closed.svg`, `tri_open.svg`, and `eq8_*.svg`) use pure-black paths dynamically recolored by Max 9's theme engine (`remapsvgcolors = 1`), keeping `dEQ Eight Alpha v0.03.amxd` self-contained and 100% reactive to any Ableton Live 11 / 12 theme.

---

## 3. Directory Contents

```text
dynamic eq/v2/
├── dEQ Eight dev.amxd            # Unfrozen v2 development Max for Live device
├── dEQ Eight Alpha v0.03.amxd    # Frozen single-file production release device
├── build_deq_eight_dev.py        # Automated patcher + frozen collective + zip builder
├── deq_eight_lom_dev.js          # Native UI controller, LOM router & pattr persistence
├── deq_eight_ui_dev.js           # Zero-alloc mgraphics EQ curve + 4096-pt FFT renderer
├── headphones.svg                # Unified headphones vector icon
├── rta_bars.svg                  # Unified RTA bars vector icon
├── dyn_ring.svg                  # Per-band dynamics ring vector icon
├── tri_closed.svg / tri_open.svg # Sidechain drawer disclosure arrows
├── eq8_*.svg                     # 8 filter curve menu icons
└── README.md                     # This document
```

---

## 4. Rebuilding from Source

```bash
python "dynamic eq/v2/build_deq_eight_dev.py"
```

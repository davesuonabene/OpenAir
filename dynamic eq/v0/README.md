# OpenAir Dynamic EQ Eight (`Dynamic_EQ.amxd`)

A standalone, ultra-transparent 8-band Dynamic EQ for Ableton Live / Max for Live (`macchinette`), combining **Ableton EQ Eight's** workflow with **FabFilter Pro-Q 3's** dynamic EQ interaction and **Andrew Simper's (Cytomic) 64-bit Zero-Delay Feedback (ZDF) Trapezoidal SVF** DSP architecture.

## Key Features

### 1. 64-Bit Cytomic ZDF Trapezoidal SVF + Nyquist-Decramped DSP Engine (`gen~`)
- **Zero Zipper Noise Under Fast Audio-Rate Modulation**: Uses Topology-Preserving Transform (TPT) / Zero-Delay Feedback state-variable integrators in 64-bit `gen~` code, allowing sample-accurate dynamic gain modulation without clicks or transient distortion.
- **Nyquist Bandwidth Decramping**: Applies $\cos(\omega_0/2)$ bandwidth compensation so high-frequency bells and shelves ($8\text{–}20\text{ kHz}$) maintain their natural analog skirt width without pinching near Nyquist.
- **All 8 Native EQ Eight Filter Shapes**:
  1. `Low Cut 48` (4-pole 48 dB/oct Highpass)
  2. `Low Cut 12` (2-pole 12 dB/oct Highpass)
  3. `Low Shelf` (Dynamic Low Shelf)
  4. `Bell` (Dynamic Peaking Bell)
  5. `Notch` (Band-Reject)
  6. `High Shelf` (Dynamic High Shelf)
  7. `High Cut 12` (2-pole 12 dB/oct Lowpass)
  8. `High Cut 48` (4-pole 48 dB/oct Lowpass)
- **Multi-Algorithm Ready Architecture**: Structured so future phase/response modes (e.g., Natural Phase allpass matching or Linear Phase) can plug directly into the per-band stage evaluation and graph magnitude renderer.

### 2. Authentic EQ Eight Clone Interface + Width-Extending Per-Band Drawer
- **Base EQ Eight Canvas (`450px × 169px`)**:
  - **Left Strip**: Selected band `ON/OFF`, Filter Shape menu, `Freq` (`10 Hz – 22 kHz`), static `Gain` (`-15 dB to +15 dB`), and `Q` (`0.1 – 18.0`) dials.
  - **Center Interactive Display (`dynamic_eq_ui.js`)**:
    - **Normal Drag on Node `(1..8)`**: Adjusts **Frequency** (X) and **Static Gain** (Y).
    - **Drag Outer Dynamic Ring / Tab (or `Alt/Cmd + Drag` on Node)**: Adjusts **Dynamic Range** (`-15 dB to +15 dB`), shaded Pro-Q style.
    - **Scroll Wheel (or `Shift + Drag`)**: Adjusts **Q**.
    - **Double-Click Node**: Toggles band **On/Off** (or resets dynamic range when double-clicking the dynamic ring).
  - **Bottom Strip**: `1..8` Band Selector tabs.
  - **Right Strip**: **`[DYN >]`** Expand Toggle, **`[Solo Band]`** audition mode, **`[Adapt. Q]`** proportional-Q toggle, **`Scale`** (`0%..200%`), and Output **`Gain`** (`-24..+24 dB`).
- **Width-Extending Per-Band Dynamic & Sidechain Drawer (`+190px -> 640px × 169px`)**:
  - Clicking **`[DYN >]`** dynamically resizes the plugin container in Ableton Live's track rack from `450px` to `640px` via `live.thisdevice` (`setwidth`), without compressing the EQ graph.
  - **Per-Band Dynamic Controls**: `Dyn ON/OFF`, `Range` (`-15..+15 dB`), `Thr` (`-60..0 dB`), `Atk` (`0.1..250 ms`), `Rel` (`5..1000 ms`), and `Trigger` (`[ Int | SC 1 | SC 2 ]`).
  - **Dual External Sidechains (`SC1` & `SC2`)**: Classic Ableton Track & Tap Point (`Pre FX / Post FX / Post Mixer`) choosers, Gain trims, and stereo level meters for two independent external sidechain sources (`In 3/4` and `In 5/6`).

## Rebuilding from Source
```bash
python "dynamic eq/build_dynamic_eq.py"
```

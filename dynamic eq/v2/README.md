# OpenAir dEQ Eight (v2 Development Edition)

**Device**: `dEQ Eight dev.amxd`  
**Folder**: `dynamic eq/v2/`  
**Primary Goal**: Minimize external asset dependencies by leveraging native M4L vector rendering and programmatic SVG recoloring (`remapsvgcolors = 1`).

---

## 1. Asset Reduction Breakdown

In **v1**, 20 external SVG files were required because multiple copies of each icon existed to represent different color states (e.g., `_on` vs `_off`, `_row`, `_full`):

| Icon Function | v1 External Files (20 total) | v2 Approach (13 total) | Reduction |
|---|---|---|---|
| **Dynamics Ring Toggle** | `ableton_dyn_ring_off.svg`<br>`ableton_dyn_ring_on.svg`<br>`ableton_dyn_ring_full.svg` (3 files) | **0 files**. Replaced by native `live.text` circle (`rounded=13.0`, `border=1`). Dynamically recolored in `deq_eight_lom_dev.js` via `bgoncolor` & `bordercolor` messages. | **-3 files** (100% eliminated) |
| **Headphones Icon** | `ableton_headphones.svg`<br>`ableton_headphones_on.svg`<br>`ableton_headphones_row.svg`<br>`ableton_headphones_row_on.svg` (4 files) | **1 file** (`headphones.svg`). Shared across SC Listen and Solo buttons. Automatically recolored by Max via `remapsvgcolors = 1`. | **-3 files** |
| **RTA Bars Icon** | `ableton_rta_bars.svg`<br>`ableton_rta_bars_on.svg` (2 files) | **1 file** (`rta_bars.svg`). Single SVG with `remapsvgcolors = 1`. | **-1 file** |
| **Drawer Arrows** | `ableton_tri_closed.svg`<br>`ableton_tri_open.svg` (2 files) | **2 files** (`tri_closed.svg`, `tri_open.svg`). Standardized with `remapsvgcolors = 1`. | Same (now theme-recolored) |
| **Vertical Sidechain** | `ableton_sidechain_vert.svg` (1 file) | **1 file** (`sidechain_vert.svg`). Standardized with `remapsvgcolors = 1`. | Same (now theme-recolored) |
| **Filter Shape Icons** | 8 files (`eq8_*.svg`) | **8 files** (`eq8_*.svg`). | Same |
| **Total SVGs** | **20 SVG files** | **13 SVG files** | **35% overall reduction** |

---

## 2. Programmatic Recoloring Mechanisms

### A. Native Vector Dynamics Circle (`rounded = 13.0`)
Instead of swapping between three SVG files:
- **OFF State**: Button value = 0. Drawn with transparent background and `live_lcd_frame` border.
- **ON State (Panel Closed)**: Button value = 1. `bgoncolor` is programmatically set to dark teal (`[0.086, 0.227, 0.259, 1.0]`) with cyan border.
- **ON State (Panel Open for Band)**: `bgoncolor` is programmatically set to bright cyan (`THEME_COLORS.control_fg`), producing a solid-lit cyan circle toggle with zero SVG dependencies.

### B. `remapsvgcolors = 1`
All vector SVGs are drawn with `fill="black"` or `stroke="black"`. With `remapsvgcolors = 1`:
- **State 0 (OFF)**: Max paints `black` with `textcolor` (themed to `live_control_fg`).
- **State 1 (ON)**: Max paints `black` with `textoncolor` (themed to `live_control_fg_on` / dark text on bright toggle background).
- Zero hardcoded hex colors; 100% reactive to any Ableton Live 11 / 12 theme.

---

## 3. Directory Contents

```
dynamic eq/v2/
├── dEQ Eight dev.amxd         # New v2 Development Max for Live device
├── build_deq_eight_dev.py     # Automated build script
├── deq_eight_lom_dev.js       # Native LOM & programmatic color manager
├── deq_eight_ui_dev.js        # Graph canvas & FFT analyzer
├── headphones.svg             # Single unified headphones vector icon
├── rta_bars.svg               # Single unified RTA bars vector icon
├── tri_closed.svg             # Drawer closed disclosure arrow
├── tri_open.svg               # Drawer open disclosure arrow
├── sidechain_vert.svg         # Vertical Sidechain text
├── eq8_*.svg                  # 8 Filter curve menu icons
└── README.md                  # This document
```

---

## 4. Rebuilding from Source

```bash
cd "dynamic eq/v2"
python build_deq_eight_dev.py
```


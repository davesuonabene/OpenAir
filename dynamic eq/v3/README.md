# OpenAir dEQ Eight — v3 (`Alpha v0.04`)

**Author:** `macchinette`

`v3` builds on the `v2` (`Alpha v0.03`) 64-bit Cytomic ZDF SVF + 36 dB/oct multiband dynamic engine while preserving `v2/` completely untouched, overhauling the entire UI and RTA spectrum analyzer to match stock **Ableton EQ Eight** with 100% vanilla Max for Live components.

## Highlights in `v3` (`Alpha v0.04`)

- **Pixel-Matched EQ Eight SVG Icons (`24×9`, `usesvgviewbox=1`):**
  - Left-aligned full-bleed filter curves inside closed & open `live.menu` dropdowns: hexagonal 45° flat-cap Bell, full-height Y-fork Low/High Shelves, disjoint curved-funnel Notch, `×4` Low Cut 48, and `4×` High Cut 48 (with flush-right open-top `4`), plus redesigned `headphones.svg` (`16×13`) and 7-bar `rta_bars.svg` (`22×15`).
- **Dynamic Ableton Theme & Zombie Visual States:**
  - Soft ice-blue open dropdown highlight (`live_lcd_control_fg`), unified flat `lcd_bezel_bg` (`live_lcd_frame`) bezel & active tab fusion, right-aligned `Ableton Sans Medium` dB scale labels, transparent unselected band rings (`r = 6.2`) with centered numerals, zombie-grey `0 dB` composite line when all 8 bands are off, zombie dial arcs when the selected band is off, and disabled `Gain` dial on Cut/Notch shapes.
- **Phase-Immune Stereo 4096-Point FFT RTA (`p rta_engine`):**
  - Uses complex `L + jR` stereo FFT conjugate-bin power extraction (`sqrt(|Z_hann[k]|^2 + |Z_hann[4096-k]|^2) / 2048` across all `2048` bins `0..2047`, including DC bin `0`), `370` 1-pixel evaluation points, solid `1.0` fill opacity, and calibrated `-75.2 dB / 66 dB` vertical mapping.

## Rebuilding

```powershell
python "c:\STUDIO\OpenAir\dynamic eq\v3\build_deq_eight_v3.py"
```

Outputs:
- `dynamic eq/v3/dEQ Eight v3 dev.amxd` (unfrozen dev device)
- `dynamic eq/v3/dEQ Eight Alpha v0.04.amxd` (self-contained frozen M4L device)
- `release/dEQ Eight Alpha v0.04.amxd` & `release/dEQ_Eight_Alpha_v0.04.zip`


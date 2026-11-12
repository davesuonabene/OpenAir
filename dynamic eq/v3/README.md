# OpenAir dEQ Eight — v3 (`Alpha v0.04`)

**Author:** `macchinette`

`v3` builds on the `v2` (`Alpha v0.03`) 64-bit Cytomic ZDF SVF + 36 dB/oct multiband dynamic engine while preserving `v2/` completely untouched, overhauling the entire UI and RTA spectrum analyzer to match stock **Ableton EQ Eight** with 100% vanilla Max for Live components.

## Highlights in `v3` (`Alpha v0.04`)

- **Pixel-Matched EQ Eight SVG Icons (`24×9`, `usesvgviewbox=1`):**
  - Left-aligned full-bleed filter curves inside closed & open `live.menu` dropdowns: hexagonal 45° flat-cap Bell, full-height Y-fork Low/High Shelves, disjoint curved-funnel Notch, `×4` Low Cut 48, and `4×` High Cut 48 (with flush-right open-top `4`), plus redesigned `headphones.svg` (`16×13`) and 7-bar `rta_bars.svg` (`22×15`).
- **2-Click Native Dropdown Open/Close Toggle Guard:**
  - Uses `[hover]` + `[mousestate]` + `key 27` + `ignoreclick` gating across all 12 `live.menu` boxes (`band_type_menu_0..7` and sidechain routing menus) so repeated clicks on the same closed dropdown cleanly cycle `Open -> Close -> Open -> Close` on Windows without altering button visuals.
- **Dynamic Ableton Theme & Zombie Visual States:**
  - Soft ice-blue open dropdown highlight (`live_lcd_control_fg`), unified flat `lcd_bezel_bg` (`live_lcd_frame`) bezel & active tab fusion, right-aligned `Ableton Sans Medium` dB scale labels, transparent unselected band rings (`r = 6.2`) with cached numeral centering, zombie-grey `0 dB` composite line when all 8 bands are off, zombie dial arcs when the selected band is off, and disabled `Gain` dial on Cut/Notch shapes.
- **Lightweight Phase-Immune Stereo 4096-Point FFT RTA (`p rta_engine`):**
  - Complex `L + jR` stereo FFT conjugate-bin power extraction in `gen~` with **zero audio-thread `sqrt()` calls** (`buffer~ ---rta_fft @samps 2049` with `frame_seq` gating so JS only reads new FFT frames at `~11.7 Hz`), density-adaptive `240`-segment grid (`~1.13 px` across mids/highs, `~2.6 px` across cubic sub-bass), dirty-cached composite EQ curves, `25 fps` UI ballistics, and calibrated `-75.2 dB / 66 dB` vertical mapping.

## Rebuilding

```powershell
python "c:\STUDIO\OpenAir\dynamic eq\v3\build_deq_eight_v3.py"
```

Outputs:
- `dynamic eq/v3/dEQ Eight v3 dev.amxd` (unfrozen dev device)
- `dynamic eq/v3/dEQ Eight Alpha v0.04.amxd` (self-contained frozen M4L device)
- `release/dEQ Eight Alpha v0.04.amxd` & `release/dEQ_Eight_Alpha_v0.04.zip`

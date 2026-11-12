#!/usr/bin/env python3
"""
OpenAir Cultural & Diagnostic Tools — OA_MultibandDifference Generator
Author: macchinette

Multiband Spectral Excess & Reference Difference Analyzer (`OA_MultibandDifference.amxd`):
- Canonical `No Input` Detection via `live.routing` Outlet 3 (`route <none>`) + `umenu` Outlet 1 (`route "No Input"`):
  * In Ableton Live's `live.routing`, `"No Input"` is the LAST item in `available_routing_types`
    (so its integer index is `N - 1 > 0`, NOT `0`). Detecting `<none>` on Outlet 3 (`available_routing_channels`)
    reliably sets `TapActive = 0` when `"No Input"` is selected and `TapActive = 1` when a Track is selected.
- Dual Audition / Analysis Modes on the Bottom-Left:
  1. `[🎧]` (Headphones — `AuditionDelta`):
     Pure time-domain Reference/Delta mode (`Track - Reference`). When `Tap` is `No Input`,
     auditions the Track against the calibrated stereo Pink/White Noise reference bed.
  2. `[|||]` (Multiband Excess — `AuditionMB`):
     9-Band Octave Filterbank (`62.5 Hz .. 14 kHz`, `svf~ <fc> 0.25`) Spectral Excess isolator.
     - In Noise Reference Mode (`Tap == No Input`): compares each octave band's envelope E_B,k(t)
       against a rock-steady analytical -3 dB/octave Pink Noise ceiling (equal energy per octave band,
       `T_k = 0.18 * dbtoa(Ref)`) or White Noise ceiling (`+3 dB/oct`, `0.18 * 1.4142**(k-4) * dbtoa(Ref)`).
     - In Track Tap Mode (`Tap > 0`): compares E_B,k(t) against the live octave-band envelope E_A,k(t)
       of the tapped reference track.
     - Passes ONLY the excess energy above the reference threshold:
         G_k(t) = clip(E_B,k(t) - E_A,k(t), 0, 10) / (E_B,k(t) + 0.0001)
       Bands at or below the Pink Noise ceiling are completely muted (G_k = 0), so the foreground
       spectrum curve and `[|||]` Audition cleanly isolate only the bands exceeding the Pink Noise floor.
"""

import json
import struct
from pathlib import Path

# Fallback RGBA values (overridden live by Ableton's theme engine via `saved_attribute_attributes`)
SURFACE_BG     = [0.204, 0.184, 0.247, 1.0]  # live_surface_bg
LCD_BG         = [0.078, 0.075, 0.102, 1.0]  # live_lcd_bg
LCD_FRAME      = [0.278, 0.255, 0.329, 1.0]  # live_lcd_frame
CONTROL_BG     = [0.106, 0.094, 0.129, 1.0]  # live_control_bg / live_control_text_bg
CONTROL_BORDER = [0.067, 0.063, 0.086, 1.0]  # live_contrast_frame
VALUE_BAR      = [0.000, 0.443, 0.498, 1.0]  # live_value_bar
ACTIVE_CYAN    = [0.224, 0.824, 0.894, 1.0]  # live_lcd_control_fg_alt
TEXT_MAIN      = [0.827, 0.804, 0.843, 1.0]  # live_control_fg
TEXT_ON        = [0.080, 0.070, 0.100, 1.0]  # live_control_fg_on
SCALE_TEXT     = [0.540, 0.520, 0.580, 1.0]  # live_display_scale_text
SPEC_DEFAULT   = [0.333, 0.314, 0.404, 1.0]  # live_spectrum_default_color
SPEC_ALT       = [0.290, 0.631, 1.000, 1.0]  # live_spectrum_alternative_color
SPEC_GRID      = [0.624, 0.624, 0.624, 0.33] # live_spectrum_grid_lines
TRANSPARENT    = [0.000, 0.000, 0.000, 0.0]

DEV_W  = 248.0
DEV_H  = 169.0
PAD_X  = 6.0
SPEC_X = PAD_X                  # 6.0 px
SPEC_W = DEV_W - 2.0 * PAD_X    # 236.0 px (right edge = 242.0 px)
SPEC_Y = 28.0                   # 5.5 px breathing room below top dropdowns
SPEC_H = 113.0                  # y = 28.0 .. 141.0 (6.0 px breathing room above bottom controls)

OCTAVE_BANDS = [62.5, 125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0, 14000.0]


def tc(token: str) -> dict:
    """Helper returning a Max 9 dynamic theme color expression dictionary."""
    return {"expression": f"themecolor.{token}"}


def write_svg_assets(out_dir: Path):
    """Writes pure-black vector SVG templates dynamically recolored by Max via remapsvgcolors=1."""
    headphones_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 14" width="16" height="14">
  <path d="M2.75 7.5A5.25 5.25 0 0 1 13.25 7.5H11.75A3.75 3.75 0 0 0 4.25 7.5H2.75Z" fill="black"/>
  <rect x="2.0" y="6.8" width="2.4" height="4.5" rx="1.0" fill="black"/>
  <rect x="11.6" y="6.8" width="2.4" height="4.5" rx="1.0" fill="black"/>
</svg>"""
    multiband_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 14" width="16" height="14">
  <rect x="1.8" y="6.5" width="2.2" height="5.5" rx="0.8" fill="black"/>
  <rect x="5.2" y="2.2" width="2.2" height="9.8" rx="0.8" fill="black"/>
  <rect x="8.6" y="4.5" width="2.2" height="7.5" rx="0.8" fill="black"/>
  <rect x="12.0" y="3.2" width="2.2" height="8.8" rx="0.8" fill="black"/>
</svg>"""
    (out_dir / "headphones.svg").write_text(headphones_svg, encoding="utf-8")
    (out_dir / "multiband.svg").write_text(multiband_svg, encoding="utf-8")


def build_spectrum_bpatcher() -> dict:
    """
    Builds the embedded `bpatcher` viewport (236 x 113 px) for the dual-layer `spectroscope~`.
    """
    x0 = 0.28
    full_w = round(SPEC_W / (1.0 - x0), 1)      # 327.8 px
    shift_x = round(-x0 * full_w, 1)            # -91.8 px

    sub_boxes = [
        {
            "box": {
                "id": "obj-in-delta",
                "maxclass": "inlet",
                "numinlets": 0,
                "numoutlets": 1,
                "outlettype": ["signal"],
                "patching_rect": [30.0, 15.0, 30.0, 30.0],
                "comment": "Tilted Difference Signal"
            }
        },
        {
            "box": {
                "id": "obj-in-ref",
                "maxclass": "inlet",
                "numinlets": 0,
                "numoutlets": 1,
                "outlettype": ["signal"],
                "patching_rect": [120.0, 15.0, 30.0, 30.0],
                "comment": "Tilted Track Signal"
            }
        },
        # Foreground Primary Spectrum (Difference — Dynamic `live_spectrum_alternative_color`, Transparent BG)
        {
            "box": {
                "id": "obj-spectroscope",
                "maxclass": "spectroscope~",
                "varname": "p0_spectroscope",
                "numinlets": 2,
                "numoutlets": 1,
                "outlettype": [""],
                "patching_rect": [30.0, 65.0, full_w, SPEC_H],
                "presentation": 1,
                "presentation_rect": [shift_x, 0.0, full_w, SPEC_H],
                "bgcolor": TRANSPARENT,
                "fgcolor": SPEC_ALT,
                "markercolor": TRANSPARENT,
                "border": 0,
                "rounded": 0,
                "domain": [0.0, 20000.0],
                "range": [0.0, 1.0],
                "logfreq": 1,
                "logamp": 1,
                "interval": 40,
                "ignoreclick": 1,
                "saved_attribute_attributes": {
                    "fgcolor": tc("live_spectrum_alternative_color")
                }
            }
        },
        # Background Reference Spectrum (Track — Dynamic `live_spectrum_default_color`, `live_lcd_bg`, `live_spectrum_grid_lines`)
        {
            "box": {
                "id": "obj-spec-ref",
                "maxclass": "spectroscope~",
                "varname": "p0_spec_ref",
                "numinlets": 2,
                "numoutlets": 1,
                "outlettype": [""],
                "patching_rect": [30.0, 205.0, full_w, SPEC_H],
                "presentation": 1,
                "presentation_rect": [shift_x, 0.0, full_w, SPEC_H],
                "bgcolor": LCD_BG,
                "fgcolor": SPEC_DEFAULT,
                "markercolor": SPEC_GRID,
                "border": 0,
                "rounded": 0,
                "domain": [0.0, 20000.0],
                "range": [0.0, 1.0],
                "logfreq": 1,
                "logamp": 1,
                "interval": 40,
                "ignoreclick": 1,
                "saved_attribute_attributes": {
                    "bgcolor": tc("live_lcd_bg"),
                    "fgcolor": tc("live_spectrum_default_color"),
                    "markercolor": tc("live_spectrum_grid_lines")
                }
            }
        }
    ]

    sub_lines = [
        {"patchline": {"source": ["obj-in-delta", 0], "destination": ["obj-spectroscope", 0]}},
        {"patchline": {"source": ["obj-in-ref", 0],   "destination": ["obj-spec-ref", 0]}},
    ]

    return {
        "fileversion": 1,
        "appversion": {
            "major": 9,
            "minor": 0,
            "revision": 0,
            "architecture": "x64",
            "modernui": 1
        },
        "classnamespace": "box",
        "rect": [100.0, 100.0, 420.0, 360.0],
        "bglocked": 0,
        "openinpresentation": 1,
        "default_fontsize": 10.0,
        "default_fontface": 0,
        "default_fontname": "Arial",
        "gridonopen": 1,
        "gridsize": [15.0, 15.0],
        "gridsnaponopen": 1,
        "objectsnaponopen": 1,
        "statusbarvisible": 2,
        "toolbarvisible": 1,
        "style": "",
        "subpatcher_template": "",
        "assistshowspatchername": 0,
        "boxes": sub_boxes,
        "lines": sub_lines,
        "autosave": 0
    }


def build_patcher() -> dict:
    boxes = []
    lines = []

    def add_box(box_dict):
        boxes.append({"box": box_dict})

    def add_line(src_id, src_out, dst_id, dst_in):
        lines.append({
            "patchline": {
                "destination": [dst_id, dst_in],
                "source": [src_id, src_out]
            }
        })

    # =========================================================================
    # 1. TOP BAR ABOVE SPECTRUM (y = 0..28 px, Controls at y = 5.0, x = 6..242)
    # =========================================================================
    add_box({
        "id": "obj-lbl-top-tap",
        "maxclass": "live.comment",
        "varname": "lbl_top_tap",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [370.0, 210.0, 26.0, 15.0],
        "presentation": 1,
        "presentation_rect": [6.0, 5.5, 26.0, 15.0],
        "text": "Tap",
        "fontname": "Ableton Sans Small Bold",
        "fontsize": 10.0,
        "fontface": 1,
        "textcolor": TEXT_MAIN,
        "ignoreclick": 1,
        "saved_attribute_attributes": {
            "textcolor": tc("live_control_fg")
        }
    })

    add_box({
        "id": "obj-ui-menu-track-a",
        "maxclass": "umenu",
        "varname": "tap_track_menu",
        "numinlets": 1,
        "numoutlets": 3,
        "outlettype": ["int", "", ""],
        "parameter_enable": 0,
        "items": ["No Input"],
        "patching_rect": [450.0, 210.0, 101.0, 16.0],
        "presentation": 1,
        "presentation_rect": [34.0, 5.0, 101.0, 16.0],
        "bgcolor": CONTROL_BG,
        "bgfillcolor": {
            "type": "color",
            "color": CONTROL_BG,
            "color1": CONTROL_BG,
            "color2": CONTROL_BG
        },
        "framecolor": CONTROL_BORDER,
        "textcolor": TEXT_MAIN,
        "fontname": "Ableton Sans Medium",
        "fontsize": 9.5,
        "fontface": 0,
        "saved_attribute_attributes": {
            "bgfillcolor": tc("live_control_text_bg"),
            "framecolor": tc("live_contrast_frame"),
            "textcolor": tc("live_control_fg")
        }
    })

    add_box({
        "id": "obj-ui-menu-chan-a",
        "maxclass": "umenu",
        "varname": "tap_chan_menu",
        "numinlets": 1,
        "numoutlets": 3,
        "outlettype": ["int", "", ""],
        "parameter_enable": 0,
        "items": ["Pink Noise", ",", "White Noise", ",", "Off"],
        "patching_rect": [565.0, 210.0, 101.0, 16.0],
        "presentation": 1,
        "presentation_rect": [141.0, 5.0, 101.0, 16.0],
        "bgcolor": CONTROL_BG,
        "bgfillcolor": {
            "type": "color",
            "color": CONTROL_BG,
            "color1": CONTROL_BG,
            "color2": CONTROL_BG
        },
        "framecolor": CONTROL_BORDER,
        "textcolor": TEXT_MAIN,
        "fontname": "Ableton Sans Medium",
        "fontsize": 9.5,
        "fontface": 0,
        "saved_attribute_attributes": {
            "bgfillcolor": tc("live_control_text_bg"),
            "framecolor": tc("live_contrast_frame"),
            "textcolor": tc("live_control_fg")
        }
    })

    # =========================================================================
    # 2. CENTER SPECTRUM ANALYZER (x = 6..242, y = 28..141, 236 x 113 px)
    # =========================================================================
    freq_markers = [
        ("100", 0.2042),
        ("500", 0.4444),
        ("1k",  0.5486),
        ("5k",  0.7913),
        ("10k", 0.8956),
    ]
    for lbl_txt, u_pos in freq_markers:
        px = round(SPEC_X + u_pos * SPEC_W - 12.0, 1)
        add_box({
            "id": f"obj-spec-f-{lbl_txt}",
            "maxclass": "live.comment",
            "varname": f"p0_freq_{lbl_txt}",
            "numinlets": 1,
            "numoutlets": 0,
            "patching_rect": [550.0, 520.0, 24.0, 12.0],
            "presentation": 1,
            "presentation_rect": [px, SPEC_Y + SPEC_H - 14.0, 24.0, 12.0],
            "text": lbl_txt,
            "fontsize": 8.0,
            "fontname": "Ableton Sans Small Bold",
            "fontface": 1,
            "textcolor": SCALE_TEXT,
            "textjustification": 1,
            "ignoreclick": 1,
            "saved_attribute_attributes": {
                "textcolor": tc("live_display_scale_text")
            }
        })

    db_markers = [
        ("0",   SPEC_Y + 3.0),
        ("-18", SPEC_Y + 39.0),
        ("-36", SPEC_Y + 75.0),
    ]
    for idx_db, (db_txt, py) in enumerate(db_markers):
        add_box({
            "id": f"obj-spec-db-{idx_db}",
            "maxclass": "live.comment",
            "varname": f"p0_db_{idx_db}",
            "numinlets": 1,
            "numoutlets": 0,
            "patching_rect": [585.0, 520.0 + idx_db * 15.0, 22.0, 12.0],
            "presentation": 1,
            "presentation_rect": [SPEC_X + SPEC_W - 25.0, py, 22.0, 12.0],
            "text": db_txt,
            "fontsize": 8.0,
            "fontname": "Ableton Sans Small Bold",
            "fontface": 1,
            "textcolor": SCALE_TEXT,
            "textjustification": 2,
            "ignoreclick": 1,
            "saved_attribute_attributes": {
                "textcolor": tc("live_display_scale_text")
            }
        })

    add_box({
        "id": "obj-spec-border",
        "maxclass": "panel",
        "mode": 0,
        "bgcolor": TRANSPARENT,
        "border": 1,
        "bordercolor": LCD_FRAME,
        "rounded": 0,
        "ignoreclick": 1,
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [550.0, 370.0, SPEC_W, SPEC_H],
        "presentation": 1,
        "presentation_rect": [SPEC_X, SPEC_Y, SPEC_W, SPEC_H],
        "saved_attribute_attributes": {
            "bordercolor": tc("live_lcd_frame")
        }
    })

    add_box({
        "id": "obj-spec-view",
        "maxclass": "bpatcher",
        "embed": 1,
        "bgmode": 0,
        "border": 0,
        "clickthrough": 1,
        "enablehscroll": 0,
        "enablevscroll": 0,
        "lockeddragscroll": 0,
        "offset": [0.0, 0.0],
        "numinlets": 2,
        "numoutlets": 0,
        "patching_rect": [550.0, 380.0, SPEC_W, SPEC_H],
        "presentation": 1,
        "presentation_rect": [SPEC_X, SPEC_Y, SPEC_W, SPEC_H],
        "patcher": build_spectrum_bpatcher()
    })

    # =========================================================================
    # 3. BOTTOM BAR (y = 141..169 px, Controls at y = 147.0, h = 16.0, x = 6..242)
    #    - `[🎧]` Classic Delta/Ref Audition (x = 6.0, w = 20.0)
    #    - `[|||]` Multiband Excess Audition (x = 28.0, w = 20.0)
    #    - `Gain` label (x = 54.0) + `DeltaBoost` numbox (x = 83.0, w = 52.0)
    #    - Contextual `Ref` / `Delay` label (x = 143.0) + numbox (x = 178.0, w = 64.0)
    # =========================================================================
    add_box({
        "id": "obj-btn-audition",
        "maxclass": "live.text",
        "varname": "AuditionDelta",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "parameter_enable": 1,
        "patching_rect": [30.0, 320.0, 20.0, 16.0],
        "presentation": 1,
        "presentation_rect": [6.0, 147.0, 20.0, 16.0],
        "text": "",
        "texton": "",
        "pictures": ["headphones.svg", "headphones.svg"],
        "usepicture": 1,
        "remapsvgcolors": 1,
        "bgcolor": CONTROL_BG,
        "activebgcolor": CONTROL_BG,
        "activebgoncolor": ACTIVE_CYAN,
        "bgoncolor": ACTIVE_CYAN,
        "bordercolor": CONTROL_BORDER,
        "focusbordercolor": CONTROL_BORDER,
        "textcolor": TEXT_MAIN,
        "activefgcolor": TEXT_MAIN,
        "textoncolor": TEXT_ON,
        "activetextoncolor": TEXT_ON,
        "mode": 1,
        "saved_attribute_attributes": {
            "bgcolor": tc("live_control_bg"),
            "activebgcolor": tc("live_control_bg"),
            "bgoncolor": tc("live_lcd_control_fg_alt"),
            "activebgoncolor": tc("live_lcd_control_fg_alt"),
            "bordercolor": tc("live_contrast_frame"),
            "focusbordercolor": tc("live_focus_frame"),
            "textcolor": tc("live_control_fg_off"),
            "activefgcolor": tc("live_control_fg_off"),
            "textoncolor": tc("live_control_fg_on"),
            "activetextoncolor": tc("live_control_fg_on"),
            "valueof": {
                "parameter_longname": "Audition Reference Delta",
                "parameter_shortname": "Audition",
                "parameter_type": 2,
                "parameter_mmax": 1,
                "parameter_enum": ["Off", "On"],
                "parameter_initial_enable": 1,
                "parameter_initial": [0]
            }
        }
    })

    add_box({
        "id": "obj-btn-mb",
        "maxclass": "live.text",
        "varname": "AuditionMB",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "parameter_enable": 1,
        "patching_rect": [55.0, 320.0, 20.0, 16.0],
        "presentation": 1,
        "presentation_rect": [28.0, 147.0, 20.0, 16.0],
        "text": "",
        "texton": "",
        "pictures": ["multiband.svg", "multiband.svg"],
        "usepicture": 1,
        "remapsvgcolors": 1,
        "bgcolor": CONTROL_BG,
        "activebgcolor": CONTROL_BG,
        "activebgoncolor": ACTIVE_CYAN,
        "bgoncolor": ACTIVE_CYAN,
        "bordercolor": CONTROL_BORDER,
        "focusbordercolor": CONTROL_BORDER,
        "textcolor": TEXT_MAIN,
        "activefgcolor": TEXT_MAIN,
        "textoncolor": TEXT_ON,
        "activetextoncolor": TEXT_ON,
        "mode": 1,
        "saved_attribute_attributes": {
            "bgcolor": tc("live_control_bg"),
            "activebgcolor": tc("live_control_bg"),
            "bgoncolor": tc("live_lcd_control_fg_alt"),
            "activebgoncolor": tc("live_lcd_control_fg_alt"),
            "bordercolor": tc("live_contrast_frame"),
            "focusbordercolor": tc("live_focus_frame"),
            "textcolor": tc("live_control_fg_off"),
            "activefgcolor": tc("live_control_fg_off"),
            "textoncolor": tc("live_control_fg_on"),
            "activetextoncolor": tc("live_control_fg_on"),
            "valueof": {
                "parameter_longname": "Audition Multiband Excess",
                "parameter_shortname": "Multiband",
                "parameter_type": 2,
                "parameter_mmax": 1,
                "parameter_enum": ["Off", "On"],
                "parameter_initial_enable": 1,
                "parameter_initial": [0]
            }
        }
    })

    add_box({
        "id": "obj-lbl-row-gain",
        "maxclass": "live.comment",
        "varname": "row_lbl_gain",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [85.0, 305.0, 28.0, 15.0],
        "presentation": 1,
        "presentation_rect": [54.0, 147.5, 28.0, 15.0],
        "text": "Gain",
        "fontname": "Ableton Sans Small Bold",
        "fontsize": 10.0,
        "fontface": 1,
        "textcolor": TEXT_MAIN,
        "ignoreclick": 1,
        "saved_attribute_attributes": {
            "textcolor": tc("live_control_fg")
        }
    })

    add_box({
        "id": "obj-dial-boost",
        "maxclass": "live.numbox",
        "varname": "DeltaBoost",
        "appearance": 2,
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "parameter_enable": 1,
        "patching_rect": [85.0, 325.0, 52.0, 16.0],
        "presentation": 1,
        "presentation_rect": [83.0, 147.0, 52.0, 16.0],
        "activebgcolor": CONTROL_BG,
        "activeslidercolor": VALUE_BAR,
        "bordercolor": CONTROL_BORDER,
        "textcolor": TEXT_MAIN,
        "fontname": "Ableton Sans Medium",
        "fontsize": 9.5,
        "fontface": 0,
        "saved_attribute_attributes": {
            "activebgcolor": tc("live_control_text_bg"),
            "activeslidercolor": tc("live_value_bar"),
            "activetricolor": tc("live_control_bg"),
            "activetricolor2": tc("live_numbox_triangle"),
            "bordercolor": tc("live_contrast_frame"),
            "focusbordercolor": tc("live_focus_frame"),
            "textcolor": tc("live_control_fg"),
            "valueof": {
                "parameter_longname": "Difference Boost",
                "parameter_shortname": "Boost",
                "parameter_type": 0,
                "parameter_mmin": 0.0,
                "parameter_mmax": 36.0,
                "parameter_initial_enable": 1,
                "parameter_initial": [0.0],
                "parameter_unitstyle": 4
            }
        }
    })

    # Contextual Control A (Shown when Tap > 0): Delay (0.0 .. 50.0 ms)
    add_box({
        "id": "obj-lbl-row-delay",
        "maxclass": "live.comment",
        "varname": "row_lbl_delay",
        "numinlets": 1,
        "numoutlets": 0,
        "hidden": 1,
        "patching_rect": [145.0, 305.0, 34.0, 15.0],
        "presentation": 1,
        "presentation_rect": [143.0, 147.5, 34.0, 15.0],
        "text": "Delay",
        "fontname": "Ableton Sans Small Bold",
        "fontsize": 10.0,
        "fontface": 1,
        "textcolor": TEXT_MAIN,
        "ignoreclick": 1,
        "saved_attribute_attributes": {
            "textcolor": tc("live_control_fg")
        }
    })

    add_box({
        "id": "obj-num-align",
        "maxclass": "live.numbox",
        "varname": "AlignNum",
        "appearance": 2,
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "parameter_enable": 1,
        "hidden": 1,
        "patching_rect": [145.0, 325.0, 64.0, 16.0],
        "presentation": 1,
        "presentation_rect": [178.0, 147.0, 64.0, 16.0],
        "activebgcolor": CONTROL_BG,
        "activeslidercolor": VALUE_BAR,
        "bordercolor": CONTROL_BORDER,
        "textcolor": TEXT_MAIN,
        "fontname": "Ableton Sans Medium",
        "fontsize": 9.5,
        "fontface": 0,
        "saved_attribute_attributes": {
            "activebgcolor": tc("live_control_text_bg"),
            "activeslidercolor": tc("live_value_bar"),
            "activetricolor": tc("live_control_bg"),
            "activetricolor2": tc("live_numbox_triangle"),
            "bordercolor": tc("live_contrast_frame"),
            "focusbordercolor": tc("live_focus_frame"),
            "textcolor": tc("live_control_fg"),
            "valueof": {
                "parameter_longname": "Time Delay",
                "parameter_shortname": "Delay",
                "parameter_type": 0,
                "parameter_mmin": 0.0,
                "parameter_mmax": 50.0,
                "parameter_initial_enable": 1,
                "parameter_initial": [0.0],
                "parameter_unitstyle": 2
            }
        }
    })

    # Contextual Control B (Shown when Tap == No Input): Ref (-36.0 .. +12.0 dB, default -6.0 dB)
    add_box({
        "id": "obj-lbl-row-ref",
        "maxclass": "live.comment",
        "varname": "row_lbl_ref",
        "numinlets": 1,
        "numoutlets": 0,
        "hidden": 0,
        "patching_rect": [215.0, 305.0, 34.0, 15.0],
        "presentation": 1,
        "presentation_rect": [143.0, 147.5, 34.0, 15.0],
        "text": "Ref",
        "fontname": "Ableton Sans Small Bold",
        "fontsize": 10.0,
        "fontface": 1,
        "textcolor": TEXT_MAIN,
        "ignoreclick": 1,
        "saved_attribute_attributes": {
            "textcolor": tc("live_control_fg")
        }
    })

    add_box({
        "id": "obj-num-ref",
        "maxclass": "live.numbox",
        "varname": "NoiseRef",
        "appearance": 2,
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "parameter_enable": 1,
        "hidden": 0,
        "patching_rect": [215.0, 325.0, 64.0, 16.0],
        "presentation": 1,
        "presentation_rect": [178.0, 147.0, 64.0, 16.0],
        "activebgcolor": CONTROL_BG,
        "activeslidercolor": VALUE_BAR,
        "bordercolor": CONTROL_BORDER,
        "textcolor": TEXT_MAIN,
        "fontname": "Ableton Sans Medium",
        "fontsize": 9.5,
        "fontface": 0,
        "saved_attribute_attributes": {
            "activebgcolor": tc("live_control_text_bg"),
            "activeslidercolor": tc("live_value_bar"),
            "activetricolor": tc("live_control_bg"),
            "activetricolor2": tc("live_numbox_triangle"),
            "bordercolor": tc("live_contrast_frame"),
            "focusbordercolor": tc("live_focus_frame"),
            "textcolor": tc("live_control_fg"),
            "valueof": {
                "parameter_longname": "Noise Reference",
                "parameter_shortname": "Ref",
                "parameter_type": 0,
                "parameter_mmin": -36.0,
                "parameter_mmax": 12.0,
                "parameter_initial_enable": 1,
                "parameter_initial": [-6.0],
                "parameter_unitstyle": 4
            }
        }
    })

    # =========================================================================
    # 4. AUDIO I/O (4-Channel plugin~: 1/2=Device Pos, 3/4=Tap Sidechain)
    # =========================================================================
    add_box({
        "id": "obj-plugin",
        "maxclass": "newobj",
        "numinlets": 2,
        "numoutlets": 4,
        "outlettype": ["signal", "signal", "signal", "signal"],
        "patching_rect": [280.0, 20.0, 120.0, 22.0],
        "text": "plugin~ 1 2 3 4"
    })

    add_box({
        "id": "obj-plugout",
        "maxclass": "newobj",
        "numinlets": 2,
        "numoutlets": 2,
        "outlettype": ["signal", "signal"],
        "patching_rect": [280.0, 750.0, 70.0, 22.0],
        "text": "plugout~"
    })

    # =========================================================================
    # 5. TAP LIVE.ROUTING + CANONICAL `<none>` NOISE REFERENCE SWAP
    # =========================================================================
    add_box({
        "id": "obj-thisdevice",
        "maxclass": "newobj",
        "numinlets": 1,
        "numoutlets": 3,
        "outlettype": ["bang", "int", "int"],
        "patching_rect": [480.0, 15.0, 85.0, 22.0],
        "text": "live.thisdevice"
    })

    add_box({"id": "obj-init-trig", "maxclass": "newobj", "numinlets": 1, "numoutlets": 4, "outlettype": ["bang", "bang", "bang", "bang"], "patching_rect": [480.0, 42.0, 62.0, 22.0], "text": "t b b b b"})
    add_box({"id": "obj-init-p0", "maxclass": "newobj", "numinlets": 1, "numoutlets": 2, "outlettype": ["bang", "int"], "patching_rect": [575.0, 68.0, 38.0, 22.0], "text": "t b 0"})
    add_box({"id": "obj-init-port-cmd", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [575.0, 95.0, 105.0, 22.0], "text": "port audio_inputs"})

    add_box({"id": "obj-init-del1", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["bang"], "patching_rect": [480.0, 68.0, 60.0, 22.0], "text": "delay 200"})
    add_box({"id": "obj-init-p1", "maxclass": "newobj", "numinlets": 1, "numoutlets": 2, "outlettype": ["bang", "int"], "patching_rect": [480.0, 95.0, 38.0, 22.0], "text": "t b 1"})
    add_box({"id": "obj-init-a-cmd", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [480.0, 120.0, 50.0, 22.0], "text": "index 1"})

    add_line("obj-thisdevice", 0, "obj-init-trig", 0)
    add_line("obj-init-trig", 1, "obj-init-p0", 0)
    add_line("obj-init-p0", 0, "obj-init-port-cmd", 0)
    add_line("obj-init-trig", 0, "obj-init-del1", 0)
    add_line("obj-init-del1", 0, "obj-init-p1", 0)
    add_line("obj-init-p1", 0, "obj-init-a-cmd", 0)

    add_box({
        "id": "obj-live-routing",
        "maxclass": "newobj",
        "numinlets": 1,
        "numoutlets": 5,
        "outlettype": ["", "", "", "", ""],
        "patching_rect": [550.0, 150.0, 140.0, 22.0],
        "text": "live.routing"
    })
    add_line("obj-init-port-cmd", 0, "obj-live-routing", 0)
    add_line("obj-init-a-cmd", 0, "obj-live-routing", 0)

    add_box({"id": "obj-rgate-type",  "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [450.0, 185.0, 55.0, 22.0], "text": "gate 1 0"})
    add_box({"id": "obj-rgate-chan",  "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [515.0, 185.0, 55.0, 22.0], "text": "gate 1 0"})
    add_box({"id": "obj-rgate-tlist", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [580.0, 185.0, 55.0, 22.0], "text": "gate 1 0"})
    add_box({"id": "obj-rgate-clist", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [645.0, 185.0, 55.0, 22.0], "text": "gate 1 0"})

    add_line("obj-live-routing", 0, "obj-rgate-type", 1)
    add_line("obj-live-routing", 1, "obj-rgate-chan", 1)
    add_line("obj-live-routing", 2, "obj-rgate-tlist", 1)
    add_line("obj-live-routing", 3, "obj-rgate-clist", 1)

    def connect_to_all_rgates(src_id, src_out):
        add_line(src_id, src_out, "obj-rgate-type", 0)
        add_line(src_id, src_out, "obj-rgate-chan", 0)
        add_line(src_id, src_out, "obj-rgate-tlist", 0)
        add_line(src_id, src_out, "obj-rgate-clist", 0)

    connect_to_all_rgates("obj-init-p0", 1)
    connect_to_all_rgates("obj-init-p1", 1)

    # Canonical `TapActive` state (`0` = No Input / Noise Mode, `1` = Track Tap Mode)
    add_box({"id": "obj-tapa-active", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["int"], "patching_rect": [220.0, 110.0, 35.0, 22.0], "text": "i 0"})
    add_box({"id": "obj-msg-tap0", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [220.0, 80.0, 29.5, 22.0], "text": "0"})
    add_box({"id": "obj-msg-tap1", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [255.0, 80.0, 29.5, 22.0], "text": "1"})
    add_line("obj-msg-tap0", 0, "obj-tapa-active", 0)
    add_line("obj-msg-tap1", 0, "obj-tapa-active", 0)
    add_line("obj-init-trig", 3, "obj-msg-tap0", 0)

    add_box({"id": "obj-trk-rnoin", "maxclass": "newobj", "numinlets": 2, "numoutlets": 2, "outlettype": ["", ""], "patching_rect": [450.0, 295.0, 95.0, 22.0], "text": "route \"No Input\""})
    add_line("obj-ui-menu-track-a", 1, "obj-trk-rnoin", 0)
    add_line("obj-trk-rnoin", 0, "obj-msg-tap0", 0)
    add_line("obj-trk-rnoin", 1, "obj-msg-tap1", 0)

    # Track Menu (`tap_track_menu`) Population
    add_box({"id": "obj-tapa-trk-set", "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": [""], "patching_rect": [450.0, 215.0, 75.0, 22.0], "text": "prepend set"})
    add_box({"id": "obj-tapa-trk-rnone", "maxclass": "newobj", "numinlets": 2, "numoutlets": 2, "outlettype": ["", ""], "patching_rect": [530.0, 215.0, 80.0, 22.0], "text": "route <none>"})
    add_box({"id": "obj-tapa-trk-clr", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [530.0, 240.0, 37.0, 22.0], "text": "clear"})
    add_box({"id": "obj-tapa-trk-tlclr", "maxclass": "newobj", "numinlets": 1, "numoutlets": 2, "outlettype": ["", "clear"], "patching_rect": [575.0, 240.0, 50.0, 22.0], "text": "t l clear"})
    add_box({"id": "obj-tapa-trk-iter", "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": [""], "patching_rect": [575.0, 265.0, 27.0, 22.0], "text": "iter"})
    add_box({"id": "obj-tapa-trk-app", "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": [""], "patching_rect": [575.0, 290.0, 96.0, 22.0], "text": "prepend append"})
    add_box({"id": "obj-tapa-trk-cmd", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [450.0, 330.0, 55.0, 22.0], "text": "type $1"})

    add_line("obj-rgate-type", 0, "obj-tapa-trk-set", 0)
    add_line("obj-rgate-tlist", 0, "obj-tapa-trk-rnone", 0)
    add_line("obj-tapa-trk-set", 0, "obj-ui-menu-track-a", 0)
    add_line("obj-tapa-trk-rnone", 0, "obj-tapa-trk-clr", 0)
    add_line("obj-tapa-trk-clr", 0, "obj-ui-menu-track-a", 0)
    add_line("obj-tapa-trk-rnone", 1, "obj-tapa-trk-tlclr", 0)
    add_line("obj-tapa-trk-tlclr", 1, "obj-ui-menu-track-a", 0)
    add_line("obj-tapa-trk-tlclr", 0, "obj-tapa-trk-iter", 0)
    add_line("obj-tapa-trk-iter", 0, "obj-tapa-trk-app", 0)
    add_line("obj-tapa-trk-app", 0, "obj-ui-menu-track-a", 0)
    add_line("obj-ui-menu-track-a", 0, "obj-tapa-trk-cmd", 0)
    add_line("obj-tapa-trk-cmd", 0, "obj-live-routing", 0)

    # Channel / Noise Reference Menu (`tap_chan_menu`) Smart Swap
    add_box({"id": "obj-gate-chan-set", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [630.0, 215.0, 55.0, 22.0], "text": "gate 1 0"})
    add_box({"id": "obj-tapa-chn-set", "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": [""], "patching_rect": [630.0, 240.0, 75.0, 22.0], "text": "prepend set"})
    add_line("obj-tapa-active", 0, "obj-gate-chan-set", 0)
    add_line("obj-rgate-chan", 0, "obj-gate-chan-set", 1)
    add_line("obj-gate-chan-set", 0, "obj-tapa-chn-set", 0)
    add_line("obj-tapa-chn-set", 0, "obj-ui-menu-chan-a", 0)

    add_box({"id": "obj-noise-mode-reg", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["int"], "patching_rect": [630.0, 325.0, 35.0, 22.0], "text": "i 0"})

    add_box({"id": "obj-tapa-chn-rnone", "maxclass": "newobj", "numinlets": 2, "numoutlets": 2, "outlettype": ["", ""], "patching_rect": [645.0, 265.0, 80.0, 22.0], "text": "route <none>"})
    add_box({"id": "obj-noise-none-trig", "maxclass": "newobj", "numinlets": 1, "numoutlets": 3, "outlettype": ["bang", "bang", "bang"], "patching_rect": [645.0, 290.0, 48.0, 22.0], "text": "t b b b"})
    add_box({
        "id": "obj-noise-menu-fill",
        "maxclass": "message",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [700.0, 290.0, 295.0, 22.0],
        "text": "clear, append \"Pink Noise\", append \"White Noise\", append Off"
    })
    add_box({"id": "obj-tapa-chn-tlclr", "maxclass": "newobj", "numinlets": 1, "numoutlets": 3, "outlettype": ["", "clear", "bang"], "patching_rect": [735.0, 265.0, 62.0, 22.0], "text": "t l clear b"})
    add_box({"id": "obj-tapa-chn-iter", "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": [""], "patching_rect": [735.0, 320.0, 27.0, 22.0], "text": "iter"})
    add_box({"id": "obj-tapa-chn-app", "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": [""], "patching_rect": [735.0, 345.0, 96.0, 22.0], "text": "prepend append"})

    add_line("obj-rgate-clist", 0, "obj-tapa-chn-rnone", 0)
    add_line("obj-tapa-chn-rnone", 0, "obj-noise-none-trig", 0)
    add_line("obj-noise-none-trig", 2, "obj-msg-tap0", 0)
    add_line("obj-noise-none-trig", 1, "obj-noise-menu-fill", 0)
    add_line("obj-noise-menu-fill", 0, "obj-ui-menu-chan-a", 0)
    add_line("obj-noise-none-trig", 0, "obj-noise-mode-reg", 0)
    add_line("obj-noise-mode-reg", 0, "obj-tapa-chn-set", 0)

    add_line("obj-tapa-chn-rnone", 1, "obj-tapa-chn-tlclr", 0)
    add_line("obj-tapa-chn-tlclr", 2, "obj-msg-tap1", 0)
    add_line("obj-tapa-chn-tlclr", 1, "obj-ui-menu-chan-a", 0)
    add_line("obj-tapa-chn-tlclr", 0, "obj-tapa-chn-iter", 0)
    add_line("obj-tapa-chn-iter", 0, "obj-tapa-chn-app", 0)
    add_line("obj-tapa-chn-app", 0, "obj-ui-menu-chan-a", 0)

    add_box({"id": "obj-tap-plus1", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["int"], "patching_rect": [555.0, 300.0, 32.0, 22.0], "text": "+ 1"})
    add_box({"id": "obj-chan-router", "maxclass": "newobj", "numinlets": 2, "numoutlets": 2, "outlettype": ["", ""], "patching_rect": [555.0, 330.0, 62.0, 22.0], "text": "gate 2 1"})
    add_box({"id": "obj-tapa-chn-cmd", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [555.0, 360.0, 67.0, 22.0], "text": "channel $1"})

    add_line("obj-tapa-active", 0, "obj-tap-plus1", 0)
    add_line("obj-tap-plus1", 0, "obj-chan-router", 0)
    add_line("obj-ui-menu-chan-a", 0, "obj-chan-router", 1)
    add_line("obj-chan-router", 0, "obj-noise-mode-reg", 0)
    add_line("obj-chan-router", 1, "obj-tapa-chn-cmd", 0)
    add_line("obj-tapa-chn-cmd", 0, "obj-live-routing", 0)

    # Contextual Bottom-Right UI Toggle (`Ref` when TapActive == 0, `Delay` when TapActive == 1)
    add_box({"id": "obj-tapa-inv", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["int"], "patching_rect": [220.0, 250.0, 35.0, 22.0], "text": "== 0"})
    add_box({"id": "obj-msg-hide-del", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [130.0, 275.0, 62.0, 22.0], "text": "hidden $1"})
    add_box({"id": "obj-msg-hide-ref", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [205.0, 275.0, 62.0, 22.0], "text": "hidden $1"})

    add_line("obj-tapa-active", 0, "obj-tapa-inv", 0)
    add_line("obj-tapa-inv", 0, "obj-msg-hide-del", 0)
    add_line("obj-tapa-active", 0, "obj-msg-hide-ref", 0)
    add_line("obj-msg-hide-del", 0, "obj-lbl-row-delay", 0)
    add_line("obj-msg-hide-del", 0, "obj-num-align", 0)
    add_line("obj-msg-hide-ref", 0, "obj-lbl-row-ref", 0)
    add_line("obj-msg-hide-ref", 0, "obj-num-ref", 0)

    # -------------------------------------------------------------------------
    # PURE VANILLA MAX 2-CLICK DROPDOWN CLOSE CONTROLLER (Zero JS)
    # -------------------------------------------------------------------------
    add_box({"id": "obj-dd-hover", "maxclass": "newobj", "numinlets": 4, "numoutlets": 4, "outlettype": ["", "", "", ""], "patching_rect": [740.0, 40.0, 55.0, 22.0], "text": "hover"})
    add_box({"id": "obj-dd-hroute", "maxclass": "newobj", "numinlets": 3, "numoutlets": 3, "outlettype": ["", "", ""], "patching_rect": [740.0, 70.0, 210.0, 22.0], "text": "route tap_track_menu tap_chan_menu"})
    add_box({"id": "obj-dd-h1", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [740.0, 100.0, 29.5, 22.0], "text": "1"})
    add_box({"id": "obj-dd-h2", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [780.0, 100.0, 29.5, 22.0], "text": "2"})
    add_box({"id": "obj-dd-h0", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [820.0, 100.0, 29.5, 22.0], "text": "0"})
    add_box({"id": "obj-dd-hid", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["int"], "patching_rect": [740.0, 132.0, 35.0, 22.0], "text": "i 0"})

    add_line("obj-dd-hover", 0, "obj-dd-hroute", 0)
    add_line("obj-dd-hroute", 0, "obj-dd-h1", 0)
    add_line("obj-dd-hroute", 1, "obj-dd-h2", 0)
    add_line("obj-dd-hroute", 2, "obj-dd-h0", 0)
    add_line("obj-dd-hover", 1, "obj-dd-h0", 0)
    add_line("obj-dd-hover", 2, "obj-dd-h0", 0)
    add_line("obj-dd-h1", 0, "obj-dd-hid", 1)
    add_line("obj-dd-h2", 0, "obj-dd-hid", 1)
    add_line("obj-dd-h0", 0, "obj-dd-hid", 1)

    add_box({"id": "obj-dd-mspoll", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [740.0, 165.0, 35.0, 22.0], "text": "poll"})
    add_box({"id": "obj-dd-mstate", "maxclass": "newobj", "numinlets": 1, "numoutlets": 5, "outlettype": ["int", "int", "int", "int", "int"], "patching_rect": [740.0, 195.0, 75.0, 22.0], "text": "mousestate"})
    add_box({"id": "obj-dd-mchg", "maxclass": "newobj", "numinlets": 1, "numoutlets": 3, "outlettype": ["", "int", "int"], "patching_rect": [740.0, 225.0, 65.0, 22.0], "text": "change -1"})
    add_box({"id": "obj-dd-msel", "maxclass": "newobj", "numinlets": 3, "numoutlets": 3, "outlettype": ["bang", "bang", ""], "patching_rect": [740.0, 255.0, 58.0, 22.0], "text": "sel 1 0"})

    add_line("obj-init-trig", 2, "obj-dd-mspoll", 0)
    add_line("obj-dd-mspoll", 0, "obj-dd-mstate", 0)
    add_line("obj-dd-mstate", 0, "obj-dd-mchg", 0)
    add_line("obj-dd-mchg", 0, "obj-dd-msel", 0)

    add_box({"id": "obj-dd-open", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["int"], "patching_rect": [740.0, 290.0, 35.0, 22.0], "text": "i 0"})
    add_box({"id": "obj-dd-osel", "maxclass": "newobj", "numinlets": 3, "numoutlets": 3, "outlettype": ["bang", "bang", ""], "patching_rect": [740.0, 320.0, 58.0, 22.0], "text": "sel 0 1"})
    add_box({"id": "obj-dd-hsel", "maxclass": "newobj", "numinlets": 3, "numoutlets": 3, "outlettype": ["bang", "bang", ""], "patching_rect": [740.0, 350.0, 58.0, 22.0], "text": "sel 1 2"})

    add_line("obj-dd-msel", 0, "obj-dd-open", 0)
    add_line("obj-dd-open", 0, "obj-dd-osel", 0)
    add_line("obj-dd-osel", 0, "obj-dd-hid", 0)
    add_line("obj-dd-hid", 0, "obj-dd-hsel", 0)

    add_box({"id": "obj-dd-trig-open", "maxclass": "newobj", "numinlets": 1, "numoutlets": 3, "outlettype": ["bang", "int", "stop"], "patching_rect": [740.0, 385.0, 75.0, 22.0], "text": "t b 1 stop"})
    add_box({"id": "obj-dd-timer", "maxclass": "newobj", "numinlets": 2, "numoutlets": 2, "outlettype": ["float", ""], "patching_rect": [845.0, 385.0, 45.0, 22.0], "text": "timer"})
    add_box({"id": "obj-dd-del-lock", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["bang"], "patching_rect": [740.0, 420.0, 58.0, 22.0], "text": "delay 15"})
    add_box({"id": "obj-dd-msg-lock", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [740.0, 450.0, 82.0, 22.0], "text": "ignoreclick 1"})

    add_line("obj-dd-hsel", 0, "obj-dd-trig-open", 0)
    add_line("obj-dd-hsel", 1, "obj-dd-trig-open", 0)
    add_line("obj-dd-trig-open", 1, "obj-dd-open", 1)
    add_line("obj-dd-trig-open", 0, "obj-dd-timer", 0)
    add_line("obj-dd-trig-open", 0, "obj-dd-del-lock", 0)
    add_line("obj-dd-del-lock", 0, "obj-dd-msg-lock", 0)
    add_line("obj-dd-msg-lock", 0, "obj-ui-menu-track-a", 0)
    add_line("obj-dd-msg-lock", 0, "obj-ui-menu-chan-a", 0)

    add_box({"id": "obj-dd-del-unlock", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["bang"], "patching_rect": [845.0, 420.0, 58.0, 22.0], "text": "delay 75"})
    add_box({"id": "obj-dd-trig-unlk", "maxclass": "newobj", "numinlets": 1, "numoutlets": 2, "outlettype": ["bang", "int"], "patching_rect": [845.0, 450.0, 42.0, 22.0], "text": "t b 0"})
    add_box({"id": "obj-dd-msg-unlk", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [845.0, 480.0, 82.0, 22.0], "text": "ignoreclick 0"})

    add_line("obj-dd-trig-open", 2, "obj-dd-del-unlock", 0)
    add_line("obj-dd-osel", 1, "obj-dd-del-unlock", 0)
    add_line("obj-ui-menu-track-a", 0, "obj-dd-del-unlock", 0)
    add_line("obj-ui-menu-chan-a", 0, "obj-dd-del-unlock", 0)

    add_box({"id": "obj-dd-up-gate", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [845.0, 290.0, 55.0, 22.0], "text": "gate 1 0"})
    add_box({"id": "obj-dd-gt220", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["int"], "patching_rect": [900.0, 385.0, 45.0, 22.0], "text": "> 220"})
    add_box({"id": "obj-dd-sel220", "maxclass": "newobj", "numinlets": 2, "numoutlets": 2, "outlettype": ["bang", ""], "patching_rect": [950.0, 385.0, 42.0, 22.0], "text": "sel 1"})
    add_line("obj-dd-trig-open", 1, "obj-dd-up-gate", 0)
    add_line("obj-dd-trig-unlk", 1, "obj-dd-up-gate", 0)
    add_line("obj-dd-msel", 1, "obj-dd-up-gate", 1)
    add_line("obj-dd-up-gate", 0, "obj-dd-timer", 1)
    add_line("obj-dd-timer", 0, "obj-dd-gt220", 0)
    add_line("obj-dd-gt220", 0, "obj-dd-sel220", 0)
    add_line("obj-dd-sel220", 0, "obj-dd-del-unlock", 0)

    add_box({"id": "obj-dd-key", "maxclass": "newobj", "numinlets": 0, "numoutlets": 4, "outlettype": ["int", "int", "int", "int"], "patching_rect": [930.0, 420.0, 40.0, 22.0], "text": "key"})
    add_box({"id": "obj-dd-esc", "maxclass": "newobj", "numinlets": 2, "numoutlets": 2, "outlettype": ["bang", ""], "patching_rect": [930.0, 450.0, 45.0, 22.0], "text": "sel 27"})
    add_line("obj-dd-key", 0, "obj-dd-esc", 0)
    add_line("obj-dd-esc", 0, "obj-dd-trig-unlk", 0)

    add_line("obj-dd-del-unlock", 0, "obj-dd-trig-unlk", 0)
    add_line("obj-dd-trig-unlk", 1, "obj-dd-open", 1)
    add_line("obj-dd-trig-unlk", 0, "obj-dd-msg-unlk", 0)
    add_line("obj-dd-msg-unlk", 0, "obj-ui-menu-track-a", 0)
    add_line("obj-dd-msg-unlk", 0, "obj-ui-menu-chan-a", 0)

    # =========================================================================
    # 6. TIME DELAY ALIGNMENT IN MS (mstosamps~ -> delay~ on Tap channels 3/4)
    # =========================================================================
    add_box({
        "id": "obj-mstosamps",
        "maxclass": "newobj",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["signal", "float"],
        "patching_rect": [130.0, 245.0, 75.0, 22.0],
        "text": "mstosamps~"
    })
    add_line("obj-num-align", 0, "obj-mstosamps", 0)

    add_box({
        "id": "obj-delay-l",
        "maxclass": "newobj",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": ["signal"],
        "patching_rect": [300.0, 80.0, 95.0, 22.0],
        "text": "delay~ 44100 0"
    })
    add_box({
        "id": "obj-delay-r",
        "maxclass": "newobj",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": ["signal"],
        "patching_rect": [400.0, 80.0, 95.0, 22.0],
        "text": "delay~ 44100 0"
    })
    add_line("obj-plugin", 2, "obj-delay-l", 0)
    add_line("obj-plugin", 3, "obj-delay-r", 0)
    add_line("obj-mstosamps", 1, "obj-delay-l", 1)
    add_line("obj-mstosamps", 1, "obj-delay-r", 1)

    # =========================================================================
    # 7. STEREO NOISE ENGINE + SMART SWAP WITH TAP
    # =========================================================================
    add_box({"id": "obj-noise-map", "maxclass": "newobj", "numinlets": 2, "numoutlets": 2, "outlettype": ["", ""], "patching_rect": [30.0, 60.0, 92.0, 22.0], "text": "zl.lookup 1 2 0"})
    add_box({"id": "obj-noise-active-mult", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["int"], "patching_rect": [30.0, 90.0, 35.0, 22.0], "text": "* 1"})
    add_box({"id": "obj-tapa-inv-trig", "maxclass": "newobj", "numinlets": 1, "numoutlets": 2, "outlettype": ["bang", "int"], "patching_rect": [75.0, 90.0, 35.0, 22.0], "text": "t b i"})

    add_line("obj-noise-mode-reg", 0, "obj-noise-map", 0)
    add_line("obj-tapa-inv", 0, "obj-tapa-inv-trig", 0)
    add_line("obj-tapa-inv-trig", 1, "obj-noise-active-mult", 1)
    add_line("obj-tapa-inv-trig", 0, "obj-noise-mode-reg", 0)
    add_line("obj-noise-map", 0, "obj-noise-active-mult", 0)

    add_box({"id": "obj-pink-l",  "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [30.0, 125.0, 42.0, 22.0], "text": "pink~"})
    add_box({"id": "obj-pink-r",  "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [80.0, 125.0, 42.0, 22.0], "text": "pink~"})
    add_box({"id": "obj-white-l", "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [130.0, 125.0, 46.0, 22.0], "text": "noise~"})
    add_box({"id": "obj-white-r", "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [180.0, 125.0, 46.0, 22.0], "text": "noise~"})
    add_box({"id": "obj-wtrim-l", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [130.0, 152.0, 46.0, 22.0], "text": "*~ 0.55"})
    add_box({"id": "obj-wtrim-r", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [180.0, 152.0, 46.0, 22.0], "text": "*~ 0.55"})
    add_line("obj-white-l", 0, "obj-wtrim-l", 0)
    add_line("obj-white-r", 0, "obj-wtrim-r", 0)

    add_box({"id": "obj-noise-sel-l", "maxclass": "newobj", "numinlets": 3, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [30.0, 185.0, 80.0, 22.0], "text": "selector~ 2 1"})
    add_box({"id": "obj-noise-sel-r", "maxclass": "newobj", "numinlets": 3, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [120.0, 185.0, 80.0, 22.0], "text": "selector~ 2 1"})
    add_line("obj-noise-active-mult", 0, "obj-noise-sel-l", 0)
    add_line("obj-noise-active-mult", 0, "obj-noise-sel-r", 0)
    add_line("obj-pink-l", 0, "obj-noise-sel-l", 1)
    add_line("obj-pink-r", 0, "obj-noise-sel-r", 1)
    add_line("obj-wtrim-l", 0, "obj-noise-sel-l", 2)
    add_line("obj-wtrim-r", 0, "obj-noise-sel-r", 2)

    add_box({"id": "obj-ref-dbtoa", "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": [""], "patching_rect": [30.0, 215.0, 41.0, 22.0], "text": "dbtoa"})
    add_box({"id": "obj-noise-gain-l", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [30.0, 245.0, 48.0, 22.0], "text": "*~ 0.501"})
    add_box({"id": "obj-noise-gain-r", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [90.0, 245.0, 48.0, 22.0], "text": "*~ 0.501"})
    add_line("obj-num-ref", 0, "obj-ref-dbtoa", 0)
    add_line("obj-noise-sel-l", 0, "obj-noise-gain-l", 0)
    add_line("obj-noise-sel-r", 0, "obj-noise-gain-r", 0)
    add_line("obj-ref-dbtoa", 0, "obj-noise-gain-l", 1)
    add_line("obj-ref-dbtoa", 0, "obj-noise-gain-r", 1)

    # Track B Gate (`obj-gate-dsp-b-l/r`): Open when `TapActive == 1` OR `NoiseActive > 0`
    add_box({"id": "obj-any-active-sum", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["int"], "patching_rect": [220.0, 115.0, 32.0, 22.0], "text": "+ 1"})
    add_box({"id": "obj-any-active", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["int"], "patching_rect": [260.0, 115.0, 35.0, 22.0], "text": "> 0"})
    add_box({"id": "obj-noise-trig-b", "maxclass": "newobj", "numinlets": 1, "numoutlets": 2, "outlettype": ["bang", "int"], "patching_rect": [180.0, 115.0, 35.0, 22.0], "text": "t b i"})
    add_line("obj-noise-active-mult", 0, "obj-noise-trig-b", 0)
    add_line("obj-noise-trig-b", 1, "obj-any-active-sum", 1)
    add_line("obj-noise-trig-b", 0, "obj-any-active-sum", 0)
    add_line("obj-tapa-active", 0, "obj-any-active-sum", 0)
    add_line("obj-any-active-sum", 0, "obj-any-active", 0)

    add_box({"id": "obj-gate-dsp-b-l", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [220.0, 145.0, 70.0, 22.0], "text": "selector~ 1 1"})
    add_box({"id": "obj-gate-dsp-b-r", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [295.0, 145.0, 70.0, 22.0], "text": "selector~ 1 1"})
    add_line("obj-any-active", 0, "obj-gate-dsp-b-l", 0)
    add_line("obj-any-active", 0, "obj-gate-dsp-b-r", 0)
    add_line("obj-plugin", 0, "obj-gate-dsp-b-l", 1)
    add_line("obj-plugin", 1, "obj-gate-dsp-b-r", 1)

    # Reference A Selector (`obj-gate-dsp-a-l/r`, `selector~ 2 1`)
    add_box({"id": "obj-gate-dsp-a-l", "maxclass": "newobj", "numinlets": 3, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [370.0, 145.0, 80.0, 22.0], "text": "selector~ 2 1"})
    add_box({"id": "obj-gate-dsp-a-r", "maxclass": "newobj", "numinlets": 3, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [455.0, 145.0, 80.0, 22.0], "text": "selector~ 2 1"})
    add_line("obj-tap-plus1", 0, "obj-gate-dsp-a-l", 0)
    add_line("obj-tap-plus1", 0, "obj-gate-dsp-a-r", 0)
    add_line("obj-noise-gain-l", 0, "obj-gate-dsp-a-l", 1)
    add_line("obj-noise-gain-r", 0, "obj-gate-dsp-a-r", 1)
    add_line("obj-delay-l", 0, "obj-gate-dsp-a-l", 2)
    add_line("obj-delay-r", 0, "obj-gate-dsp-a-r", 2)

    # =========================================================================
    # 8. PATH 1: PURE DELTA CANCELLATION (`B - A`) FOR HEADPHONES `[🎧]`
    # =========================================================================
    add_box({"id": "obj-invert-a-l", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [370.0, 180.0, 38.0, 22.0], "text": "*~ -1."})
    add_box({"id": "obj-invert-a-r", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [455.0, 180.0, 38.0, 22.0], "text": "*~ -1."})
    add_line("obj-gate-dsp-a-l", 0, "obj-invert-a-l", 0)
    add_line("obj-gate-dsp-a-r", 0, "obj-invert-a-r", 0)

    add_box({"id": "obj-sum-delta-l", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [300.0, 220.0, 38.0, 22.0], "text": "+~"})
    add_box({"id": "obj-sum-delta-r", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [350.0, 220.0, 38.0, 22.0], "text": "+~"})
    add_line("obj-gate-dsp-b-l", 0, "obj-sum-delta-l", 0)
    add_line("obj-gate-dsp-b-r", 0, "obj-sum-delta-r", 0)
    add_line("obj-invert-a-l", 0, "obj-sum-delta-l", 1)
    add_line("obj-invert-a-r", 0, "obj-sum-delta-r", 1)

    # =========================================================================
    # 9. PATH 2: 9-BAND OCTAVE MULTIBAND SPECTRAL EXCESS ENGINE FOR `[|||]`
    #    - In Noise Reference Mode (`TapActive == 0`): uses an exact, rock-steady
    #      analytical per-octave Pink Noise threshold `T_k = 0.18 * dbtoa(Ref)`
    #      (equal energy per octave band) or White Noise threshold
    #      `T_k = 0.18 * (1.4142 ** (k - 4)) * dbtoa(Ref)` so there is zero random
    #      low-frequency noise wobble.
    #    - In Track Tap Mode (`TapActive == 1`): uses the live octave-band envelope
    #      of the delayed Tap track (`obj-delay-l/r`).
    #    - Passes ONLY the excess amplitude above the reference threshold:
    #        G_k(t) = clip(E_B,k(t) - E_A,k(t), 0, 10) / (E_B,k(t) + 0.0001)
    # =========================================================================
    add_box({"id": "obj-mb-tap-mono", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [1050.0, 40.0, 42.0, 22.0], "text": "*~ 0.5"})
    add_line("obj-delay-l", 0, "obj-mb-tap-mono", 0)
    add_line("obj-delay-r", 0, "obj-mb-tap-mono", 0)

    # Analytical Pink Noise per-octave base threshold (equal across all 1-octave bands)
    add_box({"id": "obj-mb-pink-sig", "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [960.0, 40.0, 62.0, 22.0], "text": "sig~ 0.18"})
    add_box({"id": "obj-mb-pink-thr", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [960.0, 70.0, 52.0, 22.0], "text": "*~ 0.501"})
    add_line("obj-mb-pink-sig", 0, "obj-mb-pink-thr", 0)
    add_line("obj-ref-dbtoa", 0, "obj-mb-pink-thr", 1)

    add_box({"id": "obj-mb-sum-l", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [1050.0, 740.0, 45.0, 22.0], "text": "*~ 0.75"})
    add_box({"id": "obj-mb-sum-r", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [1120.0, 740.0, 45.0, 22.0], "text": "*~ 0.75"})

    for idx_b, fc in enumerate(OCTAVE_BANDS):
        bx = 1050.0 + idx_b * 115.0
        white_coeff = round(0.18 * (1.41421356 ** (idx_b - 4)), 5)

        svf_bl = f"obj-mb-b{idx_b}-svf-l"
        svf_br = f"obj-mb-b{idx_b}-svf-r"
        svf_a  = f"obj-mb-b{idx_b}-svf-a"
        abs_bl = f"obj-mb-b{idx_b}-abs-l"
        abs_br = f"obj-mb-b{idx_b}-abs-r"
        avg_b  = f"obj-mb-b{idx_b}-avg-b"
        env_b  = f"obj-mb-b{idx_b}-env-b"

        wsig_id = f"obj-mb-b{idx_b}-wsig"
        wthr_id = f"obj-mb-b{idx_b}-wthr"
        nthr_id = f"obj-mb-b{idx_b}-nthr"
        abs_a   = f"obj-mb-b{idx_b}-abs-a"
        env_a   = f"obj-mb-b{idx_b}-env-a"
        rsel_id = f"obj-mb-b{idx_b}-rsel"

        diff_e = f"obj-mb-b{idx_b}-diff"
        clip_e = f"obj-mb-b{idx_b}-clip"
        eps_b  = f"obj-mb-b{idx_b}-eps"
        div_g  = f"obj-mb-b{idx_b}-div"
        smoo_g = f"obj-mb-b{idx_b}-smoo"
        out_l  = f"obj-mb-b{idx_b}-out-l"
        out_r  = f"obj-mb-b{idx_b}-out-r"

        # Non-resonant Butterworth Q (0.25) 1-octave bandpass filters
        add_box({"id": svf_bl, "maxclass": "newobj", "numinlets": 3, "numoutlets": 4, "outlettype": ["signal", "signal", "signal", "signal"], "patching_rect": [bx, 80.0, 95.0, 22.0], "text": f"svf~ {fc} 0.25"})
        add_box({"id": svf_br, "maxclass": "newobj", "numinlets": 3, "numoutlets": 4, "outlettype": ["signal", "signal", "signal", "signal"], "patching_rect": [bx, 110.0, 95.0, 22.0], "text": f"svf~ {fc} 0.25"})
        add_box({"id": svf_a,  "maxclass": "newobj", "numinlets": 3, "numoutlets": 4, "outlettype": ["signal", "signal", "signal", "signal"], "patching_rect": [bx, 140.0, 95.0, 22.0], "text": f"svf~ {fc} 0.25"})

        add_box({"id": abs_bl, "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [bx, 175.0, 38.0, 22.0], "text": "abs~"})
        add_box({"id": abs_br, "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [bx + 45.0, 175.0, 38.0, 22.0], "text": "abs~"})
        add_box({"id": avg_b,  "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [bx, 205.0, 42.0, 22.0], "text": "*~ 0.5"})
        add_box({"id": env_b,  "maxclass": "newobj", "numinlets": 3, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [bx, 235.0, 105.0, 22.0], "text": "rampsmooth~ 128 2048"})

        # Analytical White Noise threshold for band k + selector between Pink (1) and White (2)
        add_box({"id": wsig_id, "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [bx, 265.0, 78.0, 22.0], "text": f"sig~ {white_coeff}"})
        add_box({"id": wthr_id, "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [bx, 292.0, 52.0, 22.0], "text": "*~ 0.501"})
        add_box({"id": nthr_id, "maxclass": "newobj", "numinlets": 3, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [bx, 320.0, 80.0, 22.0], "text": "selector~ 2 1"})

        # Live Tap Track envelope for band k (used when TapActive == 1)
        add_box({"id": abs_a,   "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [bx, 350.0, 38.0, 22.0], "text": "abs~"})
        add_box({"id": env_a,   "maxclass": "newobj", "numinlets": 3, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [bx, 378.0, 105.0, 22.0], "text": "rampsmooth~ 128 2048"})
        add_box({"id": rsel_id, "maxclass": "newobj", "numinlets": 3, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [bx, 408.0, 80.0, 22.0], "text": "selector~ 2 1"})

        add_box({"id": diff_e, "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [bx, 440.0, 35.0, 22.0], "text": "-~"})
        add_box({"id": clip_e, "maxclass": "newobj", "numinlets": 3, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [bx, 470.0, 68.0, 22.0], "text": "clip~ 0. 10."})
        add_box({"id": eps_b,  "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [bx, 500.0, 75.0, 22.0], "text": "+~ 0.0001"})
        add_box({"id": div_g,  "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [bx, 530.0, 35.0, 22.0], "text": "/~"})
        add_box({"id": smoo_g, "maxclass": "newobj", "numinlets": 3, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [bx, 560.0, 105.0, 22.0], "text": "rampsmooth~ 128 1024"})

        add_box({"id": out_l,  "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [bx, 595.0, 38.0, 22.0], "text": "*~"})
        add_box({"id": out_r,  "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [bx + 45.0, 595.0, 38.0, 22.0], "text": "*~"})

        add_line("obj-gate-dsp-b-l", 0, svf_bl, 0)
        add_line("obj-gate-dsp-b-r", 0, svf_br, 0)
        add_line("obj-mb-tap-mono",  0, svf_a,  0)

        # Track Bandpass envelope
        add_line(svf_bl, 2, abs_bl, 0)
        add_line(svf_br, 2, abs_br, 0)
        add_line(abs_bl, 0, avg_b, 0)
        add_line(abs_br, 0, avg_b, 0)
        add_line(avg_b,  0, env_b, 0)

        # Analytical Noise Threshold vs Live Tap Envelope
        add_line(wsig_id, 0, wthr_id, 0)
        add_line("obj-ref-dbtoa", 0, wthr_id, 1)
        add_line("obj-noise-active-mult", 0, nthr_id, 0)
        add_line("obj-mb-pink-thr", 0, nthr_id, 1)
        add_line(wthr_id, 0, nthr_id, 2)

        add_line(svf_a, 2, abs_a, 0)
        add_line(abs_a, 0, env_a, 0)

        add_line("obj-tap-plus1", 0, rsel_id, 0)
        add_line(nthr_id, 0, rsel_id, 1)
        add_line(env_a,   0, rsel_id, 2)

        # Excess calculation: max(0, E_B - E_Ref) / (E_B + 0.0001)
        add_line(env_b,   0, diff_e, 0)
        add_line(rsel_id, 0, diff_e, 1)
        add_line(diff_e,  0, clip_e, 0)
        add_line(env_b,   0, eps_b,  0)
        add_line(clip_e,  0, div_g,  0)
        add_line(eps_b,   0, div_g,  1)
        add_line(div_g,   0, smoo_g, 0)

        add_line(svf_bl, 2, out_l, 0)
        add_line(svf_br, 2, out_r, 0)
        add_line(smoo_g, 0, out_l, 1)
        add_line(smoo_g, 0, out_r, 1)

        add_line(out_l, 0, "obj-mb-sum-l", 0)
        add_line(out_r, 0, "obj-mb-sum-r", 0)

    # =========================================================================
    # 10. DUAL-BUTTON MUTUAL EXCLUSION & DIFFERENCE MULTIPLEXER (`[🎧]` vs `[|||]`)
    #     - Default visual when both OFF: Multiband Spectral Excess (inlet 2)
    #     - When `[🎧]` is turned ON: sets `[|||]` OFF, selects Pure Delta (inlet 1), and enables Audition
    #     - When `[|||]` is turned ON: sets `[🎧]` OFF, selects Multiband Excess (inlet 2), and enables Audition
    # =========================================================================
    add_box({"id": "obj-aud-trig", "maxclass": "newobj", "numinlets": 1, "numoutlets": 2, "outlettype": ["int", "int"], "patching_rect": [30.0, 345.0, 35.0, 22.0], "text": "t i i"})
    add_box({"id": "obj-mb-trig",  "maxclass": "newobj", "numinlets": 1, "numoutlets": 2, "outlettype": ["int", "int"], "patching_rect": [80.0, 345.0, 35.0, 22.0], "text": "t i i"})
    add_box({"id": "obj-aud-sel1", "maxclass": "newobj", "numinlets": 2, "numoutlets": 2, "outlettype": ["bang", ""], "patching_rect": [30.0, 372.0, 40.0, 22.0], "text": "sel 1"})
    add_box({"id": "obj-mb-sel1",  "maxclass": "newobj", "numinlets": 2, "numoutlets": 2, "outlettype": ["bang", ""], "patching_rect": [80.0, 372.0, 40.0, 22.0], "text": "sel 1"})
    add_box({"id": "obj-msg-set0",     "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [30.0, 398.0, 42.0, 22.0], "text": "set 0"})
    add_box({"id": "obj-msg-set0-aud", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [80.0, 398.0, 42.0, 22.0], "text": "set 0"})

    add_line("obj-btn-audition", 0, "obj-aud-trig", 0)
    add_line("obj-btn-mb", 0, "obj-mb-trig", 0)
    add_line("obj-aud-trig", 1, "obj-aud-sel1", 0)
    add_line("obj-mb-trig", 1, "obj-mb-sel1", 0)
    add_line("obj-aud-sel1", 0, "obj-msg-set0", 0)
    add_line("obj-msg-set0", 0, "obj-btn-mb", 0)
    add_line("obj-mb-sel1", 0, "obj-msg-set0-aud", 0)
    add_line("obj-msg-set0-aud", 0, "obj-btn-audition", 0)

    add_box({"id": "obj-reg-aud",  "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["int"], "patching_rect": [30.0, 425.0, 35.0, 22.0], "text": "i 0"})
    add_box({"id": "obj-reg-mb",   "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["int"], "patching_rect": [80.0, 425.0, 35.0, 22.0], "text": "i 0"})
    add_box({"id": "obj-zero-mb",  "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [125.0, 425.0, 29.5, 22.0], "text": "0"})
    add_box({"id": "obj-zero-aud", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [160.0, 425.0, 29.5, 22.0], "text": "0"})

    add_line("obj-aud-sel1", 0, "obj-zero-mb", 0)
    add_line("obj-zero-mb", 0, "obj-reg-mb", 0)
    add_line("obj-mb-sel1", 0, "obj-zero-aud", 0)
    add_line("obj-zero-aud", 0, "obj-reg-aud", 0)
    add_line("obj-aud-trig", 0, "obj-reg-aud", 0)
    add_line("obj-mb-trig", 0, "obj-reg-mb", 0)

    add_box({"id": "obj-aud-inv-sel", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["int"], "patching_rect": [30.0, 455.0, 35.0, 22.0], "text": "== 0"})
    add_box({"id": "obj-eng-idx",     "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["int"], "patching_rect": [30.0, 485.0, 35.0, 22.0], "text": "+ 1"})
    add_line("obj-reg-aud", 0, "obj-aud-inv-sel", 0)
    add_line("obj-aud-inv-sel", 0, "obj-eng-idx", 0)

    add_box({"id": "obj-diff-engine-sel-l", "maxclass": "newobj", "numinlets": 3, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [300.0, 248.0, 80.0, 22.0], "text": "selector~ 2 2"})
    add_box({"id": "obj-diff-engine-sel-r", "maxclass": "newobj", "numinlets": 3, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [390.0, 248.0, 80.0, 22.0], "text": "selector~ 2 2"})
    add_line("obj-eng-idx", 0, "obj-diff-engine-sel-l", 0)
    add_line("obj-eng-idx", 0, "obj-diff-engine-sel-r", 0)
    add_line("obj-sum-delta-l", 0, "obj-diff-engine-sel-l", 1)
    add_line("obj-sum-delta-r", 0, "obj-diff-engine-sel-r", 1)
    add_line("obj-mb-sum-l",    0, "obj-diff-engine-sel-l", 2)
    add_line("obj-mb-sum-r",    0, "obj-diff-engine-sel-r", 2)

    # Boost (`Gain`, 0..+36 dB) + Peak Limiter (`omx.peaklim~`)
    add_box({"id": "obj-boost-dbtoa", "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": [""], "patching_rect": [180.0, 270.0, 41.0, 22.0], "text": "dbtoa"})
    add_line("obj-dial-boost", 0, "obj-boost-dbtoa", 0)

    add_box({"id": "obj-boost-mult-l", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [300.0, 280.0, 38.0, 22.0], "text": "*~ 1."})
    add_box({"id": "obj-boost-mult-r", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [350.0, 280.0, 38.0, 22.0], "text": "*~ 1."})
    add_line("obj-diff-engine-sel-l", 0, "obj-boost-mult-l", 0)
    add_line("obj-diff-engine-sel-r", 0, "obj-boost-mult-r", 0)
    add_line("obj-boost-dbtoa", 0, "obj-boost-mult-l", 1)
    add_line("obj-boost-dbtoa", 0, "obj-boost-mult-r", 1)

    add_box({"id": "obj-limiter-delta", "maxclass": "newobj", "numinlets": 2, "numoutlets": 2, "outlettype": ["signal", "signal"], "patching_rect": [300.0, 315.0, 90.0, 22.0], "text": "omx.peaklim~"})
    add_line("obj-boost-mult-l", 0, "obj-limiter-delta", 0)
    add_line("obj-boost-mult-r", 0, "obj-limiter-delta", 1)

    add_box({"id": "obj-mb-trig-or",  "maxclass": "newobj", "numinlets": 1, "numoutlets": 2, "outlettype": ["bang", "int"], "patching_rect": [80.0, 455.0, 35.0, 22.0], "text": "t b i"})
    add_box({"id": "obj-aud-any-sum", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["int"], "patching_rect": [80.0, 485.0, 35.0, 22.0], "text": "+ 0"})
    add_box({"id": "obj-aud-any-gt0", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["int"], "patching_rect": [80.0, 515.0, 35.0, 22.0], "text": "> 0"})
    add_box({"id": "obj-mode-plus1",  "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["int"], "patching_rect": [80.0, 545.0, 35.0, 22.0], "text": "+ 1"})

    add_line("obj-reg-mb", 0, "obj-mb-trig-or", 0)
    add_line("obj-mb-trig-or", 1, "obj-aud-any-sum", 1)
    add_line("obj-mb-trig-or", 0, "obj-aud-any-sum", 0)
    add_line("obj-reg-aud", 0, "obj-aud-any-sum", 0)
    add_line("obj-aud-any-sum", 0, "obj-aud-any-gt0", 0)
    add_line("obj-aud-any-gt0", 0, "obj-mode-plus1", 0)

    add_box({"id": "obj-sel-audition-l", "maxclass": "newobj", "numinlets": 3, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [250.0, 390.0, 80.0, 22.0], "text": "selector~ 2 1"})
    add_box({"id": "obj-sel-audition-r", "maxclass": "newobj", "numinlets": 3, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [350.0, 390.0, 80.0, 22.0], "text": "selector~ 2 1"})
    add_line("obj-plugin", 0, "obj-sel-audition-l", 1)
    add_line("obj-plugin", 1, "obj-sel-audition-r", 1)
    add_line("obj-limiter-delta", 0, "obj-sel-audition-l", 2)
    add_line("obj-limiter-delta", 1, "obj-sel-audition-r", 2)
    add_line("obj-mode-plus1", 0, "obj-sel-audition-l", 0)
    add_line("obj-mode-plus1", 0, "obj-sel-audition-r", 0)
    add_line("obj-sel-audition-l", 0, "obj-plugout", 0)
    add_line("obj-sel-audition-r", 0, "obj-plugout", 1)

    # =========================================================================
    # 11. EQ-EIGHT-BALANCED SPECTRUM PRE-EMPHASIS TILT NETWORK (Visual Feed Only)
    # =========================================================================
    def add_tilt_chain(prefix: str, in_l_id: str, in_l_out: int, in_r_id: str, in_r_out: int, dst_inlet: int, base_x: float):
        sum_id  = f"obj-{prefix}-sum"
        half_id = f"obj-{prefix}-half"
        lp1_id  = f"obj-{prefix}-lp1"
        sc1_id  = f"obj-{prefix}-sc1"
        hp1_id  = f"obj-{prefix}-hp1"
        lp2_id  = f"obj-{prefix}-lp2"
        sc2_id  = f"obj-{prefix}-sc2"
        hp2_id  = f"obj-{prefix}-hp2"
        gain_id = f"obj-{prefix}-gain"

        add_box({"id": sum_id,  "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [base_x, 420.0, 35.0, 22.0], "text": "+~"})
        add_box({"id": half_id, "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [base_x, 448.0, 42.0, 22.0], "text": "*~ 0.5"})
        add_box({"id": lp1_id,  "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [base_x + 50.0, 476.0, 82.0, 22.0], "text": "onepole~ 260."})
        add_box({"id": sc1_id,  "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [base_x + 50.0, 504.0, 48.0, 22.0], "text": "*~ 0.82"})
        add_box({"id": hp1_id,  "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [base_x, 532.0, 35.0, 22.0], "text": "-~"})
        add_box({"id": lp2_id,  "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [base_x + 50.0, 560.0, 88.0, 22.0], "text": "onepole~ 2800."})
        add_box({"id": sc2_id,  "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [base_x + 50.0, 588.0, 48.0, 22.0], "text": "*~ 0.76"})
        add_box({"id": hp2_id,  "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [base_x, 616.0, 35.0, 22.0], "text": "-~"})
        add_box({"id": gain_id, "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [base_x, 644.0, 42.0, 22.0], "text": "*~ 3.6"})

        add_line(in_l_id, in_l_out, sum_id, 0)
        add_line(in_r_id, in_r_out, sum_id, 1)
        add_line(sum_id, 0, half_id, 0)
        add_line(half_id, 0, hp1_id, 0)
        add_line(half_id, 0, lp1_id, 0)
        add_line(lp1_id, 0, sc1_id, 0)
        add_line(sc1_id, 0, hp1_id, 1)
        add_line(hp1_id, 0, hp2_id, 0)
        add_line(hp1_id, 0, lp2_id, 0)
        add_line(lp2_id, 0, sc2_id, 0)
        add_line(sc2_id, 0, hp2_id, 1)
        add_line(hp2_id, 0, gain_id, 0)
        add_line(gain_id, 0, "obj-spec-view", dst_inlet)

    add_tilt_chain("tilt-del", "obj-limiter-delta", 0, "obj-limiter-delta", 1, 0, 520.0)
    add_tilt_chain("tilt-ref", "obj-plugin", 0, "obj-plugin", 1, 1, 680.0)

    # =========================================================================
    # 12. ABLETON NATIVE SURFACE BACKGROUND PANEL (Covers Entire Device 248x169)
    # =========================================================================
    add_box({
        "angle": 270.0,
        "bgcolor": SURFACE_BG,
        "border": 0,
        "id": "obj-bg-main",
        "maxclass": "panel",
        "mode": 0,
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [10.0, 830.0, DEV_W, DEV_H],
        "presentation": 1,
        "presentation_rect": [0.0, 0.0, DEV_W, DEV_H],
        "proportion": 0.39,
        "rounded": 0,
        "saved_attribute_attributes": {
            "bgfillcolor": tc("live_surface_bg")
        }
    })

    out_dir_str = str(Path(__file__).resolve().parent)
    patcher = {
        "patcher": {
            "fileversion": 1,
            "appversion": {
                "major": 9,
                "minor": 0,
                "revision": 0,
                "architecture": "x64",
                "modernui": 1
            },
            "classnamespace": "box",
            "rect": [100.0, 100.0, 1100.0, 820.0],
            "openrect": [0.0, 0.0, DEV_W, DEV_H],
            "bglocked": 0,
            "openinpresentation": 1,
            "default_fontsize": 10.0,
            "default_fontface": 0,
            "default_fontname": "Arial",
            "gridonopen": 1,
            "gridsize": [15.0, 15.0],
            "gridsnaponopen": 1,
            "objectsnaponopen": 1,
            "statusbarvisible": 2,
            "toolbarvisible": 1,
            "lefttoolbarpinned": 0,
            "toptoolbarpinned": 0,
            "righttoolbarpinned": 0,
            "bottomtoolbarpinned": 0,
            "toolbars_unpinned_last_save": 0,
            "tallnewobj": 0,
            "boxanimatetime": 200,
            "enablehscroll": 1,
            "enablevscroll": 1,
            "devicewidth": DEV_W,
            "description": "Multiband Spectral Excess & Reference Difference Analyzer",
            "digest": "9-Band Octave Spectral Excess isolator and Reference Delta audition against Pink/White Noise or Tap tracks",
            "tags": "Multiband Difference Spectral Excess Analyzer Utility",
            "style": "",
            "subpatcher_template": "",
            "assistshowspatchername": 0,
            "boxes": boxes,
            "lines": lines,
            "parameters": {
                "obj-btn-audition": ["Audition Reference Delta", "Audition", 0],
                "obj-btn-mb": ["Audition Multiband Excess", "Multiband", 0],
                "obj-dial-boost": ["Difference Boost", "Boost", 0],
                "obj-num-align": ["Time Delay", "Delay", 0],
                "obj-num-ref": ["Noise Reference", "Ref", 0],
                "parameterbanks": {}
            },
            "dependency_cache": [
                {"name": "headphones.svg", "bootpath": out_dir_str, "type": "svg", "implicit": 1},
                {"name": "multiband.svg", "bootpath": out_dir_str, "type": "svg", "implicit": 1},
            ],
            "autosave": 0
        }
    }
    return patcher


def write_amxd(patcher_dict: dict, out_path: Path):
    json_bytes = json.dumps(patcher_dict, indent="\t").encode("utf-8") + b"\n\x00"
    header = bytearray()
    header += b"ampf"
    header += struct.pack("<I", 4)
    header += b"aaaa"
    header += b"meta"
    header += struct.pack("<I", 4)
    header += struct.pack("<I", 0)
    header += b"ptch"
    header += struct.pack("<I", len(json_bytes))
    out_path.write_bytes(bytes(header) + json_bytes)


def validate_patcher(patcher_dict: dict):
    boxes = patcher_dict["patcher"]["boxes"]
    lines = patcher_dict["patcher"]["lines"]
    box_map = {}
    for b in boxes:
        bx = b["box"]
        bid = bx["id"]
        assert bid not in box_map, f"Duplicate box ID: {bid}"
        box_map[bid] = bx
        if "patcher" in bx:
            validate_patcher({"patcher": bx["patcher"]})

    for ln in lines:
        pl = ln["patchline"]
        src_id, src_out = pl["source"]
        dst_id, dst_in = pl["destination"]
        assert src_id in box_map, f"Missing source box: {src_id}"
        assert dst_id in box_map, f"Missing dest box: {dst_id}"
        src_box = box_map[src_id]
        dst_box = box_map[dst_id]
        assert src_out < src_box["numoutlets"], (
            f"Invalid outlet {src_out} on {src_id} ({src_box.get('text', src_box['maxclass'])})"
        )
        assert dst_in < dst_box["numinlets"], (
            f"Invalid inlet {dst_in} on {dst_id} ({dst_box.get('text', dst_box['maxclass'])})"
        )


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    write_svg_assets(out_dir)
    amxd_path = out_dir / "OA_MultibandDifference.amxd"
    patcher_data = build_patcher()
    validate_patcher(patcher_data)
    write_amxd(patcher_data, amxd_path)
    print(f"Generated & Validated AMXD: {amxd_path} ({amxd_path.stat().st_size} bytes)")

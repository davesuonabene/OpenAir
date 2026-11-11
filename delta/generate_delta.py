#!/usr/bin/env python3
"""
OpenAir Cultural & Diagnostic Tools — OA_Delta Generator (100% Native Ableton Live Theme & UI, Zero JS)
Author: macchinette

Architecture & Aesthetic Alignment (248 x 169 px, Uniform 6px Bezel & Symmetric 28px Top/Bottom Bars):
1. Full Dynamic Ableton Theme Reactivity (`themecolor.*` across every object):
   - Device Surface: `themecolor.live_surface_bg`
   - Spectrum LCD Background: `themecolor.live_lcd_bg`
   - Spectrum LCD Border Frame: `themecolor.live_lcd_frame`
   - Reference Spectrum Fill: `themecolor.live_spectrum_default_color`
   - Delta (Δ) Spectrum Fill: `themecolor.live_spectrum_alternative_color`
   - Spectrum Grid Lines: `themecolor.live_spectrum_grid_lines`
   - Scale Labels (Hz / dB): `themecolor.live_display_scale_text`
   - Control Labels (Tap, Gain, Delay): `themecolor.live_control_fg` (Ableton Sans Small Bold)
   - Dropdowns (`umenu`) & Numboxes (`live.numbox`): `live_control_text_bg`, `live_contrast_frame`, `live_value_bar`, `live_control_fg`
   - Audition Toggle (`[🎧]`): `headphones.svg` with `remapsvgcolors=1` (`live_control_fg_off` / `live_control_fg_on`, `live_lcd_control_fg_alt`)
2. Balanced Proportions & Paddings (248 x 169 px):
   - Left/Right outer padding: 6.0 px (`x = 6.0 .. 242.0`, inner width = 236.0 px)
   - Top Bar (`y = 0.0 .. 28.0`, 28.0 px tall):
     * 5.0 px top margin, controls at `y = 5.0 .. 22.5`, 5.5 px gap above spectrum
     * `Tap` label (`x = 6.0`) + Track `umenu` (`x = 34.0, w = 101.0`) + 6px gap + Channel `umenu` (`x = 141.0, w = 101.0`, right edge `242.0`)
   - Center Spectrum (`y = 28.0 .. 141.0`, `236.0 x 113.0 px`):
     * 3-decade EQ Eight log frequency viewport + 2-stage `onepole~` midrange tilt filter
   - Bottom Bar (`y = 141.0 .. 169.0`, 28.0 px tall):
     * 6.0 px gap below spectrum, controls at `y = 147.0 .. 163.0` (`h = 16.0`), 6.0 px bottom margin
     * Audition `[🎧]` (`x = 6.0, w = 22.0`) | `Gain` (`x = 40.0`) + Numbox (`x = 71.0, w = 56.0`) | `Delay` (`x = 141.0`) + Numbox (`x = 178.0, w = 64.0`, right edge `242.0`)
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


def tc(token: str) -> dict:
    """Helper returning a Max 9 dynamic theme color expression dictionary."""
    return {"expression": f"themecolor.{token}"}


def write_svg_assets(out_dir: Path):
    """Writes pure-black vector SVG template dynamically recolored by Max via remapsvgcolors=1."""
    headphones_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 14" width="16" height="14">
  <path d="M2.75 7.5A5.25 5.25 0 0 1 13.25 7.5H11.75A3.75 3.75 0 0 0 4.25 7.5H2.75Z" fill="black"/>
  <rect x="2.0" y="6.8" width="2.4" height="4.5" rx="1.0" fill="black"/>
  <rect x="11.6" y="6.8" width="2.4" height="4.5" rx="1.0" fill="black"/>
</svg>"""
    (out_dir / "headphones.svg").write_text(headphones_svg, encoding="utf-8")


def build_spectrum_bpatcher() -> dict:
    """
    Builds the embedded `bpatcher` viewport (236 x 113 px) for the dual-layer `spectroscope~`.
    - Cropping off the leftmost 28% (`x0 = 0.28`, corresponding to 0..25 Hz in `spectroscope~`'s
      internal 4-decade log formula) maps the visible 236 px width onto a balanced 3-decade
      EQ Eight frequency scale where 500 Hz - 1 kHz sits right in the center.
    - Uses 100% native Ableton Live dynamic theme tokens (`live_lcd_bg`, `live_spectrum_default_color`,
      `live_spectrum_alternative_color`, `live_spectrum_grid_lines`) with `curvecolor` omitted so Max
      never overrides `fgcolor`.
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
                "comment": "Tilted Delta Signal"
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
                "comment": "Tilted Reference Signal"
            }
        },
        # Foreground Primary Spectrum (Delta Δ — Dynamic `live_spectrum_alternative_color`, Transparent BG)
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
        # Background Reference Spectrum (Out B — Dynamic `live_spectrum_default_color`, `live_lcd_bg`, `live_spectrum_grid_lines`)
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
    #    - "Tap" label (`live_control_fg`) + Track `umenu` + Channel `umenu`
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
        "items": ["Pre FX", ",", "Post FX", ",", "Post Mixer"],
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
    #    - Calibrated 3-decade EQ-Eight-style frequency labels ("100", "500", "1k", "5k", "10k")
    #    - dB scale labels ("0", "-18", "-36")
    #    - 1px crisp `live_lcd_frame` border + embedded `bpatcher` viewport
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

    # 1px crisp `live_lcd_frame` border around the spectrum viewport
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

    # Embedded `bpatcher` cropping the 0..25 Hz first decade of `spectroscope~`
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
    #    - Audition `[🎧]` (`remapsvgcolors=1`) + `Gain` (`live.numbox`) + `Delay` (`live.numbox`)
    # =========================================================================
    add_box({
        "id": "obj-btn-audition",
        "maxclass": "live.text",
        "varname": "AuditionDelta",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "parameter_enable": 1,
        "patching_rect": [30.0, 320.0, 22.0, 16.0],
        "presentation": 1,
        "presentation_rect": [6.0, 147.0, 22.0, 16.0],
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
                "parameter_longname": "Audition Delta",
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
        "id": "obj-lbl-row-gain",
        "maxclass": "live.comment",
        "varname": "row_lbl_gain",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [70.0, 305.0, 30.0, 15.0],
        "presentation": 1,
        "presentation_rect": [40.0, 147.5, 30.0, 15.0],
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
        "patching_rect": [70.0, 325.0, 56.0, 16.0],
        "presentation": 1,
        "presentation_rect": [71.0, 147.0, 56.0, 16.0],
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
                "parameter_longname": "Delta Boost",
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

    add_box({
        "id": "obj-lbl-row-delay",
        "maxclass": "live.comment",
        "varname": "row_lbl_delay",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [130.0, 305.0, 36.0, 15.0],
        "presentation": 1,
        "presentation_rect": [141.0, 147.5, 36.0, 15.0],
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
        "patching_rect": [130.0, 325.0, 64.0, 16.0],
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
    # 5. TAP LIVE.ROUTING CONTROLLER + PURE-MAX 2-CLICK DROPDOWN CLOSE FIX
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

    add_box({"id": "obj-init-trig", "maxclass": "newobj", "numinlets": 1, "numoutlets": 3, "outlettype": ["bang", "bang", "bang"], "patching_rect": [480.0, 42.0, 50.0, 22.0], "text": "t b b b"})
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

    def wire_umenu_prep(prefix, umenu_id, is_track):
        set_id = f"obj-{prefix}-set"
        add_box({"id": set_id, "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": [""], "patching_rect": [450.0, 215.0, 75.0, 22.0], "text": "prepend set"})
        rnone_id = f"obj-{prefix}-rnone"
        clr_id = f"obj-{prefix}-clr"
        tlclr_id = f"obj-{prefix}-tlclr"
        iter_id = f"obj-{prefix}-iter"
        app_id = f"obj-{prefix}-app"
        add_box({"id": rnone_id, "maxclass": "newobj", "numinlets": 2, "numoutlets": 2, "outlettype": ["", ""], "patching_rect": [530.0, 215.0, 80.0, 22.0], "text": "route <none>"})
        add_box({"id": clr_id, "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [530.0, 240.0, 37.0, 22.0], "text": "clear"})
        add_box({"id": tlclr_id, "maxclass": "newobj", "numinlets": 1, "numoutlets": 2, "outlettype": ["", "clear"], "patching_rect": [575.0, 240.0, 50.0, 22.0], "text": "t l clear"})
        add_box({"id": iter_id, "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": [""], "patching_rect": [575.0, 265.0, 27.0, 22.0], "text": "iter"})
        add_box({"id": app_id, "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": [""], "patching_rect": [575.0, 290.0, 96.0, 22.0], "text": "prepend append"})

        if is_track:
            add_line("obj-rgate-type", 0, set_id, 0)
            add_line("obj-rgate-tlist", 0, rnone_id, 0)
        else:
            add_line("obj-rgate-chan", 0, set_id, 0)
            add_line("obj-rgate-clist", 0, rnone_id, 0)

        add_line(set_id, 0, umenu_id, 0)
        add_line(rnone_id, 0, clr_id, 0)
        add_line(clr_id, 0, umenu_id, 0)
        add_line(rnone_id, 1, tlclr_id, 0)
        add_line(tlclr_id, 1, umenu_id, 0)
        add_line(tlclr_id, 0, iter_id, 0)
        add_line(iter_id, 0, app_id, 0)
        add_line(app_id, 0, umenu_id, 0)

        cmd_msg_id = f"obj-{prefix}-cmd"
        cmd_word = "type" if is_track else "channel"
        add_box({"id": cmd_msg_id, "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [450.0, 325.0, 67.0, 22.0], "text": f"{cmd_word} $1"})
        add_line(umenu_id, 0, cmd_msg_id, 0)
        add_line(cmd_msg_id, 0, "obj-live-routing", 0)

    wire_umenu_prep("tapa-trk", "obj-ui-menu-track-a", True)
    wire_umenu_prep("tapa-chn", "obj-ui-menu-chan-a", False)

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
        "patching_rect": [300.0, 110.0, 95.0, 22.0],
        "text": "delay~ 44100 0"
    })
    add_box({
        "id": "obj-delay-r",
        "maxclass": "newobj",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": ["signal"],
        "patching_rect": [400.0, 110.0, 95.0, 22.0],
        "text": "delay~ 44100 0"
    })
    add_line("obj-plugin", 2, "obj-delay-l", 0)
    add_line("obj-plugin", 3, "obj-delay-r", 0)
    add_line("obj-mstosamps", 1, "obj-delay-l", 1)
    add_line("obj-mstosamps", 1, "obj-delay-r", 1)

    # =========================================================================
    # 7. DELTA DSP (Activated as soon as Tap Track > 0)
    # =========================================================================
    add_box({"id": "obj-tapa-active", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["int"], "patching_rect": [220.0, 110.0, 35.0, 22.0], "text": "> 0"})
    add_line("obj-rgate-type", 0, "obj-tapa-active", 0)
    add_line("obj-ui-menu-track-a", 0, "obj-tapa-active", 0)

    add_box({"id": "obj-gate-dsp-b-l", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [220.0, 145.0, 70.0, 22.0], "text": "selector~ 1 0"})
    add_box({"id": "obj-gate-dsp-b-r", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [295.0, 145.0, 70.0, 22.0], "text": "selector~ 1 0"})
    add_box({"id": "obj-gate-dsp-a-l", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [370.0, 145.0, 70.0, 22.0], "text": "selector~ 1 0"})
    add_box({"id": "obj-gate-dsp-a-r", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [445.0, 145.0, 70.0, 22.0], "text": "selector~ 1 0"})

    add_line("obj-tapa-active", 0, "obj-gate-dsp-b-l", 0)
    add_line("obj-tapa-active", 0, "obj-gate-dsp-b-r", 0)
    add_line("obj-tapa-active", 0, "obj-gate-dsp-a-l", 0)
    add_line("obj-tapa-active", 0, "obj-gate-dsp-a-r", 0)

    add_line("obj-plugin", 0, "obj-gate-dsp-b-l", 1)
    add_line("obj-plugin", 1, "obj-gate-dsp-b-r", 1)
    add_line("obj-delay-l", 0, "obj-gate-dsp-a-l", 1)
    add_line("obj-delay-r", 0, "obj-gate-dsp-a-r", 1)

    add_box({"id": "obj-invert-a-l", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [370.0, 180.0, 38.0, 22.0], "text": "*~ -1."})
    add_box({"id": "obj-invert-a-r", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [445.0, 180.0, 38.0, 22.0], "text": "*~ -1."})
    add_line("obj-gate-dsp-a-l", 0, "obj-invert-a-l", 0)
    add_line("obj-gate-dsp-a-r", 0, "obj-invert-a-r", 0)

    add_box({"id": "obj-sum-delta-l", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [300.0, 220.0, 38.0, 22.0], "text": "+~"})
    add_box({"id": "obj-sum-delta-r", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [350.0, 220.0, 38.0, 22.0], "text": "+~"})
    add_line("obj-gate-dsp-b-l", 0, "obj-sum-delta-l", 0)
    add_line("obj-gate-dsp-b-r", 0, "obj-sum-delta-r", 0)
    add_line("obj-invert-a-l", 0, "obj-sum-delta-l", 1)
    add_line("obj-invert-a-r", 0, "obj-sum-delta-r", 1)

    add_box({"id": "obj-boost-dbtoa", "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": [""], "patching_rect": [180.0, 270.0, 41.0, 22.0], "text": "dbtoa"})
    add_line("obj-dial-boost", 0, "obj-boost-dbtoa", 0)

    add_box({"id": "obj-boost-mult-l", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [300.0, 270.0, 38.0, 22.0], "text": "*~ 1."})
    add_box({"id": "obj-boost-mult-r", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [350.0, 270.0, 38.0, 22.0], "text": "*~ 1."})
    add_line("obj-sum-delta-l", 0, "obj-boost-mult-l", 0)
    add_line("obj-sum-delta-r", 0, "obj-boost-mult-r", 0)
    add_line("obj-boost-dbtoa", 0, "obj-boost-mult-l", 1)
    add_line("obj-boost-dbtoa", 0, "obj-boost-mult-r", 1)

    add_box({"id": "obj-limiter-delta", "maxclass": "newobj", "numinlets": 2, "numoutlets": 2, "outlettype": ["signal", "signal"], "patching_rect": [300.0, 315.0, 90.0, 22.0], "text": "omx.peaklim~"})
    add_line("obj-boost-mult-l", 0, "obj-limiter-delta", 0)
    add_line("obj-boost-mult-r", 0, "obj-limiter-delta", 1)

    add_box({"id": "obj-sel-audition-l", "maxclass": "newobj", "numinlets": 3, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [250.0, 390.0, 80.0, 22.0], "text": "selector~ 2 1"})
    add_box({"id": "obj-sel-audition-r", "maxclass": "newobj", "numinlets": 3, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [350.0, 390.0, 80.0, 22.0], "text": "selector~ 2 1"})
    add_line("obj-plugin", 0, "obj-sel-audition-l", 1)
    add_line("obj-plugin", 1, "obj-sel-audition-r", 1)
    add_line("obj-limiter-delta", 0, "obj-sel-audition-l", 2)
    add_line("obj-limiter-delta", 1, "obj-sel-audition-r", 2)
    add_line("obj-sel-audition-l", 0, "obj-plugout", 0)
    add_line("obj-sel-audition-r", 0, "obj-plugout", 1)

    add_box({"id": "obj-mode-plus1", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["int"], "patching_rect": [180.0, 165.0, 29.5, 22.0], "text": "+ 1"})
    add_line("obj-btn-audition", 0, "obj-mode-plus1", 0)
    add_line("obj-mode-plus1", 0, "obj-sel-audition-l", 0)
    add_line("obj-mode-plus1", 0, "obj-sel-audition-r", 0)

    # =========================================================================
    # 8. EQ-EIGHT-BALANCED SPECTRUM PRE-EMPHASIS TILT NETWORK (Visual Feed Only)
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
    # 9. ABLETON NATIVE SURFACE BACKGROUND PANEL (Covers Entire Device 248x169)
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
            "description": "Comparative Delta Analyzer & Audition Tool",
            "digest": "Phase-cancelled delta audition, alignment, and balanced EQ-Eight-style spectrum analysis",
            "tags": "Delta Analyzer Utility",
            "style": "",
            "subpatcher_template": "",
            "assistshowspatchername": 0,
            "boxes": boxes,
            "lines": lines,
            "parameters": {
                "obj-btn-audition": ["Audition Delta", "Audition", 0],
                "obj-dial-boost": ["Delta Boost", "Boost", 0],
                "obj-num-align": ["Time Delay", "Delay", 0],
                "parameterbanks": {}
            },
            "dependency_cache": [
                {"name": "headphones.svg", "bootpath": out_dir_str, "type": "svg", "implicit": 1},
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
    amxd_path = out_dir / "OA_Delta.amxd"
    patcher_data = build_patcher()
    validate_patcher(patcher_data)
    write_amxd(patcher_data, amxd_path)
    print(f"Generated & Validated AMXD: {amxd_path} ({amxd_path.stat().st_size} bytes)")

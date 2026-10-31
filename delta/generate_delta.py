#!/usr/bin/env python3
"""
OpenAir Cultural & Diagnostic Tools — OA_Delta Generator (Ableton Live Native UI, Pure M4L Objects, Zero JS)
Author: macchinette

Architecture (1:1 Ableton Ratios & Dynamic_EQ Sidechain Strip + Opening Panel, Pure M4L Objects):
1. Far-Left Vertical Sidechain/Tap Strip (x = 0..22 px, w = 22 px, h = 169 px):
   - Surface background: #342f3f ([0.204, 0.184, 0.247, 1.0], themecolor.live_surface_bg)
   - Bottom 2px frame border (y = 167..169): #474154 ([0.278, 0.255, 0.329, 1.0])
   - Right vertical divider:
     * When closed: 2px #474154 frame divider at x = 20..22, y = 0..169
     * When open: 1px dark #0e0e13 ([0.055, 0.055, 0.075, 1.0]) inner divider at x = 21, y = 3..164
   - Top Circular Expand/Collapse Toggle (▶ / ▼):
     * True circular panel (rounded=100, border=1, #1b1821 fill, #b8b2bd ring) at [2.5, 4.0, 15.0, 15.0]
     * Crisp ▶ / ▼ SVG icon overlaid at full 15x15 px
   - Second Circular Headphones Toggle (🎧):
     * True circular panel (rounded=100, border=0, #1b1821 off / #47e2f4 cyan on) at [3.0, 22.0, 14.0, 14.0]
     * Crisp 🎧 SVG icon overlaid at full 14x14 px
   - Vertical Rotated "Tap" Label ([3.5, 118.0, 13.0, 26.0]) + True Circular Status Dot ([6.0, 151.0, 8.0, 8.0], rounded=100)
2. Left Expandable Single-Column "Tap" Panel (x = 22..99 px, w = 77 px when open; parked at x = -500 when closed):
   - Dynamically resizes device width via live.thisdevice ("setwidth 263" closed / "setwidth 340" open)
   - Right 2px frame divider at x = 97..99, y = 0..169 (#474154)
   - Bottom 2px frame bar at x = 22..99, y = 167..169 (#474154)
   - 68px-wide controls at x = 26.0:
     * [ Tap ] indicator button ([26.0, 4.0, 68.0, 15.0])
     * "Source" label ([40.0, 22.0, 48.0, 13.0])
     * Track umenu ([26.0, 36.0, 68.0, 15.0]) & Channel umenu ([26.0, 53.0, 68.0, 15.0])
     * "Delay" label ([40.0, 76.0, 48.0, 13.0]) + Delay ms numbox ([26.0, 90.0, 68.0, 14.0])
     * "SC Gain" label ([36.0, 114.0, 54.0, 13.0]) + SC Gain dB numbox ([26.0, 128.0, 68.0, 14.0])
3. Main Section (x = 22..263 closed, x = 99..340 open; width = 241 px):
   - Ableton Native Surface Background (#342f3f) everywhere EXCEPT the center graph!
   - Top Row (y = 0..22 px, on Ableton surface):
     * Analyzer Selector [ Spectrum | Phase | Levels ] ([mx + 4.0, 3.5, 178.0, 15.0], fontsize 8.5, spacious padding)
     * Hover Freq Readout (Hz) ([mx + 187.0, 3.5, 50.0, 15.0], exact same 15.0 px height as Tab Selector!)
   - Center Graph (y = 22..147 px, h = 125 px, dark graph background #14131a): Dual-Layer Spectrum, Phase, or Levels
   - Bottom Row (y = 147..167 px, on Ableton surface, plus 2px #474154 bottom border at y = 167..169):
     * Headphones Audition Toggle [ 🎧 ] (20x14) | Gain [ 0.00 dB ] (h=14) | Delay [ 0.00 ms ] (h=14)
"""

import json
import struct
from pathlib import Path

# Exact RGB colors from dynamic_eq (build_dynamic_eq.py, dynamic_eq_sc_bar.js, dynamic_eq_top_icons.js)
SURFACE_BG     = [0.204, 0.184, 0.247, 1.0]  # #342f3f (Ableton native device surface)
FRAME_DIV      = [0.278, 0.255, 0.329, 1.0]  # #474154 (2px frame borders & dividers)
INNER_DIV      = [0.055, 0.055, 0.075, 1.0]  # #0e0e13 (1px dark inner divider)
CONTROL_BG     = [0.106, 0.094, 0.129, 1.0]  # #1b1821 (button / numbox / umenu dark bg)
CONTROL_BORDER = [0.067, 0.063, 0.086, 1.0]  # #111016 (1px control border)
RING_BORDER    = [0.720, 0.700, 0.750, 1.0]  # #b8b2bf (outer ring on top circular expand button)
SLIDER_TEAL    = [0.000, 0.518, 0.576, 1.0]  # #008493 (numbox active slider bar)
ABLETON_PINK   = [1.000, 0.569, 0.765, 1.0]  # #ff91c3 (active toggle pink / delta curve)
ABLETON_CYAN   = [0.278, 0.886, 0.957, 1.0]  # #47e2f4 (active headphones / LED cyan)
LABEL_BLUE     = [0.650, 0.750, 0.840, 1.0]  # Drawer section label color from build_dynamic_eq.py
TEXT_MAIN      = [0.827, 0.804, 0.843, 1.0]  # #d3cdd7 (main control text)
TEXT_ON_DARK   = [0.080, 0.070, 0.100, 1.0]  # Dark text when toggle is lit
TEXT_DIM       = [0.561, 0.541, 0.592, 1.0]  # Scale text
GRAPH_BG       = [0.078, 0.075, 0.102, 1.0]  # Dark background ONLY for the center graph
GRAPH_GRID     = [0.169, 0.157, 0.208, 1.0]  # Graph grid lines
SPEC_FG_FILL   = [1.000, 0.569, 0.765, 0.28]
SPEC_REF_FILL  = [0.420, 0.400, 0.500, 0.24]
TRANSPARENT    = [0.000, 0.000, 0.000, 0.0]

SPINE_W = 22.0
SC_W    = 77.0
MAIN_W  = 241.0
BASE_W  = SPINE_W + MAIN_W          # 263.0 px when Tap drawer is closed
OPEN_W  = SPINE_W + SC_W + MAIN_W   # 340.0 px when Tap drawer is open
DEV_H   = 169.0


def tc(token: str) -> dict:
    """Helper returning a Max 9 dynamic theme color expression dictionary."""
    return {"expression": f"themecolor.{token}"}


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
    # 1. FAR-LEFT VERTICAL SIDECHAIN/TAP STRIP (x = 0..22, y = 0..169)
    #    Uses true circular `panel` (rounded=100) for full-size circles +
    #    transparent `live.text` overlays for crisp Ableton-ratio icons!
    # =========================================================================
    add_box({
        "id": "obj-btn-tapa-drawer",
        "maxclass": "live.text",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "parameter_enable": 1,
        "patching_rect": [30.0, 15.0, 15.0, 15.0],
        "presentation": 1,
        "presentation_rect": [2.5, 4.0, 15.0, 15.0],
        "text": "",
        "texton": "",
        "pictures": ["ableton_tri_closed.svg", "ableton_tri_open.svg"],
        "usepicture": 1,
        "remapsvgcolors": 0,
        "bgcolor": TRANSPARENT,
        "activebgcolor": TRANSPARENT,
        "activebgoncolor": TRANSPARENT,
        "bgoncolor": TRANSPARENT,
        "bordercolor": TRANSPARENT,
        "focusbordercolor": TRANSPARENT,
        "mode": 1,
        "varname": "TapADrawer",
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": "Tap Section",
                "parameter_shortname": "Tap",
                "parameter_type": 2,
                "parameter_mmax": 1,
                "parameter_enum": ["Closed", "Open"],
                "parameter_initial_enable": 1,
                "parameter_initial": [0],
                "parameter_invisible": 1
            }
        }
    })

    # True 15x15 circular background + ring behind the Expand/Collapse triangle
    add_box({
        "id": "obj-bg-circle-tri",
        "maxclass": "panel",
        "mode": 0,
        "rounded": 100,
        "border": 1,
        "bgcolor": CONTROL_BG,
        "bordercolor": RING_BORDER,
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [12.0, 15.0, 15.0, 15.0],
        "presentation": 1,
        "presentation_rect": [2.5, 4.0, 15.0, 15.0]
    })

    add_box({
        "id": "obj-btn-audition-spine",
        "maxclass": "live.text",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "parameter_enable": 0,
        "patching_rect": [30.0, 285.0, 14.0, 14.0],
        "presentation": 1,
        "presentation_rect": [3.0, 22.0, 14.0, 14.0],
        "text": "",
        "texton": "",
        "pictures": ["ableton_headphones.svg", "ableton_headphones_on.svg"],
        "usepicture": 1,
        "remapsvgcolors": 0,
        "bgcolor": TRANSPARENT,
        "activebgcolor": TRANSPARENT,
        "activebgoncolor": TRANSPARENT,
        "bgoncolor": TRANSPARENT,
        "bordercolor": TRANSPARENT,
        "focusbordercolor": TRANSPARENT,
        "mode": 1
    })

    # True 14x14 circular background behind the Spine Headphones (dark when off, cyan when on)
    add_box({
        "id": "obj-bg-circle-aud-off",
        "maxclass": "panel",
        "varname": "spine_aud_bg_off",
        "mode": 0,
        "rounded": 100,
        "border": 0,
        "bgcolor": CONTROL_BG,
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [12.0, 285.0, 14.0, 14.0],
        "presentation": 1,
        "presentation_rect": [3.0, 22.0, 14.0, 14.0]
    })
    add_box({
        "id": "obj-bg-circle-aud-on",
        "maxclass": "panel",
        "varname": "spine_aud_bg_on",
        "mode": 0,
        "rounded": 100,
        "border": 0,
        "bgcolor": ABLETON_CYAN,
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [12.0, 302.0, 14.0, 14.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 22.0, 14.0, 14.0]
    })

    # Vertical rotated "Tap" label in Spine
    add_box({
        "id": "obj-lbl-spine-tap",
        "maxclass": "live.text",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "parameter_enable": 0,
        "ignoreclick": 1,
        "patching_rect": [30.0, 350.0, 13.0, 26.0],
        "presentation": 1,
        "presentation_rect": [3.5, 118.0, 13.0, 26.0],
        "text": "",
        "texton": "",
        "pictures": ["ableton_tap_vert.svg", "ableton_tap_vert.svg"],
        "usepicture": 1,
        "remapsvgcolors": 0,
        "bgcolor": TRANSPARENT,
        "activebgcolor": TRANSPARENT,
        "activebgoncolor": TRANSPARENT,
        "bgoncolor": TRANSPARENT,
        "bordercolor": TRANSPARENT,
        "focusbordercolor": TRANSPARENT,
        "mode": 1
    })

    # True 8x8 circular Status Dot at bottom of Spine (dark #1b1821 when off, cyan #47e2f4 when active)
    add_box({
        "id": "obj-led-spine-off",
        "maxclass": "panel",
        "varname": "spine_dot_off",
        "mode": 0,
        "rounded": 100,
        "border": 0,
        "bgcolor": CONTROL_BG,
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [30.0, 375.0, 8.0, 8.0],
        "presentation": 1,
        "presentation_rect": [6.0, 151.0, 8.0, 8.0]
    })
    add_box({
        "id": "obj-led-spine-on",
        "maxclass": "panel",
        "varname": "spine_dot_on",
        "mode": 0,
        "rounded": 100,
        "border": 0,
        "bgcolor": ABLETON_CYAN,
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [42.0, 375.0, 8.0, 8.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 151.0, 8.0, 8.0]
    })

    # Spine bottom 2px frame border (x = 0..22, y = 167..169, #474154)
    add_box({
        "id": "obj-spine-bot-bar",
        "maxclass": "panel",
        "mode": 0,
        "border": 0,
        "rounded": 0,
        "bgcolor": FRAME_DIV,
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [12.0, 395.0, 22.0, 4.0],
        "presentation": 1,
        "presentation_rect": [0.0, 167.0, 22.0, 2.0]
    })

    # Spine right vertical divider:
    # When closed: 2px #474154 frame divider at [20.0, 0.0, 2.0, 169.0]
    # When open: 1px #0e0e13 dark inner divider at [21.0, 3.0, 1.0, 161.0]
    add_box({
        "id": "obj-spine-div-closed",
        "maxclass": "panel",
        "varname": "spine_div_closed",
        "mode": 0,
        "border": 0,
        "rounded": 0,
        "bgcolor": FRAME_DIV,
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [55.0, 15.0, 4.0, 100.0],
        "presentation": 1,
        "presentation_rect": [20.0, 0.0, 2.0, DEV_H]
    })

    add_box({
        "id": "obj-spine-div-open",
        "maxclass": "panel",
        "varname": "spine_div_open",
        "mode": 0,
        "border": 0,
        "rounded": 0,
        "bgcolor": INNER_DIV,
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [62.0, 15.0, 4.0, 100.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 3.0, 1.0, 161.0]
    })

    # =========================================================================
    # 2. LEFT EXPANDABLE SINGLE-COLUMN "TAP" PANEL (x = 22..99, w = 77 px)
    #    1:1 Copy of Column 1 in build_dynamic_eq.py & dynamic_eq_lom.js
    # =========================================================================
    add_box({
        "id": "obj-sc-right-div",
        "maxclass": "panel",
        "varname": "sc_right_div",
        "mode": 0,
        "border": 0,
        "rounded": 0,
        "bgcolor": FRAME_DIV,
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [115.0, 15.0, 4.0, 100.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 0.0, 2.0, DEV_H]
    })

    add_box({
        "id": "obj-sc-bot-bar",
        "maxclass": "panel",
        "varname": "sc_bot_bar",
        "mode": 0,
        "border": 0,
        "rounded": 0,
        "bgcolor": FRAME_DIV,
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [30.0, 190.0, 77.0, 4.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 167.0, SC_W, 2.0]
    })

    add_box({
        "id": "obj-drw-hdr-tap",
        "maxclass": "live.text",
        "varname": "drw_hdr_tap",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "parameter_enable": 0,
        "ignoreclick": 1,
        "patching_rect": [30.0, 42.0, 68.0, 15.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 3.5, 68.0, 15.0],
        "text": "Tap",
        "texton": "Tap",
        "fontsize": 9.0,
        "fontname": "Ableton Sans Medium",
        "mode": 1,
        "bgcolor": CONTROL_BG,
        "bgoncolor": ABLETON_PINK,
        "activebgcolor": CONTROL_BG,
        "activebgoncolor": ABLETON_PINK,
        "bordercolor": CONTROL_BORDER,
        "textcolor": TEXT_MAIN,
        "textoncolor": TEXT_ON_DARK,
        "activetextcolor": TEXT_MAIN,
        "activetextoncolor": TEXT_ON_DARK
    })

    add_box({
        "id": "obj-ui-lbl-tapa",
        "maxclass": "live.comment",
        "varname": "drw_lbl_tapa",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [30.0, 60.0, 48.0, 13.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 22.0, 48.0, 13.0],
        "text": "Source",
        "textcolor": LABEL_BLUE
    })

    add_box({
        "id": "obj-ui-menu-track-a",
        "maxclass": "umenu",
        "varname": "drw_menu_track_a",
        "numinlets": 1,
        "numoutlets": 3,
        "outlettype": ["int", "", ""],
        "parameter_enable": 0,
        "items": ["No Input"],
        "patching_rect": [450.0, 210.0, 68.0, 15.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 36.0, 68.0, 15.0],
        "bgcolor": CONTROL_BG,
        "textcolor": TEXT_MAIN,
        "fontname": "Ableton Sans Medium",
        "fontsize": 9.5
    })

    add_box({
        "id": "obj-ui-menu-chan-a",
        "maxclass": "umenu",
        "varname": "drw_menu_chan_a",
        "numinlets": 1,
        "numoutlets": 3,
        "outlettype": ["int", "", ""],
        "parameter_enable": 0,
        "items": ["Pre FX", ",", "Post FX", ",", "Post Mixer"],
        "patching_rect": [530.0, 210.0, 68.0, 15.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 53.0, 68.0, 15.0],
        "bgcolor": CONTROL_BG,
        "textcolor": TEXT_MAIN,
        "fontname": "Ableton Sans Medium",
        "fontsize": 9.5
    })

    add_box({
        "id": "obj-drw-lbl-delay",
        "maxclass": "live.comment",
        "varname": "drw_lbl_delay",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [30.0, 115.0, 48.0, 13.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 76.0, 48.0, 13.0],
        "text": "Delay",
        "textcolor": LABEL_BLUE
    })

    add_box({
        "id": "obj-drw-num-align",
        "maxclass": "live.numbox",
        "varname": "drw_num_align",
        "appearance": 2,
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "parameter_enable": 0,
        "patching_rect": [30.0, 132.0, 68.0, 14.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 90.0, 68.0, 14.0],
        "activebgcolor": CONTROL_BG,
        "activeslidercolor": SLIDER_TEAL,
        "bordercolor": CONTROL_BORDER,
        "textcolor": TEXT_MAIN,
        "unitstyle": 2,
        "mmin": 0.0,
        "mmax": 50.0
    })

    add_box({
        "id": "obj-drw-lbl-gain",
        "maxclass": "live.comment",
        "varname": "drw_lbl_gain",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [30.0, 150.0, 54.0, 13.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 114.0, 54.0, 13.0],
        "text": "SC Gain",
        "textcolor": LABEL_BLUE
    })

    add_box({
        "id": "obj-drw-num-boost",
        "maxclass": "live.numbox",
        "varname": "drw_num_boost",
        "appearance": 2,
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "parameter_enable": 0,
        "patching_rect": [30.0, 166.0, 68.0, 14.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 128.0, 68.0, 14.0],
        "activebgcolor": CONTROL_BG,
        "activeslidercolor": SLIDER_TEAL,
        "bordercolor": CONTROL_BORDER,
        "textcolor": TEXT_MAIN,
        "unitstyle": 4,
        "mmin": 0.0,
        "mmax": 36.0
    })

    # =========================================================================
    # 3. TOP ROW (y = 0..22 px, on Ableton Native Surface #342f3f)
    #    - Analyzer Selector [ Spectrum | Phase | Levels ] (height = 15.0 px, fontsize = 8.5)
    #    - Hover Frequency Readout (Hz) (exact same height = 15.0 px at y = 3.5)
    # =========================================================================
    add_box({
        "id": "obj-tab-nav",
        "maxclass": "live.tab",
        "varname": "ViewTab",
        "num_lines_patching": 1,
        "num_lines_presentation": 1,
        "numinlets": 1,
        "numoutlets": 3,
        "outlettype": ["", "", "float"],
        "parameter_enable": 1,
        "patching_rect": [130.0, 15.0, 178.0, 15.0],
        "presentation": 1,
        "presentation_rect": [26.0, 3.5, 178.0, 15.0],
        "pictures": [],
        "bgcolor": CONTROL_BG,
        "bgoncolor": ABLETON_PINK,
        "activebgcolor": CONTROL_BG,
        "activebgoncolor": ABLETON_PINK,
        "bordercolor": CONTROL_BORDER,
        "textcolor": TEXT_MAIN,
        "textoncolor": TEXT_ON_DARK,
        "fontsize": 8.5,
        "fontname": "Ableton Sans Medium",
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_enum": ["Spectrum", "Phase", "Levels"],
                "parameter_initial": [0],
                "parameter_initial_enable": 1,
                "parameter_longname": "Visualizer View",
                "parameter_mmax": 2,
                "parameter_shortname": "View",
                "parameter_type": 2,
                "parameter_unitstyle": 9,
                "parameter_invisible": 1
            }
        }
    })

    add_box({
        "id": "obj-num-spec-freq",
        "maxclass": "live.numbox",
        "varname": "p0_num_freq",
        "appearance": 2,
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "parameter_enable": 1,
        "patching_rect": [660.0, 275.0, 50.0, 15.0],
        "presentation": 1,
        "presentation_rect": [209.0, 3.5, 50.0, 15.0],
        "fontsize": 8.5,
        "fontname": "Ableton Sans Medium",
        "activebgcolor": CONTROL_BG,
        "activeslidercolor": CONTROL_BG,
        "bordercolor": CONTROL_BORDER,
        "textcolor": ABLETON_PINK,
        "ignoreclick": 1,
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": "Hover Frequency",
                "parameter_shortname": "Freq",
                "parameter_type": 0,
                "parameter_mmin": 20.0,
                "parameter_mmax": 20000.0,
                "parameter_initial_enable": 1,
                "parameter_initial": [1000.0],
                "parameter_unitstyle": 3,
                "parameter_invisible": 1
            }
        }
    })

    # =========================================================================
    # 4. BOTTOM ROW (y = 147..167 px, on Ableton Native Surface #342f3f)
    #    - Headphones Audition Toggle [ 🎧 ] (20x14, with native box border & cyan active fill)
    #    - "Gain" label + [ 0.00 dB ] numbox (h = 14.0)
    #    - "Delay" label + [ 0.00 ms ] numbox (h = 14.0)
    #    - Bottom 2px frame border (y = 167..169, #474154)
    # =========================================================================
    add_box({
        "id": "obj-main-bot-bar",
        "maxclass": "panel",
        "varname": "main_bot_bar",
        "mode": 0,
        "border": 0,
        "rounded": 0,
        "bgcolor": FRAME_DIV,
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [130.0, 355.0, 241.0, 4.0],
        "presentation": 1,
        "presentation_rect": [22.0, 167.0, MAIN_W, 2.0]
    })

    add_box({
        "id": "obj-btn-audition",
        "maxclass": "live.text",
        "varname": "AuditionDelta",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "parameter_enable": 1,
        "patching_rect": [30.0, 320.0, 20.0, 14.0],
        "presentation": 1,
        "presentation_rect": [26.0, 150.5, 20.0, 14.0],
        "text": "",
        "texton": "",
        "pictures": ["ableton_headphones_row.svg", "ableton_headphones_row_on.svg"],
        "usepicture": 1,
        "remapsvgcolors": 0,
        "bgcolor": CONTROL_BG,
        "activebgcolor": CONTROL_BG,
        "activebgoncolor": ABLETON_CYAN,
        "bgoncolor": ABLETON_CYAN,
        "bordercolor": CONTROL_BORDER,
        "focusbordercolor": CONTROL_BORDER,
        "mode": 1,
        "saved_attribute_attributes": {
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

    # Bi-directional sync between Bottom Row Headphones and Left Spine Headphones + Circular Background
    add_box({"id": "obj-set-aud-spine", "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": [""], "patching_rect": [60.0, 285.0, 72.0, 22.0], "text": "prepend set"})
    add_line("obj-btn-audition", 0, "obj-set-aud-spine", 0)
    add_line("obj-set-aud-spine", 0, "obj-btn-audition-spine", 0)
    add_line("obj-btn-audition-spine", 0, "obj-btn-audition", 0)

    # Toggle the circular cyan/dark background behind the spine headphones button
    add_box({"id": "obj-sel-aud-bg", "maxclass": "newobj", "numinlets": 3, "numoutlets": 3, "outlettype": ["bang", "bang", ""], "patching_rect": [60.0, 315.0, 58.0, 22.0], "text": "sel 0 1"})
    add_box({"id": "obj-msg-aud-off", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [60.0, 342.0, 120.0, 22.0], "text": "script sendbox spine_aud_bg_off presentation_rect 3. 22. 14. 14., script sendbox spine_aud_bg_on presentation_rect -500. 22. 14. 14."})
    add_box({"id": "obj-msg-aud-on", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [190.0, 342.0, 120.0, 22.0], "text": "script sendbox spine_aud_bg_off presentation_rect -500. 22. 14. 14., script sendbox spine_aud_bg_on presentation_rect 3. 22. 14. 14."})
    add_line("obj-btn-audition", 0, "obj-sel-aud-bg", 0)
    add_line("obj-sel-aud-bg", 0, "obj-msg-aud-off", 0)
    add_line("obj-sel-aud-bg", 1, "obj-msg-aud-on", 0)

    # Inline "Gain" Label + Numbox in Bottom Row
    add_box({
        "id": "obj-lbl-row-gain",
        "maxclass": "live.comment",
        "varname": "row_lbl_gain",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [70.0, 305.0, 30.0, 14.0],
        "presentation": 1,
        "presentation_rect": [58.0, 150.5, 30.0, 14.0],
        "text": "Gain",
        "textcolor": LABEL_BLUE
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
        "patching_rect": [70.0, 325.0, 54.0, 14.0],
        "presentation": 1,
        "presentation_rect": [88.0, 150.5, 54.0, 14.0],
        "activebgcolor": CONTROL_BG,
        "activeslidercolor": SLIDER_TEAL,
        "bordercolor": CONTROL_BORDER,
        "textcolor": TEXT_MAIN,
        "saved_attribute_attributes": {
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

    # Inline "Delay" Label on Left + ms Numbox on Right in Bottom Row
    add_box({
        "id": "obj-lbl-row-delay",
        "maxclass": "live.comment",
        "varname": "row_lbl_delay",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [130.0, 305.0, 36.0, 14.0],
        "presentation": 1,
        "presentation_rect": [156.0, 150.5, 36.0, 14.0],
        "text": "Delay",
        "textcolor": LABEL_BLUE
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
        "patching_rect": [130.0, 325.0, 62.0, 14.0],
        "presentation": 1,
        "presentation_rect": [193.0, 150.5, 62.0, 14.0],
        "activebgcolor": CONTROL_BG,
        "activeslidercolor": SLIDER_TEAL,
        "bordercolor": CONTROL_BORDER,
        "textcolor": TEXT_MAIN,
        "saved_attribute_attributes": {
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

    # Sync Tap Column Delay & Gain boxes bi-directionally with Bottom Row parameters
    add_box({"id": "obj-set-drw-align", "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": [""], "patching_rect": [130.0, 205.0, 72.0, 22.0], "text": "prepend set"})
    add_line("obj-num-align", 0, "obj-set-drw-align", 0)
    add_line("obj-set-drw-align", 0, "obj-drw-num-align", 0)
    add_line("obj-drw-num-align", 0, "obj-num-align", 0)

    add_box({"id": "obj-set-drw-boost", "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": [""], "patching_rect": [70.0, 350.0, 72.0, 22.0], "text": "prepend set"})
    add_line("obj-dial-boost", 0, "obj-set-drw-boost", 0)
    add_line("obj-set-drw-boost", 0, "obj-drw-num-boost", 0)
    add_line("obj-drw-num-boost", 0, "obj-dial-boost", 0)

    # =========================================================================
    # 5. TAB 0 (SPECTRUM) — DUAL-LAYER ANALYZER (y = 22.0..147.0 px, h = 125.0 px)
    #     ONLY the center graph has the dark GRAPH_BG!
    # =========================================================================
    freq_markers = [
        ("100", 0.2330),
        ("500", 0.4660),
        ("1k",  0.5663),
        ("5k",  0.7993),
        ("10k", 0.8997),
    ]
    for lbl_txt, u_pos in freq_markers:
        vname = f"p0_freq_{lbl_txt}"
        px = round(22.0 + u_pos * MAIN_W - 11.0, 1)
        add_box({
            "id": f"obj-spec-f-{lbl_txt}",
            "maxclass": "live.comment",
            "varname": vname,
            "numinlets": 1,
            "numoutlets": 0,
            "patching_rect": [550.0, 490.0, 24.0, 12.0],
            "presentation": 1,
            "presentation_rect": [px, 134.0, 24.0, 12.0],
            "text": lbl_txt,
            "fontsize": 7.5,
            "fontname": "Ableton Sans Medium",
            "textcolor": TEXT_DIM,
            "textjustification": 1
        })

    db_markers = [
        ("0",    24.0),
        ("-18",  64.0),
        ("-36", 104.0),
    ]
    for idx_db, (db_txt, py) in enumerate(db_markers):
        vname = f"p0_db_{idx_db}"
        add_box({
            "id": f"obj-spec-db-{idx_db}",
            "maxclass": "live.comment",
            "varname": vname,
            "numinlets": 1,
            "numoutlets": 0,
            "patching_rect": [580.0, 490.0 + idx_db * 15.0, 22.0, 12.0],
            "presentation": 1,
            "presentation_rect": [238.0, py, 22.0, 12.0],
            "text": db_txt,
            "fontsize": 7.0,
            "fontname": "Ableton Sans Medium",
            "textcolor": TEXT_DIM,
            "textjustification": 2
        })

    # Foreground Primary Spectrum (Delta Δ in Rose-Pink, Transparent Background)
    add_box({
        "id": "obj-spectroscope",
        "maxclass": "spectroscope~",
        "varname": "p0_spectroscope",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [550.0, 380.0, 241.0, 125.0],
        "presentation": 1,
        "presentation_rect": [22.0, 22.0, MAIN_W, 125.0],
        "bgcolor": TRANSPARENT,
        "fgcolor": SPEC_FG_FILL,
        "curvecolor": ABLETON_PINK,
        "markercolor": TRANSPARENT,
        "border": 1,
        "bordercolor": CONTROL_BORDER,
        "rounded": 0,
        "domain": [20.0, 20000.0],
        "range": [0.0, 1.0],
        "logfreq": 1,
        "logamp": 1,
        "interval": 45
    })

    # Background Reference Silhouette Spectrum (Out B + Dark Graph Background)
    add_box({
        "id": "obj-spec-ref",
        "maxclass": "spectroscope~",
        "varname": "p0_spec_ref",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [550.0, 500.0, 241.0, 125.0],
        "presentation": 1,
        "presentation_rect": [22.0, 22.0, MAIN_W, 125.0],
        "bgcolor": GRAPH_BG,
        "fgcolor": SPEC_REF_FILL,
        "curvecolor": TEXT_DIM,
        "markercolor": GRAPH_GRID,
        "border": 1,
        "bordercolor": CONTROL_BORDER,
        "rounded": 0,
        "domain": [20.0, 20000.0],
        "range": [0.0, 1.0],
        "logfreq": 1,
        "logamp": 1,
        "interval": 45
    })

    add_box({"id": "obj-spec-unp", "maxclass": "newobj", "numinlets": 1, "numoutlets": 2, "outlettype": ["float", "float"], "patching_rect": [660.0, 345.0, 75.0, 22.0], "text": "unpack 0. 0."})
    add_box({"id": "obj-spec-split", "maxclass": "newobj", "numinlets": 3, "numoutlets": 2, "outlettype": ["float", "float"], "patching_rect": [660.0, 310.0, 95.0, 22.0], "text": "split 20. 20000."})
    add_line("obj-spectroscope", 0, "obj-spec-unp", 0)
    add_line("obj-spec-unp", 0, "obj-spec-split", 0)
    add_line("obj-spec-split", 0, "obj-num-spec-freq", 0)

    # =========================================================================
    # 6. TAB 1 (PHASE) VISUALIZER (y = 22.0..147.0 px, h = 125.0 px)
    # =========================================================================
    add_box({
        "id": "obj-lbl-corr",
        "maxclass": "live.comment",
        "varname": "p1_lbl_corr",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [980.0, 380.0, 52.0, 14.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 25.0, 52.0, 14.0],
        "text": "Phase Corr",
        "fontsize": 8.0,
        "fontname": "Ableton Sans Medium",
        "textcolor": TEXT_DIM,
        "textjustification": 2
    })

    add_box({
        "id": "obj-num-corr",
        "maxclass": "live.numbox",
        "varname": "p1_num_corr",
        "appearance": 4,
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "parameter_enable": 1,
        "patching_rect": [980.0, 405.0, 46.0, 15.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 39.0, 46.0, 15.0],
        "lcdbgcolor": GRAPH_BG,
        "lcdcolor": ABLETON_PINK,
        "fontsize": 9.0,
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": "Phase Correlation",
                "parameter_shortname": "Corr",
                "parameter_type": 0,
                "parameter_mmin": -1.0,
                "parameter_mmax": 1.0,
                "parameter_initial_enable": 1,
                "parameter_initial": [0.0],
                "parameter_invisible": 1
            }
        }
    })

    add_box({
        "id": "obj-phasescope",
        "maxclass": "scope~",
        "varname": "p1_phasescope",
        "numinlets": 2,
        "numoutlets": 0,
        "patching_rect": [820.0, 380.0, 241.0, 125.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 22.0, MAIN_W, 125.0],
        "bgcolor": GRAPH_BG,
        "fgcolor": ABLETON_PINK,
        "gridcolor": GRAPH_GRID,
        "border": 1,
        "bordercolor": CONTROL_BORDER,
        "xy": 1,
        "automatic": 0
    })

    # =========================================================================
    # 7. TAB 2 (LEVELS) SMART COMPARISON VISUALIZER (y = 22.0..147.0 px, h = 125.0 px)
    # =========================================================================
    add_box({
        "id": "obj-lvl-lbl-a",
        "maxclass": "live.comment",
        "varname": "p2_lbl_a",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [700.0, 520.0, 42.0, 13.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 24.0, 42.0, 13.0],
        "text": "Tap",
        "fontsize": 8.5,
        "fontname": "Ableton Sans Medium",
        "textcolor": TEXT_MAIN,
        "textjustification": 1
    })
    add_box({
        "id": "obj-lvl-meter-a",
        "maxclass": "live.meter~",
        "varname": "p2_meter_a",
        "numinlets": 2,
        "numoutlets": 2,
        "outlettype": ["float", "int"],
        "patching_rect": [700.0, 540.0, 18.0, 84.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 39.0, 18.0, 84.0],
        "orientation": 0
    })
    add_box({
        "id": "obj-lvl-db-a",
        "maxclass": "live.numbox",
        "varname": "p2_db_a",
        "appearance": 4,
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "parameter_enable": 1,
        "patching_rect": [700.0, 615.0, 42.0, 15.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 127.0, 42.0, 15.0],
        "fontsize": 8.5,
        "lcdbgcolor": GRAPH_BG,
        "lcdcolor": TEXT_MAIN,
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": "Tap Level dB",
                "parameter_shortname": "LvA",
                "parameter_type": 0,
                "parameter_mmin": -70.0,
                "parameter_mmax": 6.0,
                "parameter_initial_enable": 1,
                "parameter_initial": [-70.0],
                "parameter_unitstyle": 4,
                "parameter_invisible": 1
            }
        }
    })

    add_box({
        "id": "obj-lvl-lbl-b",
        "maxclass": "live.comment",
        "varname": "p2_lbl_b",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [755.0, 520.0, 42.0, 13.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 24.0, 42.0, 13.0],
        "text": "Out",
        "fontsize": 8.5,
        "fontname": "Ableton Sans Medium",
        "textcolor": TEXT_MAIN,
        "textjustification": 1
    })
    add_box({
        "id": "obj-lvl-meter-b",
        "maxclass": "live.meter~",
        "varname": "p2_meter_b",
        "numinlets": 2,
        "numoutlets": 2,
        "outlettype": ["float", "int"],
        "patching_rect": [755.0, 540.0, 18.0, 84.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 39.0, 18.0, 84.0],
        "orientation": 0
    })
    add_box({
        "id": "obj-lvl-db-b",
        "maxclass": "live.numbox",
        "varname": "p2_db_b",
        "appearance": 4,
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "parameter_enable": 1,
        "patching_rect": [755.0, 615.0, 42.0, 15.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 127.0, 42.0, 15.0],
        "fontsize": 8.5,
        "lcdbgcolor": GRAPH_BG,
        "lcdcolor": TEXT_MAIN,
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": "Out Level dB",
                "parameter_shortname": "LvB",
                "parameter_type": 0,
                "parameter_mmin": -70.0,
                "parameter_mmax": 6.0,
                "parameter_initial_enable": 1,
                "parameter_initial": [-70.0],
                "parameter_unitstyle": 4,
                "parameter_invisible": 1
            }
        }
    })

    add_box({
        "id": "obj-lvl-lbl-d",
        "maxclass": "live.comment",
        "varname": "p2_lbl_d",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [810.0, 520.0, 46.0, 13.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 24.0, 46.0, 13.0],
        "text": "Delta",
        "fontsize": 8.5,
        "fontname": "Ableton Sans Medium",
        "textcolor": ABLETON_PINK,
        "textjustification": 1
    })
    add_box({
        "id": "obj-lvl-meter-d",
        "maxclass": "live.meter~",
        "varname": "p2_meter_d",
        "numinlets": 2,
        "numoutlets": 2,
        "outlettype": ["float", "int"],
        "patching_rect": [810.0, 540.0, 18.0, 84.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 39.0, 18.0, 84.0],
        "orientation": 0
    })
    add_box({
        "id": "obj-lvl-db-d",
        "maxclass": "live.numbox",
        "varname": "p2_db_d",
        "appearance": 4,
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "parameter_enable": 1,
        "patching_rect": [810.0, 615.0, 42.0, 15.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 127.0, 42.0, 15.0],
        "fontsize": 8.5,
        "lcdbgcolor": GRAPH_BG,
        "lcdcolor": ABLETON_PINK,
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": "Delta Null Depth dB",
                "parameter_shortname": "LvD",
                "parameter_type": 0,
                "parameter_mmin": -70.0,
                "parameter_mmax": 6.0,
                "parameter_initial_enable": 1,
                "parameter_initial": [-70.0],
                "parameter_unitstyle": 4,
                "parameter_invisible": 1
            }
        }
    })

    add_box({
        "id": "obj-lvl-lbl-diff",
        "maxclass": "live.comment",
        "varname": "p2_lbl_diff",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [870.0, 540.0, 54.0, 14.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 56.0, 54.0, 14.0],
        "text": "Diff",
        "fontsize": 8.5,
        "fontname": "Ableton Sans Medium",
        "textcolor": TEXT_DIM,
        "textjustification": 1
    })
    add_box({
        "id": "obj-lvl-db-diff",
        "maxclass": "live.numbox",
        "varname": "p2_db_diff",
        "appearance": 4,
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "parameter_enable": 1,
        "patching_rect": [870.0, 560.0, 50.0, 16.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 72.0, 50.0, 16.0],
        "fontsize": 9.5,
        "lcdbgcolor": GRAPH_BG,
        "lcdcolor": ABLETON_PINK,
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": "Gain Difference dB",
                "parameter_shortname": "Diff",
                "parameter_type": 0,
                "parameter_mmin": -36.0,
                "parameter_mmax": 36.0,
                "parameter_initial_enable": 1,
                "parameter_initial": [0.0],
                "parameter_unitstyle": 4,
                "parameter_invisible": 1
            }
        }
    })

    add_box({
        "id": "obj-lvl-bg",
        "maxclass": "panel",
        "varname": "p2_bg",
        "mode": 0,
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [700.0, 665.0, 241.0, 125.0],
        "presentation": 1,
        "presentation_rect": [-500.0, 22.0, MAIN_W, 125.0],
        "bgcolor": GRAPH_BG,
        "border": 1,
        "bordercolor": CONTROL_BORDER,
        "rounded": 0
    })

    # =========================================================================
    # 8. AUDIO I/O (4-Channel plugin~: 1/2=Device Pos, 3/4=Tap Sidechain)
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
    # 9. TAP LIVE.ROUTING CONTROLLER + SETWIDTH MANAGER (Zero JS)
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

    add_box({"id": "obj-init-trig", "maxclass": "newobj", "numinlets": 1, "numoutlets": 2, "outlettype": ["bang", "bang"], "patching_rect": [480.0, 42.0, 40.0, 22.0], "text": "t b b"})
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

    # Pure Max setwidth controller (matches dynamic_eq_lom.js -> deferlow -> live.thisdevice)
    add_box({"id": "obj-sel-width", "maxclass": "newobj", "numinlets": 3, "numoutlets": 3, "outlettype": ["bang", "bang", ""], "patching_rect": [630.0, 15.0, 60.0, 22.0], "text": "sel 0 1"})
    add_box({"id": "obj-msg-w-closed", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [630.0, 42.0, 82.0, 22.0], "text": f"setwidth {int(BASE_W)}"})
    add_box({"id": "obj-msg-w-open", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [720.0, 42.0, 82.0, 22.0], "text": f"setwidth {int(OPEN_W)}"})
    add_box({"id": "obj-defer-width", "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": [""], "patching_rect": [630.0, 68.0, 56.0, 22.0], "text": "deferlow"})

    add_line("obj-btn-tapa-drawer", 0, "obj-sel-width", 0)
    add_line("obj-sel-width", 0, "obj-msg-w-closed", 0)
    add_line("obj-sel-width", 1, "obj-msg-w-open", 0)
    add_line("obj-msg-w-closed", 0, "obj-defer-width", 0)
    add_line("obj-msg-w-open", 0, "obj-defer-width", 0)
    add_line("obj-defer-width", 0, "obj-thisdevice", 0)

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

    add_box({"id": "obj-rgate-type", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [450.0, 185.0, 55.0, 22.0], "text": "gate 1 0"})
    add_box({"id": "obj-rgate-chan", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [515.0, 185.0, 55.0, 22.0], "text": "gate 1 0"})
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

    # =========================================================================
    # 10. TIME DELAY ALIGNMENT IN MS (mstosamps~ -> delay~ on Tap channels 3/4)
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
    # 11. DELTA DSP (Activated as soon as Tap Track > 0)
    # =========================================================================
    add_box({"id": "obj-tapa-active", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["int"], "patching_rect": [220.0, 110.0, 35.0, 22.0], "text": "> 0"})
    add_line("obj-rgate-type", 0, "obj-tapa-active", 0)
    add_line("obj-ui-menu-track-a", 0, "obj-tapa-active", 0)
    add_line("obj-tapa-active", 0, "obj-drw-hdr-tap", 0)

    # Toggle the true circular 8x8 status dot at bottom of Spine
    add_box({"id": "obj-sel-dot-bg", "maxclass": "newobj", "numinlets": 3, "numoutlets": 3, "outlettype": ["bang", "bang", ""], "patching_rect": [220.0, 75.0, 58.0, 22.0], "text": "sel 0 1"})
    add_box({"id": "obj-msg-dot-off", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [285.0, 60.0, 120.0, 22.0], "text": "script sendbox spine_dot_off presentation_rect 6. 151. 8. 8., script sendbox spine_dot_on presentation_rect -500. 151. 8. 8."})
    add_box({"id": "obj-msg-dot-on", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [285.0, 85.0, 120.0, 22.0], "text": "script sendbox spine_dot_off presentation_rect -500. 151. 8. 8., script sendbox spine_dot_on presentation_rect 6. 151. 8. 8."})
    add_line("obj-tapa-active", 0, "obj-sel-dot-bg", 0)
    add_line("obj-sel-dot-bg", 0, "obj-msg-dot-off", 0)
    add_line("obj-sel-dot-bg", 1, "obj-msg-dot-on", 0)

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
    # 12. CPU-OPTIMIZED VISUALIZER ROUTING (Dual-Layer Spectrum, Phase, Levels)
    # =========================================================================
    add_box({"id": "obj-gate-spectrum", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [550.0, 345.0, 70.0, 22.0], "text": "selector~ 1 1"})
    add_box({"id": "obj-gate-spec-ref", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [470.0, 345.0, 70.0, 22.0], "text": "selector~ 1 1"})
    add_line("obj-limiter-delta", 0, "obj-gate-spectrum", 1)
    add_line("obj-plugin", 0, "obj-gate-spec-ref", 1)
    add_line("obj-gate-spectrum", 0, "obj-spectroscope", 0)
    add_line("obj-gate-spec-ref", 0, "obj-spec-ref", 0)

    add_box({"id": "obj-gate-phase-l", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [820.0, 345.0, 70.0, 22.0], "text": "selector~ 1 0"})
    add_box({"id": "obj-gate-phase-r", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [900.0, 345.0, 70.0, 22.0], "text": "selector~ 1 0"})
    add_line("obj-limiter-delta", 0, "obj-gate-phase-l", 1)
    add_line("obj-limiter-delta", 1, "obj-gate-phase-r", 1)
    add_line("obj-gate-phase-l", 0, "obj-phasescope", 0)
    add_line("obj-gate-phase-r", 0, "obj-phasescope", 1)

    add_box({"id": "obj-corr-mult", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [950.0, 380.0, 38.0, 22.0], "text": "*~"})
    add_box({"id": "obj-corr-avg", "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [950.0, 410.0, 105.0, 22.0], "text": "average~ 2048 rms"})
    add_box({"id": "obj-corr-snap", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["float"], "patching_rect": [950.0, 440.0, 75.0, 22.0], "text": "snapshot~ 0"})
    add_line("obj-gate-phase-l", 0, "obj-corr-mult", 0)
    add_line("obj-gate-phase-r", 0, "obj-corr-mult", 1)
    add_line("obj-corr-mult", 0, "obj-corr-avg", 0)
    add_line("obj-corr-avg", 0, "obj-corr-snap", 0)
    add_line("obj-corr-snap", 0, "obj-num-corr", 0)

    add_box({"id": "obj-gate-lvl-a-l", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [700.0, 490.0, 65.0, 22.0], "text": "selector~ 1 0"})
    add_box({"id": "obj-gate-lvl-a-r", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [770.0, 490.0, 65.0, 22.0], "text": "selector~ 1 0"})
    add_box({"id": "obj-gate-lvl-b-l", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [840.0, 490.0, 65.0, 22.0], "text": "selector~ 1 0"})
    add_box({"id": "obj-gate-lvl-b-r", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [910.0, 490.0, 65.0, 22.0], "text": "selector~ 1 0"})
    add_box({"id": "obj-gate-lvl-d-l", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [980.0, 490.0, 65.0, 22.0], "text": "selector~ 1 0"})
    add_box({"id": "obj-gate-lvl-d-r", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [1050.0, 490.0, 65.0, 22.0], "text": "selector~ 1 0"})

    add_line("obj-delay-l", 0, "obj-gate-lvl-a-l", 1)
    add_line("obj-delay-r", 0, "obj-gate-lvl-a-r", 1)
    add_line("obj-plugin", 0, "obj-gate-lvl-b-l", 1)
    add_line("obj-plugin", 1, "obj-gate-lvl-b-r", 1)
    add_line("obj-sum-delta-l", 0, "obj-gate-lvl-d-l", 1)
    add_line("obj-sum-delta-r", 0, "obj-gate-lvl-d-r", 1)

    add_line("obj-gate-lvl-a-l", 0, "obj-lvl-meter-a", 0)
    add_line("obj-gate-lvl-a-r", 0, "obj-lvl-meter-a", 1)
    add_line("obj-gate-lvl-b-l", 0, "obj-lvl-meter-b", 0)
    add_line("obj-gate-lvl-b-r", 0, "obj-lvl-meter-b", 1)
    add_line("obj-gate-lvl-d-l", 0, "obj-lvl-meter-d", 0)
    add_line("obj-gate-lvl-d-r", 0, "obj-lvl-meter-d", 1)

    add_box({"id": "obj-atodb-a", "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": [""], "patching_rect": [700.0, 645.0, 41.0, 22.0], "text": "atodb"})
    add_box({"id": "obj-atodb-b", "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": [""], "patching_rect": [755.0, 645.0, 41.0, 22.0], "text": "atodb"})
    add_box({"id": "obj-atodb-d", "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": [""], "patching_rect": [810.0, 645.0, 41.0, 22.0], "text": "atodb"})
    add_box({"id": "obj-diff-sub", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["float"], "patching_rect": [870.0, 645.0, 35.0, 22.0], "text": "- 0."})

    add_line("obj-lvl-meter-a", 0, "obj-atodb-a", 0)
    add_line("obj-lvl-meter-b", 0, "obj-atodb-b", 0)
    add_line("obj-lvl-meter-d", 0, "obj-atodb-d", 0)
    add_line("obj-atodb-a", 0, "obj-lvl-db-a", 0)
    add_line("obj-atodb-b", 0, "obj-lvl-db-b", 0)
    add_line("obj-atodb-d", 0, "obj-lvl-db-d", 0)
    add_line("obj-atodb-b", 0, "obj-diff-sub", 0)
    add_line("obj-atodb-a", 0, "obj-diff-sub", 1)
    add_line("obj-diff-sub", 0, "obj-lvl-db-diff", 0)

    # =========================================================================
    # 13. ABLETON NATIVE SURFACE BACKGROUND PANEL (Covers Entire Device Width)
    #     Everything except the center graph sits on this #342f3f surface!
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
        "patching_rect": [10.0, 830.0, OPEN_W, DEV_H],
        "presentation": 1,
        "presentation_rect": [0.0, 0.0, OPEN_W, DEV_H],
        "proportion": 0.39,
        "rounded": 0,
        "saved_attribute_attributes": {
            "bgfillcolor": tc("live_surface_bg")
        }
    })

    # =========================================================================
    # 14. PURE M4L DYNAMIC LAYOUT CONTROLLER (thispatcher, Zero JS)
    #     Matches dynamic_eq_lom.js update_layout() 1:1 using presentation_rect!
    # =========================================================================
    add_box({
        "id": "obj-thispatcher",
        "maxclass": "newobj",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "patching_rect": [150.0, 690.0, 70.0, 22.0],
        "text": "thispatcher",
        "save": ["#N", "thispatcher", ";"]
    })

    add_line("obj-msg-aud-off", 0, "obj-thispatcher", 0)
    add_line("obj-msg-aud-on", 0, "obj-thispatcher", 0)
    add_line("obj-msg-dot-off", 0, "obj-thispatcher", 0)
    add_line("obj-msg-dot-on", 0, "obj-thispatcher", 0)

    add_box({"id": "obj-pak-ui", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [150.0, 460.0, 52.0, 22.0], "text": "pak 0 0"})
    add_box({"id": "obj-route-ui", "maxclass": "newobj", "numinlets": 7, "numoutlets": 7, "outlettype": ["", "", "", "", "", "", ""], "patching_rect": [150.0, 495.0, 240.0, 22.0], "text": "route 0_1 0_0 1_1 1_0 2_1 2_0"})
    add_box({"id": "obj-fmt-ui", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [210.0, 460.0, 88.0, 22.0], "text": "sprintf %ld_%ld"})

    add_line("obj-tab-nav", 0, "obj-pak-ui", 0)
    add_line("obj-btn-tapa-drawer", 0, "obj-pak-ui", 1)
    add_line("obj-pak-ui", 0, "obj-fmt-ui", 0)
    add_line("obj-fmt-ui", 0, "obj-route-ui", 0)
    add_line("obj-init-p1", 0, "obj-pak-ui", 0)

    freq_u_map = {
        "p0_freq_100": 0.2330,
        "p0_freq_500": 0.4660,
        "p0_freq_1k":  0.5663,
        "p0_freq_5k":  0.7993,
        "p0_freq_10k": 0.8997,
    }

    def build_layout_script(tab_idx: int, drawer_open: bool) -> str:
        x_off = SC_W if drawer_open else 0.0
        mx = SPINE_W + x_off  # 22.0 when closed, 99.0 when open
        sx = SPINE_W          # 22.0

        cmds = []

        def set_rect(varname, x, y, w, h, vis):
            fx = round(x, 1) if vis else -500.0
            cmds.append(f"script sendbox {varname} presentation_rect {fx} {round(y, 1)} {round(w, 1)} {round(h, 1)}")

        # 1. Spine right divider (2px #474154 when closed, 1px #0e0e13 when open)
        set_rect("spine_div_closed", 20.0, 0.0, 2.0, DEV_H, not drawer_open)
        set_rect("spine_div_open",   21.0, 3.0, 1.0, 161.0, drawer_open)

        # 2. Expandable "Tap" Column (x = 22..99 when drawer_open)
        set_rect("sc_bot_bar",       sx, 167.0, SC_W, 2.0, drawer_open)
        set_rect("sc_right_div",     sx + SC_W - 2.0, 0.0, 2.0, DEV_H, drawer_open)
        set_rect("drw_hdr_tap",      sx + 4.0,   3.5, 68.0, 15.0, drawer_open)
        set_rect("drw_lbl_tapa",     sx + 18.0, 22.0, 48.0, 13.0, drawer_open)
        set_rect("drw_menu_track_a", sx + 4.0,  36.0, 68.0, 15.0, drawer_open)
        set_rect("drw_menu_chan_a",  sx + 4.0,  53.0, 68.0, 15.0, drawer_open)
        set_rect("drw_lbl_delay",    sx + 18.0, 76.0, 48.0, 13.0, drawer_open)
        set_rect("drw_num_align",    sx + 4.0,  90.0, 68.0, 14.0, drawer_open)
        set_rect("drw_lbl_gain",     sx + 14.0, 114.0, 54.0, 13.0, drawer_open)
        set_rect("drw_num_boost",    sx + 4.0,  128.0, 68.0, 14.0, drawer_open)

        # 3. Main Top Row & Bottom Row (shifted by x_off; ViewTab & p0_num_freq both height = 15.0 at y = 3.5)
        set_rect("ViewTab",       mx + 4.0,   3.5, 178.0, 15.0, True)
        set_rect("p0_num_freq",   mx + 187.0, 3.5,  50.0, 15.0, tab_idx == 0)
        set_rect("main_bot_bar",  mx,       167.0, MAIN_W, 2.0, True)
        set_rect("AuditionDelta", mx + 4.0,  150.5, 20.0, 14.0, True)
        set_rect("row_lbl_gain",  mx + 36.0, 150.5, 30.0, 14.0, True)
        set_rect("DeltaBoost",    mx + 66.0, 150.5, 54.0, 14.0, True)
        set_rect("row_lbl_delay", mx + 134.0, 150.5, 36.0, 14.0, True)
        set_rect("AlignNum",      mx + 171.0, 150.5, 62.0, 14.0, True)

        # 4. Tab 0: Spectrum Analyzer (y = 22..147, h = 125)
        vis0 = (tab_idx == 0)
        set_rect("p0_spectroscope", mx, 22.0, MAIN_W, 125.0, vis0)
        set_rect("p0_spec_ref",     mx, 22.0, MAIN_W, 125.0, vis0)
        for fk, u_pos in freq_u_map.items():
            fpx = mx + u_pos * MAIN_W - 11.0
            set_rect(fk, fpx, 134.0, 24.0, 12.0, vis0)
        set_rect("p0_db_0", mx + 216.0,  24.0, 22.0, 12.0, vis0)
        set_rect("p0_db_1", mx + 216.0,  64.0, 22.0, 12.0, vis0)
        set_rect("p0_db_2", mx + 216.0, 104.0, 22.0, 12.0, vis0)

        # 5. Tab 1: Phase Scope (y = 22..147, h = 125)
        vis1 = (tab_idx == 1)
        set_rect("p1_phasescope", mx,         22.0, MAIN_W, 125.0, vis1)
        set_rect("p1_lbl_corr",   mx + 181.0, 25.0,   52.0,  14.0, vis1)
        set_rect("p1_num_corr",   mx + 187.0, 39.0,   46.0,  15.0, vis1)

        # 6. Tab 2: Levels Comparison (y = 22..147, h = 125)
        vis2 = (tab_idx == 2)
        set_rect("p2_bg",      mx,         22.0, MAIN_W, 125.0, vis2)
        set_rect("p2_lbl_a",   mx + 13.0,  24.0,   42.0,  13.0, vis2)
        set_rect("p2_meter_a", mx + 25.0,  39.0,   18.0,  84.0, vis2)
        set_rect("p2_db_a",    mx + 13.0, 127.0,   42.0,  15.0, vis2)
        set_rect("p2_lbl_b",   mx + 65.0,  24.0,   42.0,  13.0, vis2)
        set_rect("p2_meter_b", mx + 77.0,  39.0,   18.0,  84.0, vis2)
        set_rect("p2_db_b",    mx + 65.0, 127.0,   42.0,  15.0, vis2)
        set_rect("p2_lbl_d",   mx + 117.0, 24.0,   46.0,  13.0, vis2)
        set_rect("p2_meter_d", mx + 131.0, 39.0,   18.0,  84.0, vis2)
        set_rect("p2_db_d",    mx + 119.0, 127.0,  42.0,  15.0, vis2)
        set_rect("p2_lbl_diff", mx + 175.0, 56.0,  54.0,  14.0, vis2)
        set_rect("p2_db_diff",  mx + 177.0, 72.0,  50.0,  16.0, vis2)

        return ", ".join(cmds)

    states = [
        ("0_1", 0, True,  0),
        ("0_0", 0, False, 1),
        ("1_1", 1, True,  2),
        ("1_0", 1, False, 3),
        ("2_1", 2, True,  4),
        ("2_0", 2, False, 5),
    ]
    for label, tidx, dopen, out_idx in states:
        msg_id = f"obj-msg-ui-{label}"
        add_box({
            "id": msg_id,
            "maxclass": "message",
            "numinlets": 2,
            "numoutlets": 1,
            "outlettype": [""],
            "patching_rect": [40.0 + out_idx * 95.0, 540.0, 88.0, 22.0],
            "text": build_layout_script(tidx, dopen)
        })
        add_line("obj-route-ui", out_idx, msg_id, 0)
        add_line(msg_id, 0, "obj-thispatcher", 0)

    # Visualizer CPU gating per active tab (0 = Spectrum, 1 = Phase, 2 = Levels)
    add_box({"id": "obj-route-tab-dsp", "maxclass": "newobj", "numinlets": 4, "numoutlets": 4, "outlettype": ["", "", "", ""], "patching_rect": [150.0, 580.0, 95.0, 22.0], "text": "route 0 1 2"})
    add_line("obj-tab-nav", 0, "obj-route-tab-dsp", 0)

    def wire_lvl_gates(src_id):
        for g in ["obj-gate-lvl-a-l", "obj-gate-lvl-a-r", "obj-gate-lvl-b-l", "obj-gate-lvl-b-r", "obj-gate-lvl-d-l", "obj-gate-lvl-d-r"]:
            add_line(src_id, 0, g, 0)

    # Tab 0 (Spectrum) active
    add_box({"id": "obj-t0-on", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [40.0, 615.0, 29.5, 22.0], "text": "1"})
    add_box({"id": "obj-t0-off", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [75.0, 615.0, 29.5, 22.0], "text": "0"})
    add_box({"id": "obj-t0-specint", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [40.0, 642.0, 65.0, 22.0], "text": "interval 45"})
    add_box({"id": "obj-t0-phaseauto", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [110.0, 642.0, 75.0, 22.0], "text": "automatic 0"})
    add_line("obj-route-tab-dsp", 0, "obj-t0-on", 0)
    add_line("obj-route-tab-dsp", 0, "obj-t0-off", 0)
    add_line("obj-route-tab-dsp", 0, "obj-t0-specint", 0)
    add_line("obj-route-tab-dsp", 0, "obj-t0-phaseauto", 0)
    add_line("obj-t0-on", 0, "obj-gate-spectrum", 0)
    add_line("obj-t0-on", 0, "obj-gate-spec-ref", 0)
    add_line("obj-t0-off", 0, "obj-gate-phase-l", 0)
    add_line("obj-t0-off", 0, "obj-gate-phase-r", 0)
    add_line("obj-t0-off", 0, "obj-corr-snap", 1)
    wire_lvl_gates("obj-t0-off")
    add_line("obj-t0-specint", 0, "obj-spectroscope", 0)
    add_line("obj-t0-specint", 0, "obj-spec-ref", 0)
    add_line("obj-t0-phaseauto", 0, "obj-phasescope", 0)

    # Tab 1 (Phase) active
    add_box({"id": "obj-t1-on", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [210.0, 615.0, 29.5, 22.0], "text": "1"})
    add_box({"id": "obj-t1-off", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [245.0, 615.0, 29.5, 22.0], "text": "0"})
    add_box({"id": "obj-t1-snap", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [280.0, 615.0, 29.5, 22.0], "text": "50"})
    add_box({"id": "obj-t1-specint", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [210.0, 642.0, 58.0, 22.0], "text": "interval 0"})
    add_box({"id": "obj-t1-phaseauto", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [275.0, 642.0, 75.0, 22.0], "text": "automatic 1"})
    add_line("obj-route-tab-dsp", 1, "obj-t1-on", 0)
    add_line("obj-route-tab-dsp", 1, "obj-t1-off", 0)
    add_line("obj-route-tab-dsp", 1, "obj-t1-snap", 0)
    add_line("obj-route-tab-dsp", 1, "obj-t1-specint", 0)
    add_line("obj-route-tab-dsp", 1, "obj-t1-phaseauto", 0)
    add_line("obj-t1-on", 0, "obj-gate-phase-l", 0)
    add_line("obj-t1-on", 0, "obj-gate-phase-r", 0)
    add_line("obj-t1-off", 0, "obj-gate-spectrum", 0)
    add_line("obj-t1-off", 0, "obj-gate-spec-ref", 0)
    add_line("obj-t1-snap", 0, "obj-corr-snap", 1)
    wire_lvl_gates("obj-t1-off")
    add_line("obj-t1-specint", 0, "obj-spectroscope", 0)
    add_line("obj-t1-specint", 0, "obj-spec-ref", 0)
    add_line("obj-t1-phaseauto", 0, "obj-phasescope", 0)

    # Tab 2 (Levels) active
    add_box({"id": "obj-t2-on", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [380.0, 615.0, 29.5, 22.0], "text": "1"})
    add_box({"id": "obj-t2-off", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [415.0, 615.0, 29.5, 22.0], "text": "0"})
    add_box({"id": "obj-t2-specint", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [380.0, 642.0, 58.0, 22.0], "text": "interval 0"})
    add_box({"id": "obj-t2-phaseauto", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [445.0, 642.0, 75.0, 22.0], "text": "automatic 0"})
    add_line("obj-route-tab-dsp", 2, "obj-t2-on", 0)
    add_line("obj-route-tab-dsp", 2, "obj-t2-off", 0)
    add_line("obj-route-tab-dsp", 2, "obj-t2-specint", 0)
    add_line("obj-route-tab-dsp", 2, "obj-t2-phaseauto", 0)
    wire_lvl_gates("obj-t2-on")
    add_line("obj-t2-off", 0, "obj-gate-spectrum", 0)
    add_line("obj-t2-off", 0, "obj-gate-spec-ref", 0)
    add_line("obj-t2-off", 0, "obj-gate-phase-l", 0)
    add_line("obj-t2-off", 0, "obj-gate-phase-r", 0)
    add_line("obj-t2-off", 0, "obj-corr-snap", 1)
    add_line("obj-t2-specint", 0, "obj-spectroscope", 0)
    add_line("obj-t2-specint", 0, "obj-spec-ref", 0)
    add_line("obj-t2-phaseauto", 0, "obj-phasescope", 0)

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
            "rect": [100.0, 100.0, 1180.0, 860.0],
            "openrect": [0.0, 0.0, BASE_W, DEV_H],
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
            "devicewidth": BASE_W,
            "description": "Comparative Delta Analyzer & Audition Tool",
            "digest": "Phase-cancelled delta audition, alignment, and spectrum/phase/level analysis",
            "tags": "Delta Analyzer Utility",
            "style": "",
            "subpatcher_template": "",
            "assistshowspatchername": 0,
            "boxes": boxes,
            "lines": lines,
            "parameters": {
                "obj-btn-tapa-drawer": ["Tap Section", "Tap", 0],
                "obj-tab-nav": ["Visualizer View", "View", 0],
                "obj-num-spec-freq": ["Hover Frequency", "Freq", 0],
                "obj-btn-audition": ["Audition Delta", "Audition", 0],
                "obj-dial-boost": ["Delta Boost", "Boost", 0],
                "obj-num-align": ["Time Delay", "Delay", 0],
                "obj-num-corr": ["Phase Correlation", "Corr", 0],
                "obj-lvl-db-a": ["Tap Level dB", "LvA", 0],
                "obj-lvl-db-b": ["Out Level dB", "LvB", 0],
                "obj-lvl-db-d": ["Delta Null Depth dB", "LvD", 0],
                "obj-lvl-db-diff": ["Gain Difference dB", "Diff", 0],
                "parameterbanks": {}
            },
            "dependency_cache": [
                {"name": "ableton_tri_closed.svg", "bootpath": out_dir_str, "type": "svg", "implicit": 1},
                {"name": "ableton_tri_open.svg", "bootpath": out_dir_str, "type": "svg", "implicit": 1},
                {"name": "ableton_headphones.svg", "bootpath": out_dir_str, "type": "svg", "implicit": 1},
                {"name": "ableton_headphones_on.svg", "bootpath": out_dir_str, "type": "svg", "implicit": 1},
                {"name": "ableton_headphones_row.svg", "bootpath": out_dir_str, "type": "svg", "implicit": 1},
                {"name": "ableton_headphones_row_on.svg", "bootpath": out_dir_str, "type": "svg", "implicit": 1},
                {"name": "ableton_tap_vert.svg", "bootpath": out_dir_str, "type": "svg", "implicit": 1},
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
    amxd_path = out_dir / "OA_Delta.amxd"
    patcher_data = build_patcher()
    validate_patcher(patcher_data)
    write_amxd(patcher_data, amxd_path)
    print(f"Generated & Validated AMXD: {amxd_path} ({amxd_path.stat().st_size} bytes)")

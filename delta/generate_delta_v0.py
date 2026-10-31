"""
OA_Delta M4L Device Generator - Dual Tap (A / B) & Delta Audition Architecture
Features:
- 6-channel plugin~ (1/2 = Track Pass-Through, 3/4 = Tap A, 5/6 = Tap B)
- Dual Tap Point Routing on Setup Tab:
  - TAP A (Track A + Tap Point A) -> controls audio_inputs index 1 (ch 3/4)
  - TAP B (Track B + Tap Point B) -> controls audio_inputs index 2 (ch 5/6)
  - Track main audio (ch 1/2, index 0) is never hijacked, ensuring 100% transparent
    pass-through when Delta Audition is OFF.
- Audition at Request:
  - Latching [ AUDITION OFF / AUDITION DELTA ] toggle button.
  - When OFF: Track audio passes through untouched while analyzers & meters show A, B, and Delta.
  - When ON: Outputs pure phase-cancelled Delta (B - A) with Boost (+0 to +36 dB) and
    omx.peaklim~ safety ceiling.
- 3 Tabbed Pages: Setup, Spectrum (Show Delta / Show A / Show B), Phase (Show Delta / Show A / Show B)
- Zero-CPU Dynamic Gating: cuts audio (selector~ 1 0) and halts redraw (interval 0 / automatic 0)
  on hidden visualizers.
"""

import json
import os
import struct


def build_delta_device():
    # Palette constants matching OpenAir macchinette aesthetic
    BG_DARK = [0.07843137254902, 0.074509803921569, 0.101960784313725, 1.0]       # #14131a
    BG_INSET = [0.05, 0.05, 0.07, 1.0]                                            # #0d0c12
    BG_CONTROL = [0.12, 0.11, 0.16, 1.0]                                          # #1f1c29
    TEXT_LIGHT = [0.827450980392157, 0.803921568627451, 0.843137254901961, 1.0]   # #d3cdd7
    ACCENT_PINK = [1.0, 0.568627450980392, 0.764705882352941, 1.0]                # #ff91c3
    MUTED_PURPLE = [0.619607843137255, 0.580392156862745, 0.670588235294118, 1.0] # #9e94ab
    BORDER_COLOR = [0.23921568627451, 0.219607843137255, 0.286274509803922, 1.0]

    DEV_W = 270.0
    DEV_H = 169.0

    boxes = []
    lines = []
    seen_lines = set()

    def add_box(b):
        boxes.append({"box": b})

    def add_line(src_id, src_out, dst_id, dst_in):
        key = (src_id, src_out, dst_id, dst_in)
        if key in seen_lines:
            raise ValueError(f"Duplicate patchline detected: {key}")
        seen_lines.add(key)
        lines.append({
            "patchline": {
                "source": [src_id, src_out],
                "destination": [dst_id, dst_in]
            }
        })

    # =========================================================================
    # 1. PERSISTENT HEADER (Visible on all tabs)
    # =========================================================================
    add_box({
        "id": "obj-hdr-title",
        "maxclass": "live.comment",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [30.0, 20.0, 65.0, 24.0],
        "presentation": 1,
        "presentation_rect": [6.0, 2.0, 65.0, 22.0],
        "text": "delta ~",
        "fontsize": 16.0,
        "fontname": "Ableton Sans Medium Regular",
        "textcolor": TEXT_LIGHT
    })

    add_box({
        "id": "obj-hdr-tag",
        "maxclass": "live.comment",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [100.0, 24.0, 36.0, 14.0],
        "presentation": 1,
        "presentation_rect": [66.0, 7.0, 36.0, 14.0],
        "text": "A / B Δ",
        "fontsize": 7.5,
        "fontface": 1,
        "fontname": "Ableton Sans Medium Regular",
        "textcolor": MUTED_PURPLE
    })

    # Main Navigation Tab: [Setup, Spectrum, Phase]
    add_box({
        "id": "obj-tab-nav",
        "maxclass": "live.tab",
        "num_lines_patching": 1,
        "num_lines_presentation": 1,
        "numinlets": 1,
        "numoutlets": 3,
        "outlettype": ["", "", "float"],
        "parameter_enable": 1,
        "patching_rect": [150.0, 20.0, 156.0, 20.0],
        "presentation": 1,
        "presentation_rect": [108.0, 4.0, 156.0, 18.0],
        "varname": "MainTab",
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": "Main Tab",
                "parameter_shortname": "Tab",
                "parameter_type": 2,
                "parameter_enum": ["Setup", "Spectrum", "Phase"],
                "parameter_initial_enable": 1,
                "parameter_initial": [0.0],
                "parameter_invisible": 1
            }
        },
        "activebgcolor": BG_CONTROL,
        "activebgoncolor": ACCENT_PINK,
        "bgcolor": BG_CONTROL,
        "bgoncolor": ACCENT_PINK,
        "textcolor": TEXT_LIGHT,
        "textoncolor": BG_DARK
    })

    # =========================================================================
    # 2. PERSISTENT BOTTOM STRIP METERS: Tap A | Delta | Tap B
    # =========================================================================
    add_box({
        "id": "obj-lbl-btm-a",
        "maxclass": "live.comment",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [20.0, 700.0, 45.0, 14.0],
        "presentation": 1,
        "presentation_rect": [8.0, 139.0, 45.0, 13.0],
        "text": "Tap A",
        "fontsize": 8.0,
        "fontface": 1,
        "fontname": "Ableton Sans Medium Regular",
        "textcolor": MUTED_PURPLE
    })
    add_box({
        "id": "obj-meter-btm-a",
        "maxclass": "live.meter~",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["float", "int"],
        "patching_rect": [20.0, 720.0, 76.0, 10.0],
        "presentation": 1,
        "presentation_rect": [8.0, 153.0, 76.0, 10.0],
        "orientation": 1
    })

    add_box({
        "id": "obj-lbl-btm-delta",
        "maxclass": "live.comment",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [110.0, 700.0, 45.0, 14.0],
        "presentation": 1,
        "presentation_rect": [96.0, 139.0, 45.0, 13.0],
        "text": "Delta Δ",
        "fontsize": 8.0,
        "fontface": 1,
        "fontname": "Ableton Sans Medium Regular",
        "textcolor": ACCENT_PINK
    })
    add_box({
        "id": "obj-meter-btm-delta",
        "maxclass": "live.meter~",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["float", "int"],
        "patching_rect": [110.0, 720.0, 76.0, 10.0],
        "presentation": 1,
        "presentation_rect": [96.0, 153.0, 76.0, 10.0],
        "orientation": 1
    })

    add_box({
        "id": "obj-lbl-btm-b",
        "maxclass": "live.comment",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [200.0, 700.0, 55.0, 14.0],
        "presentation": 1,
        "presentation_rect": [184.0, 139.0, 65.0, 13.0],
        "text": "Point B (In)",
        "fontsize": 8.0,
        "fontface": 1,
        "fontname": "Ableton Sans Medium Regular",
        "textcolor": TEXT_LIGHT
    })
    add_box({
        "id": "obj-meter-btm-b",
        "maxclass": "live.meter~",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["float", "int"],
        "patching_rect": [200.0, 720.0, 78.0, 10.0],
        "presentation": 1,
        "presentation_rect": [184.0, 153.0, 78.0, 10.0],
        "orientation": 1
    })

    # =========================================================================
    # 3. TAB 1 (SETUP) UI WIDGETS — Tap A (Sidechain) & Point B (Device Pos)
    # =========================================================================
    # --- TAP A (Channels 3/4, audio_inputs index 1) ---
    add_box({
        "id": "obj-ui-lbl-tapa",
        "maxclass": "live.comment",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [30.0, 80.0, 136.0, 14.0],
        "presentation": 1,
        "presentation_rect": [8.0, 26.0, 136.0, 13.0],
        "text": "TAP A (Track / Tap Point)",
        "fontsize": 7.5,
        "fontface": 1,
        "fontname": "Ableton Sans Medium Regular",
        "textcolor": MUTED_PURPLE,
        "hidden": 0,
        "varname": "p1_lbl_tapa"
    })

    add_box({
        "id": "obj-ui-menu-track-a",
        "maxclass": "umenu",
        "numinlets": 1,
        "numoutlets": 3,
        "outlettype": ["int", "", ""],
        "parameter_enable": 0,
        "items": ["No Input"],
        "patching_rect": [450.0, 210.0, 70.0, 19.0],
        "presentation": 1,
        "presentation_rect": [8.0, 40.0, 68.0, 18.0],
        "fontsize": 8.5,
        "fontname": "Ableton Sans Medium Regular",
        "textcolor": TEXT_LIGHT,
        "bgcolor": BG_CONTROL,
        "bgfillcolor_type": "color",
        "bgfillcolor_color": BG_CONTROL,
        "hidden": 0,
        "varname": "p1_menu_track_a"
    })

    add_box({
        "id": "obj-ui-menu-chan-a",
        "maxclass": "umenu",
        "numinlets": 1,
        "numoutlets": 3,
        "outlettype": ["int", "", ""],
        "parameter_enable": 0,
        "items": ["Pre FX", ",", "Post FX", ",", "Post Mixer"],
        "patching_rect": [530.0, 210.0, 66.0, 19.0],
        "presentation": 1,
        "presentation_rect": [78.0, 40.0, 66.0, 18.0],
        "fontsize": 8.5,
        "fontname": "Ableton Sans Medium Regular",
        "textcolor": TEXT_LIGHT,
        "bgcolor": BG_CONTROL,
        "bgfillcolor_type": "color",
        "bgfillcolor_color": BG_CONTROL,
        "hidden": 0,
        "varname": "p1_menu_chan_a"
    })

    # --- POINT B (Channels 1/2, Device Insert Position) ---
    add_box({
        "id": "obj-ui-lbl-tapb",
        "maxclass": "live.comment",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [30.0, 120.0, 136.0, 14.0],
        "presentation": 1,
        "presentation_rect": [8.0, 62.0, 136.0, 13.0],
        "text": "POINT B (Device Position)",
        "fontsize": 7.5,
        "fontface": 1,
        "fontname": "Ableton Sans Medium Regular",
        "textcolor": MUTED_PURPLE,
        "hidden": 0,
        "varname": "p1_lbl_tapb"
    })

    add_box({
        "id": "obj-ui-val-tapb",
        "maxclass": "live.comment",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [30.0, 138.0, 136.0, 16.0],
        "presentation": 1,
        "presentation_rect": [8.0, 75.0, 136.0, 16.0],
        "text": "Normal Signal Flow (B - A)",
        "fontsize": 8.5,
        "fontface": 0,
        "fontname": "Ableton Sans Medium Regular",
        "textcolor": TEXT_LIGHT,
        "hidden": 0,
        "varname": "p1_val_tapb"
    })

    # --- ALIGNMENT NUDGE (Samples) ---
    add_box({
        "id": "obj-ui-lbl-align",
        "maxclass": "live.comment",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [30.0, 160.0, 130.0, 13.0],
        "presentation": 1,
        "presentation_rect": [8.0, 98.0, 136.0, 13.0],
        "text": "DELAY ALIGN (Samples)",
        "fontsize": 7.5,
        "fontface": 1,
        "fontname": "Ableton Sans Medium Regular",
        "textcolor": MUTED_PURPLE,
        "hidden": 0,
        "varname": "p1_lbl_align"
    })

    add_box({
        "id": "obj-btn-nudge-m10",
        "maxclass": "live.text",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "parameter_enable": 0,
        "patching_rect": [30.0, 180.0, 24.0, 16.0],
        "presentation": 1,
        "presentation_rect": [8.0, 113.0, 24.0, 16.0],
        "text": "-10",
        "texton": "-10",
        "fontsize": 8.0,
        "activebgcolor": BG_CONTROL,
        "activebgoncolor": ACCENT_PINK,
        "textcolor": TEXT_LIGHT,
        "mode": 0,
        "hidden": 0,
        "varname": "p1_btn_m10"
    })
    add_box({
        "id": "obj-btn-nudge-m1",
        "maxclass": "live.text",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "parameter_enable": 0,
        "patching_rect": [58.0, 180.0, 20.0, 16.0],
        "presentation": 1,
        "presentation_rect": [34.0, 113.0, 20.0, 16.0],
        "text": "-1",
        "texton": "-1",
        "fontsize": 8.0,
        "activebgcolor": BG_CONTROL,
        "activebgoncolor": ACCENT_PINK,
        "textcolor": TEXT_LIGHT,
        "mode": 0,
        "hidden": 0,
        "varname": "p1_btn_m1"
    })
    add_box({
        "id": "obj-num-align",
        "maxclass": "live.numbox",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "parameter_enable": 1,
        "patching_rect": [82.0, 180.0, 36.0, 16.0],
        "presentation": 1,
        "presentation_rect": [56.0, 113.0, 38.0, 16.0],
        "varname": "AlignNum",
        "hidden": 0,
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": "Align Samples",
                "parameter_shortname": "Align",
                "parameter_type": 1,
                "parameter_mmin": 0.0,
                "parameter_mmax": 2048.0,
                "parameter_initial_enable": 1,
                "parameter_initial": [0.0],
                "parameter_unitstyle": 0
            }
        },
        "activebgcolor": BG_CONTROL,
        "textcolor": ACCENT_PINK,
        "fontsize": 8.0
    })
    add_box({
        "id": "obj-btn-nudge-p1",
        "maxclass": "live.text",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "parameter_enable": 0,
        "patching_rect": [122.0, 180.0, 20.0, 16.0],
        "presentation": 1,
        "presentation_rect": [96.0, 113.0, 20.0, 16.0],
        "text": "+1",
        "texton": "+1",
        "fontsize": 8.0,
        "activebgcolor": BG_CONTROL,
        "activebgoncolor": ACCENT_PINK,
        "textcolor": TEXT_LIGHT,
        "mode": 0,
        "hidden": 0,
        "varname": "p1_btn_p1"
    })
    add_box({
        "id": "obj-btn-nudge-p10",
        "maxclass": "live.text",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "parameter_enable": 0,
        "patching_rect": [146.0, 180.0, 24.0, 16.0],
        "presentation": 1,
        "presentation_rect": [118.0, 113.0, 26.0, 16.0],
        "text": "+10",
        "texton": "+10",
        "fontsize": 8.0,
        "activebgcolor": BG_CONTROL,
        "activebgoncolor": ACCENT_PINK,
        "textcolor": TEXT_LIGHT,
        "mode": 0,
        "hidden": 0,
        "varname": "p1_btn_p10"
    })

    # --- RIGHT COLUMN: DELTA AUDITION AT REQUEST ---
    add_box({
        "id": "obj-ui-lbl-mode",
        "maxclass": "live.comment",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [180.0, 80.0, 110.0, 13.0],
        "presentation": 1,
        "presentation_rect": [152.0, 26.0, 110.0, 13.0],
        "text": "DELTA MONITOR",
        "fontsize": 7.5,
        "fontface": 1,
        "fontname": "Ableton Sans Medium Regular",
        "textcolor": MUTED_PURPLE,
        "hidden": 0,
        "varname": "p1_lbl_mode"
    })

    # Latching Toggle Button: AUDITION DELTA (mode = 1 toggle!)
    add_box({
        "id": "obj-btn-audition",
        "maxclass": "live.text",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "parameter_enable": 1,
        "patching_rect": [180.0, 110.0, 110.0, 24.0],
        "presentation": 1,
        "presentation_rect": [152.0, 40.0, 110.0, 22.0],
        "text": "AUDITION Δ OFF",
        "texton": "AUDITION Δ ON",
        "fontsize": 9.0,
        "fontface": 1,
        "activebgcolor": BG_CONTROL,
        "activebgoncolor": ACCENT_PINK,
        "bgcolor": BG_CONTROL,
        "bgoncolor": ACCENT_PINK,
        "textcolor": TEXT_LIGHT,
        "textoncolor": BG_DARK,
        "mode": 1,
        "hidden": 0,
        "varname": "AuditionDelta",
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": "Audition Delta",
                "parameter_shortname": "Audit",
                "parameter_type": 2,
                "parameter_enum": ["Off", "On"],
                "parameter_mmax": 1,
                "parameter_initial_enable": 1,
                "parameter_initial": [0.0]
            }
        }
    })

    # Delta Boost Dial (+0 dB to +36 dB)
    add_box({
        "id": "obj-dial-boost",
        "maxclass": "live.dial",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "parameter_enable": 1,
        "patching_rect": [180.0, 210.0, 44.0, 48.0],
        "presentation": 1,
        "presentation_rect": [156.0, 74.0, 46.0, 52.0],
        "varname": "DeltaBoost",
        "hidden": 0,
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": "Delta Boost",
                "parameter_shortname": "Boost",
                "parameter_type": 0,
                "parameter_mmin": 0.0,
                "parameter_mmax": 36.0,
                "parameter_unitstyle": 4,
                "parameter_initial_enable": 1,
                "parameter_initial": [0.0]
            }
        },
        "activedialcolor": ACCENT_PINK,
        "activefgdialcolor": TEXT_LIGHT,
        "activeneedlecolor": TEXT_LIGHT,
        "dialcolor": MUTED_PURPLE,
        "textcolor": TEXT_LIGHT,
        "tricolor": MUTED_PURPLE
    })

    # Align Delay Dial (0 to 2048 smp)
    add_box({
        "id": "obj-dial-align",
        "maxclass": "live.dial",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "parameter_enable": 1,
        "patching_rect": [240.0, 210.0, 44.0, 48.0],
        "presentation": 1,
        "presentation_rect": [212.0, 74.0, 46.0, 52.0],
        "varname": "AlignDial",
        "hidden": 0,
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": "Align Delay",
                "parameter_shortname": "Delay",
                "parameter_type": 1,
                "parameter_mmin": 0.0,
                "parameter_mmax": 2048.0,
                "parameter_unitstyle": 0,
                "parameter_initial_enable": 1,
                "parameter_initial": [0.0]
            }
        },
        "activedialcolor": ACCENT_PINK,
        "activefgdialcolor": TEXT_LIGHT,
        "activeneedlecolor": TEXT_LIGHT,
        "dialcolor": MUTED_PURPLE,
        "textcolor": TEXT_LIGHT,
        "tricolor": MUTED_PURPLE
    })

    # =========================================================================
    # 4. TAB 2 (SPECTRUM) UI WIDGETS — Initial state: hidden = 1, presentation = 0
    # =========================================================================
    add_box({
        "id": "obj-ui-lbl-specsource",
        "maxclass": "live.comment",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [550.0, 280.0, 45.0, 14.0],
        "presentation": 0,
        "presentation_rect": [8.0, 27.0, 45.0, 13.0],
        "text": "VIEW",
        "fontsize": 7.5,
        "fontface": 1,
        "fontname": "Ableton Sans Medium Regular",
        "textcolor": MUTED_PURPLE,
        "hidden": 1,
        "varname": "p2_lbl_source"
    })

    add_box({
        "id": "obj-tab-specsource",
        "maxclass": "live.tab",
        "num_lines_patching": 1,
        "num_lines_presentation": 1,
        "numinlets": 1,
        "numoutlets": 3,
        "outlettype": ["", "", "float"],
        "parameter_enable": 1,
        "patching_rect": [600.0, 280.0, 207.0, 18.0],
        "presentation": 0,
        "presentation_rect": [55.0, 25.0, 207.0, 18.0],
        "varname": "p2_tab_source",
        "hidden": 1,
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": "Spectrum Source",
                "parameter_shortname": "View",
                "parameter_type": 2,
                "parameter_enum": ["Show Delta", "Show A", "Show B"],
                "parameter_initial_enable": 1,
                "parameter_initial": [0.0],
                "parameter_invisible": 1
            }
        },
        "activebgcolor": BG_CONTROL,
        "activebgoncolor": ACCENT_PINK,
        "bgcolor": BG_CONTROL,
        "bgoncolor": ACCENT_PINK,
        "textcolor": TEXT_LIGHT,
        "textoncolor": BG_DARK
    })

    add_box({
        "id": "obj-spectroscope",
        "maxclass": "spectroscope~",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [550.0, 380.0, 254.0, 88.0],
        "presentation": 0,
        "presentation_rect": [8.0, 46.0, 254.0, 88.0],
        "bgcolor": BG_INSET,
        "fgcolor": ACCENT_PINK,
        "curvecolor": ACCENT_PINK,
        "markercolor": [0.22, 0.20, 0.27, 0.6],
        "bordercolor": BORDER_COLOR,
        "logfreq": 1,
        "monochrome": 0,
        "sono": 0,
        "interval": 0,
        "hidden": 1,
        "varname": "p2_spectroscope"
    })

    # =========================================================================
    # 5. TAB 3 (PHASE & STEREO) UI WIDGETS — Initial state: hidden = 1, presentation = 0
    # =========================================================================
    add_box({
        "id": "obj-phasescope",
        "maxclass": "scope~",
        "numinlets": 2,
        "numoutlets": 0,
        "patching_rect": [820.0, 380.0, 104.0, 104.0],
        "presentation": 0,
        "presentation_rect": [8.0, 28.0, 104.0, 104.0],
        "bgcolor": BG_INSET,
        "bordercolor": BORDER_COLOR,
        "fgcolor": ACCENT_PINK,
        "automatic": 0,
        "hidden": 1,
        "varname": "p3_phasescope"
    })

    add_box({
        "id": "obj-ui-lbl-corr",
        "maxclass": "live.comment",
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [820.0, 280.0, 120.0, 14.0],
        "presentation": 0,
        "presentation_rect": [124.0, 30.0, 130.0, 13.0],
        "text": "DELTA PHASE CORRELATION",
        "fontsize": 7.5,
        "fontface": 1,
        "fontname": "Ableton Sans Medium Regular",
        "textcolor": MUTED_PURPLE,
        "hidden": 1,
        "varname": "p3_lbl_corr"
    })

    add_box({
        "id": "obj-num-corr",
        "maxclass": "live.numbox",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", "float"],
        "parameter_enable": 1,
        "patching_rect": [820.0, 305.0, 48.0, 16.0],
        "presentation": 0,
        "presentation_rect": [124.0, 48.0, 56.0, 16.0],
        "varname": "p3_num_corr",
        "hidden": 1,
        "saved_attribute_attributes": {
            "valueof": {
                "parameter_longname": "Correlation",
                "parameter_shortname": "Corr",
                "parameter_type": 0,
                "parameter_mmin": -1.0,
                "parameter_mmax": 1.0,
                "parameter_initial_enable": 1,
                "parameter_initial": [1.0],
                "parameter_invisible": 1
            }
        },
        "activebgcolor": BG_CONTROL,
        "textcolor": ACCENT_PINK,
        "fontsize": 8.5
    })

    # =========================================================================
    # 6. AUDIO I/O (4-Channel plugin~: 1/2=Point B Insert Pos, 3/4=Tap A Sidechain)
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
    # 7. TAP A LIVE.ROUTING CONTROLLER (index 1 = Tap A on Channels 3/4)
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

    # Assembly-verified 2-stage initialization for live.routing:
    # Stage 0 (t=0ms):   close gates (0), send ONLY "port audio_inputs" so obs_list_val sets num_ports=2 ([rbx+68h]=2)
    # Stage 1 (t=200ms): open gates (1), send "index 1" -> binds to Tap A (Channels 3/4) and populates Track & Point menus
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

    # Single live.routing instance permanently locked to index 1 (Tap A)
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

    # 4 Gates (each gate 1 0) to ignore index 0 during Stage 0 and pass index 1 from Stage 1 onward
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

    # Helper to wire official Cycling '74 umenuprep chain for Tap A menus
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

        # Since live.routing stays bound to index 1, user selection sends "type $1" / "channel $1" directly
        cmd_msg_id = f"obj-{prefix}-cmd"
        cmd_word = "type" if is_track else "channel"
        add_box({"id": cmd_msg_id, "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [450.0, 325.0, 67.0, 22.0], "text": f"{cmd_word} $1"})
        add_line(umenu_id, 0, cmd_msg_id, 0)
        add_line(cmd_msg_id, 0, "obj-live-routing", 0)

    wire_umenu_prep("tapa-trk", "obj-ui-menu-track-a", True)
    wire_umenu_prep("tapa-chn", "obj-ui-menu-chan-a", False)

    # =========================================================================
    # 8. DELAY ALIGNMENT & NUDGE LOGIC (On Tap A: channels 3/4)
    # =========================================================================
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

    add_box({"id": "obj-msg-m10", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [30.0, 210.0, 35.0, 22.0], "text": "-10"})
    add_box({"id": "obj-msg-m1", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [68.0, 210.0, 29.5, 22.0], "text": "-1"})
    add_box({"id": "obj-msg-p1", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [105.0, 210.0, 29.5, 22.0], "text": "1"})
    add_box({"id": "obj-msg-p10", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [140.0, 210.0, 35.0, 22.0], "text": "10"})
    add_line("obj-btn-nudge-m10", 0, "obj-msg-m10", 0)
    add_line("obj-btn-nudge-m1", 0, "obj-msg-m1", 0)
    add_line("obj-btn-nudge-p1", 0, "obj-msg-p1", 0)
    add_line("obj-btn-nudge-p10", 0, "obj-msg-p10", 0)

    add_box({"id": "obj-accum-align", "maxclass": "newobj", "numinlets": 3, "numoutlets": 1, "outlettype": ["int"], "patching_rect": [80.0, 245.0, 68.0, 22.0], "text": "accum 0"})
    add_box({"id": "obj-clip-align", "maxclass": "newobj", "numinlets": 3, "numoutlets": 1, "outlettype": [""], "patching_rect": [80.0, 275.0, 75.0, 22.0], "text": "clip 0 2048"})
    add_line("obj-msg-m10", 0, "obj-accum-align", 1)
    add_line("obj-msg-m1", 0, "obj-accum-align", 1)
    add_line("obj-msg-p1", 0, "obj-accum-align", 1)
    add_line("obj-msg-p10", 0, "obj-accum-align", 1)
    add_line("obj-msg-m10", 0, "obj-accum-align", 0)
    add_line("obj-msg-m1", 0, "obj-accum-align", 0)
    add_line("obj-msg-p1", 0, "obj-accum-align", 0)
    add_line("obj-msg-p10", 0, "obj-accum-align", 0)
    add_line("obj-accum-align", 0, "obj-clip-align", 0)
    add_line("obj-clip-align", 0, "obj-num-align", 0)
    add_line("obj-dial-align", 0, "obj-num-align", 0)
    add_line("obj-num-align", 0, "obj-delay-l", 1)
    add_line("obj-num-align", 0, "obj-delay-r", 1)

    # =========================================================================
    # 9. AUDITION-GATED DELTA DSP (Delta = Point B [ch 1/2] - Tap A [ch 3/4])
    # =========================================================================
    # When Audition is OFF (0), selector~ 1 0 outputs 0. so B-A subtraction & analysis
    # are bypassed and normal signal (Point B) is heard. When ON (1), B-A is active.
    add_box({"id": "obj-gate-dsp-b-l", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [220.0, 145.0, 70.0, 22.0], "text": "selector~ 1 0"})
    add_box({"id": "obj-gate-dsp-b-r", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [295.0, 145.0, 70.0, 22.0], "text": "selector~ 1 0"})
    add_box({"id": "obj-gate-dsp-a-l", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [370.0, 145.0, 70.0, 22.0], "text": "selector~ 1 0"})
    add_box({"id": "obj-gate-dsp-a-r", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [445.0, 145.0, 70.0, 22.0], "text": "selector~ 1 0"})

    add_line("obj-btn-audition", 0, "obj-gate-dsp-b-l", 0)
    add_line("obj-btn-audition", 0, "obj-gate-dsp-b-r", 0)
    add_line("obj-btn-audition", 0, "obj-gate-dsp-a-l", 0)
    add_line("obj-btn-audition", 0, "obj-gate-dsp-a-r", 0)

    add_line("obj-plugin", 0, "obj-gate-dsp-b-l", 1)
    add_line("obj-plugin", 1, "obj-gate-dsp-b-r", 1)
    add_line("obj-delay-l", 0, "obj-gate-dsp-a-l", 1)
    add_line("obj-delay-r", 0, "obj-gate-dsp-a-r", 1)

    # Invert gated Tap A: *~ -1.
    add_box({"id": "obj-invert-a-l", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [370.0, 180.0, 38.0, 22.0], "text": "*~ -1."})
    add_box({"id": "obj-invert-a-r", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [445.0, 180.0, 38.0, 22.0], "text": "*~ -1."})
    add_line("obj-gate-dsp-a-l", 0, "obj-invert-a-l", 0)
    add_line("obj-gate-dsp-a-r", 0, "obj-invert-a-r", 0)

    # Delta = Point B (ch 1 & 2) + (-Tap A)
    add_box({"id": "obj-sum-delta-l", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [300.0, 220.0, 38.0, 22.0], "text": "+~"})
    add_box({"id": "obj-sum-delta-r", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [350.0, 220.0, 38.0, 22.0], "text": "+~"})
    add_line("obj-gate-dsp-b-l", 0, "obj-sum-delta-l", 0)
    add_line("obj-gate-dsp-b-r", 0, "obj-sum-delta-r", 0)
    add_line("obj-invert-a-l", 0, "obj-sum-delta-l", 1)
    add_line("obj-invert-a-r", 0, "obj-sum-delta-r", 1)

    # Boost gain multiplier
    add_box({"id": "obj-boost-dbtoa", "maxclass": "newobj", "numinlets": 1, "numoutlets": 1, "outlettype": [""], "patching_rect": [180.0, 270.0, 41.0, 22.0], "text": "dbtoa"})
    add_line("obj-dial-boost", 0, "obj-boost-dbtoa", 0)

    add_box({"id": "obj-boost-mult-l", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [300.0, 270.0, 38.0, 22.0], "text": "*~ 1."})
    add_box({"id": "obj-boost-mult-r", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [350.0, 270.0, 38.0, 22.0], "text": "*~ 1."})
    add_line("obj-sum-delta-l", 0, "obj-boost-mult-l", 0)
    add_line("obj-sum-delta-r", 0, "obj-boost-mult-r", 0)
    add_line("obj-boost-dbtoa", 0, "obj-boost-mult-l", 1)
    add_line("obj-boost-dbtoa", 0, "obj-boost-mult-r", 1)

    # Safety Limiter (omx.peaklim~)
    add_box({"id": "obj-limiter-delta", "maxclass": "newobj", "numinlets": 2, "numoutlets": 2, "outlettype": ["signal", "signal"], "patching_rect": [300.0, 315.0, 90.0, 22.0], "text": "omx.peaklim~"})
    add_line("obj-boost-mult-l", 0, "obj-limiter-delta", 0)
    add_line("obj-boost-mult-r", 0, "obj-limiter-delta", 1)

    # Output Selector (1 = Normal Signal Flow [Point B ch 1/2], 2 = Audition Carved B-A)
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

    # Bottom Strip Meters Wiring (Tap A, Delta, Point B)
    add_line("obj-delay-l", 0, "obj-meter-btm-a", 0)
    add_line("obj-limiter-delta", 0, "obj-meter-btm-delta", 0)
    add_line("obj-plugin", 0, "obj-meter-btm-b", 0)

    # =========================================================================
    # 10. CPU-OPTIMIZED VISUALIZER ROUTING
    # =========================================================================
    # Spectrum Source selector: 1 = Show Delta, 2 = Show A, 3 = Show B (Point B)
    add_box({"id": "obj-sel-spec-in", "maxclass": "newobj", "numinlets": 4, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [550.0, 310.0, 70.0, 22.0], "text": "selector~ 3 1"})
    add_box({"id": "obj-spec-plus1", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["int"], "patching_rect": [630.0, 310.0, 29.5, 22.0], "text": "+ 1"})
    add_line("obj-tab-specsource", 0, "obj-spec-plus1", 0)
    add_line("obj-spec-plus1", 0, "obj-sel-spec-in", 0)
    add_line("obj-limiter-delta", 0, "obj-sel-spec-in", 1)
    add_line("obj-delay-l", 0, "obj-sel-spec-in", 2)
    add_line("obj-plugin", 0, "obj-sel-spec-in", 3)

    add_box({"id": "obj-gate-spectrum", "maxclass": "newobj", "numinlets": 2, "numoutlets": 1, "outlettype": ["signal"], "patching_rect": [550.0, 345.0, 70.0, 22.0], "text": "selector~ 1 0"})
    add_line("obj-sel-spec-in", 0, "obj-gate-spectrum", 1)
    add_line("obj-gate-spectrum", 0, "obj-spectroscope", 0)

    # Phase scope DSP gates (analyzing Delta stereo field)
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

    # =========================================================================
    # 11. TAB SWITCHING & CPU SUSPENSION CONTROLLER (thispatcher)
    # =========================================================================
    add_box({
        "id": "obj-thispatcher",
        "maxclass": "newobj",
        "numinlets": 1,
        "numoutlets": 2,
        "outlettype": ["", ""],
        "patching_rect": [150.0, 620.0, 70.0, 22.0],
        "text": "thispatcher",
        "save": ["#N", "thispatcher", ";"]
    })

    add_box({
        "id": "obj-route-tab",
        "maxclass": "newobj",
        "numinlets": 4,
        "numoutlets": 4,
        "outlettype": ["", "", "", ""],
        "patching_rect": [150.0, 500.0, 95.0, 22.0],
        "text": "route 0 1 2"
    })
    add_line("obj-tab-nav", 0, "obj-route-tab", 0)

    p1_vars = [
        "p1_lbl_tapa", "p1_menu_track_a", "p1_menu_chan_a",
        "p1_lbl_tapb", "p1_val_tapb",
        "p1_lbl_align", "p1_btn_m10", "p1_btn_m1", "AlignNum",
        "p1_btn_p1", "p1_btn_p10", "p1_lbl_mode", "AuditionDelta",
        "DeltaBoost", "AlignDial"
    ]
    p2_vars = ["p2_lbl_source", "p2_tab_source", "p2_spectroscope"]
    p3_vars = ["p3_phasescope", "p3_lbl_corr", "p3_num_corr"]

    var_rects = {
        b["box"]["varname"]: b["box"]["presentation_rect"]
        for b in boxes if "varname" in b["box"] and "presentation_rect" in b["box"]
    }

    def build_script_msg(show_list, hide_list):
        cmds = []
        for v in show_list:
            rx, ry, rw, rh = var_rects[v]
            cmds.append(f"script show {v}")
            cmds.append(f"script sendbox {v} presentation 1")
            cmds.append(f"script sendbox {v} presentation_rect {rx} {ry} {rw} {rh}")
        for v in hide_list:
            cmds.append(f"script sendbox {v} presentation 0")
            cmds.append(f"script hide {v}")
        return ", ".join(cmds)

    # Tab 0: Setup active
    add_box({"id": "obj-msg-tab0-ui", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [40.0, 540.0, 90.0, 22.0], "text": build_script_msg(p1_vars, p2_vars + p3_vars)})
    add_box({"id": "obj-msg-tab0-off", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [40.0, 570.0, 29.5, 22.0], "text": "0"})
    add_box({"id": "obj-msg-tab0-specint", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [75.0, 570.0, 58.0, 22.0], "text": "interval 0"})
    add_box({"id": "obj-msg-tab0-phaseauto", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [40.0, 595.0, 75.0, 22.0], "text": "automatic 0"})

    add_line("obj-route-tab", 0, "obj-msg-tab0-ui", 0)
    add_line("obj-msg-tab0-ui", 0, "obj-thispatcher", 0)
    add_line("obj-route-tab", 0, "obj-msg-tab0-off", 0)
    add_line("obj-route-tab", 0, "obj-msg-tab0-specint", 0)
    add_line("obj-route-tab", 0, "obj-msg-tab0-phaseauto", 0)
    add_line("obj-msg-tab0-off", 0, "obj-gate-spectrum", 0)
    add_line("obj-msg-tab0-off", 0, "obj-gate-phase-l", 0)
    add_line("obj-msg-tab0-off", 0, "obj-gate-phase-r", 0)
    add_line("obj-msg-tab0-off", 0, "obj-corr-snap", 1)
    add_line("obj-msg-tab0-specint", 0, "obj-spectroscope", 0)
    add_line("obj-msg-tab0-phaseauto", 0, "obj-phasescope", 0)

    # Tab 1: Spectrum active
    add_box({"id": "obj-msg-tab1-ui", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [180.0, 540.0, 90.0, 22.0], "text": build_script_msg(p2_vars, p1_vars + p3_vars)})
    add_box({"id": "obj-msg-tab1-on", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [180.0, 570.0, 29.5, 22.0], "text": "1"})
    add_box({"id": "obj-msg-tab1-off", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [215.0, 570.0, 29.5, 22.0], "text": "0"})
    add_box({"id": "obj-msg-tab1-specint", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [180.0, 595.0, 65.0, 22.0], "text": "interval 33"})
    add_box({"id": "obj-msg-tab1-phaseauto", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [250.0, 595.0, 75.0, 22.0], "text": "automatic 0"})

    add_line("obj-route-tab", 1, "obj-msg-tab1-ui", 0)
    add_line("obj-msg-tab1-ui", 0, "obj-thispatcher", 0)
    add_line("obj-route-tab", 1, "obj-msg-tab1-on", 0)
    add_line("obj-route-tab", 1, "obj-msg-tab1-off", 0)
    add_line("obj-route-tab", 1, "obj-msg-tab1-specint", 0)
    add_line("obj-route-tab", 1, "obj-msg-tab1-phaseauto", 0)
    add_line("obj-msg-tab1-on", 0, "obj-gate-spectrum", 0)
    add_line("obj-msg-tab1-off", 0, "obj-gate-phase-l", 0)
    add_line("obj-msg-tab1-off", 0, "obj-gate-phase-r", 0)
    add_line("obj-msg-tab1-off", 0, "obj-corr-snap", 1)
    add_line("obj-msg-tab1-specint", 0, "obj-spectroscope", 0)
    add_line("obj-msg-tab1-phaseauto", 0, "obj-phasescope", 0)

    # Tab 2: Phase active
    add_box({"id": "obj-msg-tab2-ui", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [340.0, 540.0, 90.0, 22.0], "text": build_script_msg(p3_vars, p1_vars + p2_vars)})
    add_box({"id": "obj-msg-tab2-on", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [340.0, 570.0, 29.5, 22.0], "text": "1"})
    add_box({"id": "obj-msg-tab2-off", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [375.0, 570.0, 29.5, 22.0], "text": "0"})
    add_box({"id": "obj-msg-tab2-snap", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [410.0, 570.0, 29.5, 22.0], "text": "50"})
    add_box({"id": "obj-msg-tab2-specint", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [340.0, 595.0, 58.0, 22.0], "text": "interval 0"})
    add_box({"id": "obj-msg-tab2-phaseauto", "maxclass": "message", "numinlets": 2, "numoutlets": 1, "outlettype": [""], "patching_rect": [405.0, 595.0, 75.0, 22.0], "text": "automatic 1"})

    add_line("obj-route-tab", 2, "obj-msg-tab2-ui", 0)
    add_line("obj-msg-tab2-ui", 0, "obj-thispatcher", 0)
    add_line("obj-route-tab", 2, "obj-msg-tab2-on", 0)
    add_line("obj-route-tab", 2, "obj-msg-tab2-off", 0)
    add_line("obj-route-tab", 2, "obj-msg-tab2-snap", 0)
    add_line("obj-route-tab", 2, "obj-msg-tab2-specint", 0)
    add_line("obj-route-tab", 2, "obj-msg-tab2-phaseauto", 0)
    add_line("obj-msg-tab2-on", 0, "obj-gate-phase-l", 0)
    add_line("obj-msg-tab2-on", 0, "obj-gate-phase-r", 0)
    add_line("obj-msg-tab2-off", 0, "obj-gate-spectrum", 0)
    add_line("obj-msg-tab2-snap", 0, "obj-corr-snap", 1)
    add_line("obj-msg-tab2-specint", 0, "obj-spectroscope", 0)
    add_line("obj-msg-tab2-phaseauto", 0, "obj-phasescope", 0)

    # =========================================================================
    # 12. BACKGROUND PANELS (MUST BE LAST IN `boxes` FOR BACKMOST Z-ORDER!)
    # =========================================================================
    add_box({
        "angle": 270.0,
        "bgcolor": BG_INSET,
        "border": 1,
        "bordercolor": BORDER_COLOR,
        "id": "obj-bg-bottom",
        "maxclass": "panel",
        "mode": 0,
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [10.0, 790.0, DEV_W, 32.0],
        "presentation": 1,
        "presentation_rect": [0.0, 137.0, DEV_W, 32.0],
        "proportion": 0.39,
        "rounded": 0
    })

    add_box({
        "angle": 270.0,
        "bgcolor": BG_DARK,
        "border": 0,
        "id": "obj-bg-main",
        "maxclass": "panel",
        "mode": 0,
        "numinlets": 1,
        "numoutlets": 0,
        "patching_rect": [10.0, 650.0, DEV_W, 137.0],
        "presentation": 1,
        "presentation_rect": [0.0, 0.0, DEV_W, 137.0],
        "proportion": 0.39,
        "rounded": 0
    })

    # =========================================================================
    # 13. VALIDATE ALL BOXES & LINES BEFORE RETURNING
    # =========================================================================
    box_map = {b["box"]["id"]: b["box"] for b in boxes}
    assert boxes[-1]["box"]["id"] == "obj-bg-main", "Z-order error: main bg panel must be last!"
    assert boxes[-2]["box"]["id"] == "obj-bg-bottom", "Z-order error: bottom bg panel must be second-to-last!"

    for l in lines:
        pl = l["patchline"]
        s_id, s_out = pl["source"]
        d_id, d_in = pl["destination"]
        assert s_id in box_map, f"Missing source box: {s_id}"
        assert d_id in box_map, f"Missing dest box: {d_id}"
        assert s_out < box_map[s_id]["numoutlets"], f"Invalid outlet {s_out} on {s_id}"
        assert d_in < box_map[d_id]["numinlets"], f"Invalid inlet {d_in} on {d_id}"

    patcher = {
        "fileversion": 1,
        "appversion": {
            "major": 9,
            "minor": 0,
            "revision": 0,
            "architecture": "x64",
            "modernui": 1
        },
        "classnamespace": "box",
        "rect": [100.0, 100.0, DEV_W, DEV_H],
        "openrect": [0.0, 0.0, DEV_W, DEV_H],
        "bglocked": 1,
        "openinpresentation": 1,
        "gridsize": [8.0, 8.0],
        "boxanimatetime": 200,
        "devicewidth": DEV_W,
        "boxes": boxes,
        "lines": lines,
        "parameters": {
            "obj-tab-nav": ["Main Tab", "Tab", 0],
            "obj-btn-audition": ["Audition Delta", "Audit", 0],
            "obj-dial-boost": ["Delta Boost", "Boost", 0],
            "obj-dial-align": ["Align Delay", "Delay", 0],
            "obj-num-align": ["Align Samples", "Align", 0],
            "obj-tab-specsource": ["Spectrum Source", "View", 0],
            "obj-num-corr": ["Correlation", "Corr", 0],
            "parameterbanks": {
                "0": {
                    "index": 0,
                    "name": "",
                    "parameters": [
                        "AuditionDelta",
                        "DeltaBoost",
                        "AlignDial",
                        "MainTab",
                        "-",
                        "-",
                        "-",
                        "-"
                    ]
                }
            },
            "inherited_shortname": 1
        },
        "dependency_cache": [],
        "latency": 0,
        "is_mpe": 0,
        "minimum_live_version": "",
        "minimum_max_version": "",
        "platform_compatibility": 0,
        "project": {
            "version": 1,
            "creationdate": 3590052493,
            "modificationdate": 3590052493,
            "viewrect": [0.0, 0.0, 300.0, 500.0],
            "autoorganize": 1,
            "hideprojectwindow": 1,
            "showdependencies": 1,
            "autolocalize": 0,
            "contents": {"patchers": {}},
            "layout": {},
            "searchpath": {},
            "detailsvisible": 0,
            "amxdtype": 1633771873,
            "readonly": 0,
            "devpathtype": 0,
            "devpath": ".",
            "sortmode": 0,
            "viewmode": 0,
            "includepackages": 0
        },
        "autosave": 0,
        "saved_attribute_attributes": {
            "default_plcolor": {
                "expression": ""
            }
        },
        "oscreceiveudpport": 0
    }

    return patcher


def save_amxd(patcher_dict, out_file):
    json_bytes = json.dumps({"patcher": patcher_dict}, indent=4).encode("utf-8")
    ampf_hdr = (
        b"ampf\x04\x00\x00\x00aaaameta\x04\x00\x00\x00\x00\x00\x00\x00ptch"
        + struct.pack("<I", len(json_bytes))
    )
    final_amxd = ampf_hdr + json_bytes
    with open(out_file, "wb") as f:
        f.write(final_amxd)
    print(f"Generated & Validated AMXD: {out_file} ({len(final_amxd)} bytes)")


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    amxd_path = os.path.join(out_dir, "OA_Delta.amxd")
    patcher = build_delta_device()
    save_amxd(patcher, amxd_path)

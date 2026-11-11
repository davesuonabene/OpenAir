#!/usr/bin/env python3
"""
build_deq_eight.py
Generates `dEQ Eight.amxd` — Theme-Cohesive & Native-Component Enhanced Dev Edition
of the OpenAir 8-Band Dynamic Parametric Equalizer + Dual Sidechain + 4096-Point FFT RTA.

Enhancements matching Vanilla Ableton EQ Eight & Glue Compressor:
1. Native Dial Styling (`live.dial`):
   - `activedialcolor`: `themecolor.live_value_arc` (Cyan)
   - `activefgdialcolor`: `themecolor.live_dial_fg` (Dark unfilled arc)
   - `activeneedlecolor`: `themecolor.live_dial_needle` (Dark needle matching EQ Eight & Glue Compressor)
   - `tricolor`: `themecolor.live_dial_triangle`
   - Bold font (`fontface=1`) and double-digit float precision (`%.2f dB` on Gain, `100 %` Int on Scale/Mix).
2. Bottom 8-Band Selector Strip & Vanilla EQ Eight Graphical 8-Icon Filter Curve Popup:
   - Exact EQ Eight dimensions: `39x14` Filter Curve button (`eq8_filter_0..7.svg` with `×4` on 48dB cuts),
     `12x12` Band Activator Square (`9x9` Cyan interior + `1px` dark border), Bold band number `1..8`,
     and `12x12` vector SVG Dynamics Ring (`ableton_dyn_ring_off/on.svg`) with zero background square artifacts.
   - Clicking a band's filter curve button opens a vertical 8-icon graphical popup menu (`fpop_bg` + `fpop_item_0..7`)
     directly above that band, highlighting the active filter shape in Cyan (`live_lcd_control_fg_alt`).
3. High-Resolution 4096-Point Native C++ FFT Spectrum Analyzer (`fft~ 4096 4096 0` -> `poke~ ---rta_fft`):
   - Computes a 4096-sample Hann-windowed FFT in native C++ (`10.77 Hz` bin resolution) and maps all 2048 bins
     in `deq_eight_ui_dev.js` onto the exact `20 Hz .. 20 kHz` 3-decade logarithmic grid.
4. Sidechain Spine & Expandable Panels Matching Glue Compressor:
   - Uses `1px` `live.line` dividers (`sc_spine_div`, `sc_col_div`) instead of 4px-clamped `panel` objects.
   - Bordered `Source` dropdowns (`framecolor = live_contrast_frame`) and clean `appearance=0` `Mix` / `SC Gain` numboxes.
"""

import json
import os
import struct


def tc(token):
    """Helper returning a Max 9 dynamic theme color expression dictionary."""
    return {"expression": f"themecolor.{token}"}


TRANSPARENT = [0.0, 0.0, 0.0, 0.0]


def write_svg_assets(out_dir):
    """Writes pure-black vector SVG templates dynamically recolored inside M4L via remapsvgcolors=1."""
    svgs = {
        "tri_closed.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 14 14" width="14" height="14">
  <polygon points="5.0,3.6 10.4,7.0 5.0,10.4" fill="black"/>
</svg>""",
        "tri_open.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 14 14" width="14" height="14">
  <polygon points="3.6,5.2 10.4,5.2 7.0,10.4" fill="black"/>
</svg>""",
        "headphones.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 14" width="16" height="14">
  <path d="M2.75 7.5A5.25 5.25 0 0 1 13.25 7.5H11.75A3.75 3.75 0 0 0 4.25 7.5H2.75Z" fill="black"/>
  <rect x="2.0" y="6.8" width="2.4" height="4.5" rx="1.0" fill="black"/>
  <rect x="11.6" y="6.8" width="2.4" height="4.5" rx="1.0" fill="black"/>
</svg>""",
        "rta_bars.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 18 12" width="18" height="12">
  <rect x="2.0" y="6.0" width="1.7" height="5.0" fill="black"/>
  <rect x="5.0" y="2.2" width="1.7" height="8.8" fill="black"/>
  <rect x="8.0" y="4.2" width="1.7" height="6.8" fill="black"/>
  <rect x="11.0" y="1.0" width="1.7" height="10.0" fill="black"/>
  <rect x="14.0" y="7.0" width="1.7" height="4.0" fill="black"/>
</svg>""",
        "dyn_ring.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 13 13" width="13" height="13">
  <path fill-rule="evenodd" clip-rule="evenodd" d="M6.5 0.85A5.65 5.65 0 1 0 6.5 12.15A5.65 5.65 0 1 0 6.5 0.85ZM6.5 2.35A4.15 4.15 0 1 1 6.5 10.65A4.15 4.15 0 1 1 6.5 2.35Z" fill="black"/>
</svg>""",
        # 24x11 (`usesvgviewbox=0` + corner bounds anchors) filled-path SVGs matching Ableton EQ Eight:
        # - Left-sided with clean left padding (`x = 0.90 .. 20.10` inside `24px` width) so the curve sits left in the dropdown box
        # - Slightly shrunk from the 28x12 curve while restoring normal popup menu SVG dimensions (`usesvgviewbox=0`)
        "eq8_lc48.svg": """<svg width="24" height="11" viewBox="0 0 24 11" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="0" y="0" width="0.1" height="0.1" fill="black" fill-opacity="0.01"/>
<rect x="23.9" y="10.9" width="0.1" height="0.1" fill="black" fill-opacity="0.01"/>
<path fill-rule="evenodd" clip-rule="evenodd" d="M1.20 4.35C1.20 2.65 2.55 1.30 4.25 1.30H19.40V2.75H4.25C3.35 2.75 2.62 3.48 2.62 4.35V10.10H1.20V4.35ZM6.60 5.10L8.10 6.65L9.60 5.10L10.40 5.90L8.90 7.45L10.40 9.00L9.60 9.80L8.10 8.25L6.60 9.80L5.80 9.00L7.30 7.45L5.80 5.90L6.60 5.10ZM14.40 4.60H15.40V7.70H16.30V8.70H15.40V9.80H14.40V8.70H11.70V7.70L14.40 4.60ZM14.40 5.90L12.80 7.70H14.40V5.90Z" fill="black"/>
</svg>""",
        "eq8_lc12.svg": """<svg width="24" height="11" viewBox="0 0 24 11" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="0" y="0" width="0.1" height="0.1" fill="black" fill-opacity="0.01"/>
<rect x="23.9" y="10.9" width="0.1" height="0.1" fill="black" fill-opacity="0.01"/>
<path fill-rule="evenodd" clip-rule="evenodd" d="M1.55 5.15C1.55 3.22 3.10 1.68 5.02 1.68H19.60V3.12H5.02C3.90 3.12 3.00 4.02 3.00 5.15V10.10H1.55V5.15Z" fill="black"/>
</svg>""",
        "eq8_lshelf.svg": """<svg width="24" height="11" viewBox="0 0 24 11" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="0" y="0" width="0.1" height="0.1" fill="black" fill-opacity="0.01"/>
<rect x="23.9" y="10.9" width="0.1" height="0.1" fill="black" fill-opacity="0.01"/>
<path fill-rule="evenodd" clip-rule="evenodd" d="M0.90 1.50H7.25L10.40 4.80H19.90V6.25H10.40L7.25 9.55H0.90V8.10H6.65L9.05 5.52L6.65 2.95H0.90V1.50Z" fill="black"/>
</svg>""",
        "eq8_bell.svg": """<svg width="24" height="11" viewBox="0 0 24 11" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="0" y="0" width="0.1" height="0.1" fill="black" fill-opacity="0.01"/>
<rect x="23.9" y="10.9" width="0.1" height="0.1" fill="black" fill-opacity="0.01"/>
<path fill-rule="evenodd" clip-rule="evenodd" d="M0.90 4.80H5.15C6.05 2.30 8.15 1.18 10.85 1.18C13.55 1.18 15.65 2.30 16.55 4.80H20.80V6.25H16.55C15.65 8.75 13.55 9.88 10.85 9.88C8.15 9.88 6.05 8.75 5.15 6.25H0.90V4.80ZM10.85 2.62C8.65 2.62 6.95 3.65 6.45 5.52C6.95 7.40 8.65 8.42 10.85 8.42C13.05 8.42 14.75 7.40 15.25 5.52C14.75 3.65 13.05 2.62 10.85 2.62Z" fill="black"/>
</svg>""",
        "eq8_notch.svg": """<svg width="24" height="11" viewBox="0 0 24 11" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="0" y="0" width="0.1" height="0.1" fill="black" fill-opacity="0.01"/>
<rect x="23.9" y="10.9" width="0.1" height="0.1" fill="black" fill-opacity="0.01"/>
<path fill-rule="evenodd" clip-rule="evenodd" d="M0.90 1.90H6.40C8.70 1.90 10.10 3.75 10.10 6.45V10.05H11.70V6.45C11.70 3.75 13.10 1.90 15.40 1.90H20.80V3.35H15.40C13.90 3.35 13.10 4.70 13.10 6.45V10.05H8.70V6.45C8.70 4.70 7.90 3.35 6.40 3.35H0.90V1.90Z" fill="black"/>
</svg>""",
        "eq8_hshelf.svg": """<svg width="24" height="11" viewBox="0 0 24 11" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="0" y="0" width="0.1" height="0.1" fill="black" fill-opacity="0.01"/>
<rect x="23.9" y="10.9" width="0.1" height="0.1" fill="black" fill-opacity="0.01"/>
<path fill-rule="evenodd" clip-rule="evenodd" d="M19.90 1.50H13.55L10.40 4.80H0.90V6.25H10.40L13.55 9.55H19.90V8.10H14.15L11.75 5.52L14.15 2.95H19.90V1.50Z" fill="black"/>
</svg>""",
        "eq8_hc12.svg": """<svg width="24" height="11" viewBox="0 0 24 11" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="0" y="0" width="0.1" height="0.1" fill="black" fill-opacity="0.01"/>
<rect x="23.9" y="10.9" width="0.1" height="0.1" fill="black" fill-opacity="0.01"/>
<path fill-rule="evenodd" clip-rule="evenodd" d="M16.15 3.12H1.55V1.68H16.15C18.08 1.68 19.60 3.22 19.60 5.15V10.10H18.15V5.15C18.15 4.02 17.25 3.12 16.15 3.12Z" fill="black"/>
</svg>""",
        "eq8_hc48.svg": """<svg width="24" height="11" viewBox="0 0 24 11" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="0" y="0" width="0.1" height="0.1" fill="black" fill-opacity="0.01"/>
<rect x="23.9" y="10.9" width="0.1" height="0.1" fill="black" fill-opacity="0.01"/>
<path fill-rule="evenodd" clip-rule="evenodd" d="M16.95 2.75H1.75V1.30H16.95C18.65 1.30 20.00 2.65 20.00 4.35V10.10H18.58V4.35C18.58 3.48 17.85 2.75 16.95 2.75ZM5.20 5.10L6.70 6.65L8.20 5.10L9.00 5.90L7.50 7.45L9.00 9.00L8.20 9.80L6.70 8.25L5.20 9.80L4.40 9.00L5.90 7.45L4.40 5.90L5.20 5.10ZM13.00 4.60H14.00V7.70H14.90V8.70H14.00V9.80H13.00V8.70H10.30V7.70L13.00 4.60ZM13.00 5.90L11.40 7.70H13.00V5.90Z" fill="black"/>
</svg>""",
    }

    stale_full = os.path.join(out_dir, "dyn_ring_full.svg")
    if os.path.exists(stale_full):
        os.remove(stale_full)

    for fname, content in svgs.items():
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
            f.write(content)
    return list(svgs.keys())


def make_box(box_id, maxclass, text=None, varname="", patching_rect=None, presentation_rect=None, **kwargs):
    if patching_rect is None:
        patching_rect = [0.0, 0.0, 80.0, 20.0]
    box = {
        "id": box_id,
        "maxclass": maxclass,
        "patching_rect": patching_rect,
    }
    if text is not None:
        box["text"] = text
    if varname:
        box["varname"] = varname
    if presentation_rect is not None:
        box["presentation"] = 1
        box["presentation_rect"] = presentation_rect
    for k, v in kwargs.items():
        box[k] = v
    return {"box": box}


def make_live_menu(
    box_id, varname, shortname, items, initial_idx,
    patching_rect, presentation_rect, pictures=None,
    invisible=2, initial_enable=0, **kwargs
):
    """
    100% Native Ableton Live `live.menu` rectangle dropdown box:
    - Displays SVG curve icons via `usepicture=1, remapsvgcolors=1` (using Max 9's built-in `m4l-picts`
      `lowcut.svg`, `lowshelf.svg`, `bell.svg`, `notch.svg`, `highshelf.svg`, `highcut.svg` + 48dB `×4` variants)
      inside a single native `live.menu` box with zero JS popup overlays!
    """
    defaults = {
        "fontname": "Ableton Sans Medium",
        "fontsize": 11.0,
        "fontface": 0,
        "activebgcolor": [0.106, 0.094, 0.129, 1.0],
        "bordercolor": [0.067, 0.063, 0.086, 1.0],
        "focusbordercolor": [0.067, 0.063, 0.086, 1.0],
        "textcolor": [0.827, 0.804, 0.843, 1.0],
        "tricolor": [0.827, 0.804, 0.843, 1.0],
        "hltcolor": [0.224, 0.824, 0.894, 1.0],
        "hlttextcolor": [0.08, 0.07, 0.10, 1.0],
    }
    if pictures:
        defaults["pictures"] = pictures
        defaults["usepicture"] = 1
        defaults["remapsvgcolors"] = 1
        defaults["usesvgviewbox"] = 0
    defaults.update(kwargs)
    return make_box(
        box_id,
        "live.menu",
        varname=varname,
        patching_rect=patching_rect,
        presentation_rect=presentation_rect,
        numinlets=1,
        numoutlets=3,
        outlettype=["", "", "float"],
        parameter_enable=1,
        saved_attribute_attributes={
            "activebgcolor": tc("live_control_text_bg"),
            "bordercolor": tc("live_contrast_frame"),
            "focusbordercolor": tc("live_focus_frame"),
            "hltcolor": tc("live_lcd_control_fg_alt"),
            "hlttextcolor": tc("live_control_fg_on"),
            "textcolor": tc("live_control_fg"),
            "tricolor": tc("live_control_fg"),
            "valueof": {
                "parameter_enum": items,
                "parameter_initial": [initial_idx],
                "parameter_initial_enable": initial_enable,
                "parameter_invisible": invisible,
                "parameter_linknames": 0,
                "parameter_longname": kwargs.pop("longname", shortname),
                "parameter_mmax": len(items) - 1,
                "parameter_modmode": 0,
                "parameter_shortname": shortname,
                "parameter_type": 2,
                "parameter_unitstyle": 9,
            },
        },
        **defaults,
    )


def make_panel(box_id, varname, patching_rect, presentation_rect, bg_token="live_lcd_frame", border=0, border_token=None, rounded=0, **kwargs):
    saa = {"bgfillcolor": tc(bg_token)}
    if border_token:
        saa["bordercolor"] = tc(border_token)
    return make_box(
        box_id,
        "panel",
        varname=varname,
        patching_rect=patching_rect,
        presentation_rect=presentation_rect,
        numinlets=1,
        numoutlets=0,
        mode=0,
        border=border,
        rounded=rounded,
        bgcolor=[0.278, 0.255, 0.329, 1.0],
        saved_attribute_attributes=saa,
        **kwargs,
    )


def make_live_line(box_id, varname, patching_rect, presentation_rect, color_token="live_control_bg", thickness=1.0, **kwargs):
    """
    Uses `live.line` for 1px/2px dividers because Max's `panel` clamps its minimum width to 4px!
    """
    return make_box(
        box_id,
        "live.line",
        varname=varname,
        patching_rect=patching_rect,
        presentation_rect=presentation_rect,
        numinlets=1,
        numoutlets=0,
        justification=0,
        border=float(thickness),
        linecolor=[0.125, 0.118, 0.153, 1.0],
        saved_attribute_attributes={"linecolor": tc(color_token)},
        **kwargs,
    )


def make_comment(box_id, varname, text_str, patching_rect, presentation_rect, color_token="live_control_fg", fontsize=10.0, justification=0, fontface=1, **kwargs):
    return make_box(
        box_id,
        "live.comment",
        varname=varname,
        patching_rect=patching_rect,
        presentation_rect=presentation_rect,
        numinlets=1,
        numoutlets=0,
        text=text_str,
        fontname="Ableton Sans Small Bold",
        fontsize=fontsize,
        fontface=fontface,
        textjustification=justification,
        textcolor=[0.827, 0.804, 0.843, 1.0],
        saved_attribute_attributes={"textcolor": tc(color_token)},
        **kwargs,
    )


def make_live_tab(box_id, varname, shortname, items, initial_idx, patching_rect, presentation_rect, invisible=0, initial_enable=1, **kwargs):
    fsize = kwargs.pop("fontsize", 10.0)
    return make_box(
        box_id,
        "live.tab",
        varname=varname,
        patching_rect=patching_rect,
        presentation_rect=presentation_rect,
        numinlets=1,
        numoutlets=3,
        outlettype=["", "", "float"],
        num_lines_patching=1,
        num_lines_presentation=1,
        fontname="Ableton Sans Small Bold",
        fontsize=fsize,
        fontface=1,
        bgcolor=[0.106, 0.094, 0.129, 1.0],
        bgoncolor=[1.0, 0.569, 0.765, 1.0],
        activebgoncolor=[1.0, 0.569, 0.765, 1.0],
        bordercolor=[0.067, 0.063, 0.086, 1.0],
        textcolor=[0.827, 0.804, 0.843, 1.0],
        textoncolor=[0.08, 0.07, 0.10, 1.0],
        parameter_enable=1,
        saved_attribute_attributes={
            "bgcolor": tc("live_control_bg"),
            "activebgcolor": tc("live_control_bg"),
            "bgoncolor": tc("live_display_handle_one"),
            "activebgoncolor": tc("live_display_handle_one"),
            "bordercolor": tc("live_contrast_frame"),
            "textcolor": tc("live_control_fg_off"),
            "textoncolor": tc("live_control_fg_on"),
            "valueof": {
                "parameter_enum": items,
                "parameter_initial": [initial_idx],
                "parameter_initial_enable": initial_enable,
                "parameter_invisible": invisible,
                "parameter_linknames": 0,
                "parameter_longname": kwargs.pop("longname", shortname),
                "parameter_mmax": len(items) - 1,
                "parameter_modmode": 0,
                "parameter_shortname": shortname,
                "parameter_type": 2,
                "parameter_unitstyle": 9,
            },
        },
        **kwargs,
    )


def make_live_text(
    box_id, varname, shortname, text_off, text_on, mode, initial_val,
    patching_rect, presentation_rect, on_token="live_display_handle_one",
    invisible=0, initial_enable=1, transparent_bg=False,
    off_fg_token="live_control_fg_off", on_fg_token="live_control_fg_on", **kwargs
):
    """
    NOTE:
    1. `parameter_enable=1` with a valid `valueof` enum `["Off", "On"]` ensures `mode=1` toggles
       never get stuck in the ON state.
    2. When `transparent_bg=True` (used for circular/icon SVG buttons like `sc_expand_btn`,
       `sc_listen_btn`, `band_dyn_btn_0..7`), we MUST NOT put `bgcolor`/`bgoncolor`/`bordercolor`
       into `saved_attribute_attributes`, otherwise Max's theme engine overrides `TRANSPARENT`
       and draws an unwanted pink/black rectangular box behind the circular SVG!
    """
    val_dict = {
        "parameter_enum": [text_off if text_off else "Off", text_on if text_on else "On"],
        "parameter_initial": [initial_val],
        "parameter_initial_enable": initial_enable,
        "parameter_linknames": 0,
        "parameter_longname": kwargs.pop("longname", shortname),
        "parameter_mmax": 1,
        "parameter_modmode": 0,
        "parameter_shortname": shortname,
        "parameter_type": 2,
        "parameter_invisible": invisible,
    }
    if transparent_bg:
        saa = {
            "textcolor": tc(off_fg_token),
            "activefgcolor": tc(off_fg_token),
            "textoncolor": tc(on_fg_token),
            "activetextoncolor": tc(on_fg_token),
            "valueof": val_dict,
        }
        defaults = {
            "fontname": "Ableton Sans Small Bold",
            "fontsize": 10.0,
            "fontface": 1,
            "border": 0,
            "bgcolor": TRANSPARENT,
            "activebgcolor": TRANSPARENT,
            "bgoncolor": TRANSPARENT,
            "activebgoncolor": TRANSPARENT,
            "bordercolor": TRANSPARENT,
            "focusbordercolor": TRANSPARENT,
            "textcolor": [0.827, 0.804, 0.843, 1.0],
            "activefgcolor": [0.827, 0.804, 0.843, 1.0],
            "textoncolor": [0.224, 0.824, 0.894, 1.0],
            "activetextoncolor": [0.224, 0.824, 0.894, 1.0],
        }
    else:
        saa = {
            "bgcolor": tc("live_control_bg"),
            "activebgcolor": tc("live_control_bg"),
            "bgoncolor": tc(on_token),
            "activebgoncolor": tc(on_token),
            "bordercolor": tc("live_contrast_frame"),
            "textcolor": tc("live_control_fg_off"),
            "activefgcolor": tc("live_control_fg_off"),
            "textoncolor": tc("live_control_fg_on"),
            "activetextoncolor": tc("live_control_fg_on"),
            "valueof": val_dict,
        }
        defaults = {
            "fontname": "Ableton Sans Small Bold",
            "fontsize": 10.0,
            "fontface": 1,
            "bgcolor": [0.106, 0.094, 0.129, 1.0],
            "bgoncolor": [1.0, 0.569, 0.765, 1.0],
            "activebgoncolor": [1.0, 0.569, 0.765, 1.0],
            "bordercolor": [0.067, 0.063, 0.086, 1.0],
            "textcolor": [0.827, 0.804, 0.843, 1.0],
            "textoncolor": [0.08, 0.07, 0.10, 1.0],
        }
    extra_saa = kwargs.pop("saved_attribute_attributes", None)
    if extra_saa:
        saa.update(extra_saa)
    defaults.update(kwargs)
    return make_box(
        box_id,
        "live.text",
        text=text_off,
        varname=varname,
        patching_rect=patching_rect,
        presentation_rect=presentation_rect,
        numinlets=1,
        numoutlets=2,
        outlettype=["", ""],
        mode=mode,
        texton=text_on,
        parameter_enable=1,
        saved_attribute_attributes=saa,
        **defaults,
    )


def make_live_numbox(
    box_id, varname, shortname, mmin, mmax, initial_val, unitstyle,
    patching_rect, presentation_rect, exponent=1.0, param_type=0, custom_units=None,
    invisible=0, initial_enable=1, **kwargs
):
    """
    Matches Vanilla Ableton EQ Eight & Glue Compressor `live.numbox`:
    - `activeslidercolor`: `themecolor.live_value_bar` (Dark Teal `#00717f`, high contrast under white text!)
    - `activebgcolor`: `themecolor.live_control_text_bg`
    - `bordercolor`: `themecolor.live_contrast_frame`
    - `textcolor`: `themecolor.live_control_fg`
    - `fontface`: 1 (Bold)
    - Supports `custom_units="%.2f dB"` (`unitstyle=9`) for double-digit float precision (`0.00 dB`),
      and `custom_units="%.0f %%"` for integer-formatted percentages (`100 %`).
    """
    defaults = {
        "appearance": 2,
        "fontname": "Ableton Sans Medium",
        "fontsize": 10.5,
        "fontface": 0,
        "activebgcolor": [0.106, 0.094, 0.129, 1.0],
        "activeslidercolor": [0.0, 0.443, 0.498, 1.0],
        "bordercolor": [0.067, 0.063, 0.086, 1.0],
        "textcolor": [0.827, 0.804, 0.843, 1.0],
    }
    defaults.update(kwargs)
    val_attrs = {
        "parameter_initial": [initial_val],
        "parameter_initial_enable": initial_enable,
        "parameter_invisible": invisible,
        "parameter_longname": varname,
        "parameter_mmin": float(mmin),
        "parameter_mmax": float(mmax),
        "parameter_modmode": 3,
        "parameter_shortname": shortname,
        "parameter_type": param_type,
        "parameter_unitstyle": 9 if custom_units else unitstyle,
    }
    if custom_units:
        val_attrs["parameter_units"] = custom_units
    if exponent != 1.0:
        val_attrs["parameter_exponent"] = float(exponent)
    return make_box(
        box_id,
        "live.numbox",
        varname=varname,
        patching_rect=patching_rect,
        presentation_rect=presentation_rect,
        numinlets=1,
        numoutlets=2,
        outlettype=["", "float"],
        parameter_enable=1,
        saved_attribute_attributes={
            "activebgcolor": tc("live_control_text_bg"),
            "activeslidercolor": tc("live_value_bar"),
            "activetricolor": tc("live_control_bg"),
            "activetricolor2": tc("live_numbox_triangle"),
            "bordercolor": tc("live_contrast_frame"),
            "focusbordercolor": tc("live_focus_frame"),
            "textcolor": tc("live_control_fg"),
            "valueof": val_attrs,
        },
        **defaults,
    )


def make_live_dial(
    box_id, varname, shortname, mmin, mmax, initial_val, unitstyle,
    patching_rect, presentation_rect, exponent=1.0, custom_units=None,
    invisible=0, initial_enable=1, **kwargs
):
    """
    Matches Vanilla Ableton EQ Eight & Glue Compressor `live.dial` 1:1:
    - `activedialcolor`: `themecolor.live_value_arc` (Cyan value arc)
    - `activefgdialcolor`: `themecolor.live_dial_fg` (Dark unfilled ring)
    - `activeneedlecolor`: `themecolor.live_dial_needle` (Dark needle!)
    - `dialcolor`: `themecolor.live_value_arc_zombie`
    - `fgdialcolor`: `themecolor.live_dial_fg_zombie`
    - `needlecolor`: `themecolor.live_dial_needle_zombie`
    - `textcolor`: `themecolor.live_control_fg`
    - `tricolor`: `themecolor.live_dial_triangle`
    - `fontface`: 1 (Bold)
    """
    defaults = {
        "fontname": "Ableton Sans Medium",
        "fontsize": 10.5,
        "fontface": 0,
        "showname": 0,
        "activedialcolor": [0.224, 0.824, 0.894, 1.0],
        "activefgdialcolor": [0.078, 0.075, 0.102, 1.0],
        "activeneedlecolor": [0.078, 0.075, 0.102, 1.0],
        "dialcolor": [0.106, 0.094, 0.129, 1.0],
        "fgdialcolor": [0.106, 0.094, 0.129, 1.0],
        "needlecolor": [0.106, 0.094, 0.129, 1.0],
        "textcolor": [0.827, 0.804, 0.843, 1.0],
    }
    defaults.update(kwargs)
    val_attrs = {
        "parameter_initial": [initial_val],
        "parameter_initial_enable": initial_enable,
        "parameter_invisible": invisible,
        "parameter_longname": varname,
        "parameter_mmin": float(mmin),
        "parameter_mmax": float(mmax),
        "parameter_modmode": 3,
        "parameter_shortname": shortname,
        "parameter_type": 0,
        "parameter_unitstyle": 9 if custom_units else unitstyle,
    }
    if custom_units:
        val_attrs["parameter_units"] = custom_units
    if exponent != 1.0:
        val_attrs["parameter_exponent"] = float(exponent)
    return make_box(
        box_id,
        "live.dial",
        varname=varname,
        patching_rect=patching_rect,
        presentation_rect=presentation_rect,
        numinlets=1,
        numoutlets=2,
        outlettype=["", "float"],
        parameter_enable=1,
        saved_attribute_attributes={
            "activedialcolor": tc("live_value_arc"),
            "activefgdialcolor": tc("live_dial_fg"),
            "activeneedlecolor": tc("live_dial_needle"),
            "bordercolor": tc("live_surface_frame"),
            "dialcolor": tc("live_value_arc_zombie"),
            "fgdialcolor": tc("live_dial_fg_zombie"),
            "focusbordercolor": tc("live_focus_frame"),
            "needlecolor": tc("live_dial_needle_zombie"),
            "textcolor": tc("live_control_fg"),
            "tricolor": tc("live_dial_triangle"),
            "valueof": val_attrs,
        },
        **defaults,
    )


def make_umenu(box_id, varname, items, patching_rect, presentation_rect, **kwargs):
    """
    Matches Glue Compressor Sidechain `Source` dropdowns:
    - Interleaves `","` between items so Max renders separate menu rows.
    - Uses `live_surface_bg` fill with a crisp `1px` `live_contrast_frame` border (`framecolor`) and Bold font.
    """
    umenu_items = []
    for idx, item in enumerate(items):
        if idx > 0:
            umenu_items.append(",")
        umenu_items.append(item)

    return make_box(
        box_id,
        "umenu",
        varname=varname,
        patching_rect=patching_rect,
        presentation_rect=presentation_rect,
        numinlets=1,
        numoutlets=3,
        outlettype=["int", "", ""],
        items=umenu_items,
        applycolors=1,
        bgcolor=[0.106, 0.094, 0.129, 1.0],
        bgfillcolor={
            "type": "color",
            "color": [0.106, 0.094, 0.129, 1.0],
            "color1": [0.106, 0.094, 0.129, 1.0],
            "color2": [0.106, 0.094, 0.129, 1.0],
        },
        color=[0.224, 0.824, 0.894, 1.0],
        elementcolor=[0.180, 0.165, 0.212, 1.0],
        framecolor=[0.067, 0.063, 0.086, 1.0],
        textcolor=[0.827, 0.804, 0.843, 1.0],
        fontname="Ableton Sans Medium",
        fontsize=9.5,
        fontface=0,
        saved_attribute_attributes={
            "bgfillcolor": tc("live_control_text_bg"),
            "color": tc("live_lcd_control_fg_alt"),
            "elementcolor": tc("live_control_bg"),
            "framecolor": tc("live_contrast_frame"),
            "textcolor": tc("live_control_fg"),
        },
        **kwargs,
    )


def make_line(src_id, src_outlet, dst_id, dst_inlet):
    return {
        "patchline": {
            "source": [src_id, src_outlet],
            "destination": [dst_id, dst_inlet],
        }
    }


def generate_gen_codebox():
    """
    Generates the 64-bit GenExpr codebox for the 8-Band Cytomic ZDF Trapezoidal SVF
    + Nyquist-Decramped Dynamic EQ Engine (Outlets 1..2 audio, 3..10 dG_1..8).
    """
    default_freqs = [30.0, 200.0, 1000.0, 5000.0, 100.0, 1000.0, 5000.0, 18000.0]
    default_types = [2, 3, 3, 5, 3, 3, 3, 6]
    default_on    = [1, 1, 1, 1, 0, 0, 0, 0]

    code = [
        "// ============================================================================",
        "// OpenAir dEQ Eight - 64-Bit Cytomic ZDF Trapezoidal SVF Engine",
        "// ============================================================================",
        "",
        "Param adapt_q(1);",
        "Param dyn_scale(1.0);",
        "Param out_gain(0.0);",
        "Param solo_band(0);",
        "Param sc1_mix(0.0);",
        "Param sc2_mix(0.0);",
        "",
    ]

    for b in range(1, 9):
        f_init = default_freqs[b - 1]
        t_init = default_types[b - 1]
        on_init = default_on[b - 1]
        code.extend([
            f"Param b{b}_on({on_init});",
            f"Param b{b}_type({t_init});",
            f"Param b{b}_freq({f_init});",
            f"Param b{b}_gain(0.0);",
            f"Param b{b}_q(0.71);",
            f"Param b{b}_dyn_on(0);",
            f"Param b{b}_dyn_range(0.0);",
            f"Param b{b}_thresh(-22.0);",
            f"Param b{b}_attack(5.0);",
            f"Param b{b}_release(110.0);",
            f"Param b{b}_source(0);",
            f"History det_ic1_{b}(0.0), det_ic2_{b}(0.0);",
            f"History env_{b}(0.0), mod_db_{b}(0.0);",
            f"History s1L_ic1_{b}(0.0), s1L_ic2_{b}(0.0), s1R_ic1_{b}(0.0), s1R_ic2_{b}(0.0);",
            f"History s2L_ic1_{b}(0.0), s2L_ic2_{b}(0.0), s2R_ic1_{b}(0.0), s2R_ic2_{b}(0.0);",
        ])

    code.extend([
        "",
        "sigL = in1;",
        "sigR = in2;",
        "in_mono = (in1 + in2) * 0.5;",
        "sc1_mono = (1.0 - sc1_mix) * in_mono + sc1_mix * in3;",
        "sc2_mono = (1.0 - sc2_mix) * in_mono + sc2_mix * in4;",
        "soloL = 0.0;",
        "soloR = 0.0;",
        "",
    ])

    for b in range(1, 9):
        code.extend([
            f"// ==================== BAND {b} ====================",
            f"if (b{b}_on > 0.5 || round(solo_band) == {b}) {{",
            f"    fc_{b} = clip(b{b}_freq, 10.0, samplerate * 0.485);",
            f"    w0_{b} = pi * fc_{b} / samplerate;",
            f"    g0_{b} = tan(w0_{b});",
            f"    bp_sig_{b} = 0.0;",
            f"    if (b{b}_dyn_on > 0.5 || round(solo_band) == {b}) {{",
            f"        sc_in_{b} = (b{b}_source < 0.5) ? in_mono : ((b{b}_source < 1.5) ? sc1_mono : sc2_mono);",
            f"        k_det_{b} = 1.0 / clip(b{b}_q, 0.35, 12.0);",
            f"        da1_{b} = 1.0 / (1.0 + g0_{b} * (g0_{b} + k_det_{b}));",
            f"        da2_{b} = g0_{b} * da1_{b};",
            f"        da3_{b} = g0_{b} * da2_{b};",
            f"        dv3_{b} = sc_in_{b} - det_ic2_{b};",
            f"        dv1_{b} = da1_{b} * det_ic1_{b} + da2_{b} * dv3_{b};",
            f"        dv2_{b} = det_ic2_{b} + da2_{b} * det_ic1_{b} + da3_{b} * dv3_{b};",
            f"        det_ic1_{b} = 2.0 * dv1_{b} - det_ic1_{b};",
            f"        det_ic2_{b} = 2.0 * dv2_{b} - det_ic2_{b};",
            f"        bp_sig_{b} = k_det_{b} * dv1_{b};",
            f"        atk_c_{b} = exp(-1000.0 / (max(0.1, b{b}_attack) * samplerate));",
            f"        rel_c_{b} = exp(-1000.0 / (max(5.0, b{b}_release) * samplerate));",
            f"        rect_{b} = abs(bp_sig_{b});",
            f"        env_{b} = (rect_{b} > env_{b}) ? (atk_c_{b} * env_{b} + (1.0 - atk_c_{b}) * rect_{b}) : (rel_c_{b} * env_{b} + (1.0 - rel_c_{b}) * rect_{b});",
            f"        env_db_{b} = 20.0 * log10(max(0.000001, env_{b}));",
            f"        over_db_{b} = env_db_{b} - b{b}_thresh;",
            f"        ratio_{b} = clip(over_db_{b} / 18.0, 0.0, 1.0);",
            f"        target_mod_{b} = (over_db_{b} > 0.0) ? (b{b}_dyn_range * ratio_{b}) : 0.0;",
            f"        mod_db_{b} = (b{b}_dyn_on > 0.5) ? (0.992 * mod_db_{b} + 0.008 * target_mod_{b}) : 0.0;",
            f"    }} else {{",
            f"        env_{b} = 0.0;",
            f"        mod_db_{b} = 0.0;",
            f"    }}",
            f"    if (round(solo_band) == {b}) {{",
            f"        soloL = bp_sig_{b};",
            f"        soloR = bp_sig_{b};",
            f"    }}",
            f"    if (b{b}_on > 0.5) {{",
            f"        t_{b} = round(b{b}_type);",
            f"        tot_gain_{b} = (b{b}_gain + mod_db_{b}) * dyn_scale;",
            f"        q_base_{b} = clip(b{b}_q, 0.1, 18.0);",
            f"        q_eff_{b} = (adapt_q > 0.5 && (t_{b} == 3 || t_{b} == 2 || t_{b} == 5)) ? clip(q_base_{b} * pow(2.0, abs(tot_gain_{b}) / 18.0), 0.1, 18.0) : q_base_{b};",
            f"        nyq_{b} = max(0.25, cos(w0_{b} * 0.70));",
            f"        k_{b} = 1.0 / (q_eff_{b} * nyq_{b});",
            f"        g_{b} = g0_{b};",
            f"        m0_{b} = 1.0; m1_{b} = 0.0; m2_{b} = 0.0;",
            f"        if (t_{b} == 3) {{",
            f"            A_{b} = pow(10.0, tot_gain_{b} / 40.0);",
            f"            k_{b} = k_{b} / A_{b};",
            f"            m0_{b} = 1.0;",
            f"            m1_{b} = k_{b} * (A_{b} * A_{b} - 1.0);",
            f"            m2_{b} = 0.0;",
            f"        }} else if (t_{b} == 2) {{",
            f"            A_{b} = pow(10.0, tot_gain_{b} / 40.0);",
            f"            g_{b} = g0_{b} / sqrt(A_{b});",
            f"            m0_{b} = 1.0;",
            f"            m1_{b} = k_{b} * (A_{b} - 1.0);",
            f"            m2_{b} = A_{b} * A_{b} - 1.0;",
            f"        }} else if (t_{b} == 5) {{",
            f"            A_{b} = pow(10.0, tot_gain_{b} / 40.0);",
            f"            g_{b} = g0_{b} * sqrt(A_{b});",
            f"            m0_{b} = A_{b} * A_{b};",
            f"            m1_{b} = k_{b} * (1.0 - A_{b}) * A_{b};",
            f"            m2_{b} = 1.0 - A_{b} * A_{b};",
            f"        }} else if (t_{b} == 1 || t_{b} == 0) {{",
            f"            m0_{b} = 1.0;",
            f"            m1_{b} = -k_{b};",
            f"            m2_{b} = -1.0;",
            f"        }} else if (t_{b} == 6 || t_{b} == 7) {{",
            f"            m0_{b} = 0.0;",
            f"            m1_{b} = 0.0;",
            f"            m2_{b} = 1.0;",
            f"        }} else if (t_{b} == 4) {{",
            f"            m0_{b} = 1.0;",
            f"            m1_{b} = -k_{b};",
            f"            m2_{b} = 0.0;",
            f"        }}",
            f"        a1_{b} = 1.0 / (1.0 + g_{b} * (g_{b} + k_{b}));",
            f"        a2_{b} = g_{b} * a1_{b};",
            f"        a3_{b} = g_{b} * a2_{b};",
            f"        v3L_{b} = sigL - s1L_ic2_{b};",
            f"        v1L_{b} = a1_{b} * s1L_ic1_{b} + a2_{b} * v3L_{b};",
            f"        v2L_{b} = s1L_ic2_{b} + a2_{b} * s1L_ic1_{b} + a3_{b} * v3L_{b};",
            f"        s1L_ic1_{b} = 2.0 * v1L_{b} - s1L_ic1_{b};",
            f"        s1L_ic2_{b} = 2.0 * v2L_{b} - s1L_ic2_{b};",
            f"        sigL = m0_{b} * sigL + m1_{b} * v1L_{b} + m2_{b} * v2L_{b};",
            f"        v3R_{b} = sigR - s1R_ic2_{b};",
            f"        v1R_{b} = a1_{b} * s1R_ic1_{b} + a2_{b} * v3R_{b};",
            f"        v2R_{b} = s1R_ic2_{b} + a2_{b} * s1R_ic1_{b} + a3_{b} * v3R_{b};",
            f"        s1R_ic1_{b} = 2.0 * v1R_{b} - s1R_ic1_{b};",
            f"        s1R_ic2_{b} = 2.0 * v2R_{b} - s1R_ic2_{b};",
            f"        sigR = m0_{b} * sigR + m1_{b} * v1R_{b} + m2_{b} * v2R_{b};",
            f"        if (t_{b} == 0 || t_{b} == 7) {{",
            f"            v3L2_{b} = sigL - s2L_ic2_{b};",
            f"            v1L2_{b} = a1_{b} * s2L_ic1_{b} + a2_{b} * v3L2_{b};",
            f"            v2L2_{b} = s2L_ic2_{b} + a2_{b} * s2L_ic1_{b} + a3_{b} * v3L2_{b};",
            f"            s2L_ic1_{b} = 2.0 * v1L2_{b} - s2L_ic1_{b};",
            f"            s2L_ic2_{b} = 2.0 * v2L2_{b} - s2L_ic2_{b};",
            f"            sigL = m0_{b} * sigL + m1_{b} * v1L2_{b} + m2_{b} * v2L2_{b};",
            f"            v3R2_{b} = sigR - s2R_ic2_{b};",
            f"            v1R2_{b} = a1_{b} * s2R_ic1_{b} + a2_{b} * v3R2_{b};",
            f"            v2R2_{b} = s2R_ic2_{b} + a2_{b} * s2R_ic1_{b} + a3_{b} * v3R2_{b};",
            f"            s2R_ic1_{b} = 2.0 * v1R2_{b} - s2R_ic1_{b};",
            f"            s2R_ic2_{b} = 2.0 * v2R2_{b} - s2R_ic2_{b};",
            f"            sigR = m0_{b} * sigR + m1_{b} * v1R2_{b} + m2_{b} * v2R2_{b};",
            f"        }}",
            f"    }}",
            f"}} else {{",
            f"    mod_db_{b} = 0.0;",
            f"}}",
            f"out{b + 2} = mod_db_{b};",
            "",
        ])

    code.extend([
        "out_lin = pow(10.0, out_gain / 20.0);",
        "out_L = sigL * out_lin;",
        "out_R = sigR * out_lin;",
        "if (round(solo_band) == 9) {",
        "    out1 = sc1_mono;",
        "    out2 = sc2_mono;",
        "} else if (solo_band > 0.5) {",
        "    out1 = soloL;",
        "    out2 = soloR;",
        "} else {",
        "    out1 = out_L;",
        "    out2 = out_R;",
        "}",
    ])

    return "\r\n".join(code)


def build_gen_patcher():
    """Builds the internal `gen~` patcher (4 audio inlets, 10 audio outlets: L, R, dG_1..8)."""
    gen_boxes = [
        make_box("obj-in1", "newobj", "in 1", patching_rect=[40.0, 20.0, 30.0, 22.0], numinlets=0, numoutlets=1, outlettype=[""]),
        make_box("obj-in2", "newobj", "in 2", patching_rect=[180.0, 20.0, 30.0, 22.0], numinlets=0, numoutlets=1, outlettype=[""]),
        make_box("obj-in3", "newobj", "in 3", patching_rect=[320.0, 20.0, 30.0, 22.0], numinlets=0, numoutlets=1, outlettype=[""]),
        make_box("obj-in4", "newobj", "in 4", patching_rect=[460.0, 20.0, 30.0, 22.0], numinlets=0, numoutlets=1, outlettype=[""]),
        make_box(
            "obj-codebox",
            "codebox",
            patching_rect=[40.0, 65.0, 760.0, 520.0],
            numinlets=4,
            numoutlets=10,
            outlettype=[""] * 10,
            code=generate_gen_codebox(),
        ),
    ]
    gen_lines = [
        make_line("obj-in1", 0, "obj-codebox", 0),
        make_line("obj-in2", 0, "obj-codebox", 1),
        make_line("obj-in3", 0, "obj-codebox", 2),
        make_line("obj-in4", 0, "obj-codebox", 3),
    ]
    for o in range(1, 11):
        out_id = f"obj-out{o}"
        ox = 20.0 + (o - 1) * 65.0
        gen_boxes.append(
            make_box(out_id, "newobj", f"out {o}", patching_rect=[ox, 610.0, 42.0, 22.0], numinlets=1, numoutlets=0, outlettype=[])
        )
        gen_lines.append(make_line("obj-codebox", o - 1, out_id, 0))

    return {
        "fileversion": 1,
        "appversion": {"major": 9, "minor": 0, "revision": 0, "architecture": "x64", "modernui": 1},
        "classnamespace": "dsp.gen",
        "rect": [100.0, 100.0, 880.0, 680.0],
        "boxes": gen_boxes,
        "lines": gen_lines,
    }


def build_rta_fft_gen_patcher():
    """
    Builds a tiny 3-inlet, 2-outlet `gen~` patcher connected to `fft~ 4096 4096 0`:
    - Applies exact frequency-domain Hann windowing: `X_hann[k-1] = 0.5 * X[k-1] - 0.25 * (X[k-2] + X[k])`
      for -31.5 dB sidelobe suppression with zero time-domain phase alignment needed!
    - Outputs normalized bin magnitude on `out 1` and bin index `k-1` on `out 2` for `poke~ ---rta_fft`.
    """
    rta_code = "\r\n".join([
        "History r1(0.0), r2(0.0), i1(0.0), i2(0.0);",
        "k = in3 - 1;",
        "mag = 0.0;",
        "idx = -1;",
        "if (k >= 1 && k < 2048) {",
        "    rh = 0.5 * r1 - 0.25 * (r2 + in1);",
        "    ih = 0.5 * i1 - 0.25 * (i2 + in2);",
        "    mag = sqrt(rh * rh + ih * ih) * (2.0 / 2048.0);",
        "    idx = k;",
        "}",
        "r2 = r1; r1 = in1;",
        "i2 = i1; i1 = in2;",
        "out1 = mag;",
        "out2 = idx;",
    ])
    return {
        "fileversion": 1,
        "appversion": {"major": 9, "minor": 0, "revision": 0, "architecture": "x64", "modernui": 1},
        "classnamespace": "dsp.gen",
        "rect": [150.0, 150.0, 500.0, 320.0],
        "boxes": [
            make_box("obj-in1", "newobj", "in 1", patching_rect=[30.0, 20.0, 30.0, 22.0], numinlets=0, numoutlets=1, outlettype=[""]),
            make_box("obj-in2", "newobj", "in 2", patching_rect=[120.0, 20.0, 30.0, 22.0], numinlets=0, numoutlets=1, outlettype=[""]),
            make_box("obj-in3", "newobj", "in 3", patching_rect=[210.0, 20.0, 30.0, 22.0], numinlets=0, numoutlets=1, outlettype=[""]),
            make_box("obj-cb", "codebox", patching_rect=[30.0, 60.0, 420.0, 180.0], numinlets=3, numoutlets=2, outlettype=["", ""], code=rta_code),
            make_box("obj-out1", "newobj", "out 1", patching_rect=[30.0, 260.0, 36.0, 22.0], numinlets=1, numoutlets=0, outlettype=[]),
            make_box("obj-out2", "newobj", "out 2", patching_rect=[180.0, 260.0, 36.0, 22.0], numinlets=1, numoutlets=0, outlettype=[]),
        ],
        "lines": [
            make_line("obj-in1", 0, "obj-cb", 0),
            make_line("obj-in2", 0, "obj-cb", 1),
            make_line("obj-in3", 0, "obj-cb", 2),
            make_line("obj-cb", 0, "obj-out1", 0),
            make_line("obj-cb", 1, "obj-out2", 0),
        ],
    }


def build_device():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir_abs = out_dir.replace("\\", "/")
    svg_files = write_svg_assets(out_dir)

    boxes = []
    lines = []
    parameters = {}

    def reg_param(box_id, longname, shortname):
        parameters[box_id] = [longname, shortname, 0]

    # =========================================================================
    # 1. AUDIO I/O, 64-BIT GEN~ DSP & NATIVE C++ 4096-POINT FFT RTA (`fft~ 4096 4096 0`)
    # =========================================================================
    boxes.append(make_box("obj-plug-in", "newobj", "plugin~ 1 2", patching_rect=[30.0, 20.0, 75.0, 22.0], numinlets=2, numoutlets=2, outlettype=["signal", "signal"]))
    boxes.append(make_box("obj-sc1-in", "newobj", "plugin~ 3 4", patching_rect=[135.0, 20.0, 75.0, 22.0], numinlets=2, numoutlets=2, outlettype=["signal", "signal"]))
    boxes.append(make_box("obj-sc2-in", "newobj", "plugin~ 5 6", patching_rect=[245.0, 20.0, 75.0, 22.0], numinlets=2, numoutlets=2, outlettype=["signal", "signal"]))
    boxes.append(make_box("obj-plug-out", "newobj", "plugout~ 1 2", patching_rect=[30.0, 440.0, 82.0, 22.0], numinlets=2, numoutlets=0, outlettype=[]))

    boxes.append(make_box("obj-sc1-sum", "newobj", "+~", patching_rect=[135.0, 55.0, 32.0, 22.0], numinlets=2, numoutlets=1, outlettype=["signal"]))
    boxes.append(make_box("obj-sc1-half", "newobj", "*~ 0.5", patching_rect=[135.0, 82.0, 45.0, 22.0], numinlets=2, numoutlets=1, outlettype=["signal"]))
    boxes.append(make_box("obj-sc1-mult", "newobj", "*~ 1.", patching_rect=[135.0, 112.0, 42.0, 22.0], numinlets=2, numoutlets=1, outlettype=["signal"]))
    lines.append(make_line("obj-sc1-in", 0, "obj-sc1-sum", 0))
    lines.append(make_line("obj-sc1-in", 1, "obj-sc1-sum", 1))
    lines.append(make_line("obj-sc1-sum", 0, "obj-sc1-half", 0))
    lines.append(make_line("obj-sc1-half", 0, "obj-sc1-mult", 0))

    boxes.append(make_box("obj-sc2-sum", "newobj", "+~", patching_rect=[245.0, 55.0, 32.0, 22.0], numinlets=2, numoutlets=1, outlettype=["signal"]))
    boxes.append(make_box("obj-sc2-half", "newobj", "*~ 0.5", patching_rect=[245.0, 82.0, 45.0, 22.0], numinlets=2, numoutlets=1, outlettype=["signal"]))
    boxes.append(make_box("obj-sc2-mult", "newobj", "*~ 1.", patching_rect=[245.0, 112.0, 42.0, 22.0], numinlets=2, numoutlets=1, outlettype=["signal"]))
    lines.append(make_line("obj-sc2-in", 0, "obj-sc2-sum", 0))
    lines.append(make_line("obj-sc2-in", 1, "obj-sc2-sum", 1))
    lines.append(make_line("obj-sc2-sum", 0, "obj-sc2-half", 0))
    lines.append(make_line("obj-sc2-half", 0, "obj-sc2-mult", 0))

    boxes.append(make_box(
        "obj-gen-eq", "newobj", "gen~",
        patching_rect=[30.0, 220.0, 460.0, 24.0],
        numinlets=4, numoutlets=10,
        outlettype=["signal"] * 10,
        patcher=build_gen_patcher()
    ))
    lines.append(make_line("obj-plug-in", 0, "obj-gen-eq", 0))
    lines.append(make_line("obj-plug-in", 1, "obj-gen-eq", 1))
    lines.append(make_line("obj-sc1-mult", 0, "obj-gen-eq", 2))
    lines.append(make_line("obj-sc2-mult", 0, "obj-gen-eq", 3))
    lines.append(make_line("obj-gen-eq", 0, "obj-plug-out", 0))
    lines.append(make_line("obj-gen-eq", 1, "obj-plug-out", 1))

    # Post-EQ Mono Signal -> Native C++ 4096-Point FFT (`fft~ 4096 4096 0`) -> Hann Mag `gen~` -> `poke~ ---rta_fft`
    boxes.append(make_box("obj-rta-sum", "newobj", "+~", patching_rect=[140.0, 440.0, 32.0, 22.0], numinlets=2, numoutlets=1, outlettype=["signal"]))
    boxes.append(make_box("obj-rta-half", "newobj", "*~ 0.5", patching_rect=[140.0, 470.0, 45.0, 22.0], numinlets=2, numoutlets=1, outlettype=["signal"]))
    boxes.append(make_box("obj-rta-fft", "newobj", "fft~ 4096 4096 0", patching_rect=[140.0, 500.0, 105.0, 22.0], numinlets=2, numoutlets=3, outlettype=["signal", "signal", "signal"]))
    boxes.append(make_box(
        "obj-rta-gen", "newobj", "gen~",
        patching_rect=[140.0, 530.0, 105.0, 22.0],
        numinlets=3, numoutlets=2,
        outlettype=["signal", "signal"],
        patcher=build_rta_fft_gen_patcher()
    ))
    boxes.append(make_box("obj-rta-poke", "newobj", "poke~ ---rta_fft", patching_rect=[140.0, 560.0, 105.0, 22.0], numinlets=3, numoutlets=1, outlettype=["signal"]))
    boxes.append(make_box("obj-rta-buf", "newobj", "buffer~ ---rta_fft @samps 2048", patching_rect=[260.0, 560.0, 185.0, 22.0], numinlets=1, numoutlets=2, outlettype=["float", "bang"]))

    lines.append(make_line("obj-gen-eq", 0, "obj-rta-sum", 0))
    lines.append(make_line("obj-gen-eq", 1, "obj-rta-sum", 1))
    lines.append(make_line("obj-rta-sum", 0, "obj-rta-half", 0))
    lines.append(make_line("obj-rta-half", 0, "obj-rta-fft", 0))
    lines.append(make_line("obj-rta-fft", 0, "obj-rta-gen", 0))
    lines.append(make_line("obj-rta-fft", 1, "obj-rta-gen", 1))
    lines.append(make_line("obj-rta-fft", 2, "obj-rta-gen", 2))
    lines.append(make_line("obj-rta-gen", 0, "obj-rta-poke", 0))
    lines.append(make_line("obj-rta-gen", 1, "obj-rta-poke", 1))

    # Central Controller JS + M4L `pattr` Blob State Persistence (`obj-state-pattr`)
    # Follows official Cycling '74 M4L architecture (`Max DelayTaps.amxd`, `Waveshaper.amxd`):
    # All 8 bands + UI state persist inside `pattr eq_state @thru 2` (`parameter_type=3`, `parameter_invisible=1`)
    # so opening/closing the Max editor, saving/loading Live Sets (.als), and saving presets (.adv) never reset!
    boxes.append(make_box(
        "obj-lom", "newobj", "js deq_eight_lom_dev.js",
        varname="lom_js",
        patching_rect=[520.0, 180.0, 185.0, 22.0],
        numinlets=1, numoutlets=6, outlettype=["", "", "", "", "", ""]
    ))
    lines.append(make_line("obj-lom", 1, "obj-gen-eq", 0))

    default_freqs_init = [30.0, 200.0, 1000.0, 5000.0, 100.0, 1000.0, 5000.0, 18000.0]
    default_types_init = [2, 3, 3, 5, 3, 3, 3, 6]
    default_on_init    = [1, 1, 1, 1, 0, 0, 0, 0]
    default_state_list = [
        3,     # 0: STATE_VERSION = 3
        2,     # 1: selected_band (Band 3)
        0,     # 2: sc_panel_open
        0,     # 3: dyn_panel_open
        1,     # 4: adaptive_q
        100.0, # 5: global_scale (100%)
        0.0,   # 6: out_gain
        1,     # 7: rta_on
        0,     # 8: solo_band
        0,     # 9: sc_listen
        0,     # 10: sc1_enable
        100.0, # 11: sc1_mix
        0.0,   # 12: sc1_gain
        0,     # 13: sc2_enable
        100.0, # 14: sc2_mix
        0.0,   # 15: sc2_gain
    ]
    for b_idx in range(8):
        default_state_list.extend([
            default_on_init[b_idx],
            default_types_init[b_idx],
            default_freqs_init[b_idx],
            0.0,   # gain
            0.71,  # q
            0,     # dyn_on
            0.0,   # dyn_range
            -22.0, # thresh
            5.0,   # attack
            110.0, # release
            0,     # source
        ])

    boxes.append(make_box(
        "obj-state-pattr", "newobj", "pattr eq_state @thru 2",
        varname="eq_state",
        patching_rect=[720.0, 145.0, 135.0, 22.0],
        numinlets=1, numoutlets=3, outlettype=["", "", ""],
        parameter_enable=1,
        saved_object_attributes={
            "annotation_name": "",
            "parameter_enable": 1,
        },
        saved_attribute_attributes={
            "valueof": {
                "parameter_initial": default_state_list,
                "parameter_initial_enable": 1,
                "parameter_invisible": 1,
                "parameter_linknames": 1,
                "parameter_longname": "eq_state",
                "parameter_modmode": 0,
                "parameter_shortname": "eq_state",
                "parameter_type": 3,
                "parameter_order": 0,
            }
        }
    ))
    reg_param("obj-state-pattr", "eq_state", "eq_state")
    boxes.append(make_box(
        "obj-prep-recall", "newobj", "prepend recall_state",
        patching_rect=[720.0, 175.0, 125.0, 22.0],
        numinlets=1, numoutlets=1, outlettype=[""]
    ))
    lines.append(make_line("obj-lom", 5, "obj-state-pattr", 0))
    lines.append(make_line("obj-state-pattr", 0, "obj-prep-recall", 0))
    lines.append(make_line("obj-prep-recall", 0, "obj-lom", 0))

    boxes.append(make_box("obj-thisdevice", "newobj", "live.thisdevice", patching_rect=[520.0, 95.0, 95.0, 22.0], numinlets=1, numoutlets=2, outlettype=["bang", "int"]))
    boxes.append(make_box("obj-defer-init", "newobj", "deferlow", patching_rect=[520.0, 125.0, 60.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    boxes.append(make_box("obj-init-msg", "message", "init_device", patching_rect=[520.0, 150.0, 75.0, 22.0], numinlets=2, numoutlets=1, outlettype=[""]))
    boxes.append(make_box("obj-rtabuf-msg", "message", "set_rta_buf ---rta_fft", patching_rect=[370.0, 110.0, 135.0, 22.0], numinlets=2, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-thisdevice", 0, "obj-defer-init", 0))
    lines.append(make_line("obj-defer-init", 0, "obj-init-msg", 0))
    lines.append(make_line("obj-defer-init", 0, "obj-rtabuf-msg", 0))
    lines.append(make_line("obj-init-msg", 0, "obj-lom", 0))
    lines.append(make_line("obj-rtabuf-msg", 0, "obj-graph", 0))

    boxes.append(make_box("obj-defer-width", "newobj", "deferlow", patching_rect=[630.0, 65.0, 60.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-lom", 2, "obj-defer-width", 0))
    lines.append(make_line("obj-defer-width", 0, "obj-thisdevice", 0))

    # Native `live.colors` Bridge -> Dynamically updates `deq_eight_ui_dev.js` when Ableton Theme changes!
    boxes.append(make_box(
        "obj-live-colors", "newobj", "live.colors",
        varname="live_colors_obj",
        patching_rect=[360.0, 140.0, 75.0, 22.0],
        numinlets=1, numoutlets=1, outlettype=[""]
    ))
    boxes.append(make_box("obj-lc-route", "newobj", "route bang", patching_rect=[360.0, 168.0, 75.0, 22.0], numinlets=1, numoutlets=2, outlettype=["", ""]))
    boxes.append(make_box("obj-lc-qmsg", "message", "query_theme_colors", patching_rect=[360.0, 196.0, 118.0, 22.0], numinlets=2, numoutlets=1, outlettype=[""]))
    boxes.append(make_box("obj-lc-prep", "newobj", "prepend theme_color_reply", patching_rect=[485.0, 196.0, 150.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-live-colors", 0, "obj-lc-route", 0))
    lines.append(make_line("obj-lc-route", 0, "obj-lc-qmsg", 0))
    lines.append(make_line("obj-lc-qmsg", 0, "obj-lom", 0))
    lines.append(make_line("obj-lc-route", 1, "obj-lc-prep", 0))
    lines.append(make_line("obj-lc-prep", 0, "obj-lom", 0))

    # Real-Time 33ms (~30fps) Gain Reduction + FFT Buffer Poll Tick
    boxes.append(make_box("obj-qmetro", "newobj", "qmetro 33 @active 1", patching_rect=[30.0, 300.0, 115.0, 22.0], numinlets=2, numoutlets=1, outlettype=["bang"]))
    boxes.append(make_box(
        "obj-pack-gr", "newobj", "pack 0. 0. 0. 0. 0. 0. 0. 0.",
        patching_rect=[30.0, 362.0, 220.0, 20.0],
        numinlets=8, numoutlets=1, outlettype=[""]
    ))
    boxes.append(make_box("obj-prep-gr", "newobj", "prepend set_gr", patching_rect=[265.0, 362.0, 95.0, 20.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-pack-gr", 0, "obj-prep-gr", 0))
    lines.append(make_line("obj-prep-gr", 0, "obj-graph", 0))

    for b in range(8, 0, -1):
        snap_id = f"obj-snap-{b}"
        sx = 30.0 + (b - 1) * 75.0
        boxes.append(make_box(snap_id, "newobj", "snapshot~", patching_rect=[sx, 335.0, 65.0, 20.0], numinlets=2, numoutlets=1, outlettype=["float"]))
        lines.append(make_line("obj-gen-eq", b + 1, snap_id, 0))
        lines.append(make_line("obj-qmetro", 0, snap_id, 0))
        lines.append(make_line(snap_id, 0, "obj-pack-gr", b - 1))

    # =========================================================================
    # 3. FAR-LEFT VERTICAL SIDECHAIN BAR (x = 0..22, Matching Glue Compressor!)
    # =========================================================================
    # Expand/Collapse Triangle Button (`transparent_bg=True` so no pink/black square border ever appears!)
    boxes.append(make_live_text(
        "obj-sc-expand-btn", "sc_expand_btn", "SC Drawer",
        "", "", 1, 0,
        patching_rect=[710.0, 15.0, 15.0, 15.0],
        presentation_rect=[3.0, 4.0, 15.0, 15.0],
        invisible=2, initial_enable=0,
        transparent_bg=True,
        off_fg_token="live_control_fg", on_fg_token="live_control_fg",
        pictures=["tri_closed.svg", "tri_open.svg"],
        usepicture=1, remapsvgcolors=1,
        longname="Sidechain Drawer"
    ))
    boxes.append(make_panel(
        "obj-sc-expand-ring", "sc_expand_ring",
        patching_rect=[690.0, 15.0, 15.0, 15.0],
        presentation_rect=[3.0, 4.0, 15.0, 15.0],
        bg_token="live_control_bg",
        border=1, border_token="live_control_fg",
        rounded=100
    ))
    boxes.append(make_box("obj-msg-sc-exp", "newobj", "prepend toggle_sc_panel", patching_rect=[710.0, 36.0, 130.0, 20.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-sc-expand-btn", 0, "obj-msg-sc-exp", 0))
    lines.append(make_line("obj-msg-sc-exp", 0, "obj-lom", 0))

    # Sidechain Listen Headphones Button (`transparent_bg=True` so only the circular panel is visible!)
    boxes.append(make_live_text(
        "obj-sc-listen-btn", "sc_listen_btn", "SC Listen",
        "", "", 1, 0,
        patching_rect=[710.0, 62.0, 14.0, 14.0],
        presentation_rect=[3.5, 23.0, 14.0, 14.0],
        invisible=2, initial_enable=0,
        transparent_bg=True,
        off_fg_token="live_control_fg_off", on_fg_token="live_control_fg_on",
        pictures=["headphones.svg", "headphones.svg"],
        usepicture=1, remapsvgcolors=1, usesvgviewbox=1,
        longname="Sidechain Listen"
    ))
    boxes.append(make_panel(
        "obj-sc-listen-bg-off", "sc_listen_bg_off",
        patching_rect=[690.0, 62.0, 14.0, 14.0],
        presentation_rect=[3.5, 23.0, 14.0, 14.0],
        bg_token="live_control_bg",
        border=0, rounded=100
    ))
    boxes.append(make_panel(
        "obj-sc-listen-bg-on", "sc_listen_bg_on",
        patching_rect=[690.0, 80.0, 14.0, 14.0],
        presentation_rect=[-500.0, 23.0, 14.0, 14.0],
        bg_token="live_lcd_control_fg_alt",
        border=0, rounded=100
    ))
    boxes.append(make_box("obj-msg-sc-lst", "newobj", "prepend ui_sc_listen", patching_rect=[710.0, 82.0, 115.0, 20.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-sc-listen-btn", 0, "obj-msg-sc-lst", 0))
    lines.append(make_line("obj-msg-sc-lst", 0, "obj-lom", 0))


    # Circular Sidechain Status Dot at bottom of spine (6.5x6.5 matching Glue Compressor!)
    boxes.append(make_panel(
        "obj-sc-dot-off", "sc_dot_off",
        patching_rect=[690.0, 140.0, 6.5, 6.5],
        presentation_rect=[7.5, 151.0, 6.5, 6.5],
        bg_token="live_led_bg",
        border=0, rounded=100
    ))
    boxes.append(make_panel(
        "obj-sc-dot-on", "sc_dot_on",
        patching_rect=[702.0, 140.0, 6.5, 6.5],
        presentation_rect=[-500.0, 151.0, 6.5, 6.5],
        bg_token="live_lcd_control_fg_alt",
        border=0, rounded=100
    ))
    # 1px vertical spine divider (`live.line` instead of 4px-clamped `panel`!)
    boxes.append(make_live_line(
        "obj-sc-spine-div", "sc_spine_div",
        patching_rect=[690.0, 155.0, 5.0, 100.0],
        presentation_rect=[21.0, 3.0, 1.0, 163.0],
        color_token="live_control_bg",
        thickness=1.0
    ))

    # =========================================================================
    # 4. BASE CANVAS LEFT STRIP (x = 22..67, width = 45px): Freq, Gain, Q Dials
    #    Shared single-band inspector controls (`invisible=2` so Live excludes them
    #    from preset recall and they never overwrite `eq_state`, while `initial_enable=1`
    #    keeps native double-click-to-reset working!)
    #    Dedicated Bold `live.comment` titles (`lbl_freq`, `lbl_gain`, `lbl_q`) sit above
    #    `showname=0` Regular/Medium value dials so Control Names are Bold and Values are Regular.
    # =========================================================================
    boxes.append(make_comment(
        "obj-lbl-freq", "lbl_freq", "Freq",
        patching_rect=[760.0, 4.0, 45.0, 14.0],
        presentation_rect=[22.0, 1.0, 45.0, 14.0],
        justification=1
    ))
    boxes.append(make_live_dial(
        "obj-freq-dial", "band_freq", "Freq",
        20.0, 20000.0, 1000.0, 3,
        patching_rect=[760.0, 20.0, 45.0, 38.0],
        presentation_rect=[22.0, 13.0, 45.0, 38.0],
        exponent=3.6,
        invisible=2, initial_enable=1,
        longname="Band Frequency"
    ))
    boxes.append(make_box("obj-msg-freq", "newobj", "prepend ui_freq", patching_rect=[820.0, 25.0, 95.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-freq-dial", 0, "obj-msg-freq", 0))
    lines.append(make_line("obj-msg-freq", 0, "obj-lom", 0))

    boxes.append(make_comment(
        "obj-lbl-gain", "lbl_gain", "Gain",
        patching_rect=[760.0, 64.0, 45.0, 14.0],
        presentation_rect=[22.0, 56.0, 45.0, 14.0],
        justification=1
    ))
    boxes.append(make_live_dial(
        "obj-gain-dial", "band_gain", "Gain",
        -15.0, 15.0, 0.0, 4,
        patching_rect=[760.0, 80.0, 45.0, 38.0],
        presentation_rect=[22.0, 68.0, 45.0, 38.0],
        custom_units="%.2f dB",
        triangle=1,
        invisible=2, initial_enable=1,
        longname="Band Gain"
    ))
    boxes.append(make_box("obj-msg-gain", "newobj", "prepend ui_gain", patching_rect=[820.0, 85.0, 95.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-gain-dial", 0, "obj-msg-gain", 0))
    lines.append(make_line("obj-msg-gain", 0, "obj-lom", 0))

    boxes.append(make_comment(
        "obj-lbl-q", "lbl_q", "Q",
        patching_rect=[760.0, 124.0, 45.0, 14.0],
        presentation_rect=[22.0, 111.0, 45.0, 14.0],
        justification=1
    ))
    boxes.append(make_live_dial(
        "obj-q-dial", "band_q", "Q",
        0.1, 18.0, 0.71, 1,
        patching_rect=[760.0, 140.0, 45.0, 38.0],
        presentation_rect=[22.0, 123.0, 45.0, 38.0],
        exponent=2.6,
        invisible=2, initial_enable=1,
        longname="Band Q"
    ))
    boxes.append(make_box("obj-msg-q", "newobj", "prepend ui_q", patching_rect=[820.0, 145.0, 90.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-q-dial", 0, "obj-msg-q", 0))
    lines.append(make_line("obj-msg-q", 0, "obj-lom", 0))

    boxes.append(make_live_line(
        "obj-div-left-graph", "div_left_graph",
        patching_rect=[750.0, 20.0, 5.0, 169.0],
        presentation_rect=[67.0, 0.0, 2.0, 169.0],
        color_token="live_lcd_frame",
        thickness=2.0
    ))

    # =========================================================================
    # 5. BASE CANVAS CENTER (x = 69..439, width = 370px):
    #    - Native `live.comment` Scale Labels (`ignoreclick=1`, Bold)
    #    - `obj-graph` (`deq_eight_ui_dev.js`, 370x132, renders 4096-pt FFT + Grid + Curves + Nodes)
    # =========================================================================
    freq_lbls = [
        ("lbl_f_100", "100", 69.0 + 91.0),
        ("lbl_f_1k",  "1k",  69.0 + 205.0),
        ("lbl_f_10k", "10k", 69.0 + 318.0),
    ]
    for vname, txt, lx in freq_lbls:
        boxes.append(make_comment(
            f"obj-{vname}", vname, txt,
            patching_rect=[720.0, 345.0, 26.0, 13.0],
            presentation_rect=[lx, 118.0, 26.0, 13.0],
            color_token="live_display_scale_text",
            fontsize=8.5, justification=1, fontface=1, ignoreclick=1
        ))

    db_lbls = [
        ("lbl_db_12",  "12",  69.0 + 2.0,  7.0),
        ("lbl_db_6",   "6",   69.0 + 5.0,  33.0),
        ("lbl_db_0",   "0",   69.0 + 8.0,  60.0),
        ("lbl_db_m6",  "-6",  69.0 + 3.0,  86.0),
        ("lbl_db_m12", "-12", 69.0 + 1.0,  113.0),
    ]
    for vname, txt, lx, ly in db_lbls:
        boxes.append(make_comment(
            f"obj-{vname}", vname, txt,
            patching_rect=[760.0, 345.0, 22.0, 12.0],
            presentation_rect=[lx, ly, 22.0, 12.0],
            color_token="live_display_scale_text",
            fontsize=8.5, justification=0, fontface=1, ignoreclick=1
        ))

    # Interactive EQ Curve + Node + 4096-Point FFT Canvas (370x132)
    boxes.append(make_box(
        "obj-graph", "jsui",
        varname="eq_graph",
        filename="deq_eight_ui_dev.js",
        patching_rect=[720.0, 220.0, 370.0, 132.0],
        presentation_rect=[69.0, 0.0, 370.0, 132.0],
        numinlets=1, numoutlets=1, outlettype=[""],
        border=0
    ))
    lines.append(make_line("obj-graph", 0, "obj-lom", 0))
    lines.append(make_line("obj-lom", 0, "obj-graph", 0))

    # --- NATIVE BOTTOM 8-BAND SELECTOR STRIP (x = 69..439, y = 132..169, 370x37, Exact EQ Eight Dimensions!) ---
    default_types = [2, 3, 3, 5, 3, 3, 3, 6]
    default_on    = [1, 1, 1, 1, 0, 0, 0, 0]
    filter_names  = ["Low Cut 48", "Low Cut 12", "Low Shelf", "Bell", "Notch", "High Shelf", "High Cut 12", "High Cut 48"]
    filter_pics   = ["eq8_lc48.svg", "eq8_lc12.svg", "eq8_lshelf.svg", "eq8_bell.svg", "eq8_notch.svg", "eq8_hshelf.svg", "eq8_hc12.svg", "eq8_hc48.svg"]
    slot_w = 372.0 / 8.0

    band_bg_panels = []
    for c in range(8):
        cx0 = 69.0 + round(c * slot_w)
        cx1 = (69.0 + 370.0) if (c == 7) else (69.0 + round((c + 1) * slot_w - 2.0))
        cw = cx1 - cx0 # 45px
        ddx = cx0 + 2.0
        ddw = cw - 4.0 # 41px
        bx_patch = 520.0 + c * 115.0

        # 1. 100% Native `live.menu` (41x16) Filter Curve Dropdown (displays bold SVG curve icon + native Live dropdown!)
        boxes.append(make_live_menu(
            f"obj-btype-menu-{c}", f"band_type_menu_{c}", f"B{c+1} Type",
            filter_names, default_types[c],
            patching_rect=[bx_patch, 468.0, ddw, 16.0],
            presentation_rect=[ddx, 134.5, ddw, 16.0],
            pictures=filter_pics,
            invisible=2, initial_enable=0,
            longname=f"Band {c+1} Filter Type"
        ))
        boxes.append(make_box(f"obj-msg-btype-{c}", "newobj", f"prepend ui_band_type {c}", patching_rect=[bx_patch, 442.0, 115.0, 20.0], numinlets=1, numoutlets=1, outlettype=[""]))
        lines.append(make_line(f"obj-btype-menu-{c}", 0, f"obj-msg-btype-{c}", 0))
        lines.append(make_line(f"obj-msg-btype-{c}", 0, "obj-lom", 0))

        # 2. Native 13x13 Band Activator Square (`live.text` toggle -> 12x12 visual square with 10x10 Cyan fill!)
        boxes.append(make_live_text(
            f"obj-bon-btn-{c}", f"band_on_btn_{c}", f"B{c+1} On",
            "", "", 1, default_on[c],
            patching_rect=[bx_patch, 495.0, 13.0, 13.0],
            presentation_rect=[ddx, 152.5, 13.0, 13.0],
            on_token="live_lcd_control_fg_alt",
            invisible=2, initial_enable=0,
            longname=f"Band {c+1} On",
            saved_attribute_attributes={
                "bgcolor": tc("live_control_bg"),
                "activebgcolor": tc("live_control_bg"),
                "bgoncolor": tc("live_lcd_control_fg_alt"),
                "activebgoncolor": tc("live_lcd_control_fg_alt"),
                "bordercolor": tc("live_contrast_frame"),
            }
        ))
        boxes.append(make_box(f"obj-msg-bon-{c}", "newobj", f"prepend ui_band_on {c}", patching_rect=[bx_patch, 515.0, 105.0, 20.0], numinlets=1, numoutlets=1, outlettype=[""]))
        lines.append(make_line(f"obj-bon-btn-{c}", 0, f"obj-msg-bon-{c}", 0))
        lines.append(make_line(f"obj-msg-bon-{c}", 0, "obj-lom", 0))

        # 3. Native Band Number `1..8` Selector Button (`live.text` momentary button, Bold, 100% transparent bg)
        boxes.append(make_box(
            f"obj-bsel-btn-{c}", "live.text",
            text=str(c + 1),
            varname=f"band_sel_btn_{c}",
            patching_rect=[bx_patch, 540.0, 15.0, 14.0],
            presentation_rect=[cx0 + 15.0, 151.5, 15.0, 14.0],
            numinlets=1, numoutlets=2, outlettype=["", ""],
            parameter_enable=0,
            mode=0, texton=str(c + 1),
            fontname="Ableton Sans Small Bold",
            fontsize=10.5,
            fontface=1,
            border=0,
            bgcolor=TRANSPARENT, activebgcolor=TRANSPARENT,
            bgoncolor=TRANSPARENT, activebgoncolor=TRANSPARENT,
            bordercolor=TRANSPARENT, focusbordercolor=TRANSPARENT,
            saved_attribute_attributes={
                "textcolor": tc("live_control_fg"),
                "activefgcolor": tc("live_control_fg"),
            }
        ))
        boxes.append(make_box(f"obj-msg-bsel-{c}", "message", f"ui_band_sel {c}", patching_rect=[bx_patch, 560.0, 85.0, 20.0], numinlets=2, numoutlets=1, outlettype=[""]))
        lines.append(make_line(f"obj-bsel-btn-{c}", 0, f"obj-msg-bsel-{c}", 0))
        lines.append(make_line(f"obj-msg-bsel-{c}", 0, "obj-lom", 0))

        # 4. Native Per-Band Dynamics Circle Toggle (`13x13` with `transparent_bg=True` so no square ever appears!)
        dcx = ddx + ddw - 13.0
        boxes.append(make_live_text(
            f"obj-bdyn-btn-{c}", f"band_dyn_btn_{c}", f"B{c+1} Dyn",
            "", "", 1, 0,
            patching_rect=[bx_patch, 585.0, 13.0, 13.0],
            presentation_rect=[dcx, 152.5, 13.0, 13.0],
            invisible=2, initial_enable=0,
            transparent_bg=True,
            off_fg_token="live_lcd_frame", on_fg_token="live_lcd_control_fg_alt",
            pictures=["dyn_ring.svg", "dyn_ring.svg"],
            usepicture=1, remapsvgcolors=1,
            longname=f"Band {c+1} Dynamics"
        ))
        boxes.append(make_box(f"obj-msg-bdyn-{c}", "message", f"click_band_dyn_dot {c}", patching_rect=[bx_patch, 605.0, 110.0, 20.0], numinlets=2, numoutlets=1, outlettype=[""]))
        lines.append(make_line(f"obj-bdyn-btn-{c}", 0, f"obj-msg-bdyn-{c}", 0))
        lines.append(make_line(f"obj-msg-bdyn-{c}", 0, "obj-lom", 0))

        # Unselected card background panel (placed after controls so controls sit on top!)
        card_x_init = -500.0 if (c == 2) else cx0
        band_bg_panels.append(make_panel(
            f"obj-bcard-bg-{c}", f"band_card_bg_{c}",
            patching_rect=[bx_patch, 650.0, cw, 33.0],
            presentation_rect=[card_x_init, 134.0, cw, 33.0],
            bg_token="live_surface_bg"
        ))

    # Full-lit center fill inside the selected band's circular dyn toggle when the right Dynamic panel is open
    boxes.append(make_panel(
        "obj-dyn-ring-fill", "dyn_ring_fill",
        patching_rect=[500.0, 585.0, 9.0, 9.0],
        presentation_rect=[-500.0, 154.5, 9.0, 9.0],
        bg_token="live_lcd_control_fg_alt",
        border=0, rounded=100, ignoreclick=1
    ))
    boxes.extend(band_bg_panels)
    boxes.append(make_panel(
        "obj-band-strip-bg", "band_strip_bg",
        patching_rect=[520.0, 690.0, 370.0, 37.0],
        presentation_rect=[69.0, 132.0, 370.0, 37.0],
        bg_token="live_lcd_frame"
    ))

    # 2px vertical frame divider between Graph and Right Strip (`live.line`)
    boxes.append(make_live_line(
        "obj-div-graph-right", "div_graph_right",
        patching_rect=[1095.0, 220.0, 5.0, 169.0],
        presentation_rect=[439.0, 0.0, 2.0, 169.0],
        color_token="live_lcd_frame",
        thickness=2.0
    ))

    # =========================================================================
    # 6. BASE CANVAS RIGHT STRIP (x = 441..495, width = 54px):
    #    100% Native Top Icons (`solo_btn` [🎧] and `rta_btn` [ılı.]), Adapt. Q, Scale, Gain
    # =========================================================================
    boxes.append(make_live_text(
        "obj-solo-btn", "solo_btn", "Solo",
        "", "", 1, 0,
        patching_rect=[1060.0, 20.0, 22.0, 15.0],
        presentation_rect=[444.0, 4.0, 22.0, 15.0],
        on_token="live_lcd_control_fg_alt",
        invisible=2, initial_enable=0,
        pictures=["headphones.svg", "headphones.svg"],
        usepicture=1, remapsvgcolors=1,
        longname="Band Solo"
    ))
    boxes.append(make_box("obj-msg-solo", "newobj", "prepend ui_solo", patching_rect=[1140.0, 20.0, 95.0, 20.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-solo-btn", 0, "obj-msg-solo", 0))
    lines.append(make_line("obj-msg-solo", 0, "obj-lom", 0))

    boxes.append(make_live_text(
        "obj-rta-btn", "rta_btn", "RTA",
        "", "", 1, 1,
        patching_rect=[1090.0, 20.0, 22.0, 15.0],
        presentation_rect=[469.0, 4.0, 22.0, 15.0],
        on_token="live_display_handle_one",
        invisible=2, initial_enable=0,
        pictures=["rta_bars.svg", "rta_bars.svg"],
        usepicture=1, remapsvgcolors=1,
        longname="Spectrum Analyzer"
    ))
    boxes.append(make_box("obj-msg-rta", "newobj", "prepend ui_rta_on", patching_rect=[1140.0, 45.0, 105.0, 20.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-rta-btn", 0, "obj-msg-rta", 0))
    lines.append(make_line("obj-msg-rta", 0, "obj-lom", 0))

    # Adapt. Q Label + Toggle
    boxes.append(make_comment(
        "obj-lbl-adaptq", "lbl_adaptq", "Adapt. Q",
        patching_rect=[1060.0, 90.0, 52.0, 14.0],
        presentation_rect=[441.5, 71.0, 52.0, 14.0]
    ))
    boxes.append(make_live_text(
        "obj-adaptq", "adapt_q_btn", "Adapt. Q",
        "Off", "On", 1, 1,
        patching_rect=[1060.0, 106.0, 47.0, 16.0],
        presentation_rect=[444.0, 85.0, 47.0, 16.0],
        longname="Adaptive Q"
    ))
    reg_param("obj-adaptq", "Adaptive Q", "Adapt. Q")
    boxes.append(make_box("obj-msg-adaptq", "newobj", "prepend ui_adapt_q", patching_rect=[1140.0, 106.0, 115.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-adaptq", 0, "obj-msg-adaptq", 0))
    lines.append(make_line("obj-msg-adaptq", 0, "obj-lom", 0))

    # Scale Label + Numbox (`unitstyle=5` native M4L `%` unitstyle -> displays `100 %` cleanly with full 0..200% float range!)
    boxes.append(make_comment(
        "obj-lbl-scale", "lbl_scale", "Scale",
        patching_rect=[1060.0, 135.0, 52.0, 14.0],
        presentation_rect=[441.5, 103.0, 52.0, 14.0]
    ))
    boxes.append(make_live_numbox(
        "obj-dynscale", "dyn_scale", "Scale",
        0.0, 200.0, 100.0, 5,
        patching_rect=[1060.0, 152.0, 47.0, 16.0],
        presentation_rect=[444.0, 117.0, 47.0, 16.0],
        param_type=0,
        appearance=2,
        longname="Scale"
    ))
    reg_param("obj-dynscale", "Scale", "Scale")
    boxes.append(make_box("obj-msg-scale", "newobj", "prepend ui_dyn_scale", patching_rect=[1140.0, 152.0, 125.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-dynscale", 0, "obj-msg-scale", 0))
    lines.append(make_line("obj-msg-scale", 0, "obj-lom", 0))

    # Output Gain Label + Numbox (`custom_units="%.2f dB"`, `appearance=2` so height matches Scale 1:1!)
    boxes.append(make_comment(
        "obj-lbl-outgain", "lbl_outgain", "Gain",
        patching_rect=[1060.0, 180.0, 52.0, 14.0],
        presentation_rect=[441.5, 135.0, 52.0, 14.0]
    ))
    boxes.append(make_live_numbox(
        "obj-outgain", "out_gain", "Gain",
        -24.0, 24.0, 0.0, 4,
        patching_rect=[1060.0, 196.0, 47.0, 16.0],
        presentation_rect=[444.0, 149.0, 47.0, 16.0],
        custom_units="%.2f dB",
        appearance=2,
        longname="Output Gain"
    ))
    reg_param("obj-outgain", "Output Gain", "Gain")
    boxes.append(make_box("obj-msg-outgain", "newobj", "prepend ui_out_gain", patching_rect=[1140.0, 196.0, 120.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-outgain", 0, "obj-msg-outgain", 0))
    lines.append(make_line("obj-msg-outgain", 0, "obj-lom", 0))

    # =========================================================================
    # 7. LEFT EXPANDABLE 2-COLUMN SIDECHAIN PANEL (x = 22..176, +154px, Matching Glue Compressor!)
    # =========================================================================
    boxes.append(make_live_line(
        "obj-sc-col-div", "sc_col_div",
        patching_rect=[1325.0, 5.0, 5.0, 160.0],
        presentation_rect=[-500.0, 3.0, 1.0, 163.0],
        color_token="live_control_bg",
        thickness=1.0
    ))
    boxes.append(make_live_line(
        "obj-sc-right-div", "sc_right_div",
        patching_rect=[1335.0, 5.0, 5.0, 169.0],
        presentation_rect=[-500.0, 0.0, 2.0, 169.0],
        color_token="live_lcd_frame",
        thickness=2.0
    ))

    # --- Column 1: Sidechain A ---
    boxes.append(make_live_text(
        "obj-sc-a-btn", "sc_a_btn", "Ext. A",
        "Ext. A", "Ext. A", 1, 0,
        patching_rect=[1320.0, 20.0, 68.0, 15.0],
        presentation_rect=[-500.0, 4.0, 68.0, 15.0],
        on_token="live_lcd_control_fg_alt",
        longname="Sidechain A On"
    ))
    reg_param("obj-sc-a-btn", "Sidechain A On", "Ext. A")
    boxes.append(make_box("obj-msg-sca", "newobj", "prepend ui_sc_a_en", patching_rect=[1320.0, 42.0, 110.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-sc-a-btn", 0, "obj-msg-sca", 0))
    lines.append(make_line("obj-msg-sca", 0, "obj-lom", 0))

    boxes.append(make_comment("obj-lbl-srca", "lbl_src_a", "Source", patching_rect=[1320.0, 68.0, 68.0, 14.0], presentation_rect=[-500.0, 23.0, 68.0, 14.0]))
    boxes.append(make_umenu(
        "obj-sc1-track", "sc1_track_menu",
        ["No Input"],
        patching_rect=[1320.0, 86.0, 68.0, 16.0],
        presentation_rect=[-500.0, 37.0, 68.0, 16.0]
    ))
    boxes.append(make_umenu(
        "obj-sc1-chan", "sc1_chan_menu",
        ["Pre FX", "Post FX", "Post Mixer"],
        patching_rect=[1320.0, 108.0, 68.0, 16.0],
        presentation_rect=[-500.0, 56.0, 68.0, 16.0]
    ))
    boxes.append(make_comment("obj-lbl-mixa", "lbl_mix_a", "Mix", patching_rect=[1320.0, 130.0, 68.0, 14.0], presentation_rect=[-500.0, 82.0, 68.0, 14.0]))
    boxes.append(make_live_numbox(
        "obj-sc1-mix", "sc1_mix", "SC A Mix",
        0.0, 100.0, 100.0, 5,
        patching_rect=[1320.0, 146.0, 68.0, 16.0],
        presentation_rect=[-500.0, 96.0, 68.0, 16.0],
        param_type=0,
        appearance=2,
        longname="Sidechain A Mix"
    ))
    reg_param("obj-sc1-mix", "Sidechain A Mix", "SC A Mix")
    boxes.append(make_box("obj-msg-sc1m", "newobj", "prepend ui_sc1_mix", patching_rect=[1410.0, 146.0, 115.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-sc1-mix", 0, "obj-msg-sc1m", 0))
    lines.append(make_line("obj-msg-sc1m", 0, "obj-lom", 0))

    boxes.append(make_comment("obj-lbl-sc1g", "lbl_sc1_gain", "SC Gain", patching_rect=[1320.0, 168.0, 68.0, 14.0], presentation_rect=[-500.0, 122.0, 68.0, 14.0]))
    boxes.append(make_live_numbox(
        "obj-sc1-gain", "sc1_gain", "SC A Gain",
        -24.0, 24.0, 0.0, 4,
        patching_rect=[1320.0, 184.0, 68.0, 16.0],
        presentation_rect=[-500.0, 136.0, 68.0, 16.0],
        custom_units="%.2f dB",
        appearance=2,
        longname="Sidechain A Gain"
    ))
    reg_param("obj-sc1-gain", "Sidechain A Gain", "SC A Gain")
    boxes.append(make_box("obj-sc1-dbtoa", "newobj", "dbtoa", patching_rect=[1320.0, 206.0, 45.0, 22.0], numinlets=1, numoutlets=1, outlettype=["float"]))
    boxes.append(make_box("obj-msg-sc1g", "newobj", "prepend ui_sc1_gain", patching_rect=[1410.0, 184.0, 120.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-sc1-gain", 0, "obj-sc1-dbtoa", 0))
    lines.append(make_line("obj-sc1-dbtoa", 0, "obj-sc1-mult", 1))
    lines.append(make_line("obj-sc1-gain", 0, "obj-msg-sc1g", 0))
    lines.append(make_line("obj-msg-sc1g", 0, "obj-lom", 0))

    boxes.append(make_box("obj-msg-sc1t", "newobj", "prepend set_sc1_track", patching_rect=[1410.0, 86.0, 130.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    boxes.append(make_box("obj-msg-sc1c", "newobj", "prepend set_sc1_chan", patching_rect=[1410.0, 108.0, 130.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-sc1-track", 0, "obj-msg-sc1t", 0))
    lines.append(make_line("obj-msg-sc1t", 0, "obj-lom", 0))
    lines.append(make_line("obj-sc1-chan", 0, "obj-msg-sc1c", 0))
    lines.append(make_line("obj-msg-sc1c", 0, "obj-lom", 0))

    # --- Column 2: Sidechain B ---
    boxes.append(make_live_text(
        "obj-sc-b-btn", "sc_b_btn", "Ext. B",
        "Ext. B", "Ext. B", 1, 0,
        patching_rect=[1550.0, 20.0, 68.0, 15.0],
        presentation_rect=[-500.0, 4.0, 68.0, 15.0],
        on_token="live_lcd_control_fg_alt",
        longname="Sidechain B On"
    ))
    reg_param("obj-sc-b-btn", "Sidechain B On", "Ext. B")
    boxes.append(make_box("obj-msg-scb", "newobj", "prepend ui_sc_b_en", patching_rect=[1550.0, 42.0, 110.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-sc-b-btn", 0, "obj-msg-scb", 0))
    lines.append(make_line("obj-msg-scb", 0, "obj-lom", 0))

    boxes.append(make_comment("obj-lbl-srcb", "lbl_src_b", "Source", patching_rect=[1550.0, 68.0, 68.0, 14.0], presentation_rect=[-500.0, 23.0, 68.0, 14.0]))
    boxes.append(make_umenu(
        "obj-sc2-track", "sc2_track_menu",
        ["No Input"],
        patching_rect=[1550.0, 86.0, 68.0, 16.0],
        presentation_rect=[-500.0, 37.0, 68.0, 16.0]
    ))
    boxes.append(make_umenu(
        "obj-sc2-chan", "sc2_chan_menu",
        ["Pre FX", "Post FX", "Post Mixer"],
        patching_rect=[1550.0, 108.0, 68.0, 16.0],
        presentation_rect=[-500.0, 56.0, 68.0, 16.0]
    ))
    boxes.append(make_comment("obj-lbl-mixb", "lbl_mix_b", "Mix", patching_rect=[1550.0, 130.0, 68.0, 14.0], presentation_rect=[-500.0, 82.0, 68.0, 14.0]))
    boxes.append(make_live_numbox(
        "obj-sc2-mix", "sc2_mix", "SC B Mix",
        0.0, 100.0, 100.0, 5,
        patching_rect=[1550.0, 146.0, 68.0, 16.0],
        presentation_rect=[-500.0, 96.0, 68.0, 16.0],
        param_type=0,
        appearance=2,
        longname="Sidechain B Mix"
    ))
    reg_param("obj-sc2-mix", "Sidechain B Mix", "SC B Mix")
    boxes.append(make_box("obj-msg-sc2m", "newobj", "prepend ui_sc2_mix", patching_rect=[1640.0, 146.0, 115.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-sc2-mix", 0, "obj-msg-sc2m", 0))
    lines.append(make_line("obj-msg-sc2m", 0, "obj-lom", 0))

    boxes.append(make_comment("obj-lbl-sc2g", "lbl_sc2_gain", "SC Gain", patching_rect=[1550.0, 168.0, 68.0, 14.0], presentation_rect=[-500.0, 122.0, 68.0, 14.0]))
    boxes.append(make_live_numbox(
        "obj-sc2-gain", "sc2_gain", "SC B Gain",
        -24.0, 24.0, 0.0, 4,
        patching_rect=[1550.0, 184.0, 68.0, 16.0],
        presentation_rect=[-500.0, 136.0, 68.0, 16.0],
        custom_units="%.2f dB",
        appearance=2,
        longname="Sidechain B Gain"
    ))
    reg_param("obj-sc2-gain", "Sidechain B Gain", "SC B Gain")
    boxes.append(make_box("obj-sc2-dbtoa", "newobj", "dbtoa", patching_rect=[1550.0, 206.0, 45.0, 22.0], numinlets=1, numoutlets=1, outlettype=["float"]))
    boxes.append(make_box("obj-msg-sc2g", "newobj", "prepend ui_sc2_gain", patching_rect=[1640.0, 184.0, 120.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-sc2-gain", 0, "obj-sc2-dbtoa", 0))
    lines.append(make_line("obj-sc2-dbtoa", 0, "obj-sc2-mult", 1))
    lines.append(make_line("obj-sc2-gain", 0, "obj-msg-sc2g", 0))
    lines.append(make_line("obj-msg-sc2g", 0, "obj-lom", 0))

    boxes.append(make_box("obj-msg-sc2t", "newobj", "prepend set_sc2_track", patching_rect=[1640.0, 86.0, 130.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    boxes.append(make_box("obj-msg-sc2c", "newobj", "prepend set_sc2_chan", patching_rect=[1640.0, 108.0, 130.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-sc2-track", 0, "obj-msg-sc2t", 0))
    lines.append(make_line("obj-msg-sc2t", 0, "obj-lom", 0))
    lines.append(make_line("obj-sc2-chan", 0, "obj-msg-sc2c", 0))
    lines.append(make_line("obj-msg-sc2c", 0, "obj-lom", 0))

    # Dedicated live.routing Objects (SC A on Outlet 3, SC B on Outlet 4)
    boxes.append(make_box(
        "obj-routing-1", "newobj", "live.routing",
        patching_rect=[1320.0, 250.0, 140.0, 22.0],
        numinlets=1, numoutlets=5, outlettype=["", "", "", "", ""]
    ))
    boxes.append(make_box("obj-rt1-curtype", "newobj", "prepend rt1_cur_type", patching_rect=[1320.0, 280.0, 135.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    boxes.append(make_box("obj-rt1-curchan", "newobj", "prepend rt1_cur_chan", patching_rect=[1465.0, 280.0, 135.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    boxes.append(make_box("obj-rt1-types", "newobj", "prepend rt1_types", patching_rect=[1320.0, 310.0, 125.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    boxes.append(make_box("obj-rt1-chans", "newobj", "prepend rt1_chans", patching_rect=[1465.0, 310.0, 125.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-lom", 3, "obj-routing-1", 0))
    lines.append(make_line("obj-routing-1", 0, "obj-rt1-curtype", 0))
    lines.append(make_line("obj-routing-1", 1, "obj-rt1-curchan", 0))
    lines.append(make_line("obj-routing-1", 2, "obj-rt1-types", 0))
    lines.append(make_line("obj-routing-1", 3, "obj-rt1-chans", 0))
    lines.append(make_line("obj-rt1-curtype", 0, "obj-lom", 0))
    lines.append(make_line("obj-rt1-curchan", 0, "obj-lom", 0))
    lines.append(make_line("obj-rt1-types", 0, "obj-lom", 0))
    lines.append(make_line("obj-rt1-chans", 0, "obj-lom", 0))

    boxes.append(make_box(
        "obj-routing-2", "newobj", "live.routing",
        patching_rect=[1620.0, 250.0, 140.0, 22.0],
        numinlets=1, numoutlets=5, outlettype=["", "", "", "", ""]
    ))
    boxes.append(make_box("obj-rt2-curtype", "newobj", "prepend rt2_cur_type", patching_rect=[1620.0, 280.0, 135.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    boxes.append(make_box("obj-rt2-curchan", "newobj", "prepend rt2_cur_chan", patching_rect=[1765.0, 280.0, 135.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    boxes.append(make_box("obj-rt2-types", "newobj", "prepend rt2_types", patching_rect=[1620.0, 310.0, 125.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    boxes.append(make_box("obj-rt2-chans", "newobj", "prepend rt2_chans", patching_rect=[1765.0, 310.0, 125.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-lom", 4, "obj-routing-2", 0))
    lines.append(make_line("obj-routing-2", 0, "obj-rt2-curtype", 0))
    lines.append(make_line("obj-routing-2", 1, "obj-rt2-curchan", 0))
    lines.append(make_line("obj-routing-2", 2, "obj-rt2-types", 0))
    lines.append(make_line("obj-routing-2", 3, "obj-rt2-chans", 0))
    lines.append(make_line("obj-rt2-curtype", 0, "obj-lom", 0))
    lines.append(make_line("obj-rt2-curchan", 0, "obj-lom", 0))
    lines.append(make_line("obj-rt2-types", 0, "obj-lom", 0))
    lines.append(make_line("obj-rt2-chans", 0, "obj-lom", 0))

    # =========================================================================
    # 8. RIGHT EXPANDABLE PER-BAND DYNAMIC PANEL (x = 495..573, +78px)
    #    Vertical single-column layout with field labels directly above each box
    #    and no source or on/off label.
    # =========================================================================
    boxes.append(make_live_line(
        "obj-div-right-dyn", "div_right_dyn",
        patching_rect=[1800.0, 20.0, 5.0, 169.0],
        presentation_rect=[-500.0, 0.0, 2.0, 169.0],
        color_token="live_lcd_frame",
        thickness=2.0
    ))
    boxes.append(make_live_text(
        "obj-band-dyn-on", "band_dyn_on", "Dyn On",
        "Off", "On", 1, 0,
        patching_rect=[1820.0, 20.0, 68.0, 15.0],
        presentation_rect=[-500.0, 4.0, 68.0, 15.0],
        on_token="live_lcd_control_fg_alt",
        invisible=2, initial_enable=0,
        longname="Band Dynamics On"
    ))
    boxes.append(make_box("obj-msg-dynon", "newobj", "prepend ui_dyn_on", patching_rect=[1970.0, 20.0, 110.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-band-dyn-on", 0, "obj-msg-dynon", 0))
    lines.append(make_line("obj-msg-dynon", 0, "obj-lom", 0))

    boxes.append(make_live_tab(
        "obj-src-tab", "band_source", "Source",
        ["Int", "SC A", "SC B"], 0,
        patching_rect=[1820.0, 45.0, 68.0, 15.0],
        presentation_rect=[-500.0, 21.0, 68.0, 15.0],
        fontsize=9.5,
        invisible=2, initial_enable=0,
        longname="Band Sidechain Source"
    ))
    boxes.append(make_box("obj-msg-source", "newobj", "prepend ui_source", patching_rect=[1970.0, 45.0, 110.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-src-tab", 0, "obj-msg-source", 0))
    lines.append(make_line("obj-msg-source", 0, "obj-lom", 0))

    boxes.append(make_comment("obj-lbl-range", "lbl_range", "Dyn Range", patching_rect=[1820.0, 70.0, 68.0, 14.0], presentation_rect=[-500.0, 39.0, 68.0, 14.0]))
    boxes.append(make_live_numbox(
        "obj-dyndepth", "band_dyndepth", "Dyn Range",
        -15.0, 15.0, 0.0, 4,
        patching_rect=[1890.0, 70.0, 68.0, 16.0],
        presentation_rect=[-500.0, 53.0, 68.0, 16.0],
        custom_units="%.2f dB",
        appearance=2,
        invisible=2, initial_enable=1,
        longname="Dynamic Range"
    ))
    boxes.append(make_box("obj-msg-dyndepth", "newobj", "prepend ui_dyndepth", patching_rect=[1970.0, 70.0, 125.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-dyndepth", 0, "obj-msg-dyndepth", 0))
    lines.append(make_line("obj-msg-dyndepth", 0, "obj-lom", 0))

    boxes.append(make_comment("obj-lbl-thresh", "lbl_thresh", "Threshold", patching_rect=[1820.0, 95.0, 68.0, 14.0], presentation_rect=[-500.0, 71.0, 68.0, 14.0]))
    boxes.append(make_live_numbox(
        "obj-thresh", "band_thresh", "Threshold",
        -60.0, 0.0, -22.0, 4,
        patching_rect=[1890.0, 95.0, 68.0, 16.0],
        presentation_rect=[-500.0, 85.0, 68.0, 16.0],
        custom_units="%.2f dB",
        appearance=2,
        invisible=2, initial_enable=1,
        longname="Threshold"
    ))
    boxes.append(make_box("obj-msg-thresh", "newobj", "prepend ui_thresh", patching_rect=[1970.0, 95.0, 110.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-thresh", 0, "obj-msg-thresh", 0))
    lines.append(make_line("obj-msg-thresh", 0, "obj-lom", 0))

    boxes.append(make_comment("obj-lbl-attack", "lbl_attack", "Attack", patching_rect=[1820.0, 120.0, 68.0, 14.0], presentation_rect=[-500.0, 103.0, 68.0, 14.0]))
    boxes.append(make_live_numbox(
        "obj-attack", "band_attack", "Attack",
        0.1, 250.0, 5.0, 2,
        patching_rect=[1890.0, 120.0, 68.0, 16.0],
        presentation_rect=[-500.0, 117.0, 68.0, 16.0],
        exponent=2.2,
        appearance=2,
        invisible=2, initial_enable=1,
        longname="Attack"
    ))
    boxes.append(make_box("obj-msg-attack", "newobj", "prepend ui_attack", patching_rect=[1970.0, 120.0, 110.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-attack", 0, "obj-msg-attack", 0))
    lines.append(make_line("obj-msg-attack", 0, "obj-lom", 0))

    boxes.append(make_comment("obj-lbl-release", "lbl_release", "Release", patching_rect=[1820.0, 145.0, 68.0, 14.0], presentation_rect=[-500.0, 135.0, 68.0, 14.0]))
    boxes.append(make_live_numbox(
        "obj-release", "band_release", "Release",
        5.0, 1000.0, 110.0, 2,
        patching_rect=[1890.0, 145.0, 68.0, 16.0],
        presentation_rect=[-500.0, 149.0, 68.0, 16.0],
        exponent=2.2,
        appearance=2,
        invisible=2, initial_enable=1,
        longname="Release"
    ))
    boxes.append(make_box("obj-msg-release", "newobj", "prepend ui_release", patching_rect=[1970.0, 145.0, 115.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-release", 0, "obj-msg-release", 0))
    lines.append(make_line("obj-msg-release", 0, "obj-lom", 0))

    # =========================================================================
    # 9. BACKMOST Z-LAYER: FULL-DEVICE ABLETON SURFACE PANEL (`live_surface_bg`)
    #    Placed LAST in `boxes` so it sits behind all controls in Presentation Mode!
    # =========================================================================
    boxes.append(make_panel(
        "obj-bg-surface", "bg_surface",
        patching_rect=[30.0, 740.0, 775.0, 169.0],
        presentation_rect=[0.0, 0.0, 495.0, 169.0],
        bg_token="live_surface_bg"
    ))

    # =========================================================================
    # 10. ASSEMBLE PATCHER & WRITE dEQ Eight.amxd CONTAINER
    # =========================================================================
    dep_cache = [
        {"name": "deq_eight_lom_dev.js", "bootpath": out_dir_abs, "type": "TEXT", "implicit": 1},
        {"name": "deq_eight_ui_dev.js", "bootpath": out_dir_abs, "type": "TEXT", "implicit": 1},
    ]
    for svg_name in svg_files:
        dep_cache.append({"name": svg_name, "bootpath": out_dir_abs, "type": "svg", "implicit": 1})

    patcher = {
        "fileversion": 1,
        "appversion": {
            "major": 9,
            "minor": 0,
            "revision": 0,
            "architecture": "x64",
            "modernui": 1,
        },
        "classnamespace": "box",
        "rect": [30.0, 50.0, 1200.0, 800.0],
        "openrect": [0.0, 0.0, 495.0, 169.0],
        "openinpresentation": 1,
        "gridsize": [8.0, 8.0],
        "devicewidth": 495.0,
        "boxes": boxes,
        "lines": lines,
        "parameters": parameters,
        "dependency_cache": dep_cache,
        "latency": 0,
    }

    raw_json = json.dumps({"patcher": patcher}, indent=2).encode("utf-8")
    ampf_body = b"ampf" + struct.pack("<I", 4) + b"aaaa"
    ampf_body += b"meta" + struct.pack("<I", 4) + b"\x00\x00\x00\x00"
    ampf_body += b"ptch" + struct.pack("<I", len(raw_json)) + raw_json

    out_path = os.path.join(out_dir, "dEQ Eight dev.amxd")
    with open(out_path, "wb") as f:
        f.write(ampf_body)

    print(f"Successfully generated {out_path} ({len(ampf_body)} bytes)")
    print(f"Total boxes: {len(boxes)}, Total lines: {len(lines)}, Total parameters: {len(parameters)}")

    # =========================================================================
    # 11. BUILD SINGLE-FILE FROZEN .AMXD (mx@c / dlst Collective Container)
    # =========================================================================
    frozen_name = "dEQ Eight Alpha v0.02.amxd"
    frozen_bytes = build_frozen_amxd(
        root_name=frozen_name,
        raw_json=raw_json,
        out_dir=out_dir,
        dep_cache=dep_cache,
    )
    frozen_local_path = os.path.join(out_dir, frozen_name)
    with open(frozen_local_path, "wb") as f:
        f.write(frozen_bytes)
    print(f"Successfully generated frozen device: {frozen_local_path} ({len(frozen_bytes)} bytes)")

    repo_root = os.path.abspath(os.path.join(out_dir, "..", ".."))
    release_dir = os.path.join(repo_root, "release")
    os.makedirs(release_dir, exist_ok=True)
    frozen_release_path = os.path.join(release_dir, frozen_name)
    with open(frozen_release_path, "wb") as f:
        f.write(frozen_bytes)

    # Clean up stale v0.01 artifacts if present
    for stale_path in [
        os.path.join(out_dir, "dEQ Eight Alpha v0.01.amxd"),
        os.path.join(release_dir, "dEQ Eight Alpha v0.01.amxd"),
        os.path.join(release_dir, "dEQ_Eight_Alpha_v0.01.zip"),
    ]:
        if os.path.exists(stale_path):
            os.remove(stale_path)

    import zipfile
    zip_path = os.path.join(release_dir, "dEQ_Eight_Alpha_v0.02.zip")
    readme_txt = (
        "dEQ Eight — Alpha v0.02 (OpenAir / macchinette)\n"
        "===============================================\n\n"
        "Installation:\n"
        "1. `dEQ Eight Alpha v0.02.amxd` is a self-contained frozen Max for Live device.\n"
        "2. Drag and drop `dEQ Eight Alpha v0.02.amxd` directly onto any audio/instrument track\n"
        "   in Ableton Live 11 or 12, or place it in your User Library.\n\n"
        "Architecture:\n"
        "- 8-band 64-bit Cytomic Zero-Delay Feedback (ZDF) SVF equalizer (`gen~`)\n"
        "- Per-band upward/downward dynamic range (-15 dB to +15 dB)\n"
        "- Dual external stereo sidechain inputs (Ext. A & Ext. B via `live.routing`)\n"
        "- 4096-point C++ FFT spectrum analyzer with Catmull-Rom low-end interpolation\n"
        "- Native Live 11/12 theme color integration (`live.colors` + `remapsvgcolors`)\n"
    )
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"dEQ_Eight_Alpha_v0.02/{frozen_name}", frozen_bytes)
        zf.writestr("dEQ_Eight_Alpha_v0.02/README.txt", readme_txt.encode("utf-8"))
    print(f"Successfully packaged release archive: {zip_path}")


def make_dire_entry(ftype: str, fname: str, sz32: int, of32: int, flag: int, mdat: int = 0xE20F4145) -> bytes:
    """Packs a single `dire` entry inside the `dlst` directory footer of a frozen Max collective (`mx@c`)."""
    ftype_b = ftype.encode("ascii")
    type_chunk = b"type" + struct.pack(">I", 8 + len(ftype_b)) + ftype_b

    fname_b = fname.encode("utf-8") + b"\x00"
    pad_len = (4 - (len(fname_b) % 4)) % 4
    fname_padded = fname_b + (b"\x00" * pad_len)
    fnam_chunk = b"fnam" + struct.pack(">I", 8 + len(fname_padded)) + fname_padded

    sz32_chunk = b"sz32" + struct.pack(">II", 12, sz32)
    of32_chunk = b"of32" + struct.pack(">II", 12, of32)
    vers_chunk = b"vers" + struct.pack(">II", 12, 0)
    flag_chunk = b"flag" + struct.pack(">II", 12, flag)
    mdat_chunk = b"mdat" + struct.pack(">II", 12, mdat)

    body = type_chunk + fnam_chunk + sz32_chunk + of32_chunk + vers_chunk + flag_chunk + mdat_chunk
    return b"dire" + struct.pack(">I", 8 + len(body)) + body


def build_frozen_amxd(root_name: str, raw_json: bytes, out_dir: str, dep_cache: list) -> bytes:
    """
    Packs the top-level patcher JSON and all JS/SVG dependencies into a single-file
    frozen `.amxd` container (`meta = 7`, `mx@c` header + concatenated payloads + `dlst` directory).
    """
    payloads = []
    dire_entries = []
    cur_offset = 16  # Immediately follows the 16-byte `mx@c` header

    # 1. Root Patcher JSON (flag = 0x11: top-level frozen device patcher)
    payloads.append(raw_json)
    dire_entries.append(make_dire_entry("JSON", root_name, len(raw_json), cur_offset, flag=0x11))
    cur_offset += len(raw_json)

    # 2. Embedded Dependencies (JS = TEXT, SVG = svg)
    for dep in dep_cache:
        dep_name = dep["name"]
        dep_type = dep["type"]
        dep_path = os.path.join(out_dir, dep_name)
        with open(dep_path, "rb") as f:
            dep_bytes = f.read()
        payloads.append(dep_bytes)
        dire_entries.append(make_dire_entry(dep_type, dep_name, len(dep_bytes), cur_offset, flag=0x00))
        cur_offset += len(dep_bytes)

    dlst_offset = cur_offset
    dlst_body = b"".join(dire_entries)
    dlst_chunk = b"dlst" + struct.pack(">I", 8 + len(dlst_body)) + dlst_body

    mxc_header = b"mx@c" + struct.pack(">III", 16, 0, dlst_offset)
    ptch_payload = mxc_header + b"".join(payloads) + dlst_chunk

    ampf_body = b"ampf" + struct.pack("<I", 4) + b"aaaa"
    ampf_body += b"meta" + struct.pack("<I", 4) + b"\x00\x00\x00\x07"
    ampf_body += b"ptch" + struct.pack("<I", len(ptch_payload)) + ptch_payload
    return ampf_body


if __name__ == "__main__":
    build_device()

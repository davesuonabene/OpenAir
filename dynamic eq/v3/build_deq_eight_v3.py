#!/usr/bin/env python3
"""
build_deq_eight_v3.py
Generates `dEQ Eight v3 dev.amxd` and `dEQ Eight Alpha v0.04.amxd` — Stock Ableton EQ Eight UI & Stereo RTA
Fidelity Edition of the OpenAir 8-Band Dynamic Parametric Equalizer + Dual Sidechain + 4096-Point Stereo FFT RTA.
"""

import json
import os
import re
import struct
import zipfile


def tc(token):
    """Helper returning a Max 9 dynamic theme color expression dictionary."""
    return {"expression": f"themecolor.{token}"}


TRANSPARENT = [0.0, 0.0, 0.0, 0.0]


def _mirror_svg_path_x(d_str, x_sum=15.80):
    tokens = re.findall(r"[MLHVCZmlhvcz]|[-+]?(?:\d+\.?\d*|\.\d+)", d_str)
    out = []
    i = 0
    cmd = ""
    while i < len(tokens):
        tok = tokens[i]
        if tok.isalpha():
            cmd = tok
            out.append(cmd)
            i += 1
            if cmd in ("Z", "z"):
                continue
        if cmd in ("M", "L"):
            out.append(f"{x_sum - float(tokens[i]):.2f} {float(tokens[i + 1]):.2f}")
            i += 2
        elif cmd == "H":
            out.append(f"{x_sum - float(tokens[i]):.2f}")
            i += 1
        elif cmd == "V":
            out.append(f"{float(tokens[i]):.2f}")
            i += 1
        elif cmd == "C":
            pts = [f"{x_sum - float(tokens[i + 2 * k]):.2f} {float(tokens[i + 2 * k + 1]):.2f}" for k in range(3)]
            out.append(", ".join(pts))
            i += 6
    return " ".join(out)


def _make_cross_glyph(cx, cy, half_sz=1.52, thick=0.80):
    r = half_sz
    d = thick * 0.70710678
    pts = [
        (cx - r + d, cy - r), (cx, cy - d), (cx + r - d, cy - r), (cx + r, cy - r + d),
        (cx + d, cy), (cx + r, cy + r - d), (cx + r - d, cy + r), (cx, cy + d),
        (cx - r + d, cy + r), (cx - r, cy + r - d), (cx - d, cy), (cx - r, cy - r + d),
    ]
    return "M " + " L ".join(f"{px:.2f} {py:.2f}" for px, py in pts) + " Z"


def _make_open_four_glyph(x0):
    w = 0.92
    xr0 = x0 + 2.13
    xr1 = xr0 + w
    pts = [
        (x0, 2.95), (x0 + w, 2.95), (x0 + w, 5.55), (xr0, 5.55), (xr0, 4.30),
        (xr1, 4.30), (xr1, 8.45), (xr0, 8.45), (xr0, 6.50), (x0, 6.50),
    ]
    return "M " + " L ".join(f"{px:.2f} {py:.2f}" for px, py in pts) + " Z"


def write_svg_assets(out_dir):
    """Writes pixel-matched pure-black vector SVG templates dynamically recolored via remapsvgcolors=1."""
    lc12_d = (
        "M 0.55 8.35 V 4.30 C 0.55 2.25, 2.05 0.85, 4.10 0.85 H 15.25 V 1.90 H 4.10 "
        "C 2.62 1.90, 1.60 2.85, 1.60 4.30 V 8.35 H 0.55 Z"
    )
    hc12_d = _mirror_svg_path_x(lc12_d, 15.80)

    lc48_curve = (
        "M 0.55 8.40 V 4.10 C 0.55 2.15, 1.95 0.80, 3.90 0.80 H 15.25 V 1.85 H 3.90 "
        "C 2.52 1.85, 1.60 2.75, 1.60 4.10 V 8.40 H 0.55 Z"
    )
    hc48_curve = _mirror_svg_path_x(lc48_curve, 15.80)
    lc48_d = lc48_curve + " " + _make_cross_glyph(8.35, 6.70, 1.52, 0.80) + " " + _make_open_four_glyph(11.45)
    hc48_d = hc48_curve + " " + _make_open_four_glyph(0.55) + " " + _make_cross_glyph(6.45, 6.70, 1.52, 0.80)

    lshelf_d = (
        "M 0.25 0.25 H 5.65 L 9.36 3.96 H 15.55 V 5.04 H 9.36 L 5.65 8.75 H 0.25 V 7.67 "
        "H 5.20 L 8.37 4.50 L 5.20 1.33 H 0.25 V 0.25 Z"
    )
    hshelf_d = _mirror_svg_path_x(lshelf_d, 15.80)

    bell_d = (
        "M 0.25 3.96 H 2.05 L 5.76 0.25 H 10.04 L 13.75 3.96 H 15.55 V 5.04 H 13.75 "
        "L 10.04 8.75 H 5.76 L 2.05 5.04 H 0.25 V 3.96 Z "
        "M 3.04 4.50 L 6.21 7.67 H 9.59 L 12.76 4.50 L 9.59 1.33 H 6.21 L 3.04 4.50 Z"
    )

    notch_left = (
        "M 0.25 0.85 H 3.35 C 5.55 0.85, 7.32 2.95, 7.32 5.75 V 8.45 H 6.30 V 5.75 "
        "C 6.30 3.55, 4.95 1.90, 3.35 1.90 H 0.25 V 0.85 Z"
    )
    notch_d = notch_left + " " + _mirror_svg_path_x(notch_left, 15.80)

    headphones_d = (
        "M 8.00 1.25 C 4.95 1.25, 2.75 3.55, 2.75 6.65 C 2.75 8.55, 3.75 10.35, 5.45 11.55 "
        "L 6.55 10.30 C 5.65 9.45, 5.15 8.45, 5.15 7.45 L 4.05 7.25 C 4.05 4.75, 5.70 2.55, 8.00 2.55 "
        "C 10.30 2.55, 11.95 4.75, 11.95 7.25 L 10.85 7.45 C 10.85 8.45, 10.35 9.45, 9.45 10.30 "
        "L 10.55 11.55 C 12.25 10.35, 13.25 8.55, 13.25 6.65 C 13.25 3.55, 11.05 1.25, 8.00 1.25 Z"
    )

    rta_bars_d = " ".join(
        f"M {bx:.2f} {11.35 - bh:.2f} H {bx + 1.05:.2f} V 11.35 H {bx:.2f} Z"
        for bx, bh in [
            (3.40, 3.50), (5.65, 7.60), (7.90, 5.50), (10.15, 7.60),
            (12.40, 3.20), (14.65, 5.50), (16.90, 1.85),
        ]
    )

    def wrap_eq8_svg(path_d):
        return (
            '<svg width="24" height="9" viewBox="0 0 24 9" fill="none" xmlns="http://www.w3.org/2000/svg">\n'
            f'  <path fill-rule="evenodd" clip-rule="evenodd" d="{path_d}" fill="black"/>\n'
            '</svg>'
        )

    svgs = {
        "tri_closed.svg": (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 14 14" width="14" height="14">\n'
            '  <polygon points="5.0,3.6 10.4,7.0 5.0,10.4" fill="black"/>\n'
            '</svg>'
        ),
        "tri_open.svg": (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 14 14" width="14" height="14">\n'
            '  <polygon points="3.6,5.2 10.4,5.2 7.0,10.4" fill="black"/>\n'
            '</svg>'
        ),
        "headphones.svg": (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 13" width="16" height="13" fill="none">\n'
            f'  <path fill-rule="evenodd" clip-rule="evenodd" d="{headphones_d}" fill="black"/>\n'
            '</svg>'
        ),
        "rta_bars.svg": (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 22 15" width="22" height="15" fill="none">\n'
            f'  <path fill-rule="evenodd" clip-rule="evenodd" d="{rta_bars_d}" fill="black"/>\n'
            '</svg>'
        ),
        "dyn_ring.svg": (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 13 13" width="13" height="13">\n'
            '  <path fill-rule="evenodd" clip-rule="evenodd" d="M6.5 0.85A5.65 5.65 0 1 0 6.5 12.15A5.65 5.65 0 1 0 6.5 0.85ZM6.5 2.35A4.15 4.15 0 1 1 6.5 10.65A4.15 4.15 0 1 1 6.5 2.35Z" fill="black"/>\n'
            '</svg>'
        ),
        "eq8_lc48.svg": wrap_eq8_svg(lc48_d),
        "eq8_lc12.svg": wrap_eq8_svg(lc12_d),
        "eq8_lshelf.svg": wrap_eq8_svg(lshelf_d),
        "eq8_bell.svg": wrap_eq8_svg(bell_d),
        "eq8_notch.svg": wrap_eq8_svg(notch_d),
        "eq8_hshelf.svg": wrap_eq8_svg(hshelf_d),
        "eq8_hc12.svg": wrap_eq8_svg(hc12_d),
        "eq8_hc48.svg": wrap_eq8_svg(hc48_d),
    }

    for fname, content in svgs.items():
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
            f.write(content)
    return list(svgs.keys())


def make_box(box_id, maxclass, text=None, varname="", patching_rect=None, presentation_rect=None, **kwargs):
    if patching_rect is None:
        patching_rect = [0.0, 0.0, 80.0, 20.0]
    box = {"id": box_id, "maxclass": maxclass, "patching_rect": patching_rect}
    if text is not None:
        box["text"] = text
    if varname:
        box["varname"] = varname
    if presentation_rect is not None:
        box["presentation"] = 1
        box["presentation_rect"] = presentation_rect
    box.update(kwargs)
    return {"box": box}


def make_live_menu(
    box_id, varname, shortname, items, initial_idx,
    patching_rect, presentation_rect, pictures=None,
    invisible=2, initial_enable=0, **kwargs
):
    defaults = {
        "fontname": "Ableton Sans Medium",
        "fontsize": 11.0,
        "fontface": 0,
        "activebgcolor": [0.106, 0.094, 0.129, 1.0],
        "bordercolor": [0.067, 0.063, 0.086, 1.0],
        "focusbordercolor": [0.067, 0.063, 0.086, 1.0],
        "textcolor": [0.827, 0.804, 0.843, 1.0],
        "tricolor": [0.827, 0.804, 0.843, 1.0],
        "hltcolor": [0.749, 0.843, 0.890, 1.0],
        "hlttextcolor": [0.05, 0.05, 0.07, 1.0],
    }
    if pictures:
        defaults["pictures"] = pictures
        defaults["usepicture"] = 1
        defaults["remapsvgcolors"] = 1
        defaults["usesvgviewbox"] = 1
        defaults["justification"] = 0
        defaults["fontsize"] = 11.5
    longname = kwargs.pop("longname", shortname)
    defaults.update(kwargs)
    return make_box(
        box_id, "live.menu", varname=varname,
        patching_rect=patching_rect, presentation_rect=presentation_rect,
        numinlets=1, numoutlets=3, outlettype=["", "", "float"],
        parameter_enable=1,
        saved_attribute_attributes={
            "activebgcolor": tc("live_control_text_bg"),
            "bordercolor": tc("live_contrast_frame"),
            "focusbordercolor": tc("live_focus_frame"),
            "hltcolor": tc("live_lcd_control_fg"),
            "hlttextcolor": tc("live_control_fg_on"),
            "textcolor": tc("live_control_fg"),
            "tricolor": tc("live_control_fg"),
            "valueof": {
                "parameter_enum": items,
                "parameter_initial": [initial_idx],
                "parameter_initial_enable": initial_enable,
                "parameter_invisible": invisible,
                "parameter_linknames": 0,
                "parameter_longname": longname,
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
        box_id, "panel", varname=varname,
        patching_rect=patching_rect, presentation_rect=presentation_rect,
        numinlets=1, numoutlets=0, mode=0, border=border, rounded=rounded,
        bgcolor=[0.278, 0.255, 0.329, 1.0],
        saved_attribute_attributes=saa, **kwargs,
    )


def make_live_line(box_id, varname, patching_rect, presentation_rect, color_token="live_control_bg", thickness=1.0, **kwargs):
    default_lc = [0.278, 0.255, 0.329, 1.0] if color_token == "live_lcd_frame" else [0.125, 0.118, 0.153, 1.0]
    return make_box(
        box_id, "live.line", varname=varname,
        patching_rect=patching_rect, presentation_rect=presentation_rect,
        numinlets=1, numoutlets=0, justification=0, border=float(thickness),
        linecolor=default_lc,
        saved_attribute_attributes={"linecolor": tc(color_token)}, **kwargs,
    )


def make_comment(box_id, varname, text_str, patching_rect, presentation_rect, color_token="live_control_fg", fontsize=10.0, justification=0, fontface=1, **kwargs):
    fname = kwargs.pop("fontname", "Ableton Sans Small Bold")
    return make_box(
        box_id, "live.comment", varname=varname,
        patching_rect=patching_rect, presentation_rect=presentation_rect,
        numinlets=1, numoutlets=0, text=text_str,
        fontname=fname, fontsize=fontsize, fontface=fontface,
        textjustification=justification,
        textcolor=[0.827, 0.804, 0.843, 1.0],
        saved_attribute_attributes={"textcolor": tc(color_token)}, **kwargs,
    )


def make_live_tab(box_id, varname, shortname, items, initial_idx, patching_rect, presentation_rect, invisible=0, initial_enable=1, **kwargs):
    fsize = kwargs.pop("fontsize", 10.0)
    longname = kwargs.pop("longname", shortname)
    return make_box(
        box_id, "live.tab", varname=varname,
        patching_rect=patching_rect, presentation_rect=presentation_rect,
        numinlets=1, numoutlets=3, outlettype=["", "", "float"],
        num_lines_patching=1, num_lines_presentation=1,
        fontname="Ableton Sans Small Bold", fontsize=fsize, fontface=1,
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
                "parameter_longname": longname,
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
    longname = kwargs.pop("longname", shortname)
    val_dict = {
        "parameter_enum": [text_off if text_off else "Off", text_on if text_on else "On"],
        "parameter_initial": [initial_val],
        "parameter_initial_enable": initial_enable,
        "parameter_linknames": 0,
        "parameter_longname": longname,
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
        box_id, "live.text", text=text_off, varname=varname,
        patching_rect=patching_rect, presentation_rect=presentation_rect,
        numinlets=1, numoutlets=2, outlettype=["", ""],
        mode=mode, texton=text_on, parameter_enable=1,
        saved_attribute_attributes=saa, **defaults,
    )


def make_live_numbox(
    box_id, varname, shortname, mmin, mmax, initial_val, unitstyle,
    patching_rect, presentation_rect, exponent=1.0, param_type=0, custom_units=None,
    invisible=0, initial_enable=1, **kwargs
):
    longname = kwargs.pop("longname", varname)
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
        "parameter_longname": longname,
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
        box_id, "live.numbox", varname=varname,
        patching_rect=patching_rect, presentation_rect=presentation_rect,
        numinlets=1, numoutlets=2, outlettype=["", "float"],
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
    longname = kwargs.pop("longname", varname)
    defaults = {
        "fontname": "Ableton Sans Medium",
        "fontsize": 10.5,
        "fontface": 0,
        "showname": 0,
        "activedialcolor": [0.224, 0.824, 0.894, 1.0],
        "activefgdialcolor": [0.078, 0.075, 0.102, 1.0],
        "activeneedlecolor": [0.078, 0.075, 0.102, 1.0],
        "dialcolor": [0.514, 0.478, 0.561, 1.0],
        "fgdialcolor": [0.106, 0.094, 0.129, 1.0],
        "needlecolor": [0.106, 0.094, 0.129, 1.0],
        "textcolor": [0.827, 0.804, 0.843, 1.0],
    }
    defaults.update(kwargs)
    val_attrs = {
        "parameter_initial": [initial_val],
        "parameter_initial_enable": initial_enable,
        "parameter_invisible": invisible,
        "parameter_longname": longname,
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
        box_id, "live.dial", varname=varname,
        patching_rect=patching_rect, presentation_rect=presentation_rect,
        numinlets=1, numoutlets=2, outlettype=["", "float"],
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
    umenu_items = []
    for idx, item in enumerate(items):
        if idx > 0:
            umenu_items.append(",")
        umenu_items.append(item)

    return make_box(
        box_id, "umenu", varname=varname,
        patching_rect=patching_rect, presentation_rect=presentation_rect,
        numinlets=1, numoutlets=3, outlettype=["int", "", ""],
        items=umenu_items, applycolors=1,
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
        fontname="Ableton Sans Medium", fontsize=9.5, fontface=0,
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
    return {"patchline": {"source": [src_id, src_outlet], "destination": [dst_id, dst_inlet]}}


def generate_gen_codebox():
    """64-bit GenExpr codebox for 8-Band Cytomic ZDF SVF + 36 dB/oct Shape-Aware Multiband Detector."""
    default_freqs = [30.0, 200.0, 1000.0, 5000.0, 100.0, 1000.0, 5000.0, 18000.0]
    default_types = [2, 3, 3, 5, 3, 3, 3, 6]
    default_on    = [1, 1, 1, 1, 0, 0, 0, 0]

    code = [
        "// ============================================================================",
        "// OpenAir dEQ Eight v0.04 - 64-Bit Cytomic ZDF SVF + 36 dB/oct Band Isolator",
        "// ============================================================================",
        "",
        "Param adapt_q(1);",
        "Param dyn_scale(1.0);",
        "Param out_gain(0.0);",
        "Param solo_band(0);",
        "Param sc_listen_src(1);",
        "Param sc1_en(0);",
        "Param sc1_mix(1.0);",
        "Param sc1_gain(0.0);",
        "Param sc2_en(0);",
        "Param sc2_mix(1.0);",
        "Param sc2_gain(0.0);",
        "",
        "History prev_sr(0.0);",
        "History gr_tick(0);",
        "History out_gain_sm(0.0), prev_out_sm(-999.0), out_lin_c(1.0);",
        "History sc1_gain_sm(0.0), prev_sc1_sm(-999.0), sc1_lin_c(1.0);",
        "History sc2_gain_sm(0.0), prev_sc2_sm(-999.0), sc2_lin_c(1.0);",
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
            f"History freq_sm_{b}({f_init}), gain_sm_{b}(0.0);",
            f"History prev_freq_{b}(-1.0), g0_c_{b}(0.05), nyq_c_{b}(1.0);",
            f"History prev_det_f_{b}(-1.0), prev_det_q_{b}(-1.0), prev_det_t_{b}(-1);",
            f"History da1_{b}(0.0), da2_{b}(0.0), da3_{b}(0.0), dm0_{b}(0.0), dm1_{b}(1.0), dm2_{b}(0.0);",
            f"History prev_atk_{b}(-1.0), atk_c_{b}(0.99), prev_rel_{b}(-1.0), rel_c_{b}(0.999);",
            f"History d1L_ic1_{b}(0.0), d1L_ic2_{b}(0.0), d1R_ic1_{b}(0.0), d1R_ic2_{b}(0.0);",
            f"History d2L_ic1_{b}(0.0), d2L_ic2_{b}(0.0), d2R_ic1_{b}(0.0), d2R_ic2_{b}(0.0);",
            f"History d3L_ic1_{b}(0.0), d3L_ic2_{b}(0.0), d3R_ic1_{b}(0.0), d3R_ic2_{b}(0.0);",
            f"History env_{b}(0.0), mod_db_{b}(0.0);",
            f"History prev_eq_f_{b}(-1.0), prev_eq_q_{b}(-1.0), prev_eq_g_{b}(-999.0), prev_eq_t_{b}(-1), prev_eq_aq_{b}(-1);",
            f"History a1_c_{b}(0.0), a2_c_{b}(0.0), a3_c_{b}(0.0), m0_c_{b}(1.0), m1_c_{b}(0.0), m2_c_{b}(0.0);",
            f"History eq_bypassed_{b}(0);",
            f"History s1L_ic1_{b}(0.0), s1L_ic2_{b}(0.0), s1R_ic1_{b}(0.0), s1R_ic2_{b}(0.0);",
            f"History s2L_ic1_{b}(0.0), s2L_ic2_{b}(0.0), s2R_ic1_{b}(0.0), s2R_ic2_{b}(0.0);",
        ])

    code.extend([
        "",
        "sr_changed = (samplerate != prev_sr);",
        "prev_sr = samplerate;",
        "sm_alpha = clip(240.0 / samplerate, 0.0005, 0.10);",
        "",
        "out_gain_sm = out_gain_sm + sm_alpha * (out_gain - out_gain_sm);",
        "if (abs(out_gain_sm - prev_out_sm) > 0.0002) {",
        "    out_lin_c = exp(out_gain_sm * 0.11512925464970229);",
        "    prev_out_sm = out_gain_sm;",
        "}",
        "sc1_gain_sm = sc1_gain_sm + sm_alpha * (sc1_gain - sc1_gain_sm);",
        "if (abs(sc1_gain_sm - prev_sc1_sm) > 0.0002) {",
        "    sc1_lin_c = exp(sc1_gain_sm * 0.11512925464970229);",
        "    prev_sc1_sm = sc1_gain_sm;",
        "}",
        "sc2_gain_sm = sc2_gain_sm + sm_alpha * (sc2_gain - sc2_gain_sm);",
        "if (abs(sc2_gain_sm - prev_sc2_sm) > 0.0002) {",
        "    sc2_lin_c = exp(sc2_gain_sm * 0.11512925464970229);",
        "    prev_sc2_sm = sc2_gain_sm;",
        "}",
        "",
        "sigL = in1;",
        "sigR = in2;",
        "sc1_L = in3 * sc1_lin_c;",
        "sc1_R = in4 * sc1_lin_c;",
        "sc2_L = in5 * sc2_lin_c;",
        "sc2_R = in6 * sc2_lin_c;",
        "ext_a_peak = max(abs(sc1_L), abs(sc1_R));",
        "ext_b_peak = max(abs(sc2_L), abs(sc2_R));",
        "solo_idx = round(solo_band);",
        "soloL = 0.0;",
        "soloR = 0.0;",
        "",
    ])

    for b in range(1, 9):
        code.extend([
            f"// ==================== BAND {b} ====================",
            f"is_solo_{b} = (solo_idx == {b});",
            f"if (b{b}_on > 0.5 || is_solo_{b}) {{",
            f"    t_{b} = round(b{b}_type);",
            f"    is_gain_shape_{b} = (t_{b} == 2 || t_{b} == 3 || t_{b} == 5);",
            f"    has_dyn_{b} = (b{b}_dyn_on > 0.5 && is_gain_shape_{b} && abs(b{b}_dyn_range) > 0.01);",
            f"    freq_sm_{b} = freq_sm_{b} + sm_alpha * (b{b}_freq - freq_sm_{b});",
            f"    gain_sm_{b} = gain_sm_{b} + sm_alpha * (b{b}_gain - gain_sm_{b});",
            f"    if (sr_changed || abs(freq_sm_{b} - prev_freq_{b}) > 0.005) {{",
            f"        fc_{b} = clip(freq_sm_{b}, 12.0, samplerate * 0.485);",
            f"        w0_{b} = pi * fc_{b} / samplerate;",
            f"        g0_c_{b} = tan(w0_{b});",
            f"        nyq_c_{b} = max(0.25, cos(w0_{b} * 0.70));",
            f"        prev_freq_{b} = freq_sm_{b};",
            f"    }}",
            f"    if (has_dyn_{b} || is_solo_{b}) {{",
            f"        src_{b} = round(b{b}_source);",
            f"        need_iso_{b} = (is_solo_{b} || src_{b} == 0 || (src_{b} == 1 && sc1_mix < 0.999) || (src_{b} == 2 && sc2_mix < 0.999));",
            f"        det_int_{b} = 0.0;",
            f"        if (need_iso_{b}) {{",
            f"            if (sr_changed || abs(freq_sm_{b} - prev_det_f_{b}) > 0.005 || abs(b{b}_q - prev_det_q_{b}) > 0.0005 || t_{b} != prev_det_t_{b}) {{",
            f"                g_det_{b} = g0_c_{b};",
            f"                k_det_{b} = 1.4142135623730951;",
            f"                if (t_{b} == 2 || t_{b} == 6 || t_{b} == 7) {{",
            f"                    g_det_{b} = min(g0_c_{b} * 1.40, 12.0);",
            f"                    dm0_{b} = 0.0; dm1_{b} = 0.0; dm2_{b} = 1.0;",
            f"                }} else if (t_{b} == 5 || t_{b} == 0 || t_{b} == 1) {{",
            f"                    g_det_{b} = max(g0_c_{b} * 0.714, 0.0002);",
            f"                    dm0_{b} = 1.0; dm1_{b} = -k_det_{b}; dm2_{b} = -1.0;",
            f"                }} else {{",
            f"                    k_det_{b} = 1.0 / (clip(0.35 + b{b}_q * 0.52, 0.68, 12.0) * nyq_c_{b});",
            f"                    dm0_{b} = 0.0; dm1_{b} = k_det_{b}; dm2_{b} = 0.0;",
            f"                }}",
            f"                da1_{b} = 1.0 / (1.0 + g_det_{b} * (g_det_{b} + k_det_{b}));",
            f"                da2_{b} = g_det_{b} * da1_{b};",
            f"                da3_{b} = g_det_{b} * da2_{b};",
            f"                prev_det_f_{b} = freq_sm_{b};",
            f"                prev_det_q_{b} = b{b}_q;",
            f"                prev_det_t_{b} = t_{b};",
            f"            }}",
            f"            dv3L1_{b} = sigL - d1L_ic2_{b};",
            f"            dv1L1_{b} = da1_{b} * d1L_ic1_{b} + da2_{b} * dv3L1_{b};",
            f"            dv2L1_{b} = d1L_ic2_{b} + da2_{b} * d1L_ic1_{b} + da3_{b} * dv3L1_{b};",
            f"            d1L_ic1_{b} = fixdenorm(2.0 * dv1L1_{b} - d1L_ic1_{b});",
            f"            d1L_ic2_{b} = fixdenorm(2.0 * dv2L1_{b} - d1L_ic2_{b});",
            f"            isoL1_{b} = dm0_{b} * sigL + dm1_{b} * dv1L1_{b} + dm2_{b} * dv2L1_{b};",
            f"            dv3R1_{b} = sigR - d1R_ic2_{b};",
            f"            dv1R1_{b} = da1_{b} * d1R_ic1_{b} + da2_{b} * dv3R1_{b};",
            f"            dv2R1_{b} = d1R_ic2_{b} + da2_{b} * d1R_ic1_{b} + da3_{b} * dv3R1_{b};",
            f"            d1R_ic1_{b} = fixdenorm(2.0 * dv1R1_{b} - d1R_ic1_{b});",
            f"            d1R_ic2_{b} = fixdenorm(2.0 * dv2R1_{b} - d1R_ic2_{b});",
            f"            isoR1_{b} = dm0_{b} * sigR + dm1_{b} * dv1R1_{b} + dm2_{b} * dv2R1_{b};",
            f"            dv3L2_{b} = isoL1_{b} - d2L_ic2_{b};",
            f"            dv1L2_{b} = da1_{b} * d2L_ic1_{b} + da2_{b} * dv3L2_{b};",
            f"            dv2L2_{b} = d2L_ic2_{b} + da2_{b} * d2L_ic1_{b} + da3_{b} * dv3L2_{b};",
            f"            d2L_ic1_{b} = fixdenorm(2.0 * dv1L2_{b} - d2L_ic1_{b});",
            f"            d2L_ic2_{b} = fixdenorm(2.0 * dv2L2_{b} - d2L_ic2_{b});",
            f"            isoL2_{b} = dm0_{b} * isoL1_{b} + dm1_{b} * dv1L2_{b} + dm2_{b} * dv2L2_{b};",
            f"            dv3R2_{b} = isoR1_{b} - d2R_ic2_{b};",
            f"            dv1R2_{b} = da1_{b} * d2R_ic1_{b} + da2_{b} * dv3R2_{b};",
            f"            dv2R2_{b} = d2R_ic2_{b} + da2_{b} * d2R_ic1_{b} + da3_{b} * dv3R2_{b};",
            f"            d2R_ic1_{b} = fixdenorm(2.0 * dv1R2_{b} - d2R_ic1_{b});",
            f"            d2R_ic2_{b} = fixdenorm(2.0 * dv2R2_{b} - d2R_ic2_{b});",
            f"            isoR2_{b} = dm0_{b} * isoR1_{b} + dm1_{b} * dv1R2_{b} + dm2_{b} * dv2R2_{b};",
            f"            dv3L3_{b} = isoL2_{b} - d3L_ic2_{b};",
            f"            dv1L3_{b} = da1_{b} * d3L_ic1_{b} + da2_{b} * dv3L3_{b};",
            f"            dv2L3_{b} = d3L_ic2_{b} + da2_{b} * d3L_ic1_{b} + da3_{b} * dv3L3_{b};",
            f"            d3L_ic1_{b} = fixdenorm(2.0 * dv1L3_{b} - d3L_ic1_{b});",
            f"            d3L_ic2_{b} = fixdenorm(2.0 * dv2L3_{b} - d3L_ic2_{b});",
            f"            isoL3_{b} = dm0_{b} * isoL2_{b} + dm1_{b} * dv1L3_{b} + dm2_{b} * dv2L3_{b};",
            f"            dv3R3_{b} = isoR2_{b} - d3R_ic2_{b};",
            f"            dv1R3_{b} = da1_{b} * d3R_ic1_{b} + da2_{b} * dv3R3_{b};",
            f"            dv2R3_{b} = d3R_ic2_{b} + da2_{b} * d3R_ic1_{b} + da3_{b} * dv3R3_{b};",
            f"            d3R_ic1_{b} = fixdenorm(2.0 * dv1R3_{b} - d3R_ic1_{b});",
            f"            d3R_ic2_{b} = fixdenorm(2.0 * dv2R3_{b} - d3R_ic2_{b});",
            f"            isoR3_{b} = dm0_{b} * isoR2_{b} + dm1_{b} * dv1R3_{b} + dm2_{b} * dv2R3_{b};",
            f"            det_int_{b} = max(abs(isoL3_{b}), abs(isoR3_{b}));",
            f"            if (is_solo_{b}) {{",
            f"                soloL = isoL3_{b};",
            f"                soloR = isoR3_{b};",
            f"            }}",
            f"        }}",
            f"        if (has_dyn_{b}) {{",
            f"            if (sr_changed || abs(b{b}_attack - prev_atk_{b}) > 0.001) {{",
            f"                atk_c_{b} = exp(-1000.0 / (max(0.1, b{b}_attack) * samplerate));",
            f"                prev_atk_{b} = b{b}_attack;",
            f"            }}",
            f"            if (sr_changed || abs(b{b}_release - prev_rel_{b}) > 0.001) {{",
            f"                rel_c_{b} = exp(-1000.0 / (max(5.0, b{b}_release) * samplerate));",
            f"                prev_rel_{b} = b{b}_release;",
            f"            }}",
            f"            rect_{b} = det_int_{b};",
            f"            if (src_{b} == 1) {{",
            f"                rect_{b} = (sc1_en > 0.5) ? ((1.0 - sc1_mix) * det_int_{b} + sc1_mix * ext_a_peak) : 0.0;",
            f"            }} else if (src_{b} == 2) {{",
            f"                rect_{b} = (sc2_en > 0.5) ? ((1.0 - sc2_mix) * det_int_{b} + sc2_mix * ext_b_peak) : 0.0;",
            f"            }}",
            f"            env_{b} = fixdenorm((rect_{b} > env_{b}) ? (atk_c_{b} * env_{b} + (1.0 - atk_c_{b}) * rect_{b}) : (rel_c_{b} * env_{b} + (1.0 - rel_c_{b}) * rect_{b}));",
            f"            env_db_{b} = log(max(0.000001, env_{b})) * 8.685889638065035;",
            f"            over_db_{b} = env_db_{b} - b{b}_thresh;",
            f"            knee_over_{b} = (over_db_{b} <= -1.5) ? 0.0 : ((over_db_{b} < 1.5) ? ((over_db_{b} + 1.5) * (over_db_{b} + 1.5) * 0.16666666666666666) : over_db_{b});",
            f"            max_r_{b} = max(0.001, abs(b{b}_dyn_range));",
            f"            norm_over_{b} = knee_over_{b} / max_r_{b};",
            f"            curve_{b} = norm_over_{b} / sqrt(1.0 + norm_over_{b} * norm_over_{b});",
            f"            target_mod_{b} = (knee_over_{b} > 0.0 && abs(b{b}_dyn_range) > 0.01) ? (b{b}_dyn_range * curve_{b}) : 0.0;",
            f"            mod_db_{b} = fixdenorm(0.990 * mod_db_{b} + 0.010 * target_mod_{b});",
            f"        }} else {{",
            f"            env_{b} = 0.0;",
            f"            mod_db_{b} = 0.0;",
            f"        }}",
            f"    }} else {{",
            f"        env_{b} = 0.0;",
            f"        mod_db_{b} = 0.0;",
            f"    }}",
            f"    if (b{b}_on > 0.5) {{",
            f"        tot_gain_{b} = (gain_sm_{b} + mod_db_{b}) * dyn_scale;",
            f"        can_bypass_{b} = (is_gain_shape_{b} && (has_dyn_{b} == 0) && abs(b{b}_gain) < 0.0005 && abs(gain_sm_{b}) < 0.0005 && abs(mod_db_{b}) < 0.0005);",
            f"        if (can_bypass_{b}) {{",
            f"            if (eq_bypassed_{b} == 0) {{",
            f"                s1L_ic1_{b} = 0.0; s1L_ic2_{b} = 0.0; s1R_ic1_{b} = 0.0; s1R_ic2_{b} = 0.0;",
            f"                s2L_ic1_{b} = 0.0; s2L_ic2_{b} = 0.0; s2R_ic1_{b} = 0.0; s2R_ic2_{b} = 0.0;",
            f"                eq_bypassed_{b} = 1;",
            f"            }}",
            f"        }} else {{",
            f"            eq_bypassed_{b} = 0;",
            f"            aq_flag_{b} = (adapt_q > 0.5) ? 1 : 0;",
            f"            if (sr_changed || abs(freq_sm_{b} - prev_eq_f_{b}) > 0.005 || abs(tot_gain_{b} - prev_eq_g_{b}) > 0.0005 || abs(b{b}_q - prev_eq_q_{b}) > 0.0005 || t_{b} != prev_eq_t_{b} || aq_flag_{b} != prev_eq_aq_{b}) {{",
            f"                q_base_{b} = clip(b{b}_q, 0.1, 18.0);",
            f"                q_eff_{b} = (aq_flag_{b} == 1 && is_gain_shape_{b}) ? clip(q_base_{b} * exp(abs(tot_gain_{b}) * 0.03850817669777474), 0.1, 18.0) : q_base_{b};",
            f"                k_eq_{b} = 1.0 / (q_eff_{b} * nyq_c_{b});",
            f"                g_eq_{b} = g0_c_{b};",
            f"                m0_c_{b} = 1.0; m1_c_{b} = 0.0; m2_c_{b} = 0.0;",
            f"                if (t_{b} == 3) {{",
            f"                    A_{b} = exp(tot_gain_{b} * 0.05756462732485114);",
            f"                    k_eq_{b} = k_eq_{b} / A_{b};",
            f"                    m0_c_{b} = 1.0;",
            f"                    m1_c_{b} = k_eq_{b} * (A_{b} * A_{b} - 1.0);",
            f"                    m2_c_{b} = 0.0;",
            f"                }} else if (t_{b} == 2) {{",
            f"                    A_{b} = exp(tot_gain_{b} * 0.05756462732485114);",
            f"                    g_eq_{b} = g0_c_{b} / sqrt(A_{b});",
            f"                    m0_c_{b} = 1.0;",
            f"                    m1_c_{b} = k_eq_{b} * (A_{b} - 1.0);",
            f"                    m2_c_{b} = A_{b} * A_{b} - 1.0;",
            f"                }} else if (t_{b} == 5) {{",
            f"                    A_{b} = exp(tot_gain_{b} * 0.05756462732485114);",
            f"                    g_eq_{b} = g0_c_{b} * sqrt(A_{b});",
            f"                    m0_c_{b} = A_{b} * A_{b};",
            f"                    m1_c_{b} = k_eq_{b} * (1.0 - A_{b}) * A_{b};",
            f"                    m2_c_{b} = 1.0 - A_{b} * A_{b};",
            f"                }} else if (t_{b} == 1 || t_{b} == 0) {{",
            f"                    m0_c_{b} = 1.0;",
            f"                    m1_c_{b} = -k_eq_{b};",
            f"                    m2_c_{b} = -1.0;",
            f"                }} else if (t_{b} == 6 || t_{b} == 7) {{",
            f"                    m0_c_{b} = 0.0;",
            f"                    m1_c_{b} = 0.0;",
            f"                    m2_c_{b} = 1.0;",
            f"                }} else if (t_{b} == 4) {{",
            f"                    m0_c_{b} = 1.0;",
            f"                    m1_c_{b} = -k_eq_{b};",
            f"                    m2_c_{b} = 0.0;",
            f"                }}",
            f"                a1_c_{b} = 1.0 / (1.0 + g_eq_{b} * (g_eq_{b} + k_eq_{b}));",
            f"                a2_c_{b} = g_eq_{b} * a1_c_{b};",
            f"                a3_c_{b} = g_eq_{b} * a2_c_{b};",
            f"                prev_eq_f_{b} = freq_sm_{b};",
            f"                prev_eq_g_{b} = tot_gain_{b};",
            f"                prev_eq_q_{b} = b{b}_q;",
            f"                prev_eq_t_{b} = t_{b};",
            f"                prev_eq_aq_{b} = aq_flag_{b};",
            f"            }}",
            f"            v3L_{b} = sigL - s1L_ic2_{b};",
            f"            v1L_{b} = a1_c_{b} * s1L_ic1_{b} + a2_c_{b} * v3L_{b};",
            f"            v2L_{b} = s1L_ic2_{b} + a2_c_{b} * s1L_ic1_{b} + a3_c_{b} * v3L_{b};",
            f"            s1L_ic1_{b} = fixdenorm(2.0 * v1L_{b} - s1L_ic1_{b});",
            f"            s1L_ic2_{b} = fixdenorm(2.0 * v2L_{b} - s1L_ic2_{b});",
            f"            sigL = m0_c_{b} * sigL + m1_c_{b} * v1L_{b} + m2_c_{b} * v2L_{b};",
            f"            v3R_{b} = sigR - s1R_ic2_{b};",
            f"            v1R_{b} = a1_c_{b} * s1R_ic1_{b} + a2_c_{b} * v3R_{b};",
            f"            v2R_{b} = s1R_ic2_{b} + a2_c_{b} * s1R_ic1_{b} + a3_c_{b} * v3R_{b};",
            f"            s1R_ic1_{b} = fixdenorm(2.0 * v1R_{b} - s1R_ic1_{b});",
            f"            s1R_ic2_{b} = fixdenorm(2.0 * v2R_{b} - s1R_ic2_{b});",
            f"            sigR = m0_c_{b} * sigR + m1_c_{b} * v1R_{b} + m2_c_{b} * v2R_{b};",
            f"            if (t_{b} == 0 || t_{b} == 7) {{",
            f"                v3L2_{b} = sigL - s2L_ic2_{b};",
            f"                v1L2_{b} = a1_c_{b} * s2L_ic1_{b} + a2_c_{b} * v3L2_{b};",
            f"                v2L2_{b} = s2L_ic2_{b} + a2_c_{b} * s2L_ic1_{b} + a3_c_{b} * v3L2_{b};",
            f"                s2L_ic1_{b} = fixdenorm(2.0 * v1L2_{b} - s2L_ic1_{b});",
            f"                s2L_ic2_{b} = fixdenorm(2.0 * v2L2_{b} - s2L_ic2_{b});",
            f"                sigL = m0_c_{b} * sigL + m1_c_{b} * v1L2_{b} + m2_c_{b} * v2L2_{b};",
            f"                v3R2_{b} = sigR - s2R_ic2_{b};",
            f"                v1R2_{b} = a1_c_{b} * s2R_ic1_{b} + a2_c_{b} * v3R2_{b};",
            f"                v2R2_{b} = s2R_ic2_{b} + a2_c_{b} * s2R_ic1_{b} + a3_c_{b} * v3R2_{b};",
            f"                s2R_ic1_{b} = fixdenorm(2.0 * v1R2_{b} - s2R_ic1_{b});",
            f"                s2R_ic2_{b} = fixdenorm(2.0 * v2R2_{b} - s2R_ic2_{b});",
            f"                sigR = m0_c_{b} * sigR + m1_c_{b} * v1R2_{b} + m2_c_{b} * v2R2_{b};",
            f"            }}",
            f"        }}",
            f"    }}",
            f"}} else {{",
            f"    mod_db_{b} = 0.0;",
            f"    env_{b} = 0.0;",
            f"    if (eq_bypassed_{b} == 0) {{",
            f"        s1L_ic1_{b} = 0.0; s1L_ic2_{b} = 0.0; s1R_ic1_{b} = 0.0; s1R_ic2_{b} = 0.0;",
            f"        s2L_ic1_{b} = 0.0; s2L_ic2_{b} = 0.0; s2R_ic1_{b} = 0.0; s2R_ic2_{b} = 0.0;",
            f"        d1L_ic1_{b} = 0.0; d1L_ic2_{b} = 0.0; d1R_ic1_{b} = 0.0; d1R_ic2_{b} = 0.0;",
            f"        d2L_ic1_{b} = 0.0; d2L_ic2_{b} = 0.0; d2R_ic1_{b} = 0.0; d2R_ic2_{b} = 0.0;",
            f"        d3L_ic1_{b} = 0.0; d3L_ic2_{b} = 0.0; d3R_ic1_{b} = 0.0; d3R_ic2_{b} = 0.0;",
            f"        eq_bypassed_{b} = 1;",
            f"    }}",
            f"}}",
            "",
        ])

    code.extend([
        "out_L = sigL * out_lin_c;",
        "out_R = sigR * out_lin_c;",
        "if (solo_idx == 9) {",
        "    if (round(sc_listen_src) == 2) {",
        "        out1 = fixnan(sc2_L);",
        "        out2 = fixnan(sc2_R);",
        "    } else {",
        "        out1 = fixnan(sc1_L);",
        "        out2 = fixnan(sc1_R);",
        "    }",
        "} else if (solo_idx > 0) {",
        "    out1 = fixnan(soloL);",
        "    out2 = fixnan(soloR);",
        "} else {",
        "    out1 = fixnan(out_L);",
        "    out2 = fixnan(out_R);",
        "}",
        "",
        "gr_val = 0.0;",
        "gr_idx = -1;",
        "if (gr_tick == 0) { gr_val = mod_db_1; gr_idx = 0; }",
        "else if (gr_tick == 1) { gr_val = mod_db_2; gr_idx = 1; }",
        "else if (gr_tick == 2) { gr_val = mod_db_3; gr_idx = 2; }",
        "else if (gr_tick == 3) { gr_val = mod_db_4; gr_idx = 3; }",
        "else if (gr_tick == 4) { gr_val = mod_db_5; gr_idx = 4; }",
        "else if (gr_tick == 5) { gr_val = mod_db_6; gr_idx = 5; }",
        "else if (gr_tick == 6) { gr_val = mod_db_7; gr_idx = 6; }",
        "else if (gr_tick == 7) { gr_val = mod_db_8; gr_idx = 7; }",
        "gr_tick = (gr_tick >= 255) ? 0 : (gr_tick + 1);",
        "out3 = gr_val;",
        "out4 = gr_idx;",
    ])
    return "\r\n".join(code)


def build_gen_patcher():
    gen_boxes = []
    gen_lines = []
    for i in range(1, 7):
        in_id = f"obj-in{i}"
        gen_boxes.append(make_box(in_id, "newobj", f"in {i}", patching_rect=[40.0 + (i - 1) * 110.0, 20.0, 34.0, 22.0], numinlets=0, numoutlets=1, outlettype=[""]))
        gen_lines.append(make_line(in_id, 0, "obj-codebox", i - 1))

    gen_boxes.append(make_box("obj-codebox", "codebox", patching_rect=[40.0, 65.0, 760.0, 520.0], numinlets=6, numoutlets=4, outlettype=[""] * 4, code=generate_gen_codebox()))
    for o in range(1, 5):
        out_id = f"obj-out{o}"
        gen_boxes.append(make_box(out_id, "newobj", f"out {o}", patching_rect=[40.0 + (o - 1) * 140.0, 610.0, 42.0, 22.0], numinlets=1, numoutlets=0, outlettype=[]))
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
    Phase-Immune Stereo Power 4096-Point Hann FFT Extractor (`L + jR` -> `sqrt(|Z_hann[k]|^2 + |Z_hann[4096-k]|^2) / 2048`):
    - Eliminates `(L + R) * 0.5` high-frequency stereo phase cancellation completely using a single `fft~ 4096 4096 0`.
    - Writes all 2048 Hann-windowed bins `0 .. 2047` (including DC bin `0`) into `buffer~ ---rta_fft`.
    """
    rta_code = "\r\n".join([
        "Data z_re(2049);",
        "Data z_im(2049);",
        "History r1(0.0), r2(0.0), i1(0.0), i2(0.0);",
        "History z0_re(0.0), z0_im(0.0), z1_re(0.0), z1_im(0.0);",
        "History saved_dc(0.0), has_frame(0);",
        "",
        "m = round(in3);",
        "mag = 0.0;",
        "idx = -1;",
        "if (m == 0) {",
        "    if (has_frame > 0) {",
        "        rh_n = 0.5 * r1 - 0.25 * (r2 + z0_re);",
        "        ih_n = 0.5 * i1 - 0.25 * (i2 + z0_im);",
        "        rh_p = peek(z_re, 1, 0);",
        "        ih_p = peek(z_im, 1, 0);",
        "        mag = sqrt(rh_p * rh_p + ih_p * ih_p + rh_n * rh_n + ih_n * ih_n) * (1.0 / 2048.0);",
        "        idx = 1;",
        "        dc_r = 0.5 * z0_re - 0.25 * (r1 + z1_re);",
        "        dc_i = 0.5 * z0_im - 0.25 * (i1 + z1_im);",
        "        saved_dc = sqrt(dc_r * dc_r + dc_i * dc_i) * (1.4142135623730951 / 4096.0);",
        "    }",
        "    z0_re = in1;",
        "    z0_im = in2;",
        "} else if (m == 1) {",
        "    if (has_frame > 0) {",
        "        mag = saved_dc;",
        "        idx = 0;",
        "    }",
        "    z1_re = in1;",
        "    z1_im = in2;",
        "} else if (m >= 2 && m <= 2049) {",
        "    k_st = m - 1;",
        "    rh_s = 0.5 * r1 - 0.25 * (r2 + in1);",
        "    ih_s = 0.5 * i1 - 0.25 * (i2 + in2);",
        "    poke(z_re, rh_s, k_st, 0);",
        "    poke(z_im, ih_s, k_st, 0);",
        "} else if (m >= 2050 && m <= 4095) {",
        "    k_pos = 4097 - m;",
        "    rh_n2 = 0.5 * r1 - 0.25 * (r2 + in1);",
        "    ih_n2 = 0.5 * i1 - 0.25 * (i2 + in2);",
        "    rh_p2 = peek(z_re, k_pos, 0);",
        "    ih_p2 = peek(z_im, k_pos, 0);",
        "    mag = sqrt(rh_p2 * rh_p2 + ih_p2 * ih_p2 + rh_n2 * rh_n2 + ih_n2 * ih_n2) * (1.0 / 2048.0);",
        "    idx = k_pos;",
        "    if (m == 4095) {",
        "        has_frame = 1;",
        "    }",
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
        "rect": [150.0, 150.0, 560.0, 420.0],
        "boxes": [
            make_box("obj-in1", "newobj", "in 1", patching_rect=[30.0, 20.0, 30.0, 22.0], numinlets=0, numoutlets=1, outlettype=[""]),
            make_box("obj-in2", "newobj", "in 2", patching_rect=[120.0, 20.0, 30.0, 22.0], numinlets=0, numoutlets=1, outlettype=[""]),
            make_box("obj-in3", "newobj", "in 3", patching_rect=[210.0, 20.0, 30.0, 22.0], numinlets=0, numoutlets=1, outlettype=[""]),
            make_box("obj-cb", "codebox", patching_rect=[30.0, 60.0, 480.0, 280.0], numinlets=3, numoutlets=2, outlettype=["", ""], code=rta_code),
            make_box("obj-out1", "newobj", "out 1", patching_rect=[30.0, 360.0, 36.0, 22.0], numinlets=1, numoutlets=0, outlettype=[]),
            make_box("obj-out2", "newobj", "out 2", patching_rect=[180.0, 360.0, 36.0, 22.0], numinlets=1, numoutlets=0, outlettype=[]),
        ],
        "lines": [
            make_line("obj-in1", 0, "obj-cb", 0),
            make_line("obj-in2", 0, "obj-cb", 1),
            make_line("obj-in3", 0, "obj-cb", 2),
            make_line("obj-cb", 0, "obj-out1", 0),
            make_line("obj-cb", 1, "obj-out2", 0),
        ],
    }


def build_rta_subpatcher():
    return {
        "fileversion": 1,
        "appversion": {"major": 9, "minor": 0, "revision": 0, "architecture": "x64", "modernui": 1},
        "classnamespace": "box",
        "rect": [150.0, 150.0, 420.0, 300.0],
        "boxes": [
            make_box("obj-in-l", "inlet", None, patching_rect=[30.0, 20.0, 30.0, 30.0], numinlets=0, numoutlets=1, outlettype=["signal"], index=1),
            make_box("obj-in-r", "inlet", None, patching_rect=[116.0, 20.0, 30.0, 30.0], numinlets=0, numoutlets=1, outlettype=["signal"], index=2),
            make_box("obj-in-m", "inlet", None, patching_rect=[190.0, 20.0, 30.0, 30.0], numinlets=0, numoutlets=1, outlettype=[""], index=3),
            make_box("obj-rta-fft", "newobj", "fft~ 4096 4096 0", patching_rect=[30.0, 80.0, 105.0, 22.0], numinlets=2, numoutlets=3, outlettype=["signal", "signal", "signal"]),
            make_box("obj-rta-gen", "newobj", "gen~", patching_rect=[30.0, 125.0, 105.0, 22.0], numinlets=3, numoutlets=2, outlettype=["signal", "signal"], patcher=build_rta_fft_gen_patcher()),
            make_box("obj-rta-poke", "newobj", "poke~ ---rta_fft", patching_rect=[30.0, 170.0, 105.0, 22.0], numinlets=3, numoutlets=1, outlettype=["signal"]),
        ],
        "lines": [
            make_line("obj-in-l", 0, "obj-rta-fft", 0),
            make_line("obj-in-r", 0, "obj-rta-fft", 1),
            make_line("obj-rta-fft", 0, "obj-rta-gen", 0),
            make_line("obj-rta-fft", 1, "obj-rta-gen", 1),
            make_line("obj-rta-fft", 2, "obj-rta-gen", 2),
            make_line("obj-rta-gen", 0, "obj-rta-poke", 0),
            make_line("obj-rta-gen", 1, "obj-rta-poke", 1),
        ],
    }


def make_dire_entry(ftype: str, fname: str, sz32: int, of32: int, flag: int, mdat: int = 0xE20F4145) -> bytes:
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
    payloads = [raw_json]
    dire_entries = [make_dire_entry("JSON", root_name, len(raw_json), 16, flag=0x11)]
    cur_offset = 16 + len(raw_json)

    for dep in dep_cache:
        dep_name = dep["name"]
        with open(os.path.join(out_dir, dep_name), "rb") as f:
            dep_bytes = f.read()
        payloads.append(dep_bytes)
        dire_entries.append(make_dire_entry(dep["type"], dep_name, len(dep_bytes), cur_offset, flag=0x00))
        cur_offset += len(dep_bytes)

    dlst_body = b"".join(dire_entries)
    dlst_chunk = b"dlst" + struct.pack(">I", 8 + len(dlst_body)) + dlst_body
    mxc_header = b"mx@c" + struct.pack(">III", 16, 0, cur_offset)
    ptch_payload = mxc_header + b"".join(payloads) + dlst_chunk

    ampf_body = b"ampf" + struct.pack("<I", 4) + b"aaaa"
    ampf_body += b"meta" + struct.pack("<I", 4) + b"\x00\x00\x00\x07"
    ampf_body += b"ptch" + struct.pack("<I", len(ptch_payload)) + ptch_payload
    return ampf_body


def build_device():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir_abs = out_dir.replace("\\", "/")
    svg_files = write_svg_assets(out_dir)

    boxes = []
    lines = []
    parameters = {}

    def reg_param(box_id, longname, shortname):
        parameters[box_id] = [longname, shortname, 0]

    def wire_lom(ctrl_id, msg_id, prep_str, px, py, pw=115.0, ph=22.0, is_msg=False):
        boxes.append(make_box(msg_id, "message" if is_msg else "newobj", prep_str, patching_rect=[px, py, pw, ph], numinlets=2 if is_msg else 1, numoutlets=1, outlettype=[""]))
        lines.append(make_line(ctrl_id, 0, msg_id, 0))
        lines.append(make_line(msg_id, 0, "obj-lom", 0))

    # 1. AUDIO I/O, 64-BIT GEN~ DSP, GR BUFFER & MUTE-GATED STEREO 4096-POINT FFT RTA
    boxes.append(make_box("obj-plug-in", "newobj", "plugin~ 1 2", patching_rect=[30.0, 20.0, 75.0, 22.0], numinlets=2, numoutlets=2, outlettype=["signal", "signal"]))
    boxes.append(make_box("obj-sc1-in", "newobj", "plugin~ 3 4", patching_rect=[135.0, 20.0, 75.0, 22.0], numinlets=2, numoutlets=2, outlettype=["signal", "signal"]))
    boxes.append(make_box("obj-sc2-in", "newobj", "plugin~ 5 6", patching_rect=[245.0, 20.0, 75.0, 22.0], numinlets=2, numoutlets=2, outlettype=["signal", "signal"]))
    boxes.append(make_box("obj-plug-out", "newobj", "plugout~ 1 2", patching_rect=[30.0, 440.0, 82.0, 22.0], numinlets=2, numoutlets=0, outlettype=[]))

    boxes.append(make_box("obj-gen-eq", "newobj", "gen~", patching_rect=[30.0, 220.0, 340.0, 24.0], numinlets=6, numoutlets=4, outlettype=["signal"] * 4, patcher=build_gen_patcher()))
    for src, so, di in [("obj-plug-in", 0, 0), ("obj-plug-in", 1, 1), ("obj-sc1-in", 0, 2), ("obj-sc1-in", 1, 3), ("obj-sc2-in", 0, 4), ("obj-sc2-in", 1, 5)]:
        lines.append(make_line(src, so, "obj-gen-eq", di))
    lines.append(make_line("obj-gen-eq", 0, "obj-plug-out", 0))
    lines.append(make_line("obj-gen-eq", 1, "obj-plug-out", 1))

    boxes.append(make_box("obj-gr-poke", "newobj", "poke~ ---deq_gr", patching_rect=[235.0, 265.0, 100.0, 22.0], numinlets=3, numoutlets=1, outlettype=["signal"]))
    boxes.append(make_box("obj-gr-buf", "newobj", "buffer~ ---deq_gr @samps 8", patching_rect=[235.0, 295.0, 165.0, 22.0], numinlets=1, numoutlets=2, outlettype=["float", "bang"]))
    lines.append(make_line("obj-gen-eq", 2, "obj-gr-poke", 0))
    lines.append(make_line("obj-gen-eq", 3, "obj-gr-poke", 1))

    boxes.append(make_box("obj-rta-mute", "newobj", "mute~", varname="rta_mute", patching_rect=[250.0, 405.0, 48.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    boxes.append(make_box("obj-rta-sub", "newobj", "p rta_engine", patching_rect=[140.0, 440.0, 115.0, 22.0], numinlets=3, numoutlets=0, outlettype=[], patcher=build_rta_subpatcher()))
    boxes.append(make_box("obj-rta-buf", "newobj", "buffer~ ---rta_fft @samps 2048", patching_rect=[265.0, 440.0, 185.0, 22.0], numinlets=1, numoutlets=2, outlettype=["float", "bang"]))
    lines.append(make_line("obj-gen-eq", 0, "obj-rta-sub", 0))
    lines.append(make_line("obj-gen-eq", 1, "obj-rta-sub", 1))
    lines.append(make_line("obj-rta-mute", 0, "obj-rta-sub", 2))

    boxes.append(make_box("obj-dspstate", "newobj", "dspstate~", patching_rect=[235.0, 110.0, 68.0, 22.0], numinlets=1, numoutlets=4, outlettype=["int", "float", "int", "int"]))
    boxes.append(make_box("obj-prep-srate", "newobj", "prepend set_srate", patching_rect=[235.0, 140.0, 105.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-dspstate", 1, "obj-prep-srate", 0))
    lines.append(make_line("obj-prep-srate", 0, "obj-graph", 0))

    # 2. CONTROLLER JS (`deq_eight_lom_v3.js`), PATTR STATE BLOB & `live.colors` BRIDGE
    boxes.append(make_box("obj-lom", "newobj", "js deq_eight_lom_v3.js", varname="lom_js", patching_rect=[520.0, 180.0, 185.0, 22.0], numinlets=1, numoutlets=6, outlettype=[""] * 6))
    lines.append(make_line("obj-lom", 1, "obj-gen-eq", 0))

    default_freqs_init = [30.0, 200.0, 1000.0, 5000.0, 100.0, 1000.0, 5000.0, 18000.0]
    default_types_init = [2, 3, 3, 5, 3, 3, 3, 6]
    default_on_init    = [1, 1, 1, 1, 0, 0, 0, 0]
    default_state_list = [3, 2, 0, 0, 1, 100.0, 0.0, 1, 0, 0, 0, 100.0, 0.0, 0, 100.0, 0.0]
    for b_idx in range(8):
        default_state_list.extend([default_on_init[b_idx], default_types_init[b_idx], default_freqs_init[b_idx], 0.0, 0.71, 0, 0.0, -22.0, 5.0, 110.0, 0])

    boxes.append(make_box(
        "obj-state-pattr", "newobj", "pattr eq_state @thru 2", varname="eq_state",
        patching_rect=[720.0, 145.0, 135.0, 22.0], numinlets=1, numoutlets=3, outlettype=["", "", ""],
        parameter_enable=1,
        saved_object_attributes={"annotation_name": "", "parameter_enable": 1},
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
    boxes.append(make_box("obj-prep-recall", "newobj", "prepend recall_state", patching_rect=[720.0, 175.0, 125.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-lom", 5, "obj-state-pattr", 0))
    lines.append(make_line("obj-state-pattr", 0, "obj-prep-recall", 0))
    lines.append(make_line("obj-prep-recall", 0, "obj-lom", 0))

    boxes.append(make_box("obj-thisdevice", "newobj", "live.thisdevice", patching_rect=[520.0, 95.0, 95.0, 22.0], numinlets=1, numoutlets=2, outlettype=["bang", "int"]))
    boxes.append(make_box("obj-defer-init", "newobj", "deferlow", patching_rect=[520.0, 125.0, 60.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    boxes.append(make_box("obj-init-msg", "message", "init_device", patching_rect=[520.0, 150.0, 75.0, 22.0], numinlets=2, numoutlets=1, outlettype=[""]))
    boxes.append(make_box("obj-rtabuf-msg", "message", "set_rta_buf ---rta_fft, set_gr_buf ---deq_gr", patching_rect=[330.0, 82.0, 245.0, 22.0], numinlets=2, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-thisdevice", 0, "obj-defer-init", 0))
    lines.append(make_line("obj-defer-init", 0, "obj-init-msg", 0))
    lines.append(make_line("obj-defer-init", 0, "obj-rtabuf-msg", 0))
    lines.append(make_line("obj-defer-init", 0, "obj-dspstate", 0))
    lines.append(make_line("obj-init-msg", 0, "obj-lom", 0))
    lines.append(make_line("obj-rtabuf-msg", 0, "obj-graph", 0))

    boxes.append(make_box("obj-defer-width", "newobj", "deferlow", patching_rect=[630.0, 65.0, 60.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-lom", 2, "obj-defer-width", 0))
    lines.append(make_line("obj-defer-width", 0, "obj-thisdevice", 0))

    boxes.append(make_box("obj-live-colors", "newobj", "live.colors", varname="live_colors_obj", patching_rect=[360.0, 140.0, 75.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    boxes.append(make_box("obj-lc-route", "newobj", "route bang", patching_rect=[360.0, 168.0, 75.0, 22.0], numinlets=1, numoutlets=2, outlettype=["", ""]))
    boxes.append(make_box("obj-lc-qmsg", "message", "query_theme_colors", patching_rect=[360.0, 196.0, 118.0, 22.0], numinlets=2, numoutlets=1, outlettype=[""]))
    boxes.append(make_box("obj-lc-prep", "newobj", "prepend theme_color_reply", patching_rect=[485.0, 196.0, 150.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
    lines.append(make_line("obj-live-colors", 0, "obj-lc-route", 0))
    lines.append(make_line("obj-lc-route", 0, "obj-lc-qmsg", 0))
    lines.append(make_line("obj-lc-qmsg", 0, "obj-lom", 0))
    lines.append(make_line("obj-lc-route", 1, "obj-lc-prep", 0))
    lines.append(make_line("obj-lc-prep", 0, "obj-lom", 0))

    boxes.append(make_box("obj-qmetro", "newobj", "qmetro 33 @active 1", varname="ui_qmetro", patching_rect=[30.0, 300.0, 125.0, 22.0], numinlets=2, numoutlets=1, outlettype=["bang"]))
    lines.append(make_line("obj-qmetro", 0, "obj-graph", 0))

    # 3. FAR-LEFT VERTICAL SIDECHAIN SPINE (x = 0..22)
    boxes.append(make_live_text(
        "obj-sc-expand-btn", "sc_expand_btn", "SC Drawer", "", "", 1, 0,
        patching_rect=[710.0, 15.0, 15.0, 15.0], presentation_rect=[3.0, 4.0, 15.0, 15.0],
        invisible=2, initial_enable=0, transparent_bg=True,
        off_fg_token="live_control_fg", on_fg_token="live_control_fg",
        pictures=["tri_closed.svg", "tri_open.svg"], usepicture=1, remapsvgcolors=1, usesvgviewbox=1,
        longname="Sidechain Drawer"
    ))
    boxes.append(make_panel("obj-sc-expand-ring", "sc_expand_ring", patching_rect=[690.0, 15.0, 15.0, 15.0], presentation_rect=[3.0, 4.0, 15.0, 15.0], bg_token="live_control_bg", border=1, border_token="live_control_fg", rounded=100))
    wire_lom("obj-sc-expand-btn", "obj-msg-sc-exp", "prepend toggle_sc_panel", 710.0, 36.0, 130.0, 20.0)

    boxes.append(make_live_text(
        "obj-sc-listen-btn", "sc_listen_btn", "SC Listen", "", "", 1, 0,
        patching_rect=[710.0, 62.0, 14.0, 14.0], presentation_rect=[3.5, 23.0, 14.0, 14.0],
        invisible=2, initial_enable=0, transparent_bg=True,
        off_fg_token="live_control_fg_off", on_fg_token="live_control_fg_on",
        pictures=["headphones.svg", "headphones.svg"], usepicture=1, remapsvgcolors=1, usesvgviewbox=1,
        longname="Sidechain Listen"
    ))
    boxes.append(make_panel("obj-sc-listen-bg-off", "sc_listen_bg_off", patching_rect=[690.0, 62.0, 14.0, 14.0], presentation_rect=[3.5, 23.0, 14.0, 14.0], bg_token="live_control_bg", border=0, rounded=100))
    boxes.append(make_panel("obj-sc-listen-bg-on", "sc_listen_bg_on", patching_rect=[690.0, 80.0, 14.0, 14.0], presentation_rect=[-500.0, 23.0, 14.0, 14.0], bg_token="live_lcd_control_fg_alt", border=0, rounded=100))
    wire_lom("obj-sc-listen-btn", "obj-msg-sc-lst", "prepend ui_sc_listen", 710.0, 82.0, 115.0, 20.0)

    boxes.append(make_panel("obj-sc-dot-off", "sc_dot_off", patching_rect=[690.0, 140.0, 6.5, 6.5], presentation_rect=[7.5, 151.0, 6.5, 6.5], bg_token="live_led_bg", border=0, rounded=100))
    boxes.append(make_panel("obj-sc-dot-on", "sc_dot_on", patching_rect=[702.0, 140.0, 6.5, 6.5], presentation_rect=[-500.0, 151.0, 6.5, 6.5], bg_token="live_lcd_control_fg_alt", border=0, rounded=100))
    boxes.append(make_live_line("obj-sc-spine-div", "sc_spine_div", patching_rect=[690.0, 155.0, 5.0, 100.0], presentation_rect=[21.0, 3.0, 1.0, 163.0], color_token="live_control_bg", thickness=1.0))

    # 4. LEFT INSPECTOR STRIP (x = 22..67): Freq, Gain, Q Dials
    boxes.append(make_comment("obj-lbl-freq", "lbl_freq", "Freq", patching_rect=[760.0, 4.0, 45.0, 14.0], presentation_rect=[22.0, 1.0, 45.0, 14.0], justification=1))
    boxes.append(make_live_dial("obj-freq-dial", "band_freq", "Freq", 20.0, 20000.0, 1000.0, 3, patching_rect=[760.0, 20.0, 45.0, 38.0], presentation_rect=[22.0, 13.0, 45.0, 38.0], exponent=3.6, invisible=2, initial_enable=1, longname="Band Frequency"))
    wire_lom("obj-freq-dial", "obj-msg-freq", "prepend ui_freq", 820.0, 25.0, 95.0, 22.0)

    boxes.append(make_comment("obj-lbl-gain", "lbl_gain", "Gain", patching_rect=[760.0, 64.0, 45.0, 14.0], presentation_rect=[22.0, 54.5, 45.0, 14.0], justification=1))
    boxes.append(make_live_dial("obj-gain-dial", "band_gain", "Gain", -15.0, 15.0, 0.0, 4, patching_rect=[760.0, 80.0, 45.0, 38.0], presentation_rect=[22.0, 68.0, 45.0, 38.0], custom_units="%.2f dB", triangle=1, invisible=2, initial_enable=1, longname="Band Gain"))
    wire_lom("obj-gain-dial", "obj-msg-gain", "prepend ui_gain", 820.0, 85.0, 95.0, 22.0)

    boxes.append(make_comment("obj-lbl-q", "lbl_q", "Q", patching_rect=[760.0, 124.0, 45.0, 14.0], presentation_rect=[22.0, 111.0, 45.0, 14.0], justification=1))
    boxes.append(make_live_dial("obj-q-dial", "band_q", "Q", 0.1, 18.0, 0.71, 1, patching_rect=[760.0, 140.0, 45.0, 38.0], presentation_rect=[22.0, 123.0, 45.0, 38.0], exponent=2.6, invisible=2, initial_enable=1, longname="Band Q"))
    wire_lom("obj-q-dial", "obj-msg-q", "prepend ui_q", 820.0, 145.0, 90.0, 22.0)

    # 5. CENTER EQ DISPLAY (x = 69..439, 370x132), SCALE LABELS, 8-BAND STRIP & UNIFIED BEZEL (`lcd_bezel_bg`)
    for vname, txt, lx in [("lbl_f_100", "100", 69.0 + 91.0), ("lbl_f_1k", "1k", 69.0 + 205.0), ("lbl_f_10k", "10k", 69.0 + 318.0)]:
        boxes.append(make_comment(
            f"obj-{vname}", vname, txt,
            patching_rect=[720.0, 345.0, 26.0, 13.0], presentation_rect=[lx, 118.0, 26.0, 13.0],
            color_token="live_display_scale_text", fontname="Ableton Sans Medium",
            fontsize=9.0, justification=1, fontface=0, ignoreclick=1
        ))

    for vname, txt, ly in [("lbl_db_12", "12", 6.5), ("lbl_db_6", "6", 33.0), ("lbl_db_0", "0", 59.5), ("lbl_db_m6", "-6", 86.0), ("lbl_db_m12", "-12", 112.5)]:
        boxes.append(make_comment(
            f"obj-{vname}", vname, txt,
            patching_rect=[760.0, 345.0, 17.5, 12.0], presentation_rect=[70.0, ly, 17.5, 12.0],
            color_token="live_display_scale_text", fontname="Ableton Sans Medium",
            fontsize=9.0, justification=2, fontface=0, ignoreclick=1
        ))

    boxes.append(make_box("obj-graph", "jsui", varname="eq_graph", filename="deq_eight_ui_v3.js", patching_rect=[720.0, 220.0, 370.0, 132.0], presentation_rect=[69.0, 0.0, 370.0, 132.0], numinlets=1, numoutlets=1, outlettype=[""], border=0))
    lines.append(make_line("obj-graph", 0, "obj-lom", 0))
    lines.append(make_line("obj-lom", 0, "obj-graph", 0))

    filter_names = ["Low Cut 48", "Low Cut 12", "Low Shelf", "Bell", "Notch", "High Shelf", "High Cut 12", "High Cut 48"]
    filter_pics  = ["eq8_lc48.svg", "eq8_lc12.svg", "eq8_lshelf.svg", "eq8_bell.svg", "eq8_notch.svg", "eq8_hshelf.svg", "eq8_hc12.svg", "eq8_hc48.svg"]
    slot_w = 372.0 / 8.0
    band_bg_panels = []

    for c in range(8):
        cx0 = 69.0 + round(c * slot_w)
        cx1 = (69.0 + 370.0) if (c == 7) else (69.0 + round((c + 1) * slot_w - 2.0))
        cw = cx1 - cx0
        ddx = cx0 + 2.0
        ddw = cw - 4.0
        bx_patch = 520.0 + c * 115.0

        boxes.append(make_live_menu(
            f"obj-btype-menu-{c}", f"band_type_menu_{c}", f"B{c+1} Type",
            filter_names, default_types_init[c],
            patching_rect=[bx_patch, 468.0, ddw, 15.5], presentation_rect=[ddx, 134.5, ddw, 15.5],
            pictures=filter_pics, invisible=2, initial_enable=0, longname=f"Band {c+1} Filter Type"
        ))
        wire_lom(f"obj-btype-menu-{c}", f"obj-msg-btype-{c}", f"prepend ui_band_type {c}", bx_patch, 442.0, 115.0, 20.0)

        boxes.append(make_live_text(
            f"obj-bon-btn-{c}", f"band_on_btn_{c}", f"B{c+1} On", "", "", 1, default_on_init[c],
            patching_rect=[bx_patch, 495.0, 13.0, 13.0], presentation_rect=[ddx, 152.5, 13.0, 13.0],
            on_token="live_lcd_control_fg_alt", invisible=2, initial_enable=0, longname=f"Band {c+1} On",
            saved_attribute_attributes={
                "bgcolor": tc("live_control_bg"),
                "activebgcolor": tc("live_control_bg"),
                "bgoncolor": tc("live_lcd_control_fg_alt"),
                "activebgoncolor": tc("live_lcd_control_fg_alt"),
                "bordercolor": tc("live_contrast_frame"),
            }
        ))
        wire_lom(f"obj-bon-btn-{c}", f"obj-msg-bon-{c}", f"prepend ui_band_on {c}", bx_patch, 515.0, 105.0, 20.0)

        boxes.append(make_box(
            f"obj-bsel-btn-{c}", "live.text", text=str(c + 1), varname=f"band_sel_btn_{c}",
            patching_rect=[bx_patch, 540.0, 15.0, 14.0], presentation_rect=[cx0 + 15.0, 151.5, 15.0, 14.0],
            numinlets=1, numoutlets=2, outlettype=["", ""], parameter_enable=0, mode=0, texton=str(c + 1),
            fontname="Ableton Sans Small Bold", fontsize=10.5, fontface=1, border=0,
            bgcolor=TRANSPARENT, activebgcolor=TRANSPARENT, bgoncolor=TRANSPARENT, activebgoncolor=TRANSPARENT,
            bordercolor=TRANSPARENT, focusbordercolor=TRANSPARENT,
            textcolor=[0.827, 0.804, 0.843, 1.0], activefgcolor=[0.827, 0.804, 0.843, 1.0],
            saved_attribute_attributes={"textcolor": tc("live_control_fg"), "activefgcolor": tc("live_control_fg")}
        ))
        wire_lom(f"obj-bsel-btn-{c}", f"obj-msg-bsel-{c}", f"ui_band_sel {c}", bx_patch, 560.0, 85.0, 20.0, is_msg=True)

        dcx = ddx + ddw - 13.0
        boxes.append(make_live_text(
            f"obj-bdyn-btn-{c}", f"band_dyn_btn_{c}", f"B{c+1} Dyn", "", "", 1, 0,
            patching_rect=[bx_patch, 585.0, 13.0, 13.0], presentation_rect=[dcx, 152.5, 13.0, 13.0],
            invisible=2, initial_enable=0, transparent_bg=True,
            off_fg_token="live_lcd_frame", on_fg_token="live_lcd_control_fg_alt",
            pictures=["dyn_ring.svg", "dyn_ring.svg"], usepicture=1, remapsvgcolors=1, usesvgviewbox=1,
            longname=f"Band {c+1} Dynamics"
        ))
        wire_lom(f"obj-bdyn-btn-{c}", f"obj-msg-bdyn-{c}", f"click_band_dyn_dot {c}", bx_patch, 605.0, 110.0, 20.0, is_msg=True)

        band_bg_panels.append(make_panel(
            f"obj-bcard-bg-{c}", f"band_card_bg_{c}",
            patching_rect=[bx_patch, 650.0, cw, 33.0],
            presentation_rect=[-500.0 if (c == 2) else cx0, 134.0, cw, 33.0],
            bg_token="live_surface_bg"
        ))

    boxes.append(make_panel("obj-dyn-ring-fill", "dyn_ring_fill", patching_rect=[500.0, 585.0, 9.0, 9.0], presentation_rect=[-500.0, 154.5, 9.0, 9.0], bg_token="live_lcd_control_fg_alt", border=0, rounded=100, ignoreclick=1))
    boxes.extend(band_bg_panels)
    boxes.append(make_panel("obj-lcd-bezel-bg", "lcd_bezel_bg", patching_rect=[520.0, 690.0, 374.0, 169.0], presentation_rect=[67.0, 0.0, 374.0, 169.0], bg_token="live_lcd_frame"))

    # 6. RIGHT STRIP (x = 441..495): Solo [🎧], RTA [7-Bar], Adapt. Q, Scale, Output Gain
    boxes.append(make_live_text(
        "obj-solo-btn", "solo_btn", "Solo", "", "", 1, 0,
        patching_rect=[1060.0, 20.0, 22.0, 15.0], presentation_rect=[444.0, 4.0, 22.0, 15.0],
        on_token="live_lcd_control_fg_alt", invisible=2, initial_enable=0,
        pictures=["headphones.svg", "headphones.svg"], usepicture=1, remapsvgcolors=1, usesvgviewbox=1,
        longname="Band Solo"
    ))
    wire_lom("obj-solo-btn", "obj-msg-solo", "prepend ui_solo", 1140.0, 20.0, 95.0, 20.0)

    boxes.append(make_live_text(
        "obj-rta-btn", "rta_btn", "RTA", "", "", 1, 1,
        patching_rect=[1090.0, 20.0, 22.0, 15.0], presentation_rect=[469.0, 4.0, 22.0, 15.0],
        on_token="live_display_handle_one", invisible=2, initial_enable=0,
        pictures=["rta_bars.svg", "rta_bars.svg"], usepicture=1, remapsvgcolors=1, usesvgviewbox=1,
        longname="Spectrum Analyzer"
    ))
    wire_lom("obj-rta-btn", "obj-msg-rta", "prepend ui_rta_on", 1140.0, 45.0, 105.0, 20.0)

    boxes.append(make_comment("obj-lbl-adaptq", "lbl_adaptq", "Adapt. Q", patching_rect=[1060.0, 90.0, 52.0, 14.0], presentation_rect=[441.5, 71.0, 52.0, 14.0]))
    boxes.append(make_live_text("obj-adaptq", "adapt_q_btn", "Adapt. Q", "Off", "On", 1, 1, patching_rect=[1060.0, 106.0, 47.0, 16.0], presentation_rect=[444.0, 85.0, 47.0, 16.0], longname="Adaptive Q"))
    reg_param("obj-adaptq", "Adaptive Q", "Adapt. Q")
    wire_lom("obj-adaptq", "obj-msg-adaptq", "prepend ui_adapt_q", 1140.0, 106.0, 115.0, 22.0)

    boxes.append(make_comment("obj-lbl-scale", "lbl_scale", "Scale", patching_rect=[1060.0, 135.0, 52.0, 14.0], presentation_rect=[441.5, 103.0, 52.0, 14.0]))
    boxes.append(make_live_numbox("obj-dynscale", "dyn_scale", "Scale", 0.0, 200.0, 100.0, 5, patching_rect=[1060.0, 152.0, 47.0, 16.0], presentation_rect=[444.0, 117.0, 47.0, 16.0], param_type=0, appearance=2, longname="Scale"))
    reg_param("obj-dynscale", "Scale", "Scale")
    wire_lom("obj-dynscale", "obj-msg-scale", "prepend ui_dyn_scale", 1140.0, 152.0, 125.0, 22.0)

    boxes.append(make_comment("obj-lbl-outgain", "lbl_outgain", "Gain", patching_rect=[1060.0, 180.0, 52.0, 14.0], presentation_rect=[441.5, 135.0, 52.0, 14.0]))
    boxes.append(make_live_numbox("obj-outgain", "out_gain", "Gain", -24.0, 24.0, 0.0, 4, patching_rect=[1060.0, 196.0, 47.0, 16.0], presentation_rect=[444.0, 149.0, 47.0, 16.0], custom_units="%.2f dB", appearance=2, longname="Output Gain"))
    reg_param("obj-outgain", "Output Gain", "Gain")
    wire_lom("obj-outgain", "obj-msg-outgain", "prepend ui_out_gain", 1140.0, 196.0, 120.0, 22.0)

    # 7. LEFT EXPANDABLE 2-COLUMN SIDECHAIN PANEL (+154px)
    boxes.append(make_live_line("obj-sc-col-div", "sc_col_div", patching_rect=[1325.0, 5.0, 5.0, 160.0], presentation_rect=[-500.0, 3.0, 1.0, 163.0], color_token="live_control_bg", thickness=1.0))
    boxes.append(make_live_line("obj-sc-right-div", "sc_right_div", patching_rect=[1335.0, 5.0, 5.0, 169.0], presentation_rect=[-500.0, 0.0, 2.0, 169.0], color_token="live_lcd_frame", thickness=2.0))

    for idx_sc, (tag, ltr, px0, out_idx) in enumerate([("1", "a", 1320.0, 3), ("2", "b", 1550.0, 4)]):
        U = ltr.upper()
        boxes.append(make_live_text(f"obj-sc-{ltr}-btn", f"sc_{ltr}_btn", f"Ext. {U}", f"Ext. {U}", f"Ext. {U}", 1, 0, patching_rect=[px0, 20.0, 68.0, 15.0], presentation_rect=[-500.0, 4.0, 68.0, 15.0], on_token="live_lcd_control_fg_alt", longname=f"Sidechain {U} On"))
        reg_param(f"obj-sc-{ltr}-btn", f"Sidechain {U} On", f"Ext. {U}")
        wire_lom(f"obj-sc-{ltr}-btn", f"obj-msg-sc{ltr}", f"prepend ui_sc_{ltr}_en", px0, 42.0, 110.0, 22.0)

        boxes.append(make_comment(f"obj-lbl-src{ltr}", f"lbl_src_{ltr}", "Source", patching_rect=[px0, 68.0, 68.0, 14.0], presentation_rect=[-500.0, 23.0, 68.0, 14.0]))
        boxes.append(make_umenu(f"obj-sc{tag}-track", f"sc{tag}_track_menu", ["No Input"], patching_rect=[px0, 86.0, 68.0, 16.0], presentation_rect=[-500.0, 37.0, 68.0, 16.0]))
        boxes.append(make_umenu(f"obj-sc{tag}-chan", f"sc{tag}_chan_menu", ["Pre FX", "Post FX", "Post Mixer"], patching_rect=[px0, 108.0, 68.0, 16.0], presentation_rect=[-500.0, 56.0, 68.0, 16.0]))
        wire_lom(f"obj-sc{tag}-track", f"obj-msg-sc{tag}t", f"prepend set_sc{tag}_track", px0 + 90.0, 86.0, 130.0, 22.0)
        wire_lom(f"obj-sc{tag}-chan", f"obj-msg-sc{tag}c", f"prepend set_sc{tag}_chan", px0 + 90.0, 108.0, 130.0, 22.0)

        boxes.append(make_comment(f"obj-lbl-mix{ltr}", f"lbl_mix_{ltr}", "Mix", patching_rect=[px0, 130.0, 68.0, 14.0], presentation_rect=[-500.0, 82.0, 68.0, 14.0]))
        boxes.append(make_live_numbox(f"obj-sc{tag}-mix", f"sc{tag}_mix", f"SC {U} Mix", 0.0, 100.0, 100.0, 5, patching_rect=[px0, 146.0, 68.0, 16.0], presentation_rect=[-500.0, 96.0, 68.0, 16.0], param_type=0, appearance=2, longname=f"Sidechain {U} Mix"))
        reg_param(f"obj-sc{tag}-mix", f"Sidechain {U} Mix", f"SC {U} Mix")
        wire_lom(f"obj-sc{tag}-mix", f"obj-msg-sc{tag}m", f"prepend ui_sc{tag}_mix", px0 + 90.0, 146.0, 115.0, 22.0)

        boxes.append(make_comment(f"obj-lbl-sc{tag}g", f"lbl_sc{tag}_gain", "SC Gain", patching_rect=[px0, 168.0, 68.0, 14.0], presentation_rect=[-500.0, 122.0, 68.0, 14.0]))
        boxes.append(make_live_numbox(f"obj-sc{tag}-gain", f"sc{tag}_gain", f"SC {U} Gain", -24.0, 24.0, 0.0, 4, patching_rect=[px0, 184.0, 68.0, 16.0], presentation_rect=[-500.0, 136.0, 68.0, 16.0], custom_units="%.2f dB", appearance=2, longname=f"Sidechain {U} Gain"))
        reg_param(f"obj-sc{tag}-gain", f"Sidechain {U} Gain", f"SC {U} Gain")
        wire_lom(f"obj-sc{tag}-gain", f"obj-msg-sc{tag}g", f"prepend ui_sc{tag}_gain", px0 + 90.0, 184.0, 120.0, 22.0)

        rx0 = 1320.0 + idx_sc * 300.0
        rt_id = f"obj-routing-{tag}"
        boxes.append(make_box(rt_id, "newobj", "live.routing", patching_rect=[rx0, 250.0, 140.0, 22.0], numinlets=1, numoutlets=5, outlettype=[""] * 5))
        lines.append(make_line("obj-lom", out_idx, rt_id, 0))
        for ro, rname, rpx, rpy in [
            (0, f"rt{tag}_cur_type", rx0, 280.0),
            (1, f"rt{tag}_cur_chan", rx0 + 145.0, 280.0),
            (2, f"rt{tag}_types", rx0, 310.0),
            (3, f"rt{tag}_chans", rx0 + 145.0, 310.0),
        ]:
            rid = f"obj-{rname.replace('_', '-')}"
            boxes.append(make_box(rid, "newobj", f"prepend {rname}", patching_rect=[rpx, rpy, 135.0, 22.0], numinlets=1, numoutlets=1, outlettype=[""]))
            lines.append(make_line(rt_id, ro, rid, 0))
            lines.append(make_line(rid, 0, "obj-lom", 0))

    # 8. RIGHT EXPANDABLE PER-BAND DYNAMIC PANEL (+78px)
    boxes.append(make_live_line("obj-div-right-dyn", "div_right_dyn", patching_rect=[1800.0, 20.0, 5.0, 169.0], presentation_rect=[-500.0, 0.0, 2.0, 169.0], color_token="live_lcd_frame", thickness=2.0))
    boxes.append(make_live_text("obj-band-dyn-on", "band_dyn_on", "Dyn On", "Off", "On", 1, 0, patching_rect=[1820.0, 20.0, 68.0, 15.0], presentation_rect=[-500.0, 4.0, 68.0, 15.0], on_token="live_lcd_control_fg_alt", invisible=2, initial_enable=0, longname="Band Dynamics On"))
    wire_lom("obj-band-dyn-on", "obj-msg-dynon", "prepend ui_dyn_on", 1970.0, 20.0, 110.0, 22.0)

    boxes.append(make_live_tab("obj-src-tab", "band_source", "Source", ["Int", "SC A", "SC B"], 0, patching_rect=[1820.0, 45.0, 68.0, 15.0], presentation_rect=[-500.0, 21.0, 68.0, 15.0], fontsize=9.5, invisible=2, initial_enable=0, longname="Band Sidechain Source"))
    wire_lom("obj-src-tab", "obj-msg-source", "prepend ui_source", 1970.0, 45.0, 110.0, 22.0)

    boxes.append(make_comment("obj-lbl-range", "lbl_range", "Dyn Range", patching_rect=[1820.0, 70.0, 68.0, 14.0], presentation_rect=[-500.0, 39.0, 68.0, 14.0]))
    boxes.append(make_live_numbox("obj-dyndepth", "band_dyndepth", "Dyn Range", -15.0, 15.0, 0.0, 4, patching_rect=[1890.0, 70.0, 68.0, 16.0], presentation_rect=[-500.0, 53.0, 68.0, 16.0], custom_units="%.2f dB", appearance=2, invisible=2, initial_enable=1, longname="Dynamic Range"))
    wire_lom("obj-dyndepth", "obj-msg-dyndepth", "prepend ui_dyndepth", 1970.0, 70.0, 125.0, 22.0)

    boxes.append(make_comment("obj-lbl-thresh", "lbl_thresh", "Threshold", patching_rect=[1820.0, 95.0, 68.0, 14.0], presentation_rect=[-500.0, 71.0, 68.0, 14.0]))
    boxes.append(make_live_numbox("obj-thresh", "band_thresh", "Threshold", -60.0, 0.0, -22.0, 4, patching_rect=[1890.0, 95.0, 68.0, 16.0], presentation_rect=[-500.0, 85.0, 68.0, 16.0], custom_units="%.2f dB", appearance=2, invisible=2, initial_enable=1, longname="Threshold"))
    wire_lom("obj-thresh", "obj-msg-thresh", "prepend ui_thresh", 1970.0, 95.0, 110.0, 22.0)

    boxes.append(make_comment("obj-lbl-attack", "lbl_attack", "Attack", patching_rect=[1820.0, 120.0, 68.0, 14.0], presentation_rect=[-500.0, 103.0, 68.0, 14.0]))
    boxes.append(make_live_numbox("obj-attack", "band_attack", "Attack", 0.1, 250.0, 5.0, 2, patching_rect=[1890.0, 120.0, 68.0, 16.0], presentation_rect=[-500.0, 117.0, 68.0, 16.0], exponent=2.2, appearance=2, invisible=2, initial_enable=1, longname="Attack"))
    wire_lom("obj-attack", "obj-msg-attack", "prepend ui_attack", 1970.0, 120.0, 110.0, 22.0)

    boxes.append(make_comment("obj-lbl-release", "lbl_release", "Release", patching_rect=[1820.0, 145.0, 68.0, 14.0], presentation_rect=[-500.0, 135.0, 68.0, 14.0]))
    boxes.append(make_live_numbox("obj-release", "band_release", "Release", 5.0, 1000.0, 110.0, 2, patching_rect=[1890.0, 145.0, 68.0, 16.0], presentation_rect=[-500.0, 149.0, 68.0, 16.0], exponent=2.2, appearance=2, invisible=2, initial_enable=1, longname="Release"))
    wire_lom("obj-release", "obj-msg-release", "prepend ui_release", 1970.0, 145.0, 115.0, 22.0)

    # 9. BACKMOST Z-LAYER: FULL-DEVICE ABLETON SURFACE PANEL (`live_surface_bg`)
    boxes.append(make_panel("obj-bg-surface", "bg_surface", patching_rect=[30.0, 740.0, 775.0, 169.0], presentation_rect=[0.0, 0.0, 495.0, 169.0], bg_token="live_surface_bg"))

    # 10. ASSEMBLE PATCHER & WRITE `dEQ Eight v3 dev.amxd` + FROZEN `dEQ Eight Alpha v0.04.amxd`
    dep_cache = [
        {"name": "deq_eight_lom_v3.js", "bootpath": out_dir_abs, "type": "TEXT", "implicit": 1},
        {"name": "deq_eight_ui_v3.js", "bootpath": out_dir_abs, "type": "TEXT", "implicit": 1},
    ]
    for svg_name in svg_files:
        dep_cache.append({"name": svg_name, "bootpath": out_dir_abs, "type": "svg", "implicit": 1})

    patcher = {
        "fileversion": 1,
        "appversion": {"major": 9, "minor": 0, "revision": 0, "architecture": "x64", "modernui": 1},
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

    dev_path = os.path.join(out_dir, "dEQ Eight v3 dev.amxd")
    with open(dev_path, "wb") as f:
        f.write(ampf_body)
    print(f"Successfully generated {dev_path} ({len(ampf_body)} bytes)")
    print(f"Total boxes: {len(boxes)}, Total lines: {len(lines)}, Total parameters: {len(parameters)}")

    frozen_name = "dEQ Eight Alpha v0.04.amxd"
    frozen_bytes = build_frozen_amxd(root_name=frozen_name, raw_json=raw_json, out_dir=out_dir, dep_cache=dep_cache)
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

    zip_path = os.path.join(release_dir, "dEQ_Eight_Alpha_v0.04.zip")
    readme_txt = (
        "dEQ Eight — Alpha v0.04 (OpenAir / macchinette)\n"
        "===============================================\n\n"
        "Installation:\n"
        "1. `dEQ Eight Alpha v0.04.amxd` is a self-contained frozen Max for Live device.\n"
        "2. Drag and drop `dEQ Eight Alpha v0.04.amxd` directly onto any audio/instrument track\n"
        "   in Ableton Live 11 or 12, or place it in your User Library.\n\n"
        "What's New in Alpha v0.04 (v3 UI & RTA Overhaul):\n"
        "- Pixel-Matched EQ Eight SVG Filter Icons: Full-bleed `24x9` left-aligned curves (`usesvgviewbox=1`),\n"
        "  authentic hexagonal 45-degree Bell, full-height Y-fork Shelves, curved Notch, `x4` Low Cut 48,\n"
        "  `4x` High Cut 48, compact Headphones, and 7-bar Spectrum toggle.\n"
        "- Native Ableton Theme & Zombie States: Ice-blue open dropdown highlight (`live_lcd_control_fg`),\n"
        "  unified flat `live_lcd_frame` bezel, zombie `0 dB` curve (`#837a8f`) when all 8 bands are off,\n"
        "  zombie dial arcs when selected band is inactive, and disabled `Gain` dial on Cut/Notch shapes.\n"
        "- Phase-Immune Stereo 4096-Point FFT RTA: Complex `L + jR` stereo power spectrum (`370` 1px points,\n"
        "  DC bin `0` sub-bass accuracy, solid `1.0` opacity `#595169`, zero wide-stereo cancellation).\n"
    )
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"dEQ_Eight_Alpha_v0.04/{frozen_name}", frozen_bytes)
        zf.writestr("dEQ_Eight_Alpha_v0.04/README.txt", readme_txt.encode("utf-8"))
    print(f"Successfully packaged release archive: {zip_path}")


if __name__ == "__main__":
    build_device()


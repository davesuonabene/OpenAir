"""
build_dynamic_eq.py
Builds the standalone Dynamic_EQ.amxd Max for Live device with:
- 64-Bit gen~ Cytomic Zero-Delay Feedback (ZDF) Trapezoidal SVF + Nyquist-Decramped DSP Core
  + 16-Band Real-Time RTA Spectrum Analyzer
- Far-Left Vertical Sidechain Strip (dynamic_eq_sc_bar.js, 22px x 159px):
    * Circular (▶) Expand button, Circular (🎧) SC Listen button, rotated vertical "Sidechain" label & status dot
- Left Expandable 2-Column Native Ableton Sidechain Panel (+156px via live.thisdevice setwidth):
    * Column 1 (Ext. A): [Ext. A] toggle, Source, Track chooser, Channel chooser, Mix %, SC Gain dB
    * Column 2 (Ext. B): [Ext. B] toggle, Source, Track chooser, Channel chooser, Mix %, SC Gain dB
- Authentic Ableton EQ Eight Clone Base Canvas (450px x 169px):
    * Left Strip: Full-height Freq (y=4), Gain (y=58), Q (y=112) Dials matching EQ Eight
    * Center Display (dynamic_eq_ui.js): EQ Eight Graph + Lavender RTA + 8 Raised Band Cards with Filter Dropdowns
    * Right Strip: Wide Vector [🎧 | ılı.] Top Icons (dynamic_eq_top_icons.js), [DYN >], Adapt. Q, Scale %, Gain dB
- Right Expandable Per-Band Dynamic Panel (+136px via live.thisdevice setwidth):
    * Streamlined Per-Band Dynamic Setup ONLY: Dyn ON/OFF, Source [Int | SC A | SC B], Dyn Range, Thresh, Attack, Release
"""

import json
import os
import struct


def make_box(box_id, maxclass, text="", varname="", patching_rect=None, presentation_rect=None, **kwargs):
    if patching_rect is None:
        patching_rect = [0.0, 0.0, 80.0, 20.0]
    box = {
        "id": box_id,
        "maxclass": maxclass,
        "patching_rect": patching_rect,
    }
    if text:
        box["text"] = text
    if varname:
        box["varname"] = varname
    if presentation_rect is not None:
        box["presentation"] = 1
        box["presentation_rect"] = presentation_rect
    for k, v in kwargs.items():
        box[k] = v
    return {"box": box}


def make_live_tab(box_id, varname, shortname, items, initial_idx, patching_rect, presentation_rect, **kwargs):
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
        bgcolor=[0.106, 0.094, 0.129, 1.0],
        bgoncolor=[1.0, 0.569, 0.765, 1.0],
        activebgoncolor=[1.0, 0.569, 0.765, 1.0],
        bordercolor=[0.067, 0.063, 0.086, 1.0],
        textcolor=[0.827, 0.804, 0.843, 1.0],
        textoncolor=[0.08, 0.07, 0.10, 1.0],
        parameter_enable=1,
        saved_attribute_attributes={
            "valueof": {
                "parameter_enum": items,
                "parameter_initial": [initial_idx],
                "parameter_initial_enable": 1,
                "parameter_longname": varname,
                "parameter_mmax": len(items) - 1,
                "parameter_modmode": 0,
                "parameter_shortname": shortname,
                "parameter_type": 2,
                "parameter_unitstyle": 9,
            }
        },
        **kwargs,
    )


def make_live_text(box_id, varname, shortname, text_off, text_on, mode, initial_val, patching_rect, presentation_rect, **kwargs):
    return make_box(
        box_id,
        "live.text",
        varname=varname,
        patching_rect=patching_rect,
        presentation_rect=presentation_rect,
        numinlets=1,
        numoutlets=2,
        outlettype=["", ""],
        mode=mode,
        text=text_off,
        texton=text_on,
        bgcolor=[0.106, 0.094, 0.129, 1.0],
        bgoncolor=[1.0, 0.569, 0.765, 1.0],
        activebgoncolor=[1.0, 0.569, 0.765, 1.0],
        bordercolor=[0.067, 0.063, 0.086, 1.0],
        textcolor=[0.827, 0.804, 0.843, 1.0],
        textoncolor=[0.08, 0.07, 0.10, 1.0],
        parameter_enable=1,
        saved_attribute_attributes={
            "valueof": {
                "parameter_enum": [text_off, text_on],
                "parameter_initial": [initial_val],
                "parameter_initial_enable": 1,
                "parameter_longname": varname,
                "parameter_mmax": 1,
                "parameter_modmode": 0,
                "parameter_shortname": shortname,
                "parameter_type": 2,
            }
        },
        **kwargs,
    )


def make_live_numbox(box_id, varname, shortname, mmin, mmax, initial_val, unitstyle, patching_rect, presentation_rect, **kwargs):
    defaults = {
        "appearance": 2,
        "activebgcolor": [0.106, 0.094, 0.129, 1.0],
        "activeslidercolor": [0.0, 0.518, 0.576, 1.0],
        "bordercolor": [0.067, 0.063, 0.086, 1.0],
        "textcolor": [0.827, 0.804, 0.843, 1.0],
    }
    defaults.update(kwargs)
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
            "valueof": {
                "parameter_initial": [initial_val],
                "parameter_initial_enable": 1,
                "parameter_longname": varname,
                "parameter_mmin": float(mmin),
                "parameter_mmax": float(mmax),
                "parameter_modmode": 3,
                "parameter_shortname": shortname,
                "parameter_type": 0,
                "parameter_unitstyle": unitstyle,
            }
        },
        **defaults,
    )


def make_live_dial(box_id, varname, shortname, mmin, mmax, initial_val, unitstyle, patching_rect, presentation_rect, **kwargs):
    defaults = {
        "activedialcolor": [0.278, 0.886, 0.957, 1.0],
        "dialcolor": [0.106, 0.094, 0.129, 1.0],
        "textcolor": [0.827, 0.804, 0.843, 1.0],
    }
    defaults.update(kwargs)
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
            "valueof": {
                "parameter_initial": [initial_val],
                "parameter_initial_enable": 1,
                "parameter_longname": varname,
                "parameter_mmin": float(mmin),
                "parameter_mmax": float(mmax),
                "parameter_modmode": 3,
                "parameter_shortname": shortname,
                "parameter_type": 0,
                "parameter_unitstyle": unitstyle,
            }
        },
        **defaults,
    )


def make_umenu(box_id, varname, items, patching_rect, presentation_rect, **kwargs):
    return make_box(
        box_id,
        "umenu",
        varname=varname,
        patching_rect=patching_rect,
        presentation_rect=presentation_rect,
        numinlets=1,
        numoutlets=3,
        outlettype=["int", "", ""],
        items=items,
        bgcolor=[0.106, 0.094, 0.129, 1.0],
        textcolor=[0.827, 0.804, 0.843, 1.0],
        fontname="Ableton Sans Medium",
        fontsize=9.5,
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
    Generates the 64-bit GenExpr codebox for:
    1. 8-Band Cytomic ZDF Trapezoidal SVF + Nyquist-Decramped Dynamic EQ Engine (Outlets 1..2 audio, 3..10 dG_1..8)
       - 100% v0-verified GenExpr syntax.
       - Inactive bands (b_on == 0) are completely bypassed.
       - Sidechain detector & envelope follower (exp/log10) are bypassed when b_dyn_on == 0.
    2. 16-Band High-Q (Q=5.0, k=0.20) Real-Time RTA Spectrum Analyzer on Post-EQ Output (Outlets 11..26)
       - Outputs linear envelope (0 log10 calls in gen~; dB conversion runs at 20Hz in JS).
    """
    default_freqs = [30.0, 200.0, 1000.0, 5000.0, 100.0, 1000.0, 5000.0, 18000.0]
    default_types = [1, 3, 3, 5, 3, 3, 3, 6]
    default_on    = [1, 1, 1, 1, 0, 0, 0, 0]
    rta_freqs     = [25.0, 40.0, 63.0, 100.0, 160.0, 250.0, 400.0, 630.0, 1000.0, 1600.0, 2500.0, 4000.0, 6300.0, 10000.0, 14000.0, 18000.0]

    code = [
        "// ============================================================================",
        "// OpenAir Dynamic EQ Eight - 64-Bit Cytomic ZDF Trapezoidal SVF + 16-Band RTA",
        "// Algorithm 0 (Active): Zero-Latency Nyquist-Decramped TPT State Variable Filter",
        "// Architecture Hook: Future Natural Phase & Linear Phase modes branch below.",
        "// ============================================================================",
        "",
        "Param adapt_q(1);",
        "Param dyn_scale(1.0);",
        "Param out_gain(0.0);",
        "Param solo_band(0);",
        "Param sc1_mix(1.0);",
        "Param sc2_mix(1.0);",
        "Param rta_active(1);",
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
            f"Param b{b}_thresh(-18.0);",
            f"Param b{b}_attack(5.0);",
            f"Param b{b}_release(80.0);",
            f"Param b{b}_source(0);",
            f"History det_ic1_{b}(0.0), det_ic2_{b}(0.0);",
            f"History env_{b}(0.0), mod_db_{b}(0.0);",
            f"History s1L_ic1_{b}(0.0), s1L_ic2_{b}(0.0), s1R_ic1_{b}(0.0), s1R_ic2_{b}(0.0);",
            f"History s2L_ic1_{b}(0.0), s2L_ic2_{b}(0.0), s2R_ic1_{b}(0.0), s2R_ic2_{b}(0.0);",
        ])

    for r in range(1, 17):
        code.append(f"History rta_ic1_{r}(0.0), rta_ic2_{r}(0.0), rta_env_{r}(0.0);")

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
            f"        targ_mod_{b} = (b{b}_on > 0.5 && b{b}_dyn_on > 0.5) ? (ratio_{b} * b{b}_dyn_range) : 0.0;",
            f"        mod_db_{b} = 0.992 * mod_db_{b} + 0.008 * targ_mod_{b};",
            f"    }} else {{",
            f"        mod_db_{b} = 0.0;",
            f"    }}",
            f"    if (b{b}_on > 0.5) {{",
            f"        t_type_{b} = round(b{b}_type);",
            f"        tot_db_{b} = (b{b}_gain + mod_db_{b}) * dyn_scale;",
            f"        q_prop_{b} = (adapt_q > 0.5 && (t_type_{b} == 2 || t_type_{b} == 3 || t_type_{b} == 5)) ? (b{b}_q * pow(2.0, abs(tot_db_{b}) / 18.0)) : b{b}_q;",
            f"        q_eff_{b} = clip(q_prop_{b} * max(0.35, cos(w0_{b} * 0.5)), 0.1, 24.0);",
            f"        k0_{b} = 1.0 / q_eff_{b};",
            f"        A_{b} = pow(10.0, tot_db_{b} / 40.0);",
            f"        g_{b} = g0_{b};",
            f"        k_{b} = k0_{b};",
            f"        m0_{b} = 1.0;",
            f"        m1_{b} = 0.0;",
            f"        m2_{b} = 0.0;",
            f"        if (t_type_{b} == 3) {{",
            f"            k_{b} = k0_{b} / A_{b};",
            f"            m0_{b} = 1.0;",
            f"            m1_{b} = k_{b} * (A_{b} * A_{b} - 1.0);",
            f"            m2_{b} = 0.0;",
            f"        }} else if (t_type_{b} == 2) {{",
            f"            g_{b} = g0_{b} / sqrt(A_{b});",
            f"            k_{b} = k0_{b};",
            f"            m0_{b} = 1.0;",
            f"            m1_{b} = k_{b} * (A_{b} - 1.0);",
            f"            m2_{b} = A_{b} * A_{b} - 1.0;",
            f"        }} else if (t_type_{b} == 5) {{",
            f"            g_{b} = g0_{b} * sqrt(A_{b});",
            f"            k_{b} = k0_{b};",
            f"            m0_{b} = A_{b} * A_{b};",
            f"            m1_{b} = k_{b} * (1.0 - A_{b}) * A_{b};",
            f"            m2_{b} = 1.0 - A_{b} * A_{b};",
            f"        }} else if (t_type_{b} == 1 || t_type_{b} == 0) {{",
            f"            m0_{b} = 1.0;",
            f"            m1_{b} = -k0_{b};",
            f"            m2_{b} = -1.0;",
            f"        }} else if (t_type_{b} == 6 || t_type_{b} == 7) {{",
            f"            m0_{b} = 0.0;",
            f"            m1_{b} = 0.0;",
            f"            m2_{b} = 1.0;",
            f"        }} else if (t_type_{b} == 4) {{",
            f"            m0_{b} = 1.0;",
            f"            m1_{b} = -k0_{b};",
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
            f"        if (t_type_{b} == 0 || t_type_{b} == 7) {{",
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
            f"    if (round(solo_band) == {b}) {{",
            f"        soloL = bp_sig_{b};",
            f"        soloR = bp_sig_{b};",
            f"    }}",
            f"}} else {{",
            f"    mod_db_{b} = 0.0;",
            f"}}",
            f"out{b + 2} = mod_db_{b};",
        ])

    code.extend([
        "if (round(solo_band) == 9) {",
        "    soloL = sc1_mono + sc2_mono;",
        "    soloR = sc1_mono + sc2_mono;",
        "}",
        "master_lin = pow(10.0, out_gain / 20.0);",
        "finalL = (solo_band > 0.5) ? soloL : (sigL * master_lin);",
        "finalR = (solo_band > 0.5) ? soloR : (sigR * master_lin);",
        "out1 = finalL;",
        "out2 = finalR;",
        "",
        "// ==================== 16-BAND HIGH-Q REAL-TIME RTA ANALYZER ====================",
        "if (rta_active > 0.5) {",
        "    rta_in = (finalL + finalR) * 0.5;",
        "    rta_k = 0.20;",
    ])

    for r in range(1, 17):
        rf = rta_freqs[r - 1]
        code.extend([
            f"    rg_{r} = tan(pi * min({rf}, samplerate * 0.47) / samplerate);",
            f"    ra1_{r} = 1.0 / (1.0 + rg_{r} * (rg_{r} + rta_k));",
            f"    ra2_{r} = rg_{r} * ra1_{r};",
            f"    ra3_{r} = rg_{r} * ra2_{r};",
            f"    rv3_{r} = rta_in - rta_ic2_{r};",
            f"    rv1_{r} = ra1_{r} * rta_ic1_{r} + ra2_{r} * rv3_{r};",
            f"    rv2_{r} = rta_ic2_{r} + ra2_{r} * rta_ic1_{r} + ra3_{r} * rv3_{r};",
            f"    rta_ic1_{r} = 2.0 * rv1_{r} - rta_ic1_{r};",
            f"    rta_ic2_{r} = 2.0 * rv2_{r} - rta_ic2_{r};",
            f"    rrect_{r} = abs(rta_k * rv1_{r});",
            f"    rta_env_{r} = (rrect_{r} > rta_env_{r}) ? (0.982 * rta_env_{r} + 0.018 * rrect_{r}) : (0.9993 * rta_env_{r} + 0.0007 * rrect_{r});",
            f"    out{r + 10} = rta_env_{r};",
        ])

    code.append("} else {")
    for r in range(1, 17):
        code.append(f"    out{r + 10} = 0.0;")
    code.append("}")

    return "\r\n".join(code)


def make_gen_box(box_id, patching_rect):
    gen_boxes = []
    gen_lines = []
    num_outlets = 26

    for i in range(1, 5):
        gen_boxes.append(make_box(
            f"gen-in-{i}", "newobj", f"in {i}",
            patching_rect=[30.0 + (i - 1) * 120.0, 20.0, 35.0, 22.0],
            numinlets=0, numoutlets=1, outlettype=[""]
        ))

    gen_boxes.append(make_box(
        "gen-codebox", "codebox",
        patching_rect=[30.0, 65.0, 1050.0, 520.0],
        numinlets=4, numoutlets=num_outlets,
        outlettype=[""] * num_outlets,
        code=generate_gen_codebox()
    ))

    for i in range(1, 5):
        gen_lines.append(make_line(f"gen-in-{i}", 0, "gen-codebox", i - 1))

    for o in range(1, num_outlets + 1):
        gen_boxes.append(make_box(
            f"gen-out-{o}", "newobj", f"out {o}",
            patching_rect=[30.0 + (o - 1) * 42.0, 610.0, 40.0, 22.0],
            numinlets=1, numoutlets=0
        ))
        gen_lines.append(make_line("gen-codebox", o - 1, f"gen-out-{o}", 0))

    gen_patcher = {
        "fileversion": 1,
        "appversion": {"major": 9, "minor": 0, "revision": 0, "architecture": "x64", "modernui": 1},
        "classnamespace": "dsp.gen",
        "rect": [50.0, 50.0, 1140.0, 680.0],
        "boxes": gen_boxes,
        "lines": gen_lines,
    }

    return make_box(
        box_id, "newobj", "gen~",
        patching_rect=patching_rect,
        numinlets=4, numoutlets=num_outlets,
        outlettype=["signal"] * num_outlets,
        patcher=gen_patcher,
        saved_object_attributes={"globalpatchername": ""}
    )


def build_device():
    boxes = []
    lines = []
    parameters = {}

    def reg_param(box_id, longname, shortname):
        parameters[box_id] = [longname, shortname, 0]

    # =========================================================================
    # 1. AUDIO INPUTS (6 Channels: Track 1/2, Sidechain A 3/4, Sidechain B 5/6)
    # =========================================================================
    boxes.append(make_box(
        "obj-plugin", "newobj", "plugin~ 1 2 3 4 5 6",
        patching_rect=[30.0, 20.0, 130.0, 22.0],
        numinlets=0, numoutlets=6,
        outlettype=["signal", "signal", "signal", "signal", "signal", "signal"]
    ))
    boxes.append(make_box(
        "obj-plugout", "newobj", "plugout~ 1 2",
        patching_rect=[30.0, 520.0, 85.0, 22.0],
        numinlets=2, numoutlets=0
    ))

    # Sum External Sidechain A (Ch 3 & 4) to Mono + Trim Gain
    boxes.append(make_box("obj-sum2", "newobj", "+~", patching_rect=[180.0, 60.0, 30.0, 22.0]))
    boxes.append(make_box("obj-scale2", "newobj", "*~ 0.5", patching_rect=[180.0, 90.0, 45.0, 22.0]))
    boxes.append(make_box("obj-sc1-mult", "newobj", "*~ 1.0", patching_rect=[180.0, 120.0, 45.0, 22.0]))
    lines.append(make_line("obj-plugin", 2, "obj-sum2", 0))
    lines.append(make_line("obj-plugin", 3, "obj-sum2", 1))
    lines.append(make_line("obj-sum2", 0, "obj-scale2", 0))
    lines.append(make_line("obj-scale2", 0, "obj-sc1-mult", 0))

    # Sum External Sidechain B (Ch 5 & 6) to Mono + Trim Gain
    boxes.append(make_box("obj-sum3", "newobj", "+~", patching_rect=[250.0, 60.0, 30.0, 22.0]))
    boxes.append(make_box("obj-scale3", "newobj", "*~ 0.5", patching_rect=[250.0, 90.0, 45.0, 22.0]))
    boxes.append(make_box("obj-sc2-mult", "newobj", "*~ 1.0", patching_rect=[250.0, 120.0, 45.0, 22.0]))
    lines.append(make_line("obj-plugin", 4, "obj-sum3", 0))
    lines.append(make_line("obj-plugin", 5, "obj-sum3", 1))
    lines.append(make_line("obj-sum3", 0, "obj-scale3", 0))
    lines.append(make_line("obj-scale3", 0, "obj-sc2-mult", 0))

    # =========================================================================
    # 2. 64-BIT gen~ CYTOMIC ZDF DYNAMIC EQ + 16-BAND RTA CORE
    # =========================================================================
    boxes.append(make_gen_box("obj-gen-eq", patching_rect=[30.0, 260.0, 450.0, 24.0]))
    lines.append(make_line("obj-plugin", 0, "obj-gen-eq", 0))
    lines.append(make_line("obj-plugin", 1, "obj-gen-eq", 1))
    lines.append(make_line("obj-sc1-mult", 0, "obj-gen-eq", 2))
    lines.append(make_line("obj-sc2-mult", 0, "obj-gen-eq", 3))
    lines.append(make_line("obj-gen-eq", 0, "obj-plugout", 0))
    lines.append(make_line("obj-gen-eq", 1, "obj-plugout", 1))

    # Central Controller JS + live.thisdevice (with dynamic setwidth support)
    boxes.append(make_box(
        "obj-lom", "newobj", "js dynamic_eq_lom.js",
        patching_rect=[520.0, 180.0, 175.0, 22.0],
        numinlets=1, numoutlets=5, outlettype=["", "", "", "", ""]
    ))
    lines.append(make_line("obj-lom", 1, "obj-gen-eq", 0))

    boxes.append(make_box("obj-thisdevice", "newobj", "live.thisdevice", patching_rect=[520.0, 95.0, 95.0, 22.0], numinlets=1, numoutlets=2, outlettype=["bang", "int"]))
    boxes.append(make_box("obj-defer-init", "newobj", "deferlow", patching_rect=[520.0, 125.0, 60.0, 22.0]))
    boxes.append(make_box("obj-init-msg", "message", "init_device", patching_rect=[520.0, 150.0, 75.0, 22.0]))
    lines.append(make_line("obj-thisdevice", 0, "obj-defer-init", 0))
    lines.append(make_line("obj-defer-init", 0, "obj-init-msg", 0))
    lines.append(make_line("obj-init-msg", 0, "obj-lom", 0))

    boxes.append(make_box("obj-defer-width", "newobj", "deferlow", patching_rect=[630.0, 65.0, 60.0, 22.0]))
    lines.append(make_line("obj-lom", 2, "obj-defer-width", 0))
    lines.append(make_line("obj-defer-width", 0, "obj-thisdevice", 0))

    # Real-Time 45ms Graph Telemetry (8 Dynamic Reductions + 16 Linear RTA Bins directly to obj-graph)
    boxes.append(make_box("obj-qmetro", "newobj", "qmetro 45 @active 1", patching_rect=[30.0, 300.0, 115.0, 22.0]))
    for b in range(1, 9):
        snap_id = f"obj-snap-{b}"
        penv_id = f"obj-penv-{b}"
        sx = 30.0 + (b - 1) * 115.0
        boxes.append(make_box(snap_id, "newobj", "snapshot~", patching_rect=[sx, 335.0, 65.0, 20.0]))
        boxes.append(make_box(penv_id, "newobj", f"prepend set_gr_one {b - 1}", patching_rect=[sx, 360.0, 115.0, 20.0]))
        lines.append(make_line("obj-gen-eq", b + 1, snap_id, 0))
        lines.append(make_line("obj-qmetro", 0, snap_id, 0))
        lines.append(make_line(snap_id, 0, penv_id, 0))
        lines.append(make_line(penv_id, 0, "obj-graph", 0))

    for r in range(1, 17):
        rsnap_id = f"obj-rsnap-{r}"
        rpenv_id = f"obj-rpenv-{r}"
        rx = 30.0 + ((r - 1) % 8) * 115.0
        ry = 400.0 if r <= 8 else 455.0
        boxes.append(make_box(rsnap_id, "newobj", "snapshot~", patching_rect=[rx, ry, 65.0, 20.0]))
        boxes.append(make_box(rpenv_id, "newobj", f"prepend set_rta_lin_one {r - 1}", patching_rect=[rx, ry + 22.0, 125.0, 20.0]))
        lines.append(make_line("obj-gen-eq", r + 9, rsnap_id, 0))
        lines.append(make_line("obj-qmetro", 0, rsnap_id, 0))
        lines.append(make_line(rsnap_id, 0, rpenv_id, 0))
        lines.append(make_line(rpenv_id, 0, "obj-graph", 0))

    # =========================================================================
    # 3. FAR-LEFT VERTICAL SIDECHAIN BAR (x = 0..22, dynamic_eq_sc_bar.js)
    #    Matches Screenshot 2: (▶) Expand, (🎧) SC Listen, vertical "Sidechain" text
    # =========================================================================
    boxes.append(make_box(
        "obj-sc-bar", "jsui",
        varname="sc_bar",
        filename="dynamic_eq_sc_bar.js",
        patching_rect=[720.0, 20.0, 22.0, 169.0],
        presentation_rect=[0.0, 0.0, 22.0, 169.0],
        numinlets=1, numoutlets=1, outlettype=[""],
        border=0
    ))
    lines.append(make_line("obj-sc-bar", 0, "obj-lom", 0))

    # =========================================================================
    # 4. BASE CANVAS LEFT STRIP (x = 22..67, width = 45px): Freq, Gain, Q Dials
    # =========================================================================
    boxes.append(make_live_dial(
        "obj-freq-dial", "band_freq", "Freq",
        10.0, 22000.0, 1000.0, 3,
        patching_rect=[760.0, 20.0, 45.0, 50.0],
        presentation_rect=[22.0, 2.0, 45.0, 50.0]
    ))
    reg_param("obj-freq-dial", "band_freq", "Freq")
    boxes.append(make_box("obj-msg-freq", "newobj", "prepend ui_freq", patching_rect=[820.0, 25.0, 95.0, 22.0]))
    lines.append(make_line("obj-freq-dial", 0, "obj-msg-freq", 0))
    lines.append(make_line("obj-msg-freq", 0, "obj-lom", 0))

    boxes.append(make_live_dial(
        "obj-gain-dial", "band_gain", "Gain",
        -15.0, 15.0, 0.0, 4,
        patching_rect=[760.0, 80.0, 45.0, 50.0],
        presentation_rect=[22.0, 56.0, 45.0, 50.0]
    ))
    reg_param("obj-gain-dial", "band_gain", "Gain")
    boxes.append(make_box("obj-msg-gain", "newobj", "prepend ui_gain", patching_rect=[820.0, 85.0, 95.0, 22.0]))
    lines.append(make_line("obj-gain-dial", 0, "obj-msg-gain", 0))
    lines.append(make_line("obj-msg-gain", 0, "obj-lom", 0))

    boxes.append(make_live_dial(
        "obj-q-dial", "band_q", "Q",
        0.1, 18.0, 0.71, 1,
        patching_rect=[760.0, 140.0, 45.0, 50.0],
        presentation_rect=[22.0, 112.0, 45.0, 50.0]
    ))
    reg_param("obj-q-dial", "band_q", "Q")
    boxes.append(make_box("obj-msg-q", "newobj", "prepend ui_q", patching_rect=[820.0, 145.0, 90.0, 22.0]))
    lines.append(make_line("obj-q-dial", 0, "obj-msg-q", 0))
    lines.append(make_line("obj-msg-q", 0, "obj-lom", 0))

    # 2px bottom border & 2px vertical frame divider between Left Strip and Graph (#474154)
    boxes.append(make_box(
        "obj-left-bot-bar", "panel",
        varname="left_bot_bar",
        patching_rect=[760.0, 195.0, 45.0, 4.0],
        presentation_rect=[22.0, 167.0, 45.0, 2.0],
        bgcolor=[0.278, 0.255, 0.329, 1.0],
        border=0, rounded=0
    ))
    boxes.append(make_box(
        "obj-div-left-graph", "panel",
        varname="div_left_graph",
        patching_rect=[750.0, 20.0, 4.0, 169.0],
        presentation_rect=[67.0, 0.0, 2.0, 169.0],
        bgcolor=[0.278, 0.255, 0.329, 1.0],
        border=0, rounded=0
    ))

    # =========================================================================
    # 5. BASE CANVAS CENTER (x = 69..439, width = 370px, height = 169px):
    #    Exact EQ Eight Display + Bottom 8-Band Strip
    # =========================================================================
    boxes.append(make_box(
        "obj-graph", "jsui",
        varname="eq_graph",
        filename="dynamic_eq_ui.js",
        patching_rect=[720.0, 220.0, 370.0, 169.0],
        presentation_rect=[69.0, 0.0, 370.0, 169.0],
        numinlets=1, numoutlets=1, outlettype=[""],
        border=0
    ))
    lines.append(make_line("obj-graph", 0, "obj-lom", 0))
    lines.append(make_line("obj-lom", 0, "obj-graph", 0))

    # 2px vertical frame divider between Graph and Right Strip (#474154)
    boxes.append(make_box(
        "obj-div-graph-right", "panel",
        varname="div_graph_right",
        patching_rect=[1095.0, 220.0, 4.0, 169.0],
        presentation_rect=[439.0, 0.0, 2.0, 169.0],
        bgcolor=[0.278, 0.255, 0.329, 1.0],
        border=0, rounded=0
    ))

    # =========================================================================
    # 6. BASE CANVAS RIGHT STRIP (x = 441..491, width = 50px, inner controls 44px):
    #    Top Icons [🎧] [ılı.] (20x13 + 4px gap + 20x13), Dynamic [DYN >], Adapt. Q, Scale, Gain
    # =========================================================================
    boxes.append(make_box(
        "obj-right-bot-bar", "panel",
        varname="right_bot_bar",
        patching_rect=[1060.0, 215.0, 50.0, 4.0],
        presentation_rect=[441.0, 167.0, 50.0, 2.0],
        bgcolor=[0.278, 0.255, 0.329, 1.0],
        border=0, rounded=0
    ))
    boxes.append(make_box(
        "obj-top-icons", "jsui",
        varname="top_icons",
        filename="dynamic_eq_top_icons.js",
        patching_rect=[1060.0, 20.0, 44.0, 13.0],
        presentation_rect=[444.0, 5.0, 44.0, 13.0],
        numinlets=1, numoutlets=1, outlettype=[""],
        border=0
    ))
    lines.append(make_line("obj-top-icons", 0, "obj-lom", 0))

    # Clean empty whitespace below top icons (y = 18..77), matching user request!

    # Adapt. Q Label + Toggle (exact EQ Eight y=77 label, y=90 44x13 button)
    boxes.append(make_box(
        "obj-lbl-adaptq", "live.comment",
        varname="lbl_adaptq",
        patching_rect=[1060.0, 90.0, 48.0, 13.0],
        presentation_rect=[442.0, 77.0, 48.0, 13.0],
        text="Adapt. Q",
        textcolor=[0.65, 0.75, 0.84, 1.0]
    ))
    boxes.append(make_live_text(
        "obj-adaptq", "adapt_q_btn", "Adapt Q",
        "Off", "On", 1, 1,
        patching_rect=[1060.0, 106.0, 44.0, 13.0],
        presentation_rect=[444.0, 90.0, 44.0, 13.0]
    ))
    reg_param("obj-adaptq", "adapt_q_btn", "Adapt Q")
    boxes.append(make_box("obj-msg-adaptq", "newobj", "prepend ui_adapt_q", patching_rect=[1140.0, 106.0, 115.0, 22.0]))
    lines.append(make_line("obj-adaptq", 0, "obj-msg-adaptq", 0))
    lines.append(make_line("obj-msg-adaptq", 0, "obj-lom", 0))

    # Scale Label + Numbox (exact EQ Eight y=106 label, y=119 44x13 numbox)
    boxes.append(make_box(
        "obj-lbl-scale", "live.comment",
        varname="lbl_scale",
        patching_rect=[1060.0, 135.0, 48.0, 13.0],
        presentation_rect=[442.0, 106.0, 48.0, 13.0],
        text="Scale",
        textcolor=[0.65, 0.75, 0.84, 1.0]
    ))
    boxes.append(make_live_numbox(
        "obj-dynscale", "dyn_scale", "Scale",
        0.0, 200.0, 100.0, 5,
        patching_rect=[1060.0, 152.0, 44.0, 13.0],
        presentation_rect=[444.0, 119.0, 44.0, 13.0]
    ))
    reg_param("obj-dynscale", "dyn_scale", "Scale")
    boxes.append(make_box("obj-msg-scale", "newobj", "prepend ui_dyn_scale", patching_rect=[1140.0, 152.0, 125.0, 22.0]))
    lines.append(make_line("obj-dynscale", 0, "obj-msg-scale", 0))
    lines.append(make_line("obj-msg-scale", 0, "obj-lom", 0))

    # Output Gain Label + Numbox (exact EQ Eight y=135 label, y=148 44x13 numbox)
    boxes.append(make_box(
        "obj-lbl-outgain", "live.comment",
        varname="lbl_outgain",
        patching_rect=[1060.0, 180.0, 48.0, 13.0],
        presentation_rect=[442.0, 135.0, 48.0, 13.0],
        text="Gain",
        textcolor=[0.65, 0.75, 0.84, 1.0]
    ))
    boxes.append(make_live_numbox(
        "obj-outgain", "out_gain", "Out Gain",
        -24.0, 24.0, 0.0, 4,
        patching_rect=[1060.0, 196.0, 44.0, 13.0],
        presentation_rect=[444.0, 148.0, 44.0, 13.0]
    ))
    reg_param("obj-outgain", "out_gain", "Out Gain")
    boxes.append(make_box("obj-msg-outgain", "newobj", "prepend ui_out_gain", patching_rect=[1140.0, 196.0, 120.0, 22.0]))
    lines.append(make_line("obj-outgain", 0, "obj-msg-outgain", 0))
    lines.append(make_line("obj-msg-outgain", 0, "obj-lom", 0))

    # =========================================================================
    # 7. LEFT EXPANDABLE 2-COLUMN SIDECHAIN PANEL (x = 22..176, +154px)
    #    Initialized off-screen at x = -500 without hidden=1 so Max Presentation
    #    Mode never suppresses visibility when opened.
    # =========================================================================
    boxes.append(make_box(
        "obj-sc-col-div", "panel",
        varname="sc_col_div",
        patching_rect=[1325.0, 5.0, 4.0, 20.0],
        presentation_rect=[-500.0, 4.0, 1.0, 160.0],
        bgcolor=[0.055, 0.055, 0.075, 1.0],
        border=0, rounded=0
    ))
    boxes.append(make_box(
        "obj-sc-right-div", "panel",
        varname="sc_right_div",
        patching_rect=[1335.0, 5.0, 4.0, 20.0],
        presentation_rect=[-500.0, 0.0, 2.0, 169.0],
        bgcolor=[0.278, 0.255, 0.329, 1.0],
        border=0, rounded=0
    ))
    boxes.append(make_box(
        "obj-sc-bot-bar", "panel",
        varname="sc_bot_bar",
        patching_rect=[1345.0, 5.0, 20.0, 4.0],
        presentation_rect=[-500.0, 167.0, 154.0, 2.0],
        bgcolor=[0.278, 0.255, 0.329, 1.0],
        border=0, rounded=0
    ))

    # --- Column 1: Sidechain A ---
    boxes.append(make_live_text(
        "obj-sc-a-btn", "sc_a_btn", "Ext A",
        "Ext. A", "Ext. A", 1, 1,
        patching_rect=[1320.0, 20.0, 68.0, 13.0],
        presentation_rect=[-500.0, 5.0, 68.0, 13.0]
    ))
    reg_param("obj-sc-a-btn", "sc_a_btn", "Ext A")
    boxes.append(make_box("obj-msg-sca", "newobj", "prepend ui_sc_a_en", patching_rect=[1320.0, 42.0, 110.0, 22.0]))
    lines.append(make_line("obj-sc-a-btn", 0, "obj-msg-sca", 0))
    lines.append(make_line("obj-msg-sca", 0, "obj-lom", 0))

    boxes.append(make_box("obj-lbl-srca", "live.comment", varname="lbl_src_a", patching_rect=[1320.0, 68.0, 68.0, 13.0], presentation_rect=[-500.0, 22.0, 48.0, 13.0], text="Source", textcolor=[0.65, 0.75, 0.84, 1.0]))
    boxes.append(make_umenu(
        "obj-sc1-track", "sc1_track_menu",
        ["No Input"],
        patching_rect=[1320.0, 86.0, 68.0, 15.0],
        presentation_rect=[-500.0, 36.0, 68.0, 15.0]
    ))
    boxes.append(make_umenu(
        "obj-sc1-chan", "sc1_chan_menu",
        ["Pre FX", "Post FX", "Post Mixer"],
        patching_rect=[1320.0, 108.0, 68.0, 15.0],
        presentation_rect=[-500.0, 53.0, 68.0, 15.0]
    ))
    boxes.append(make_box("obj-lbl-mixa", "live.comment", varname="lbl_mix_a", patching_rect=[1320.0, 130.0, 68.0, 13.0], presentation_rect=[-500.0, 76.0, 36.0, 13.0], text="Mix", textcolor=[0.65, 0.75, 0.84, 1.0]))
    boxes.append(make_live_numbox(
        "obj-sc1-mix", "sc1_mix", "SC A Mix",
        0.0, 100.0, 100.0, 5,
        patching_rect=[1320.0, 146.0, 68.0, 13.0],
        presentation_rect=[-500.0, 90.0, 68.0, 13.0]
    ))
    reg_param("obj-sc1-mix", "sc1_mix", "SC A Mix")
    boxes.append(make_box("obj-msg-sc1m", "newobj", "prepend ui_sc1_mix", patching_rect=[1410.0, 146.0, 115.0, 22.0]))
    lines.append(make_line("obj-sc1-mix", 0, "obj-msg-sc1m", 0))
    lines.append(make_line("obj-msg-sc1m", 0, "obj-lom", 0))

    boxes.append(make_box("obj-lbl-sc1g", "live.comment", varname="lbl_sc1_gain", patching_rect=[1320.0, 168.0, 68.0, 13.0], presentation_rect=[-500.0, 114.0, 54.0, 13.0], text="SC Gain", textcolor=[0.65, 0.75, 0.84, 1.0]))
    boxes.append(make_live_numbox(
        "obj-sc1-gain", "sc1_gain", "SC A Gain",
        -24.0, 24.0, 0.0, 4,
        patching_rect=[1320.0, 184.0, 68.0, 13.0],
        presentation_rect=[-500.0, 128.0, 68.0, 13.0]
    ))
    reg_param("obj-sc1-gain", "sc1_gain", "SC A Gain")
    boxes.append(make_box("obj-sc1-dbtoa", "newobj", "dbtoa", patching_rect=[1320.0, 206.0, 45.0, 22.0]))
    lines.append(make_line("obj-sc1-gain", 0, "obj-sc1-dbtoa", 0))
    lines.append(make_line("obj-sc1-dbtoa", 0, "obj-sc1-mult", 1))

    boxes.append(make_box("obj-msg-sc1t", "newobj", "prepend set_sc1_track", patching_rect=[1410.0, 86.0, 130.0, 22.0]))
    boxes.append(make_box("obj-msg-sc1c", "newobj", "prepend set_sc1_chan", patching_rect=[1410.0, 108.0, 130.0, 22.0]))
    lines.append(make_line("obj-sc1-track", 0, "obj-msg-sc1t", 0))
    lines.append(make_line("obj-msg-sc1t", 0, "obj-lom", 0))
    lines.append(make_line("obj-sc1-chan", 0, "obj-msg-sc1c", 0))
    lines.append(make_line("obj-msg-sc1c", 0, "obj-lom", 0))

    # --- Column 2: Sidechain B ---
    boxes.append(make_live_text(
        "obj-sc-b-btn", "sc_b_btn", "Ext B",
        "Ext. B", "Ext. B", 1, 1,
        patching_rect=[1550.0, 20.0, 68.0, 13.0],
        presentation_rect=[-500.0, 5.0, 68.0, 13.0]
    ))
    reg_param("obj-sc-b-btn", "sc_b_btn", "Ext B")
    boxes.append(make_box("obj-msg-scb", "newobj", "prepend ui_sc_b_en", patching_rect=[1550.0, 42.0, 110.0, 22.0]))
    lines.append(make_line("obj-sc-b-btn", 0, "obj-msg-scb", 0))
    lines.append(make_line("obj-msg-scb", 0, "obj-lom", 0))

    boxes.append(make_box("obj-lbl-srcb", "live.comment", varname="lbl_src_b", patching_rect=[1550.0, 68.0, 68.0, 13.0], presentation_rect=[-500.0, 22.0, 48.0, 13.0], text="Source", textcolor=[0.65, 0.75, 0.84, 1.0]))
    boxes.append(make_umenu(
        "obj-sc2-track", "sc2_track_menu",
        ["No Input"],
        patching_rect=[1550.0, 86.0, 68.0, 15.0],
        presentation_rect=[-500.0, 36.0, 68.0, 15.0]
    ))
    boxes.append(make_umenu(
        "obj-sc2-chan", "sc2_chan_menu",
        ["Pre FX", "Post FX", "Post Mixer"],
        patching_rect=[1550.0, 108.0, 68.0, 15.0],
        presentation_rect=[-500.0, 53.0, 68.0, 15.0]
    ))
    boxes.append(make_box("obj-lbl-mixb", "live.comment", varname="lbl_mix_b", patching_rect=[1550.0, 130.0, 68.0, 13.0], presentation_rect=[-500.0, 76.0, 36.0, 13.0], text="Mix", textcolor=[0.65, 0.75, 0.84, 1.0]))
    boxes.append(make_live_numbox(
        "obj-sc2-mix", "sc2_mix", "SC B Mix",
        0.0, 100.0, 100.0, 5,
        patching_rect=[1550.0, 146.0, 68.0, 13.0],
        presentation_rect=[-500.0, 90.0, 68.0, 13.0]
    ))
    reg_param("obj-sc2-mix", "sc2_mix", "SC B Mix")
    boxes.append(make_box("obj-msg-sc2m", "newobj", "prepend ui_sc2_mix", patching_rect=[1640.0, 146.0, 115.0, 22.0]))
    lines.append(make_line("obj-sc2-mix", 0, "obj-msg-sc2m", 0))
    lines.append(make_line("obj-msg-sc2m", 0, "obj-lom", 0))

    boxes.append(make_box("obj-lbl-sc2g", "live.comment", varname="lbl_sc2_gain", patching_rect=[1550.0, 168.0, 68.0, 13.0], presentation_rect=[-500.0, 114.0, 54.0, 13.0], text="SC Gain", textcolor=[0.65, 0.75, 0.84, 1.0]))
    boxes.append(make_live_numbox(
        "obj-sc2-gain", "sc2_gain", "SC B Gain",
        -24.0, 24.0, 0.0, 4,
        patching_rect=[1550.0, 184.0, 68.0, 13.0],
        presentation_rect=[-500.0, 128.0, 68.0, 13.0]
    ))
    reg_param("obj-sc2-gain", "sc2_gain", "SC B Gain")
    boxes.append(make_box("obj-sc2-dbtoa", "newobj", "dbtoa", patching_rect=[1550.0, 206.0, 45.0, 22.0]))
    lines.append(make_line("obj-sc2-gain", 0, "obj-sc2-dbtoa", 0))
    lines.append(make_line("obj-sc2-dbtoa", 0, "obj-sc2-mult", 1))

    boxes.append(make_box("obj-msg-sc2t", "newobj", "prepend set_sc2_track", patching_rect=[1640.0, 86.0, 130.0, 22.0]))
    boxes.append(make_box("obj-msg-sc2c", "newobj", "prepend set_sc2_chan", patching_rect=[1640.0, 108.0, 130.0, 22.0]))
    lines.append(make_line("obj-sc2-track", 0, "obj-msg-sc2t", 0))
    lines.append(make_line("obj-msg-sc2t", 0, "obj-lom", 0))
    lines.append(make_line("obj-sc2-chan", 0, "obj-msg-sc2c", 0))
    lines.append(make_line("obj-msg-sc2c", 0, "obj-lom", 0))

    # Dedicated live.routing Objects (SC A on Outlet 3, SC B on Outlet 4)
    boxes.append(make_box(
        "obj-routing-1", "newobj", "live.routing @port audio_inputs",
        patching_rect=[1320.0, 250.0, 190.0, 22.0],
        numinlets=1, numoutlets=5, outlettype=["", "", "", "", ""]
    ))
    boxes.append(make_box("obj-rt1-curtype", "newobj", "prepend rt1_cur_type", patching_rect=[1320.0, 280.0, 135.0, 22.0]))
    boxes.append(make_box("obj-rt1-curchan", "newobj", "prepend rt1_cur_chan", patching_rect=[1465.0, 280.0, 135.0, 22.0]))
    boxes.append(make_box("obj-rt1-types", "newobj", "prepend rt1_types", patching_rect=[1320.0, 310.0, 125.0, 22.0]))
    boxes.append(make_box("obj-rt1-chans", "newobj", "prepend rt1_chans", patching_rect=[1465.0, 310.0, 125.0, 22.0]))
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
        "obj-routing-2", "newobj", "live.routing @port audio_inputs",
        patching_rect=[1620.0, 250.0, 190.0, 22.0],
        numinlets=1, numoutlets=5, outlettype=["", "", "", "", ""]
    ))
    boxes.append(make_box("obj-rt2-curtype", "newobj", "prepend rt2_cur_type", patching_rect=[1620.0, 280.0, 135.0, 22.0]))
    boxes.append(make_box("obj-rt2-curchan", "newobj", "prepend rt2_cur_chan", patching_rect=[1765.0, 280.0, 135.0, 22.0]))
    boxes.append(make_box("obj-rt2-types", "newobj", "prepend rt2_types", patching_rect=[1620.0, 310.0, 125.0, 22.0]))
    boxes.append(make_box("obj-rt2-chans", "newobj", "prepend rt2_chans", patching_rect=[1765.0, 310.0, 125.0, 22.0]))
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
    # 8. RIGHT EXPANDABLE PER-BAND DYNAMIC PANEL (x = 491..621, +130px)
    #    Initialized off-screen at x = -500 without hidden=1.
    # =========================================================================
    boxes.append(make_box(
        "obj-div-right-dyn", "panel",
        varname="div_right_dyn",
        patching_rect=[1800.0, 20.0, 4.0, 169.0],
        presentation_rect=[-500.0, 0.0, 2.0, 169.0],
        bgcolor=[0.278, 0.255, 0.329, 1.0],
        border=0, rounded=0
    ))
    boxes.append(make_box(
        "obj-dyn-bot-bar", "panel",
        varname="dyn_bot_bar",
        patching_rect=[1810.0, 195.0, 128.0, 4.0],
        presentation_rect=[-500.0, 167.0, 128.0, 2.0],
        bgcolor=[0.278, 0.255, 0.329, 1.0],
        border=0, rounded=0
    ))
    boxes.append(make_box(
        "obj-dyn-band-lbl", "live.comment",
        varname="dyn_band_lbl",
        patching_rect=[1820.0, 20.0, 74.0, 14.0],
        presentation_rect=[-500.0, 5.0, 74.0, 14.0],
        text="Band 1 Dyn",
        textcolor=[0.65, 0.75, 0.84, 1.0]
    ))
    boxes.append(make_live_text(
        "obj-band-dyn-on", "band_dyn_on", "Dyn On",
        "OFF", "ON", 1, 0,
        patching_rect=[1910.0, 20.0, 42.0, 13.0],
        presentation_rect=[-500.0, 5.0, 42.0, 13.0]
    ))
    reg_param("obj-band-dyn-on", "band_dyn_on", "Dyn On")
    boxes.append(make_box("obj-msg-dynon", "newobj", "prepend ui_dyn_on", patching_rect=[1970.0, 20.0, 110.0, 22.0]))
    lines.append(make_line("obj-band-dyn-on", 0, "obj-msg-dynon", 0))
    lines.append(make_line("obj-msg-dynon", 0, "obj-lom", 0))

    boxes.append(make_box("obj-lbl-src", "live.comment", varname="lbl_src", patching_rect=[1820.0, 45.0, 30.0, 14.0], presentation_rect=[-500.0, 26.0, 30.0, 14.0], text="Src:", textcolor=[0.65, 0.75, 0.84, 1.0]))
    boxes.append(make_live_tab(
        "obj-src-tab", "band_source", "Source",
        ["Int", "SC A", "SC B"], 0,
        patching_rect=[1865.0, 45.0, 88.0, 14.0],
        presentation_rect=[-500.0, 26.0, 88.0, 14.0]
    ))
    reg_param("obj-src-tab", "band_source", "Source")
    boxes.append(make_box("obj-msg-source", "newobj", "prepend ui_source", patching_rect=[1970.0, 45.0, 110.0, 22.0]))
    lines.append(make_line("obj-src-tab", 0, "obj-msg-source", 0))
    lines.append(make_line("obj-msg-source", 0, "obj-lom", 0))

    boxes.append(make_box("obj-lbl-range", "live.comment", varname="lbl_range", patching_rect=[1820.0, 70.0, 62.0, 14.0], presentation_rect=[-500.0, 52.0, 62.0, 14.0], text="Dyn Range:", textcolor=[0.65, 0.75, 0.84, 1.0]))
    boxes.append(make_live_numbox(
        "obj-dyndepth", "band_dyndepth", "Dyn Range",
        -15.0, 15.0, 0.0, 4,
        patching_rect=[1890.0, 70.0, 56.0, 13.0],
        presentation_rect=[-500.0, 52.0, 56.0, 13.0]
    ))
    reg_param("obj-dyndepth", "band_dyndepth", "Dyn Range")
    boxes.append(make_box("obj-msg-dyndepth", "newobj", "prepend ui_dyndepth", patching_rect=[1970.0, 70.0, 125.0, 22.0]))
    lines.append(make_line("obj-dyndepth", 0, "obj-msg-dyndepth", 0))
    lines.append(make_line("obj-msg-dyndepth", 0, "obj-lom", 0))

    boxes.append(make_box("obj-lbl-thresh", "live.comment", varname="lbl_thresh", patching_rect=[1820.0, 95.0, 62.0, 14.0], presentation_rect=[-500.0, 76.0, 62.0, 14.0], text="Threshold:", textcolor=[0.65, 0.75, 0.84, 1.0]))
    boxes.append(make_live_numbox(
        "obj-thresh", "band_thresh", "Thresh",
        -60.0, 0.0, -18.0, 4,
        patching_rect=[1890.0, 95.0, 56.0, 13.0],
        presentation_rect=[-500.0, 76.0, 56.0, 13.0]
    ))
    reg_param("obj-thresh", "band_thresh", "Thresh")
    boxes.append(make_box("obj-msg-thresh", "newobj", "prepend ui_thresh", patching_rect=[1970.0, 95.0, 110.0, 22.0]))
    lines.append(make_line("obj-thresh", 0, "obj-msg-thresh", 0))
    lines.append(make_line("obj-msg-thresh", 0, "obj-lom", 0))

    boxes.append(make_box("obj-lbl-attack", "live.comment", varname="lbl_attack", patching_rect=[1820.0, 120.0, 62.0, 14.0], presentation_rect=[-500.0, 100.0, 62.0, 14.0], text="Attack:", textcolor=[0.65, 0.75, 0.84, 1.0]))
    boxes.append(make_live_numbox(
        "obj-attack", "band_attack", "Attack",
        0.1, 250.0, 5.0, 2,
        patching_rect=[1890.0, 120.0, 56.0, 13.0],
        presentation_rect=[-500.0, 100.0, 56.0, 13.0]
    ))
    reg_param("obj-attack", "band_attack", "Attack")
    boxes.append(make_box("obj-msg-attack", "newobj", "prepend ui_attack", patching_rect=[1970.0, 120.0, 110.0, 22.0]))
    lines.append(make_line("obj-attack", 0, "obj-msg-attack", 0))
    lines.append(make_line("obj-msg-attack", 0, "obj-lom", 0))

    boxes.append(make_box("obj-lbl-release", "live.comment", varname="lbl_release", patching_rect=[1820.0, 145.0, 62.0, 14.0], presentation_rect=[-500.0, 124.0, 62.0, 14.0], text="Release:", textcolor=[0.65, 0.75, 0.84, 1.0]))
    boxes.append(make_live_numbox(
        "obj-release", "band_release", "Release",
        5.0, 1000.0, 80.0, 2,
        patching_rect=[1890.0, 145.0, 56.0, 13.0],
        presentation_rect=[-500.0, 124.0, 56.0, 13.0]
    ))
    reg_param("obj-release", "band_release", "Release")
    boxes.append(make_box("obj-msg-release", "newobj", "prepend ui_release", patching_rect=[1970.0, 145.0, 115.0, 22.0]))
    lines.append(make_line("obj-release", 0, "obj-msg-release", 0))
    lines.append(make_line("obj-msg-release", 0, "obj-lom", 0))

    # =========================================================================
    # 9. ASSEMBLE PATCHER & WRITE AMXD CONTAINER
    # =========================================================================
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
        "openrect": [0.0, 0.0, 491.0, 169.0],
        "openinpresentation": 1,
        "gridsize": [8.0, 8.0],
        "devicewidth": 491.0,
        "boxes": boxes,
        "lines": lines,
        "parameters": parameters,
        "dependency_cache": [
            {"name": "dynamic_eq_lom.js", "bootpath": ".", "type": "TEXT", "implicit": 1},
            {"name": "dynamic_eq_ui.js", "bootpath": ".", "type": "TEXT", "implicit": 1},
            {"name": "dynamic_eq_sc_bar.js", "bootpath": ".", "type": "TEXT", "implicit": 1},
            {"name": "dynamic_eq_top_icons.js", "bootpath": ".", "type": "TEXT", "implicit": 1},
        ],
        "latency": 0,
    }

    raw_json = json.dumps({"patcher": patcher}, indent=2).encode("utf-8")
    ampf_body = b"ampf" + struct.pack("<I", 4) + b"aaaa"
    ampf_body += b"meta" + struct.pack("<I", 4) + b"\x00\x00\x00\x00"
    ampf_body += b"ptch" + struct.pack("<I", len(raw_json)) + raw_json

    out_path = os.path.join("dynamic eq", "Dynamic_EQ.amxd")
    with open(out_path, "wb") as f:
        f.write(ampf_body)

    print(f"Successfully generated {out_path} ({len(ampf_body)} bytes)")
    print(f"Total boxes: {len(boxes)}, Total lines: {len(lines)}, Total parameters: {len(parameters)}")


if __name__ == "__main__":
    build_device()

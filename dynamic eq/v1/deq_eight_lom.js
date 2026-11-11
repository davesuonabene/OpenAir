// deq_eight_lom.js
// Native-Component Controller, State Persistence Manager, Theme Color Router & Width Manager for dEQ Eight.amxd
// - Manages 100% native Max/M4L UI components (`panel`, `live.line`, `live.text`, `umenu`, `live.comment`).
// - Persists all 8 EQ bands, dynamic parameters, and UI drawer/selection state via M4L `pattr eq_state` Blob
//   so opening/closing the Max editor, saving/loading Live Sets, and switching presets never reset the UI or DSP.
// - Queries `live.colors` whenever Ableton's theme changes and forwards dynamic theme RGBs to `deq_eight_ui.js`.

autowatch = 1;
inlets = 1;
outlets = 6;
// Outlet 0 -> jsui eq_graph (`deq_eight_ui.js`) messages
// Outlet 1 -> gen~ DSP parameter messages
// Outlet 2 -> live.thisdevice ("setwidth <px>")
// Outlet 3 -> live.routing (Sidechain A, Inlets 3/4, index 1)
// Outlet 4 -> live.routing (Sidechain B, Inlets 5/6, index 2)
// Outlet 5 -> pattr eq_state @thru 2 (authoritative 104-float M4L state persistence)

var STATE_VERSION = 2;
var NUM_BANDS = 8;

// Lifecycle guards: prevent shared single-band inspector controls from overwriting `bands[]` before `live.thisdevice`
var device_ready = 0;
var state_restored = 0;
var is_syncing_controls = 0;

var selected_band = 2; // Default selected band = Band 3 (1.00 kHz), matching EQ Eight!
var sc_panel_open = 0;  // Left Sidechain panel (0 or 1, +154px)
var dyn_panel_open = 0; // Right Dynamic panel (0 or 1, +130px)

var SC_W = 154;
var BASE_W = 495; // 22 (SC bar) + 473 (EQ8 core) = 495px
var DYN_W = 136;

var global_scale = 100.0;
var out_gain = 0.0;
var adaptive_q = 1;
var rta_on = 1;
var solo_band = 0;
var sc_listen = 0;

var sc1_enable = 0;
var sc1_mix = 100.0;
var sc1_gain = 0.0;
var sc2_enable = 0;
var sc2_mix = 100.0;
var sc2_gain = 0.0;

var rt1_type_list = [];
var rt1_chan_list = [];
var rt1_cur_type_sym = null;
var rt1_cur_chan_sym = null;
var rt2_type_list = [];
var rt2_chan_list = [];
var rt2_cur_type_sym = null;
var rt2_cur_chan_sym = null;

var DEFAULT_FREQS = [30.0, 200.0, 1000.0, 5000.0, 100.0, 1000.0, 5000.0, 18000.0];
var DEFAULT_TYPES = [2, 3, 3, 5, 3, 3, 3, 6];
var DEFAULT_ACTIVE = [1, 1, 1, 1, 0, 0, 0, 0];
var bands = [];
var loaded_dyn_ring_full = [0, 0, 0, 0, 0, 0, 0, 0];
var drag_tick = 0;
var save_tick = 0;

for (var i = 0; i < NUM_BANDS; i++) {
    bands.push({
        active: DEFAULT_ACTIVE[i],
        freq: DEFAULT_FREQS[i],
        gain: 0.0,
        q: 0.71,
        type: DEFAULT_TYPES[i],
        dyn_on: 0,
        range: 0.0,
        thresh: -18.0,
        atk: 5.0,
        rel: 80.0,
        sc_src: 0 // 0=Internal, 1=Ext. A, 2=Ext. B
    });
}

var obj_cache = {};

function get_box(varname) {
    if (obj_cache[varname]) return obj_cache[varname];
    if (!this.patcher) return null;
    var obj = this.patcher.getnamed(varname);
    if (obj) obj_cache[varname] = obj;
    return obj;
}

function clamp(v, lo, hi) {
    return v < lo ? lo : (v > hi ? hi : v);
}

function set_box_rect(varname, x, y, w, h, vis) {
    var obj = get_box(varname);
    if (obj) {
        var final_x = vis ? x : -500;
        obj.message("presentation_rect", final_x, y, w, h);
    }
}

function set_named_val(varname, val) {
    var obj = get_box(varname);
    if (obj) {
        obj.message("set", val);
    }
}

// ============================================================================
// AUTHORITATIVE M4L STATE PERSISTENCE (`pattr eq_state` + `getvalueof`/`setvalueof`)
// ============================================================================
function build_state_array() {
    var arr = [
        STATE_VERSION,
        selected_band,
        sc_panel_open ? 1 : 0,
        dyn_panel_open ? 1 : 0,
        adaptive_q ? 1 : 0,
        global_scale,
        out_gain,
        rta_on ? 1 : 0,
        solo_band ? 1 : 0,
        sc_listen ? 1 : 0,
        sc1_enable ? 1 : 0,
        sc1_mix,
        sc1_gain,
        sc2_enable ? 1 : 0,
        sc2_mix,
        sc2_gain
    ];
    for (var i = 0; i < NUM_BANDS; i++) {
        var b = bands[i];
        arr.push(
            b.active ? 1 : 0,
            b.type,
            b.freq,
            b.gain,
            b.q,
            b.dyn_on ? 1 : 0,
            b.range,
            b.thresh,
            b.atk,
            b.rel,
            b.sc_src
        );
    }
    return arr;
}

function apply_state_array(args) {
    if (!args || args.length < 104) return false;
    var ver = Math.round(Number(args[0]));
    if (ver !== STATE_VERSION) return false;

    selected_band = clamp(Math.round(Number(args[1])), 0, NUM_BANDS - 1);
    sc_panel_open = Number(args[2]) ? 1 : 0;
    dyn_panel_open = Number(args[3]) ? 1 : 0;
    adaptive_q = Number(args[4]) ? 1 : 0;
    global_scale = clamp(Number(args[5]), 0.0, 200.0);
    out_gain = clamp(Number(args[6]), -24.0, 24.0);
    rta_on = Number(args[7]) ? 1 : 0;
    solo_band = Number(args[8]) ? 1 : 0;
    sc_listen = Number(args[9]) ? 1 : 0;
    sc1_enable = Number(args[10]) ? 1 : 0;
    sc1_mix = clamp(Number(args[11]), 0.0, 100.0);
    sc1_gain = clamp(Number(args[12]), -24.0, 24.0);
    sc2_enable = Number(args[13]) ? 1 : 0;
    sc2_mix = clamp(Number(args[14]), 0.0, 100.0);
    sc2_gain = clamp(Number(args[15]), -24.0, 24.0);

    for (var i = 0; i < NUM_BANDS; i++) {
        var base = 16 + i * 11;
        var b = bands[i];
        b.active = Number(args[base + 0]) ? 1 : 0;
        b.type   = clamp(Math.round(Number(args[base + 1])), 0, 7);
        b.freq   = clamp(Number(args[base + 2]), 20.0, 20000.0);
        b.gain   = clamp(Number(args[base + 3]), -15.0, 15.0);
        b.q      = clamp(Number(args[base + 4]), 0.1, 18.0);
        b.dyn_on = Number(args[base + 5]) ? 1 : 0;
        b.range  = clamp(Number(args[base + 6]), -15.0, 15.0);
        b.thresh = clamp(Number(args[base + 7]), -60.0, 0.0);
        b.atk    = clamp(Number(args[base + 8]), 0.1, 250.0);
        b.rel    = clamp(Number(args[base + 9]), 5.0, 1000.0);
        b.sc_src = clamp(Math.round(Number(args[base + 10])), 0, 2);
    }
    state_restored = 1;
    return true;
}

function save_state() {
    if (!device_ready) return;
    outlet(5, build_state_array());
    notifyclients();
}

function recall_state() {
    var args = arrayfromargs(arguments);
    if (apply_state_array(args)) {
        if (device_ready) {
            update_layout();
            sync_all();
        }
    }
}

function getvalueof() {
    return build_state_array();
}

function setvalueof() {
    var args = arrayfromargs(arguments);
    if (apply_state_array(args)) {
        if (device_ready) {
            update_layout();
            sync_all();
        }
    }
}

// --- Update Native Bottom 8-Band Cards (Selection, Activator, Filter Curve Menu, Dyn Ring) ---
function update_band_strip_layout(gx) {
    set_box_rect("band_strip_bg", gx, 132, 370, 37, 1);
    var slot_w = 372.0 / NUM_BANDS; // 46.5px

    for (var c = 0; c < NUM_BANDS; c++) {
        var cx0 = gx + Math.round(c * slot_w);
        var cx1 = (c === NUM_BANDS - 1) ? (gx + 370) : (gx + Math.round((c + 1) * slot_w - 2.0));
        var cw = cx1 - cx0; // 45px
        var is_sel = (c === selected_band);

        // Unselected cards show recessed `live_surface_bg` panel; selected card hides it to reveal raised `live_lcd_frame` tab
        set_box_rect("band_card_bg_" + c, cx0, 134, cw, 33, is_sel ? 0 : 1);

        // Top row: Native `live.menu` Filter Curve dropdown (width = cw - 4 = 41px, height = 16px, matching EQ Eight!)
        var ddx = cx0 + 2.0;
        var ddw = cw - 4.0;
        set_box_rect("band_type_menu_" + c, ddx, 134.5, ddw, 16, 1);

        // Bottom row left: 13x13 Band Activator Square (`live.text` -> 12x12 visual square with 10x10 Cyan fill!)
        set_box_rect("band_on_btn_" + c, ddx, 152.5, 13, 13, 1);

        // Bottom row center: Band Number 1..8 selector (`live.text` Bold)
        set_box_rect("band_sel_btn_" + c, cx0 + 15.0, 151.5, 15, 14, 1);

        // Bottom row right: 13x13 Vector SVG Dynamics Circle Toggle (`live.text` with off/on/full ring SVGs)
        var dcx = ddx + ddw - 13.0;
        set_box_rect("band_dyn_btn_" + c, dcx, 152.5, 13, 13, 1);
    }
}

function sync_band_strip_widgets(idx) {
    var b = bands[idx];
    set_named_val("band_on_btn_" + idx, b.active);
    set_named_val("band_type_menu_" + idx, b.type);

    var is_full_lit = (dyn_panel_open && selected_band === idx) ? 1 : 0;
    var dbtn = get_box("band_dyn_btn_" + idx);
    if (dbtn) {
        if (loaded_dyn_ring_full[idx] !== is_full_lit) {
            var on_svg = is_full_lit ? "ableton_dyn_ring_full.svg" : "ableton_dyn_ring_on.svg";
            dbtn.message("pictures", "ableton_dyn_ring_off.svg", on_svg);
            loaded_dyn_ring_full[idx] = is_full_lit;
        }
        dbtn.message("set", (is_full_lit || b.dyn_on) ? 1 : 0);
    }
}

// --- Dynamic Layout & Device Width Management ---
function update_layout() {
    var x_off = sc_panel_open ? SC_W : 0;
    var total_w = BASE_W + x_off + (dyn_panel_open ? DYN_W : 0);

    // Full-device background surface panel (`themecolor.live_surface_bg`)
    set_box_rect("bg_surface", 0, 0, total_w, 169, 1);

    // 0. Far-left vertical Sidechain Spine (100% Native Max Components at x=0..22)
    set_box_rect("sc_expand_btn", 3.0, 4.0, 15.0, 15.0, 1);
    set_box_rect("sc_expand_ring", 3.0, 4.0, 15.0, 15.0, 1);
    set_box_rect("sc_listen_btn", 3.5, 23.0, 14.0, 14.0, 1);
    set_box_rect("sc_listen_bg_off", 3.5, 23.0, 14.0, 14.0, sc_listen ? 0 : 1);
    set_box_rect("sc_listen_bg_on",  3.5, 23.0, 14.0, 14.0, sc_listen ? 1 : 0);
    set_box_rect("sc_vert_lbl", 2.0, 82.0, 17.0, 64.0, 1);
    var sc_act = (sc1_enable || sc2_enable) ? 1 : 0;
    set_box_rect("sc_dot_off", 7.5, 151.0, 6.5, 6.5, sc_act ? 0 : 1);
    set_box_rect("sc_dot_on",  7.5, 151.0, 6.5, 6.5, sc_act ? 1 : 0);
    set_box_rect("sc_spine_div", 21.0, 3.0, 1.0, 163.0, 1);

    // 1. Left Expandable Sidechain Panel (x = 22 .. 176 when sc_panel_open == 1, Glue Compressor layout!)
    var sc_vis = sc_panel_open ? 1 : 0;
    var sx = 22;
    set_box_rect("sc_col_div", sx + 76, 3, 1, 163, sc_vis);
    set_box_rect("sc_right_div", sx + SC_W - 2, 0, 2, 169, sc_vis);

    set_box_rect("sc_a_btn", sx + 4, 5, 68, 16, sc_vis);
    set_box_rect("lbl_src_a", sx + 16, 23, 48, 14, sc_vis);
    set_box_rect("sc1_track_menu", sx + 4, 38, 68, 16, sc_vis);
    set_box_rect("sc1_chan_menu", sx + 4, 57, 68, 16, sc_vis);
    set_box_rect("lbl_mix_a", sx + 22, 82, 36, 14, sc_vis);
    set_box_rect("sc1_mix", sx + 4, 96, 68, 16, sc_vis);
    set_box_rect("lbl_sc1_gain", sx + 13, 122, 54, 14, sc_vis);
    set_box_rect("sc1_gain", sx + 4, 136, 68, 16, sc_vis);

    set_box_rect("sc_b_btn", sx + 82, 5, 68, 16, sc_vis);
    set_box_rect("lbl_src_b", sx + 94, 23, 48, 14, sc_vis);
    set_box_rect("sc2_track_menu", sx + 82, 38, 68, 16, sc_vis);
    set_box_rect("sc2_chan_menu", sx + 82, 57, 68, 16, sc_vis);
    set_box_rect("lbl_mix_b", sx + 100, 82, 36, 14, sc_vis);
    set_box_rect("sc2_mix", sx + 82, 96, 68, 16, sc_vis);
    set_box_rect("lbl_sc2_gain", sx + 91, 122, 54, 14, sc_vis);
    set_box_rect("sc2_gain", sx + 82, 136, 68, 16, sc_vis);

    // 2. EQ Eight Left Strip (Freq / Gain / Q, width = 45px: x = 22+x_off .. 67+x_off)
    set_box_rect("lbl_freq",  22 + x_off, 1,   45, 14, 1);
    set_box_rect("band_freq", 22 + x_off, 13,  45, 38, 1);
    set_box_rect("lbl_gain",  22 + x_off, 56,  45, 14, 1);
    set_box_rect("band_gain", 22 + x_off, 68,  45, 38, 1);
    set_box_rect("lbl_q",     22 + x_off, 111, 45, 14, 1);
    set_box_rect("band_q",    22 + x_off, 123, 45, 38, 1);
    set_box_rect("div_left_graph", 67 + x_off, 0, 2, 169, 1);

    // 3. Center EQ Eight Display (x = 69+x_off, w = 370, h = 132) + Native Bottom 8-Band Strip (y = 132..169)
    var gx = 69 + x_off;
    set_box_rect("eq_graph",  gx, 0, 370, 132, 1);

    // Native Scale Labels (`live.comment` with `themecolor.live_display_scale_text`, matching 12 Hz .. 22 kHz grid)
    set_box_rect("lbl_f_100", gx + 91,  118, 26, 13, 1);
    set_box_rect("lbl_f_1k",  gx + 205, 118, 26, 13, 1);
    set_box_rect("lbl_f_10k", gx + 318, 118, 26, 13, 1);
    set_box_rect("lbl_db_12",  gx + 2, 7,   20, 12, 1);
    set_box_rect("lbl_db_6",   gx + 5, 33,  16, 12, 1);
    set_box_rect("lbl_db_0",   gx + 8, 60,  14, 12, 1);
    set_box_rect("lbl_db_m6",  gx + 3, 86,  18, 12, 1);
    set_box_rect("lbl_db_m12", gx + 1, 113, 22, 12, 1);

    update_band_strip_layout(gx);
    set_box_rect("div_graph_right", 439 + x_off, 0, 2, 169, 1);

    // 4. EQ Eight Right Strip (width = 54px: x = 441+x_off .. 495+x_off)
    var rx = 444 + x_off;
    set_box_rect("solo_btn", rx,      4, 22, 15, 1);
    set_box_rect("rta_btn",  rx + 25, 4, 22, 15, 1);
    set_box_rect("lbl_adaptq", rx - 2.5, 71, 52, 14, 1);
    set_box_rect("adapt_q_btn", rx, 85, 47, 16, 1);
    set_box_rect("lbl_scale", rx - 2.5, 103, 52, 14, 1);
    set_box_rect("dyn_scale", rx, 117, 47, 16, 1);
    set_box_rect("lbl_outgain", rx - 2.5, 135, 52, 14, 1);
    set_box_rect("out_gain", rx, 149, 47, 16, 1);

    // 5. Right Expandable Per-Band Dynamic Panel (+136px at x = 495+x_off when dyn_panel_open == 1)
    var dyn_vis = dyn_panel_open ? 1 : 0;
    var dx = 495 + x_off;
    set_box_rect("div_right_dyn", dx, 0, 2, 169, dyn_vis);
    set_box_rect("dyn_band_lbl", dx + 6,  6, 76, 15, dyn_vis);
    set_box_rect("band_dyn_on",  dx + 84, 5, 46, 16, dyn_vis);

    set_box_rect("lbl_src",      dx + 6,  28, 32, 15, dyn_vis);
    set_box_rect("band_source",  dx + 38, 27, 92, 16, dyn_vis);

    set_box_rect("lbl_range",    dx + 6,  55, 64, 15, dyn_vis);
    set_box_rect("band_dyndepth", dx + 70, 54, 60, 16, dyn_vis);

    set_box_rect("lbl_thresh",   dx + 6,  81, 64, 15, dyn_vis);
    set_box_rect("band_thresh",  dx + 70, 80, 60, 16, dyn_vis);

    set_box_rect("lbl_attack",   dx + 6,  107, 64, 15, dyn_vis);
    set_box_rect("band_attack",  dx + 70, 106, 60, 16, dyn_vis);

    set_box_rect("lbl_release",  dx + 6,  133, 64, 15, dyn_vis);
    set_box_rect("band_release", dx + 70, 132, 60, 16, dyn_vis);

    // Resize device width in Ableton Live
    outlet(2, "setwidth", total_w);
}

// --- Sync State to Gen~ DSP & JSUI ---
function sync_band_to_dsp(idx) {
    var b = bands[idx];
    var p = "b" + (idx + 1) + "_";
    outlet(1, p + "on", b.active);
    outlet(1, p + "type", b.type);
    outlet(1, p + "freq", b.freq);
    outlet(1, p + "gain", b.gain);
    outlet(1, p + "q", b.q);
    outlet(1, p + "dyn_on", b.dyn_on);
    outlet(1, p + "dyn_range", b.range);
    outlet(1, p + "thresh", b.thresh);
    outlet(1, p + "attack", b.atk);
    outlet(1, p + "release", b.rel);
    outlet(1, p + "source", b.sc_src);
}

function sync_band_to_ui(idx) {
    var b = bands[idx];
    outlet(0, "set_band", idx, b.active, b.freq, b.gain, b.q, b.type, b.dyn_on, b.range, b.thresh);
    sync_band_strip_widgets(idx);
}

function update_solo_dsp() {
    var s_val = 0;
    if (sc_listen) {
        s_val = 9;
    } else if (solo_band) {
        s_val = selected_band + 1;
    }
    outlet(1, "solo_band", s_val);
    set_named_val("solo_btn", solo_band);
    set_named_val("sc_listen_btn", sc_listen);
    set_box_rect("sc_listen_bg_off", 3.5, 23.0, 14.0, 14.0, sc_listen ? 0 : 1);
    set_box_rect("sc_listen_bg_on",  3.5, 23.0, 14.0, 14.0, sc_listen ? 1 : 0);
}

function update_sc_dsp() {
    var eff1 = sc1_enable ? clamp(sc1_mix / 100.0, 0.0, 1.0) : 0.0;
    var eff2 = sc2_enable ? clamp(sc2_mix / 100.0, 0.0, 1.0) : 0.0;
    outlet(1, "sc1_mix", eff1);
    outlet(1, "sc2_mix", eff2);
    var sc_act = (sc1_enable || sc2_enable) ? 1 : 0;
    set_box_rect("sc_dot_off", 7.5, 151.0, 6.5, 6.5, sc_act ? 0 : 1);
    set_box_rect("sc_dot_on",  7.5, 151.0, 6.5, 6.5, sc_act ? 1 : 0);
}

function sync_selected_band_controls() {
    is_syncing_controls = 1;
    var b = bands[selected_band];
    var f_box = get_box("band_freq");
    if (f_box) {
        f_box.message("_parameter_initial", DEFAULT_FREQS[selected_band]);
        f_box.message("set", b.freq);
    }
    set_named_val("band_gain", b.gain);
    set_named_val("band_q", b.q);
    set_named_val("band_dyn_on", b.dyn_on);
    set_named_val("band_dyndepth", b.range);
    set_named_val("band_thresh", b.thresh);
    set_named_val("band_attack", b.atk);
    set_named_val("band_release", b.rel);
    set_named_val("band_source", b.sc_src);

    var hdr = get_box("dyn_band_lbl");
    if (hdr) hdr.message("set", "Band " + (selected_band + 1) + " Dyn");
    set_named_val("sc_expand_btn", sc_panel_open);
    set_named_val("rta_btn", rta_on);
    update_solo_dsp();

    var gx = 69 + (sc_panel_open ? SC_W : 0);
    update_band_strip_layout(gx);
    for (var s_idx = 0; s_idx < NUM_BANDS; s_idx++) {
        sync_band_strip_widgets(s_idx);
    }
    is_syncing_controls = 0;
}

function query_theme_colors() {
    var lc = get_box("live_colors_obj");
    if (lc) {
        lc.message("lcd_bg");
        lc.message("lcd_frame");
        lc.message("display_scale_text");
        lc.message("lcd_control_fg_alt");
        lc.message("display_handle_one");
        lc.message("spectrum_default_color");
    }
}

function theme_color_reply(token, r, g, b, a) {
    var map = {
        "lcd_bg": "lcd_bg",
        "lcd_frame": "lcd_frame",
        "display_scale_text": "scale_text",
        "lcd_control_fg_alt": "control_fg",
        "display_handle_one": "handle_one",
        "spectrum_default_color": "spectrum_fill"
    };
    if (map[token]) {
        outlet(0, "set_theme_color", map[token], r, g, b, a);
    }
}

function sync_all() {
    is_syncing_controls = 1;
    set_named_val("adapt_q_btn", adaptive_q);
    set_named_val("dyn_scale", global_scale);
    set_named_val("out_gain", out_gain);
    set_named_val("sc_a_btn", sc1_enable);
    set_named_val("sc_b_btn", sc2_enable);
    set_named_val("sc1_mix", sc1_mix);
    set_named_val("sc2_mix", sc2_mix);
    set_named_val("sc1_gain", sc1_gain);
    set_named_val("sc2_gain", sc2_gain);
    is_syncing_controls = 0;

    outlet(1, "dyn_scale", global_scale / 100.0);
    outlet(1, "out_gain", out_gain);
    outlet(1, "adapt_q", adaptive_q);
    update_sc_dsp();
    update_solo_dsp();

    outlet(0, "set_scale", global_scale);
    outlet(0, "set_adaptive_q", adaptive_q);
    outlet(0, "set_rta_on", rta_on);
    outlet(0, "select", selected_band);

    for (var i = 0; i < NUM_BANDS; i++) {
        sync_band_to_dsp(i);
        sync_band_to_ui(i);
    }
    sync_selected_band_controls();
    query_theme_colors();
}

function init_device() {
    obj_cache = {};

    // Pull stored 104-float state array directly from `pattr eq_state` if not yet delivered via patchline
    if (!state_restored) {
        var st_box = get_box("eq_state");
        if (st_box && st_box.getvalueof) {
            var sv = st_box.getvalueof();
            if (sv && sv.length >= 104) {
                apply_state_array(sv);
            }
        }
    }

    device_ready = 1;
    update_layout();
    sync_all();

    // Native live.routing initialization (port audio_inputs + index 1 for SC A, index 2 for SC B)
    outlet(3, "port", "audio_inputs");
    outlet(3, "index", 1);
    outlet(4, "port", "audio_inputs");
    outlet(4, "index", 2);
}

// Fallback auto-boot task in case `deq_eight_lom.js` is recompiled on the fly while Max Editor is open
var boot_task = new Task(function() {
    if (!device_ready) {
        init_device();
    }
}, this);
boot_task.schedule(80);

// --- Handlers from Native Left Sidechain Spine & Native Bottom Band Strip ---
function set_sc_panel(v) {
    if (!device_ready || is_syncing_controls) return;
    sc_panel_open = v ? 1 : 0;
    set_named_val("sc_expand_btn", sc_panel_open);
    update_layout();
    save_state();
}

function toggle_sc_panel(v) {
    set_sc_panel(v);
}

function set_dyn_panel(v) {
    if (!device_ready || is_syncing_controls) return;
    dyn_panel_open = v ? 1 : 0;
    for (var s_idx = 0; s_idx < NUM_BANDS; s_idx++) {
        sync_band_strip_widgets(s_idx);
    }
    update_layout();
    save_state();
}

function click_band_dyn_dot(idx) {
    if (!device_ready || is_syncing_controls) return;
    var b_idx = clamp(idx, 0, NUM_BANDS - 1);
    if (dyn_panel_open && selected_band === b_idx) {
        dyn_panel_open = 0;
    } else {
        selected_band = b_idx;
        dyn_panel_open = 1;
        outlet(0, "select", selected_band);
        sync_selected_band_controls();
    }
    for (var s_idx = 0; s_idx < NUM_BANDS; s_idx++) {
        sync_band_strip_widgets(s_idx);
    }
    update_layout();
    save_state();
}

function ui_band_sel(idx) {
    if (!device_ready || is_syncing_controls) return;
    select_band(idx);
}

function ui_band_on(idx, v) {
    if (!device_ready || is_syncing_controls) return;
    bands[idx].active = v ? 1 : 0;
    outlet(1, "b" + (idx + 1) + "_on", bands[idx].active);
    sync_band_to_ui(idx);
    select_band(idx);
}

function ui_band_type(idx, v) {
    if (!device_ready || is_syncing_controls) return;
    band_type(idx, v);
    if (!bands[idx].active) {
        bands[idx].active = 1;
        outlet(1, "b" + (idx + 1) + "_on", 1);
        sync_band_to_ui(idx);
    }
    select_band(idx);
}

// --- Handlers from Dedicated Global & Sidechain Controls ---
function ui_dyn_scale(v) {
    if (is_syncing_controls) return;
    global_scale = clamp(v, 0.0, 200.0);
    outlet(1, "dyn_scale", global_scale / 100.0);
    outlet(0, "set_scale", global_scale);
    save_state();
}

function ui_scale(v) {
    ui_dyn_scale(v);
}

function ui_out_gain(v) {
    if (is_syncing_controls) return;
    out_gain = clamp(v, -24.0, 24.0);
    outlet(1, "out_gain", out_gain);
    save_state();
}

function ui_adapt_q(v) {
    if (is_syncing_controls) return;
    adaptive_q = v ? 1 : 0;
    outlet(1, "adapt_q", adaptive_q);
    outlet(0, "set_adaptive_q", adaptive_q);
    save_state();
}

function ui_rta_on(v) {
    if (!device_ready || is_syncing_controls) return;
    rta_on = v ? 1 : 0;
    outlet(0, "set_rta_on", rta_on);
    save_state();
}

function ui_solo(v) {
    if (!device_ready || is_syncing_controls) return;
    solo_band = v ? 1 : 0;
    update_solo_dsp();
    save_state();
}

function ui_sc_listen(v) {
    if (!device_ready || is_syncing_controls) return;
    sc_listen = v ? 1 : 0;
    update_solo_dsp();
    save_state();
}

function ui_sc_a_en(v) {
    if (is_syncing_controls) return;
    sc1_enable = v ? 1 : 0;
    update_sc_dsp();
    save_state();
}

function ui_sc1_mix(v) {
    if (is_syncing_controls) return;
    sc1_mix = clamp(v, 0.0, 100.0);
    update_sc_dsp();
    save_state();
}

function ui_sc1_gain(v) {
    if (is_syncing_controls) return;
    sc1_gain = clamp(v, -24.0, 24.0);
    save_state();
}

function ui_sc_b_en(v) {
    if (is_syncing_controls) return;
    sc2_enable = v ? 1 : 0;
    update_sc_dsp();
    save_state();
}

function ui_sc2_mix(v) {
    if (is_syncing_controls) return;
    sc2_mix = clamp(v, 0.0, 100.0);
    update_sc_dsp();
    save_state();
}

function ui_sc2_gain(v) {
    if (is_syncing_controls) return;
    sc2_gain = clamp(v, -24.0, 24.0);
    save_state();
}

// --- Sidechain live.routing Handlers (Matching Official Max 9 `live.routing` Snippet) ---
function apply_umenu_sym(varname, sym) {
    if (sym === null || sym === undefined) return;
    var menu = get_box(varname);
    if (!menu) return;
    if (typeof sym === "number") {
        menu.message("set", sym);
    } else {
        menu.message("setsymbol", sym);
    }
}

function populate_umenu(varname, items, cur_sym) {
    var menu = get_box(varname);
    if (!menu) return;
    menu.message("clear");
    if (!items || items.length === 0) {
        menu.message("append", "No Input");
        return;
    }
    for (var i = 0; i < items.length; i++) {
        if (items[i] !== "<none>") {
            menu.message("append", items[i]);
        }
    }
    if (cur_sym !== null && cur_sym !== undefined) {
        apply_umenu_sym(varname, cur_sym);
    }
}

function rt1_types() {
    rt1_type_list = arrayfromargs(arguments);
    populate_umenu("sc1_track_menu", rt1_type_list, rt1_cur_type_sym);
}

function rt1_chans() {
    rt1_chan_list = arrayfromargs(arguments);
    populate_umenu("sc1_chan_menu", rt1_chan_list, rt1_cur_chan_sym);
}

function rt1_cur_type(v) {
    rt1_cur_type_sym = v;
    apply_umenu_sym("sc1_track_menu", v);
}

function rt1_cur_chan(v) {
    rt1_cur_chan_sym = v;
    apply_umenu_sym("sc1_chan_menu", v);
}

function set_sc1_track(idx) {
    if (!device_ready) return;
    outlet(3, "type", idx);
}

function set_sc1_chan(idx) {
    if (!device_ready) return;
    outlet(3, "channel", idx);
}

function rt2_types() {
    rt2_type_list = arrayfromargs(arguments);
    populate_umenu("sc2_track_menu", rt2_type_list, rt2_cur_type_sym);
}

function rt2_chans() {
    rt2_chan_list = arrayfromargs(arguments);
    populate_umenu("sc2_chan_menu", rt2_chan_list, rt2_cur_chan_sym);
}

function rt2_cur_type(v) {
    rt2_cur_type_sym = v;
    apply_umenu_sym("sc2_track_menu", v);
}

function rt2_cur_chan(v) {
    rt2_cur_chan_sym = v;
    apply_umenu_sym("sc2_chan_menu", v);
}

function set_sc2_track(idx) {
    if (!device_ready) return;
    outlet(4, "type", idx);
}

function set_sc2_chan(idx) {
    if (!device_ready) return;
    outlet(4, "channel", idx);
}

// --- Handlers from Shared Single-Band Inspector Controls (Left Strip & Right Dynamic Panel) ---
function ui_freq(v) {
    if (!device_ready || is_syncing_controls) return;
    var b = bands[selected_band];
    b.freq = clamp(v, 20.0, 20000.0);
    outlet(1, "b" + (selected_band + 1) + "_freq", b.freq);
    sync_band_to_ui(selected_band);
    save_state();
}

function ui_gain(v) {
    if (!device_ready || is_syncing_controls) return;
    var b = bands[selected_band];
    b.gain = clamp(v, -15.0, 15.0);
    outlet(1, "b" + (selected_band + 1) + "_gain", b.gain);
    sync_band_to_ui(selected_band);
    save_state();
}

function ui_q(v) {
    if (!device_ready || is_syncing_controls) return;
    var b = bands[selected_band];
    b.q = clamp(v, 0.1, 18.0);
    outlet(1, "b" + (selected_band + 1) + "_q", b.q);
    sync_band_to_ui(selected_band);
    save_state();
}

function ui_type(v) {
    if (!device_ready || is_syncing_controls) return;
    var b = bands[selected_band];
    b.type = clamp(Math.round(v), 0, 7);
    outlet(1, "b" + (selected_band + 1) + "_type", b.type);
    sync_band_to_ui(selected_band);
    save_state();
}

function ui_dyn_on(v) {
    if (!device_ready || is_syncing_controls) return;
    var b = bands[selected_band];
    b.dyn_on = v ? 1 : 0;
    outlet(1, "b" + (selected_band + 1) + "_dyn_on", b.dyn_on);
    sync_band_to_ui(selected_band);
    save_state();
}

function ui_dyndepth(v) {
    if (!device_ready || is_syncing_controls) return;
    var b = bands[selected_band];
    b.range = clamp(v, -15.0, 15.0);
    if (Math.abs(b.range) > 0.05 && !b.dyn_on) {
        b.dyn_on = 1;
        outlet(1, "b" + (selected_band + 1) + "_dyn_on", 1);
        set_named_val("band_dyn_on", 1);
    }
    outlet(1, "b" + (selected_band + 1) + "_dyn_range", b.range);
    sync_band_to_ui(selected_band);
    save_state();
}

function ui_thresh(v) {
    if (!device_ready || is_syncing_controls) return;
    var b = bands[selected_band];
    b.thresh = clamp(v, -60.0, 0.0);
    outlet(1, "b" + (selected_band + 1) + "_thresh", b.thresh);
    sync_band_to_ui(selected_band);
    save_state();
}

function ui_attack(v) {
    if (!device_ready || is_syncing_controls) return;
    var b = bands[selected_band];
    b.atk = clamp(v, 0.1, 250.0);
    outlet(1, "b" + (selected_band + 1) + "_attack", b.atk);
    save_state();
}

function ui_release(v) {
    if (!device_ready || is_syncing_controls) return;
    var b = bands[selected_band];
    b.rel = clamp(v, 5.0, 1000.0);
    outlet(1, "b" + (selected_band + 1) + "_release", b.rel);
    save_state();
}

function ui_source(v) {
    if (!device_ready || is_syncing_controls) return;
    var b = bands[selected_band];
    b.sc_src = clamp(Math.round(v), 0, 2);
    outlet(1, "b" + (selected_band + 1) + "_source", b.sc_src);
    save_state();
}

// --- Handlers from JSUI Curve Editor ---
function select_band(idx) {
    selected_band = clamp(idx, 0, NUM_BANDS - 1);
    outlet(0, "select", selected_band);
    if (solo_band) update_solo_dsp();
    sync_selected_band_controls();
    save_state();
}

function band_fg(idx, f, g) {
    if (idx < 0 || idx >= NUM_BANDS) return;
    var b = bands[idx];
    b.freq = clamp(f, 20.0, 20000.0);
    b.gain = clamp(g, -15.0, 15.0);
    var p = "b" + (idx + 1) + "_";
    outlet(1, p + "freq", b.freq);
    outlet(1, p + "gain", b.gain);
    if (idx === selected_band) {
        drag_tick = (drag_tick + 1) & 1;
        if (drag_tick === 0) {
            set_named_val("band_freq", b.freq);
            set_named_val("band_gain", b.gain);
        }
    }
    save_tick = (save_tick + 1) & 3;
    if (save_tick === 0) {
        save_state();
    }
}

function band_q(idx, q_val) {
    if (idx < 0 || idx >= NUM_BANDS) return;
    var b = bands[idx];
    b.q = clamp(q_val, 0.1, 18.0);
    outlet(1, "b" + (idx + 1) + "_q", b.q);
    if (idx === selected_band) {
        set_named_val("band_q", b.q);
    }
    save_state();
}

function band_range(idx, r_val) {
    if (idx < 0 || idx >= NUM_BANDS) return;
    var b = bands[idx];
    b.range = clamp(r_val, -15.0, 15.0);
    b.dyn_on = (Math.abs(b.range) > 0.05) ? 1 : b.dyn_on;
    var p = "b" + (idx + 1) + "_";
    outlet(1, p + "dyn_range", b.range);
    outlet(1, p + "dyn_on", b.dyn_on);
    sync_band_strip_widgets(idx);
    if (idx === selected_band) {
        set_named_val("band_dyndepth", b.range);
        set_named_val("band_dyn_on", b.dyn_on);
    }
    save_tick = (save_tick + 1) & 3;
    if (save_tick === 0) {
        save_state();
    }
}

function drag_end(idx) {
    if (idx === selected_band) {
        sync_selected_band_controls();
    }
    save_state();
}

function band_dyn_on(idx, state) {
    if (idx < 0 || idx >= NUM_BANDS) return;
    bands[idx].dyn_on = state ? 1 : 0;
    outlet(1, "b" + (idx + 1) + "_dyn_on", bands[idx].dyn_on);
    sync_band_strip_widgets(idx);
    if (idx === selected_band) {
        set_named_val("band_dyn_on", bands[idx].dyn_on);
    }
    save_state();
}

function band_active(idx, state) {
    if (idx < 0 || idx >= NUM_BANDS) return;
    bands[idx].active = state ? 1 : 0;
    outlet(1, "b" + (idx + 1) + "_on", bands[idx].active);
    sync_band_to_ui(idx);
    if (idx === selected_band) {
        sync_selected_band_controls();
    }
    save_state();
}

function band_type(idx, t) {
    if (idx < 0 || idx >= NUM_BANDS) return;
    bands[idx].type = clamp(Math.round(t), 0, 7);
    outlet(1, "b" + (idx + 1) + "_type", bands[idx].type);
    sync_band_to_ui(idx);
    save_state();
}

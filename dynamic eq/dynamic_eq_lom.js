// dynamic_eq_lom.js
// Standalone 8-Band Dynamic EQ Eight Controller, Routing Manager & Width Manager
// Exact Ableton EQ Eight dimensions:
// - Far-left vertical Sidechain Strip (sc_bar): 22px (x=0..22)
// - Left Expandable Sidechain Drawer: +154px (when (▶) on Sidechain strip is open)
// - Left Strip (Freq / Gain / Q): 45px + 2px divider
// - Center Graph + 8 Bottom Band Cards (eq_graph): 370px + 2px divider
// - Right Strip (Top Icons, clean whitespace, Adapt. Q, Scale, Gain): 50px
// - Base Collapsed Width: 491px (22px SC bar + 469px EQ Eight core)
// - Right Expandable Per-Band Dynamic Drawer: +130px (opened by clicking the
//   minimalistic Dynamics Circle next to any band's activator toggle in the bottom row)

autowatch = 1;
inlets = 1;
outlets = 5;
// Outlet 0 -> jsui eq_graph messages
// Outlet 1 -> gen~ DSP parameter messages
// Outlet 2 -> live.thisdevice ("setwidth <px>")
// Outlet 3 -> live.routing (Sidechain A, Inlets 3/4)
// Outlet 4 -> live.routing (Sidechain B, Inlets 5/6)

var NUM_BANDS = 8;
var selected_band = 0; // 0..7
var sc_panel_open = 0;  // Left Sidechain panel (0 or 1, +154px)
var dyn_panel_open = 0; // Right Dynamic panel (0 or 1, +130px)

var SC_W = 154;
var BASE_W = 491; // 22 (SC bar) + 469 (EQ8 core) = 491px
var DYN_W = 130;

var global_scale = 100.0;
var out_gain = 0.0;
var adaptive_q = 1;
var rta_on = 1;
var solo_band = 0;
var sc_listen = 0;

var sc1_enable = 1;
var sc1_mix = 100.0;
var sc2_enable = 1;
var sc2_mix = 100.0;

var rt1_type_list = [];
var rt1_chan_list = [];
var rt2_type_list = [];
var rt2_chan_list = [];

var DEFAULT_FREQS = [30.0, 200.0, 1000.0, 5000.0, 100.0, 1000.0, 5000.0, 18000.0];
var DEFAULT_TYPES = [1, 3, 3, 5, 3, 3, 3, 6];
var bands = [];

for (var i = 0; i < NUM_BANDS; i++) {
    bands.push({
        active: (i < 4) ? 1 : 0,
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

// --- Dynamic Layout & Device Width Management ---
function update_layout() {
    var x_off = sc_panel_open ? SC_W : 0;
    var total_w = BASE_W + x_off + (dyn_panel_open ? DYN_W : 0);

    // 0. Far-left vertical Sidechain strip (always at x=0, y=0, w=22, h=169)
    set_box_rect("sc_bar", 0, 0, 22, 169, 1);

    var sc_bar_obj = get_box("sc_bar");
    if (sc_bar_obj) {
        sc_bar_obj.message("set_open", sc_panel_open);
    }

    // 1. Left Expandable Sidechain Panel (x = 22 .. 176 when sc_panel_open == 1)
    var sc_vis = sc_panel_open ? 1 : 0;
    var sx = 22;
    set_box_rect("sc_bot_bar", sx, 167, SC_W, 2, sc_vis);
    set_box_rect("sc_col_div", sx + 75, 4, 1, 160, sc_vis);
    set_box_rect("sc_right_div", sx + SC_W - 2, 0, 2, 169, sc_vis);

    // Column 1: Sidechain A (Ext. A)
    set_box_rect("sc_a_btn", sx + 4, 5, 68, 13, sc_vis);
    set_box_rect("lbl_src_a", sx + 18, 22, 48, 13, sc_vis);
    set_box_rect("sc1_track_menu", sx + 4, 36, 68, 15, sc_vis);
    set_box_rect("sc1_chan_menu", sx + 4, 53, 68, 15, sc_vis);
    set_box_rect("lbl_mix_a", sx + 23, 76, 36, 13, sc_vis);
    set_box_rect("sc1_mix", sx + 4, 90, 68, 13, sc_vis);
    set_box_rect("lbl_sc1_gain", sx + 14, 114, 54, 13, sc_vis);
    set_box_rect("sc1_gain", sx + 4, 128, 68, 13, sc_vis);

    // Column 2: Sidechain B (Ext. B)
    set_box_rect("sc_b_btn", sx + 80, 5, 68, 13, sc_vis);
    set_box_rect("lbl_src_b", sx + 94, 22, 48, 13, sc_vis);
    set_box_rect("sc2_track_menu", sx + 80, 36, 68, 15, sc_vis);
    set_box_rect("sc2_chan_menu", sx + 80, 53, 68, 15, sc_vis);
    set_box_rect("lbl_mix_b", sx + 99, 76, 36, 13, sc_vis);
    set_box_rect("sc2_mix", sx + 80, 90, 68, 13, sc_vis);
    set_box_rect("lbl_sc2_gain", sx + 90, 114, 54, 13, sc_vis);
    set_box_rect("sc2_gain", sx + 80, 128, 68, 13, sc_vis);

    // 2. EQ Eight Left Strip (Freq / Gain / Q, width = 45px: x = 22+x_off .. 67+x_off)
    set_box_rect("band_freq", 22 + x_off, 2, 45, 50, 1);
    set_box_rect("band_gain", 22 + x_off, 56, 45, 50, 1);
    set_box_rect("band_q",    22 + x_off, 112, 45, 50, 1);
    set_box_rect("left_bot_bar", 22 + x_off, 167, 45, 2, 1);
    set_box_rect("div_left_graph", 67 + x_off, 0, 2, 169, 1);

    // 3. Center EQ Eight Graph + 8 Bottom Band Cards (width = 370px, height = 169px)
    set_box_rect("eq_graph", 69 + x_off, 0, 370, 169, 1);
    set_box_rect("div_graph_right", 439 + x_off, 0, 2, 169, 1);

    // 4. EQ Eight Right Strip (width = 50px: x = 441+x_off .. 491+x_off, inner controls width = 44px at x = 444+x_off)
    //    Clean whitespace between Top Icons (y=5..18) and Adapt. Q (y=77)!
    var rx = 444 + x_off;
    set_box_rect("right_bot_bar", 441 + x_off, 167, 50, 2, 1);
    set_box_rect("top_icons", rx, 5, 44, 13, 1);
    set_box_rect("lbl_adaptq", rx - 2, 77, 48, 13, 1);
    set_box_rect("adapt_q_btn", rx, 90, 44, 13, 1);
    set_box_rect("lbl_scale", rx - 2, 106, 48, 13, 1);
    set_box_rect("dyn_scale", rx, 119, 44, 13, 1);
    set_box_rect("lbl_outgain", rx - 2, 135, 48, 13, 1);
    set_box_rect("out_gain", rx, 148, 44, 13, 1);

    // 5. Right Expandable Per-Band Dynamic Panel (+130px at x = 491+x_off when dyn_panel_open == 1)
    var dyn_vis = dyn_panel_open ? 1 : 0;
    var dx = 491 + x_off;
    set_box_rect("div_right_dyn", dx, 0, 2, 169, dyn_vis);
    set_box_rect("dyn_bot_bar", dx + 2, 167, DYN_W - 2, 2, dyn_vis);
    set_box_rect("dyn_band_lbl", dx + 6, 5, 74, 14, dyn_vis);
    set_box_rect("band_dyn_on",  dx + 82, 5, 42, 13, dyn_vis);

    set_box_rect("lbl_src",      dx + 6, 26, 30, 14, dyn_vis);
    set_box_rect("band_source",  dx + 36, 26, 88, 14, dyn_vis);

    set_box_rect("lbl_range",    dx + 6, 52, 62, 14, dyn_vis);
    set_box_rect("band_dyndepth", dx + 68, 52, 56, 13, dyn_vis);

    set_box_rect("lbl_thresh",   dx + 6, 76, 62, 14, dyn_vis);
    set_box_rect("band_thresh",  dx + 68, 76, 56, 13, dyn_vis);

    set_box_rect("lbl_attack",   dx + 6, 100, 62, 14, dyn_vis);
    set_box_rect("band_attack",  dx + 68, 100, 56, 13, dyn_vis);

    set_box_rect("lbl_release",  dx + 6, 124, 62, 14, dyn_vis);
    set_box_rect("band_release", dx + 68, 124, 56, 13, dyn_vis);

    outlet(0, "set_dyn_open", dyn_panel_open);

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
}

function update_solo_dsp() {
    var s_val = 0;
    if (sc_listen) {
        s_val = 9;
    } else if (solo_band) {
        s_val = selected_band + 1;
    }
    outlet(1, "solo_band", s_val);
    var top_ic = get_box("top_icons");
    if (top_ic) top_ic.message("set_solo", solo_band);
}

function update_sc_dsp() {
    var eff1 = sc1_enable ? clamp(sc1_mix / 100.0, 0.0, 1.0) : 0.0;
    var eff2 = sc2_enable ? clamp(sc2_mix / 100.0, 0.0, 1.0) : 0.0;
    outlet(1, "sc1_mix", eff1);
    outlet(1, "sc2_mix", eff2);
    var sc_bar = get_box("sc_bar");
    if (sc_bar) sc_bar.message("set_active", (sc1_enable || sc2_enable) ? 1 : 0);
}

function sync_selected_band_controls() {
    var b = bands[selected_band];
    set_named_val("band_freq", b.freq);
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
    var sc_bar = get_box("sc_bar");
    if (sc_bar) {
        sc_bar.message("set_open", sc_panel_open);
        sc_bar.message("set_listen", sc_listen);
        sc_bar.message("set_active", (sc1_enable || sc2_enable) ? 1 : 0);
    }
    var top_ic = get_box("top_icons");
    if (top_ic) {
        top_ic.message("set_solo", solo_band);
        top_ic.message("set_rta", rta_on);
    }
    update_solo_dsp();
}

function sync_all() {
    outlet(1, "dyn_scale", global_scale / 100.0);
    outlet(1, "out_gain", out_gain);
    outlet(1, "adapt_q", adaptive_q);
    outlet(1, "rta_active", rta_on);
    update_sc_dsp();
    update_solo_dsp();

    outlet(0, "set_scale", global_scale);
    outlet(0, "set_adaptive_q", adaptive_q);
    outlet(0, "set_rta_on", rta_on);
    outlet(0, "set_dyn_open", dyn_panel_open);
    outlet(0, "select", selected_band);

    for (var i = 0; i < NUM_BANDS; i++) {
        sync_band_to_dsp(i);
        sync_band_to_ui(i);
    }
    sync_selected_band_controls();
}

function loadbang() {
    obj_cache = {};
    update_layout();
    sync_all();
}

function init_device() {
    obj_cache = {};
    update_layout();
    sync_all();
    outlet(3, "getavailable_routing_types");
    outlet(3, "getavailable_routing_channels");
    outlet(4, "getavailable_routing_types");
    outlet(4, "getavailable_routing_channels");
}

// --- Handlers from Left Sidechain Strip & Bottom Band Dynamics Circle ---
function set_sc_panel(v) {
    sc_panel_open = v ? 1 : 0;
    update_layout();
}

function toggle_sc_panel(v) {
    set_sc_panel(v);
}

function set_dyn_panel(v) {
    dyn_panel_open = v ? 1 : 0;
    update_layout();
}

function click_band_dyn_dot(idx) {
    var b_idx = clamp(idx, 0, NUM_BANDS - 1);
    if (dyn_panel_open && selected_band === b_idx) {
        // Clicking the open band's dynamics circle again closes the right drawer
        dyn_panel_open = 0;
    } else {
        // Select this band and open the right dynamics drawer
        selected_band = b_idx;
        dyn_panel_open = 1;
        outlet(0, "select", selected_band);
        sync_selected_band_controls();
    }
    update_layout();
}

// --- Handlers from Global Controls ---
function ui_dyn_scale(v) {
    global_scale = clamp(v, 0.0, 200.0);
    outlet(1, "dyn_scale", global_scale / 100.0);
    outlet(0, "set_scale", global_scale);
}

function ui_scale(v) {
    ui_dyn_scale(v);
}

function ui_out_gain(v) {
    out_gain = clamp(v, -24.0, 24.0);
    outlet(1, "out_gain", out_gain);
}

function ui_adapt_q(v) {
    adaptive_q = v ? 1 : 0;
    outlet(1, "adapt_q", adaptive_q);
    outlet(0, "set_adaptive_q", adaptive_q);
}

function ui_rta_on(v) {
    rta_on = v ? 1 : 0;
    outlet(1, "rta_active", rta_on);
    outlet(0, "set_rta_on", rta_on);
}

function ui_solo(v) {
    solo_band = v ? 1 : 0;
    update_solo_dsp();
}

function ui_sc_listen(v) {
    sc_listen = v ? 1 : 0;
    update_solo_dsp();
}

function ui_sc_a_en(v) {
    sc1_enable = v ? 1 : 0;
    update_sc_dsp();
}

function ui_sc1_mix(v) {
    sc1_mix = clamp(v, 0.0, 100.0);
    update_sc_dsp();
}

function ui_sc_b_en(v) {
    sc2_enable = v ? 1 : 0;
    update_sc_dsp();
}

function ui_sc2_mix(v) {
    sc2_mix = clamp(v, 0.0, 100.0);
    update_sc_dsp();
}

// --- Sidechain live.routing Handlers ---
function populate_umenu(varname, items) {
    var menu = get_box(varname);
    if (!menu) return;
    menu.message("clear");
    if (!items || items.length === 0) {
        menu.message("append", "No Input");
        return;
    }
    for (var i = 0; i < items.length; i++) {
        menu.message("append", items[i]);
    }
}

function rt1_types() {
    rt1_type_list = arrayfromargs(arguments);
    populate_umenu("sc1_track_menu", rt1_type_list);
}

function rt1_chans() {
    rt1_chan_list = arrayfromargs(arguments);
    populate_umenu("sc1_chan_menu", rt1_chan_list);
}

function rt1_cur_type() {}
function rt1_cur_chan() {}

function set_sc1_track(idx) {
    if (idx >= 0 && idx < rt1_type_list.length) {
        outlet(3, "routing_type", rt1_type_list[idx]);
    }
}

function set_sc1_chan(idx) {
    if (idx >= 0 && idx < rt1_chan_list.length) {
        outlet(3, "routing_channel", rt1_chan_list[idx]);
    }
}

function rt2_types() {
    rt2_type_list = arrayfromargs(arguments);
    populate_umenu("sc2_track_menu", rt2_type_list);
}

function rt2_chans() {
    rt2_chan_list = arrayfromargs(arguments);
    populate_umenu("sc2_chan_menu", rt2_chan_list);
}

function rt2_cur_type() {}
function rt2_cur_chan() {}

function set_sc2_track(idx) {
    if (idx >= 0 && idx < rt2_type_list.length) {
        outlet(4, "routing_type", rt2_type_list[idx]);
    }
}

function set_sc2_chan(idx) {
    if (idx >= 0 && idx < rt2_chan_list.length) {
        outlet(4, "routing_channel", rt2_chan_list[idx]);
    }
}

// --- Handlers from Selected Band Controls ---
function select_band(idx) {
    selected_band = clamp(idx, 0, NUM_BANDS - 1);
    outlet(0, "select", selected_band);
    sync_selected_band_controls();
}

function ui_freq(v) {
    var b = bands[selected_band];
    b.freq = clamp(v, 20.0, 20000.0);
    outlet(1, "b" + (selected_band + 1) + "_freq", b.freq);
    sync_band_to_ui(selected_band);
}

function ui_gain(v) {
    var b = bands[selected_band];
    b.gain = clamp(v, -15.0, 15.0);
    outlet(1, "b" + (selected_band + 1) + "_gain", b.gain);
    sync_band_to_ui(selected_band);
}

function ui_q(v) {
    var b = bands[selected_band];
    b.q = clamp(v, 0.1, 18.0);
    outlet(1, "b" + (selected_band + 1) + "_q", b.q);
    sync_band_to_ui(selected_band);
}

function ui_dyn_on(v) {
    var b = bands[selected_band];
    b.dyn_on = v ? 1 : 0;
    outlet(1, "b" + (selected_band + 1) + "_dyn_on", b.dyn_on);
    sync_band_to_ui(selected_band);
}

function ui_dyndepth(v) {
    var b = bands[selected_band];
    b.range = clamp(v, -24.0, 24.0);
    if (Math.abs(b.range) > 0.05 && !b.dyn_on) {
        b.dyn_on = 1;
        set_named_val("band_dyn_on", 1);
        outlet(1, "b" + (selected_band + 1) + "_dyn_on", 1);
    }
    outlet(1, "b" + (selected_band + 1) + "_dyn_range", b.range);
    sync_band_to_ui(selected_band);
}

function ui_thresh(v) {
    var b = bands[selected_band];
    b.thresh = clamp(v, -60.0, 0.0);
    outlet(1, "b" + (selected_band + 1) + "_thresh", b.thresh);
    sync_band_to_ui(selected_band);
}

function ui_attack(v) {
    var b = bands[selected_band];
    b.atk = clamp(v, 0.1, 500.0);
    outlet(1, "b" + (selected_band + 1) + "_attack", b.atk);
}

function ui_release(v) {
    var b = bands[selected_band];
    b.rel = clamp(v, 5.0, 2000.0);
    outlet(1, "b" + (selected_band + 1) + "_release", b.rel);
}

function ui_source(v) {
    var b = bands[selected_band];
    b.sc_src = clamp(Math.round(v), 0, 2);
    outlet(1, "b" + (selected_band + 1) + "_source", b.sc_src);
}

// --- High-Speed Handlers from JSUI Graph Direct Manipulation ---
function band_active(idx, v) {
    if (idx < 0 || idx >= NUM_BANDS) return;
    bands[idx].active = v ? 1 : 0;
    outlet(1, "b" + (idx + 1) + "_on", bands[idx].active);
    sync_band_to_ui(idx);
}

function band_type(idx, v) {
    if (idx < 0 || idx >= NUM_BANDS) return;
    bands[idx].type = clamp(Math.round(v), 0, 7);
    outlet(1, "b" + (idx + 1) + "_type", bands[idx].type);
    sync_band_to_ui(idx);
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
        set_named_val("band_freq", b.freq);
        set_named_val("band_gain", b.gain);
    }
}

function band_freq(idx, v) {
    if (idx < 0 || idx >= NUM_BANDS) return;
    bands[idx].freq = clamp(v, 20.0, 20000.0);
    outlet(1, "b" + (idx + 1) + "_freq", bands[idx].freq);
    if (idx === selected_band) set_named_val("band_freq", bands[idx].freq);
}

function band_gain(idx, v) {
    if (idx < 0 || idx >= NUM_BANDS) return;
    bands[idx].gain = clamp(v, -15.0, 15.0);
    outlet(1, "b" + (idx + 1) + "_gain", bands[idx].gain);
    if (idx === selected_band) set_named_val("band_gain", bands[idx].gain);
}

function band_q(idx, v) {
    if (idx < 0 || idx >= NUM_BANDS) return;
    bands[idx].q = clamp(v, 0.1, 18.0);
    outlet(1, "b" + (idx + 1) + "_q", bands[idx].q);
    if (idx === selected_band) set_named_val("band_q", bands[idx].q);
}

function band_dyn_on(idx, v) {
    if (idx < 0 || idx >= NUM_BANDS) return;
    bands[idx].dyn_on = v ? 1 : 0;
    outlet(1, "b" + (idx + 1) + "_dyn_on", bands[idx].dyn_on);
    if (idx === selected_band) {
        set_named_val("band_dyn_on", bands[idx].dyn_on);
    }
}

function band_range(idx, v) {
    if (idx < 0 || idx >= NUM_BANDS) return;
    bands[idx].range = clamp(v, -24.0, 24.0);
    if (Math.abs(bands[idx].range) > 0.05 && !bands[idx].dyn_on) {
        bands[idx].dyn_on = 1;
        outlet(1, "b" + (idx + 1) + "_dyn_on", 1);
        if (idx === selected_band) set_named_val("band_dyn_on", 1);
    }
    outlet(1, "b" + (idx + 1) + "_dyn_range", bands[idx].range);
    if (idx === selected_band) {
        set_named_val("band_dyndepth", bands[idx].range);
    }
}

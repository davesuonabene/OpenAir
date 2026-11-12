// deq_eight_lom_v3.js
// Native-Component Controller, State Persistence Manager, Dynamic Theme/Zombie Sync & Width Manager
// for OpenAir dEQ Eight v3 (`dEQ Eight v3 dev.amxd` / `dEQ Eight Alpha v0.04.amxd`)
// - Manages 100% vanilla Max/M4L UI components (`panel`, `live.line`, `live.text`, `live.menu`, `umenu`, `live.comment`).
// - Persists all 8 EQ bands, dynamic parameters, and UI drawer/selection state via M4L `pattr eq_state` Blob.
// - Queries `live.colors` (`everything`) whenever Ableton's theme changes, forwarding dynamic colors to `deq_eight_ui_v3.js`
//   and syncing stock EQ Eight zombie states on Left-Strip Dials (`Freq`, `Gain`, `Q`) and Band Strip numbers (`1..8`).

autowatch = 1;
inlets = 1;
outlets = 6;
// Outlet 0 -> jsui eq_graph (`deq_eight_ui_v3.js`) messages
// Outlet 1 -> gen~ DSP parameter messages
// Outlet 2 -> live.thisdevice ("setwidth <px>")
// Outlet 3 -> live.routing (Sidechain A, Inlets 3/4, index 1)
// Outlet 4 -> live.routing (Sidechain B, Inlets 5/6, index 2)
// Outlet 5 -> pattr eq_state @thru 2 (authoritative 104-float M4L state persistence)

var STATE_VERSION = 3;
var NUM_BANDS = 8;

var device_ready = 0;
var state_restored = 0;
var is_syncing_controls = 0;
var is_syncing_routing = 0;
var is_saving_state = 0;
var save_state_pending = 0;
var routing_initialized = 0;
var last_poll_active = -1;
var last_rta_muted = -1;

var selected_band = 2; // Default selected band = Band 3 (1.00 kHz), matching EQ Eight
var sc_panel_open = 0;  // Left Sidechain panel (0 or 1, +154px)
var dyn_panel_open = 0; // Right Dynamic panel (0 or 1, +78px)

var SC_W = 154;
var BASE_W = 495; // 22 (SC bar) + 473 (EQ8 core) = 495px
var DYN_W = 78;

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
var rt1_type_map = [];
var rt1_chan_map = [];
var rt1_cur_type_sym = null;
var rt1_cur_chan_sym = null;
var rt2_type_list = [];
var rt2_chan_list = [];
var rt2_type_map = [];
var rt2_chan_map = [];
var rt2_cur_type_sym = null;
var rt2_cur_chan_sym = null;

var DEFAULT_FREQS = [30.0, 200.0, 1000.0, 5000.0, 100.0, 1000.0, 5000.0, 18000.0];
var DEFAULT_TYPES = [2, 3, 3, 5, 3, 3, 3, 6];
var DEFAULT_ACTIVE = [1, 1, 1, 1, 0, 0, 0, 0];
var bands = [];
var drag_tick = 0;
var is_graph_dragging = 0;

// --- 2-Click Native Dropdown Open/Close Toggle Guard (`live.menu` & `umenu`) ---
var DD_MENU_LIST = [
    "band_type_menu_0", "band_type_menu_1", "band_type_menu_2", "band_type_menu_3",
    "band_type_menu_4", "band_type_menu_5", "band_type_menu_6", "band_type_menu_7",
    "sc1_track_menu", "sc1_chan_menu", "sc2_track_menu", "sc2_chan_menu"
];
var DD_MENU_MAP = {};
for (var dmi = 0; dmi < DD_MENU_LIST.length; dmi++) {
    DD_MENU_MAP[DD_MENU_LIST[dmi]] = dmi + 1;
}
var dd_hover_id = 0;
var dd_open_id = 0;
var dd_last_id = 0;
var dd_last_mx = -99999;
var dd_last_my = -99999;
var dd_open_ms = 0;
var dd_locked = -1;

// Cached dynamic Ableton Live theme colors (initialized to Live 12 Default Dark Theme)
var LIVE_COLORS = {
    lcd_frame:         [0.278, 0.255, 0.329, 1.0],
    value_arc:         [0.224, 0.824, 0.894, 1.0],
    value_arc_zombie:  [0.514, 0.478, 0.561, 1.0],
    ui_text_on:        [0.827, 0.804, 0.843, 1.0],
    ui_text_zombie:    [0.514, 0.478, 0.561, 1.0]
};

var save_state_task = new Task(function() {
    save_state_now();
}, this);

var dd_lock_task = new Task(function() {
    if (dd_open_id > 0) {
        dd_set_ignoreclick(1);
    }
}, this);

var dd_unlock_task = new Task(function() {
    dd_open_id = 0;
    dd_set_ignoreclick(0);
}, this);

function notifydeleted() {
    if (save_state_task) save_state_task.cancel();
    if (dd_lock_task) dd_lock_task.cancel();
    if (dd_unlock_task) dd_unlock_task.cancel();
}

function freebang() {
    notifydeleted();
}

for (var i = 0; i < NUM_BANDS; i++) {
    bands.push({
        active: DEFAULT_ACTIVE[i],
        freq: DEFAULT_FREQS[i],
        gain: 0.0,
        q: 0.71,
        type: DEFAULT_TYPES[i],
        dyn_on: 0,
        range: 0.0,
        thresh: -22.0,
        atk: 5.0,
        rel: 110.0,
        sc_src: 0 // 0=Internal, 1=Ext. A, 2=Ext. B
    });
}

var obj_cache = {};
var rect_cache = {};
var last_device_width = -1;
var last_dial_zombie = -1;
var last_gain_enabled = -1;
var band_num_dim_cache = [-1, -1, -1, -1, -1, -1, -1, -1];

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

function is_gain_filter_type(t) {
    return (t === 2 || t === 3 || t === 5);
}

function set_box_rect(varname, x, y, w, h, vis) {
    var final_x = vis ? x : -500;
    var key = final_x + "," + y + "," + w + "," + h;
    if (rect_cache[varname] === key) return;
    var obj = get_box(varname);
    if (obj) {
        rect_cache[varname] = key;
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
// 2-CLICK NATIVE DROPDOWN OPEN/CLOSE TOGGLE GUARD (`live.menu` & `umenu`)
// ============================================================================
function dd_set_ignoreclick(flag) {
    var v = flag ? 1 : 0;
    if (dd_locked === v) return;
    dd_locked = v;
    for (var i = 0; i < DD_MENU_LIST.length; i++) {
        var m = get_box(DD_MENU_LIST[i]);
        if (m) {
            m.message("ignoreclick", v);
        }
    }
}

function dd_notify_selected() {
    if (dd_open_id > 0) {
        dd_last_id = 0;
        dd_lock_task.cancel();
        dd_unlock_task.schedule(40);
    }
}

function dd_hover_in(vname) {
    dd_hover_id = DD_MENU_MAP[vname] || 0;
    if (dd_open_id === 0) {
        dd_last_id = 0;
    }
}

function dd_hover_none() {
    dd_hover_id = 0;
    if (dd_open_id === 0) {
        dd_last_id = 0;
    }
}

function dd_hover_leave(vname) {
    var id = DD_MENU_MAP[vname] || 0;
    if (id > 0 && dd_hover_id === id) {
        dd_hover_id = 0;
    }
    if (dd_open_id === 0) {
        dd_last_id = 0;
    }
}

function dd_mouse(but, mx, my) {
    var b_down = Math.round(Number(but)) ? 1 : 0;
    var x = Number(mx) || 0;
    var y = Number(my) || 0;
    var now_ms = Date.now ? Date.now() : (new Date()).getTime();

    if (b_down === 1) {
        if (dd_open_id > 0) {
            if (Math.abs(x - dd_last_mx) <= 28 && Math.abs(y - dd_last_my) <= 11) {
                dd_last_mx = x;
                dd_last_my = y;
            } else {
                dd_last_id = 0;
            }
            dd_lock_task.cancel();
            dd_unlock_task.schedule(55);
        } else {
            var tid = dd_hover_id;
            if (tid === 0 && dd_last_id > 0 && Math.abs(x - dd_last_mx) <= 28 && Math.abs(y - dd_last_my) <= 11) {
                tid = dd_last_id;
            }
            if (tid > 0) {
                dd_open_id = tid;
                dd_last_id = tid;
                dd_last_mx = x;
                dd_last_my = y;
                dd_open_ms = now_ms;
                dd_unlock_task.cancel();
                dd_lock_task.schedule(15);
            }
        }
    } else {
        if (dd_open_id > 0 && (now_ms - dd_open_ms) > 220) {
            if (Math.abs(x - dd_last_mx) > 28 || Math.abs(y - dd_last_my) > 11) {
                dd_last_id = 0;
            }
            dd_lock_task.cancel();
            dd_unlock_task.schedule(55);
        }
    }
}

function dd_esc() {
    dd_lock_task.cancel();
    dd_unlock_task.cancel();
    dd_open_id = 0;
    dd_last_id = 0;
    dd_set_ignoreclick(0);
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

function save_state_now() {
    if (!device_ready) return;
    save_state_task.cancel();
    save_state_pending = 0;
    is_saving_state = 1;
    outlet(5, build_state_array());
    notifyclients();
    is_saving_state = 0;
}

function save_state() {
    if (!device_ready || is_graph_dragging) return;
    save_state_pending = 1;
    save_state_task.schedule(250);
}

function recall_state() {
    if (is_saving_state) return;
    save_state_task.cancel();
    save_state_pending = 0;
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
    if (is_saving_state) return;
    save_state_task.cancel();
    save_state_pending = 0;
    var args = arrayfromargs(arguments);
    if (apply_state_array(args)) {
        if (device_ready) {
            update_layout();
            sync_all();
        }
    }
}

// --- Stock EQ Eight Zombie & Filter-Shape Visual State Sync ---
function sync_inspector_visual_state(force) {
    var b = bands[selected_band];
    if (!b) return;

    var is_zombie = b.active ? 0 : 1;
    if (force || is_zombie !== last_dial_zombie) {
        last_dial_zombie = is_zombie;
        var arc_col = is_zombie ? LIVE_COLORS.value_arc_zombie : LIVE_COLORS.value_arc;
        var d_names = ["band_freq", "band_gain", "band_q"];
        for (var di = 0; di < d_names.length; di++) {
            var d_obj = get_box(d_names[di]);
            if (d_obj) {
                d_obj.message("activedialcolor", arc_col[0], arc_col[1], arc_col[2], arc_col[3]);
            }
        }
    }

    var gain_en = is_gain_filter_type(b.type) ? 1 : 0;
    if (force || gain_en !== last_gain_enabled) {
        last_gain_enabled = gain_en;
        var g_dial = get_box("band_gain");
        if (g_dial) {
            g_dial.message("active", gain_en);
        }
        var g_lbl = get_box("lbl_gain");
        if (g_lbl) {
            var tc_col = gain_en ? LIVE_COLORS.ui_text_on : LIVE_COLORS.ui_text_zombie;
            g_lbl.message("textcolor", tc_col[0], tc_col[1], tc_col[2], tc_col[3]);
        }
    }
}

function sync_band_number_color(idx, force) {
    var b = bands[idx];
    if (!b) return;
    if (!force && band_num_dim_cache[idx] === 1) return;
    band_num_dim_cache[idx] = 1;
    var sbtn = get_box("band_sel_btn_" + idx);
    if (sbtn) {
        var col = LIVE_COLORS.ui_text_on;
        sbtn.message("textcolor", col[0], col[1], col[2], col[3]);
        sbtn.message("activefgcolor", col[0], col[1], col[2], col[3]);
    }
}

// --- Update Native Bottom 8-Band Cards (Selection, Activator, Filter Curve Menu, Dyn Ring) ---
function update_band_strip_layout(gx) {
    set_box_rect("lcd_bezel_bg", gx - 2, 0, 374, 169, 1);
    var slot_w = 372.0 / NUM_BANDS; // 46.5px
    var sel_dcx = -500;

    for (var c = 0; c < NUM_BANDS; c++) {
        var cx0 = gx + Math.round(c * slot_w);
        var cx1 = (c === NUM_BANDS - 1) ? (gx + 370) : (gx + Math.round((c + 1) * slot_w - 2.0));
        var cw = cx1 - cx0; // 45px
        var is_sel = (c === selected_band);

        // Unselected cards show recessed `live_surface_bg` panel; selected card hides it to reveal `lcd_bezel_bg` tab
        set_box_rect("band_card_bg_" + c, cx0, 134, cw, 33, is_sel ? 0 : 1);

        // Top row: Vanilla `live.menu` Filter Curve dropdown (41x15.5, left-aligned full-bleed SVG)
        var ddx = cx0 + 2.0;
        var ddw = cw - 4.0;
        set_box_rect("band_type_menu_" + c, ddx, 134.5, ddw, 15.5, 1);

        // Bottom row left: 13x13 Band Activator Square
        set_box_rect("band_on_btn_" + c, ddx, 152.5, 13, 13, 1);

        // Bottom row center: Band Number 1..8 selector
        set_box_rect("band_sel_btn_" + c, cx0 + 15.0, 151.5, 15, 14, 1);

        // Bottom row right: 13x13 Vector SVG Dynamics Circle Toggle
        var dcx = ddx + ddw - 13.0;
        set_box_rect("band_dyn_btn_" + c, dcx, 152.5, 13, 13, 1);
        if (is_sel) {
            sel_dcx = dcx;
        }
    }

    set_box_rect("dyn_ring_fill", sel_dcx + 2.0, 154.5, 9.0, 9.0, dyn_panel_open ? 1 : 0);
}

function sync_band_strip_widgets(idx) {
    var b = bands[idx];
    set_named_val("band_on_btn_" + idx, b.active);
    set_named_val("band_type_menu_" + idx, b.type);
    sync_band_number_color(idx, false);

    var is_full_lit = (dyn_panel_open && selected_band === idx) ? 1 : 0;
    var dbtn = get_box("band_dyn_btn_" + idx);
    if (dbtn) {
        dbtn.message("set", (is_full_lit || b.dyn_on) ? 1 : 0);
    }
}

// --- Dynamic Layout & Device Width Management ---
function update_layout() {
    var x_off = sc_panel_open ? SC_W : 0;
    var total_w = BASE_W + x_off + (dyn_panel_open ? DYN_W : 0);

    set_box_rect("bg_surface", 0, 0, total_w, 169, 1);

    // 0. Far-left vertical Sidechain Spine (x = 0..22)
    set_box_rect("sc_expand_btn", 3.0, 4.0, 15.0, 15.0, 1);
    set_box_rect("sc_expand_ring", 3.0, 4.0, 15.0, 15.0, 1);
    set_box_rect("sc_listen_btn", 3.5, 23.0, 14.0, 14.0, 1);
    set_box_rect("sc_listen_bg_off", 3.5, 23.0, 14.0, 14.0, sc_listen ? 0 : 1);
    set_box_rect("sc_listen_bg_on",  3.5, 23.0, 14.0, 14.0, sc_listen ? 1 : 0);
    var sc_act = (sc1_enable || sc2_enable) ? 1 : 0;
    set_box_rect("sc_dot_off", 7.5, 151.0, 6.5, 6.5, sc_act ? 0 : 1);
    set_box_rect("sc_dot_on",  7.5, 151.0, 6.5, 6.5, sc_act ? 1 : 0);
    set_box_rect("sc_spine_div", 21.0, 3.0, 1.0, 163.0, 1);

    // 1. Left Expandable Sidechain Panel (x = 22 .. 176 when sc_panel_open == 1)
    var sc_vis = sc_panel_open ? 1 : 0;
    var sx = 22;
    set_box_rect("sc_col_div", sx + 76, 3, 1, 163, sc_vis);
    set_box_rect("sc_right_div", sx + SC_W - 2, 0, 2, 169, sc_vis);

    set_box_rect("sc_a_btn",       sx + 4,   4,   68, 15, sc_vis);
    set_box_rect("lbl_src_a",      sx + 1.5, 23,  68, 14, sc_vis);
    set_box_rect("sc1_track_menu", sx + 4,   37,  68, 16, sc_vis);
    set_box_rect("sc1_chan_menu",  sx + 4,   56,  68, 16, sc_vis);
    set_box_rect("lbl_mix_a",      sx + 1.5, 82,  68, 14, sc_vis);
    set_box_rect("sc1_mix",        sx + 4,   96,  68, 16, sc_vis);
    set_box_rect("lbl_sc1_gain",   sx + 1.5, 122, 68, 14, sc_vis);
    set_box_rect("sc1_gain",       sx + 4,   136, 68, 16, sc_vis);

    set_box_rect("sc_b_btn",       sx + 82,   4,   68, 15, sc_vis);
    set_box_rect("lbl_src_b",      sx + 79.5, 23,  68, 14, sc_vis);
    set_box_rect("sc2_track_menu", sx + 82,   37,  68, 16, sc_vis);
    set_box_rect("sc2_chan_menu",  sx + 82,   56,  68, 16, sc_vis);
    set_box_rect("lbl_mix_b",      sx + 79.5, 82,  68, 14, sc_vis);
    set_box_rect("sc2_mix",        sx + 82,   96,  68, 16, sc_vis);
    set_box_rect("lbl_sc2_gain",   sx + 79.5, 122, 68, 14, sc_vis);
    set_box_rect("sc2_gain",       sx + 82,   136, 68, 16, sc_vis);

    // 2. EQ Eight Left Strip (Freq / Gain / Q, width = 45px: x = 22+x_off .. 67+x_off)
    set_box_rect("lbl_freq",  22 + x_off, 1,    45, 14, 1);
    set_box_rect("band_freq", 22 + x_off, 13,   45, 38, 1);
    set_box_rect("lbl_gain",  22 + x_off, 54.5, 45, 14, 1);
    set_box_rect("band_gain", 22 + x_off, 68,   45, 38, 1);
    set_box_rect("lbl_q",     22 + x_off, 111,  45, 14, 1);
    set_box_rect("band_q",    22 + x_off, 123,  45, 38, 1);

    // 3. Center EQ Eight Display (x = 69+x_off, w = 370, h = 132) + Unified Bezel + Bottom 8-Band Strip
    var gx = 69 + x_off;
    set_box_rect("eq_graph", gx, 0, 370, 132, 1);

    // Right-aligned dB labels (`justification=2`) & centered frequency labels matching Stock EQ Eight
    set_box_rect("lbl_f_100",  gx + 91,  118,   26,   13, 1);
    set_box_rect("lbl_f_1k",   gx + 205, 118,   26,   13, 1);
    set_box_rect("lbl_f_10k",  gx + 318, 118,   26,   13, 1);
    set_box_rect("lbl_db_12",  gx + 1.0, 6.5,   17.5, 12, 1);
    set_box_rect("lbl_db_6",   gx + 1.0, 33.0,  17.5, 12, 1);
    set_box_rect("lbl_db_0",   gx + 1.0, 59.5,  17.5, 12, 1);
    set_box_rect("lbl_db_m6",  gx + 1.0, 86.0,  17.5, 12, 1);
    set_box_rect("lbl_db_m12", gx + 1.0, 112.5, 17.5, 12, 1);

    update_band_strip_layout(gx);

    // 4. EQ Eight Right Strip (width = 54px: x = 441+x_off .. 495+x_off)
    var rx = 444 + x_off;
    set_box_rect("solo_btn", rx,      4, 22, 15, 1);
    set_box_rect("rta_btn",  rx + 25, 4, 22, 15, 1);
    set_box_rect("lbl_adaptq",  rx - 2.5, 71,  52, 14, 1);
    set_box_rect("adapt_q_btn", rx,       85,  47, 16, 1);
    set_box_rect("lbl_scale",   rx - 2.5, 103, 52, 14, 1);
    set_box_rect("dyn_scale",   rx,       117, 47, 16, 1);
    set_box_rect("lbl_outgain", rx - 2.5, 135, 52, 14, 1);
    set_box_rect("out_gain",    rx,       149, 47, 16, 1);

    // 5. Right Expandable Per-Band Dynamic Panel (+78px at x = 495+x_off when dyn_panel_open == 1)
    var dyn_vis = dyn_panel_open ? 1 : 0;
    var dx = 495 + x_off;
    set_box_rect("div_right_dyn", dx,       0,   2,  169, dyn_vis);
    set_box_rect("band_dyn_on",   dx + 5,   4,   68, 15,  dyn_vis);
    set_box_rect("band_source",   dx + 5,   21,  68, 15,  dyn_vis);
    set_box_rect("lbl_range",     dx + 2.5, 39,  68, 14,  dyn_vis);
    set_box_rect("band_dyndepth", dx + 5,   53,  68, 16,  dyn_vis);
    set_box_rect("lbl_thresh",    dx + 2.5, 71,  68, 14,  dyn_vis);
    set_box_rect("band_thresh",   dx + 5,   85,  68, 16,  dyn_vis);
    set_box_rect("lbl_attack",    dx + 2.5, 103, 68, 14,  dyn_vis);
    set_box_rect("band_attack",   dx + 5,   117, 68, 16,  dyn_vis);
    set_box_rect("lbl_release",   dx + 2.5, 135, 68, 14,  dyn_vis);
    set_box_rect("band_release",  dx + 5,   149, 68, 16,  dyn_vis);

    if (total_w !== last_device_width) {
        last_device_width = total_w;
        outlet(2, "setwidth", total_w);
    }
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

function send_band_to_graph(idx) {
    var b = bands[idx];
    outlet(0, "set_band", idx, b.active, b.freq, b.gain, b.q, b.type, b.dyn_on, b.range, b.thresh);
}

function sync_band_to_ui(idx) {
    send_band_to_graph(idx);
    sync_band_strip_widgets(idx);
    if (idx === selected_band) {
        sync_inspector_visual_state(false);
    }
}

function update_power_gating() {
    var mute_rta = rta_on ? 0 : 1;
    if (mute_rta !== last_rta_muted) {
        var rm = get_box("rta_mute");
        if (rm) {
            last_rta_muted = mute_rta;
            rm.message(mute_rta);
        }
    }

    var any_dyn = 0;
    for (var i = 0; i < NUM_BANDS; i++) {
        var b = bands[i];
        if (b.active && b.dyn_on && is_gain_filter_type(b.type) && Math.abs(b.range) > 0.01) {
            any_dyn = 1;
            break;
        }
    }
    var need_poll = (rta_on || any_dyn) ? 1 : 0;
    if (need_poll !== last_poll_active) {
        var qm = get_box("ui_qmetro");
        if (qm) {
            last_poll_active = need_poll;
            qm.message("active", need_poll);
            if (!need_poll) {
                outlet(0, "bang");
            }
        }
    }
}

function update_solo_dsp() {
    var s_val = 0;
    if (sc_listen) {
        s_val = 9;
    } else if (solo_band) {
        s_val = selected_band + 1;
    }
    var b_src = bands[selected_band] ? bands[selected_band].sc_src : 0;
    var listen_src = 1;
    if (b_src === 2 || (!sc1_enable && sc2_enable)) {
        listen_src = 2;
    }
    outlet(1, "sc_listen_src", listen_src);
    outlet(1, "solo_band", s_val);
    set_named_val("solo_btn", solo_band);
    set_named_val("sc_listen_btn", sc_listen);
    set_box_rect("sc_listen_bg_off", 3.5, 23.0, 14.0, 14.0, sc_listen ? 0 : 1);
    set_box_rect("sc_listen_bg_on",  3.5, 23.0, 14.0, 14.0, sc_listen ? 1 : 0);
}

function update_sc_dsp() {
    var mix1 = clamp(sc1_mix / 100.0, 0.0, 1.0);
    var mix2 = clamp(sc2_mix / 100.0, 0.0, 1.0);
    outlet(1, "sc1_en", sc1_enable ? 1 : 0);
    outlet(1, "sc1_mix", mix1);
    outlet(1, "sc1_gain", sc1_gain);
    outlet(1, "sc2_en", sc2_enable ? 1 : 0);
    outlet(1, "sc2_mix", mix2);
    outlet(1, "sc2_gain", sc2_gain);
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

    set_named_val("sc_expand_btn", sc_panel_open);
    set_named_val("rta_btn", rta_on);
    update_solo_dsp();
    sync_inspector_visual_state(false);

    var gx = 69 + (sc_panel_open ? SC_W : 0);
    update_band_strip_layout(gx);
    for (var s_idx = 0; s_idx < NUM_BANDS; s_idx++) {
        sync_band_strip_widgets(s_idx);
    }
    is_syncing_controls = 0;
}

var THEME_QUERY_TOKENS = [
    "lcd_bg", "lcd_frame", "display_scale_text", "lcd_control_fg_alt",
    "lcd_control_fg_zombie", "display_handle_one", "spectrum_default_color",
    "value_arc", "value_arc_zombie", "control_fg"
];

function query_theme_colors() {
    var lc = get_box("live_colors_obj");
    if (lc) {
        for (var i = 0; i < THEME_QUERY_TOKENS.length; i++) {
            lc.message(THEME_QUERY_TOKENS[i]);
        }
        outlet(0, "flush_theme_redraw");
    }
}

function theme_color_reply(token, r, g, b, a) {
    var alpha = (a !== undefined) ? a : 1.0;
    var graph_map = {
        "lcd_bg": "lcd_bg",
        "lcd_frame": "lcd_frame",
        "display_scale_text": "scale_text",
        "lcd_control_fg_alt": "control_fg",
        "lcd_control_fg_zombie": "control_fg_zombie",
        "display_handle_one": "handle_one",
        "spectrum_default_color": "spectrum_fill"
    };
    if (graph_map[token]) {
        outlet(0, "set_theme_color", graph_map[token], r, g, b, alpha);
    }

    var ui_recolor_needed = false;
    if (token === "lcd_frame") {
        LIVE_COLORS.lcd_frame = [r, g, b, alpha];
        var sc_div = get_box("sc_right_div");
        if (sc_div) sc_div.message("linecolor", r, g, b, alpha);
        var dyn_div = get_box("div_right_dyn");
        if (dyn_div) dyn_div.message("linecolor", r, g, b, alpha);
    } else if (token === "value_arc") {
        LIVE_COLORS.value_arc = [r, g, b, alpha];
        ui_recolor_needed = true;
    } else if (token === "value_arc_zombie" || token === "control_zombie") {
        if (token === "value_arc_zombie" || LIVE_COLORS.value_arc_zombie[0] === 0.514) {
            LIVE_COLORS.value_arc_zombie = [r, g, b, alpha];
            ui_recolor_needed = true;
        }
    } else if (token === "control_fg") {
        LIVE_COLORS.ui_text_on = [r, g, b, alpha];
        ui_recolor_needed = true;
    } else if (token === "control_fg_zombie" || token === "lcd_control_fg_zombie" || token === "control_zombie") {
        LIVE_COLORS.ui_text_zombie = [r, g, b, alpha];
        if (token === "control_zombie") {
            outlet(0, "set_theme_color", "control_fg_zombie", r, g, b, alpha);
        }
        ui_recolor_needed = true;
    }

    if (ui_recolor_needed && device_ready) {
        sync_inspector_visual_state(true);
        for (var bi = 0; bi < NUM_BANDS; bi++) {
            sync_band_number_color(bi, true);
        }
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
    sync_inspector_visual_state(true);
    for (var k = 0; k < NUM_BANDS; k++) {
        sync_band_number_color(k, true);
    }
    update_power_gating();
    query_theme_colors();
}

function init_device() {
    if (device_ready && save_state_pending) {
        save_state_now();
    }
    dd_lock_task.cancel();
    dd_unlock_task.cancel();
    obj_cache = {};
    rect_cache = {};
    last_device_width = -1;
    last_poll_active = -1;
    last_rta_muted = -1;
    last_dial_zombie = -1;
    last_gain_enabled = -1;
    band_num_dim_cache = [-1, -1, -1, -1, -1, -1, -1, -1];
    is_graph_dragging = 0;
    dd_hover_id = 0;
    dd_open_id = 0;
    dd_last_id = 0;
    dd_locked = -1;
    dd_set_ignoreclick(0);

    var st_box = get_box("eq_state");
    if (st_box && st_box.getvalueof) {
        var sv = st_box.getvalueof();
        if (sv && sv.length >= 104) {
            apply_state_array(sv);
        }
    }

    device_ready = 1;
    update_layout();
    sync_all();

    if (!routing_initialized) {
        routing_initialized = 1;
        outlet(3, "port", "audio_inputs");
        outlet(3, "index", 1);
        outlet(4, "port", "audio_inputs");
        outlet(4, "index", 2);
    }
}

// --- Handlers from Native Left Sidechain Spine & Native Bottom Band Strip ---
function set_sc_panel(v) {
    if (!device_ready || is_syncing_controls) return;
    sc_panel_open = v ? 1 : 0;
    set_named_val("sc_expand_btn", sc_panel_open);
    update_layout();
    save_state_now();
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
    save_state_now();
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
    save_state_now();
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
    update_power_gating();
    if (selected_band !== idx) {
        select_band(idx);
    } else {
        sync_inspector_visual_state(false);
        save_state_now();
    }
}

function ui_band_type(idx, v) {
    if (!device_ready || is_syncing_controls) return;
    dd_notify_selected();
    var b_idx = clamp(idx, 0, NUM_BANDS - 1);
    var new_t = clamp(Math.round(v), 0, 7);
    var changed = (bands[b_idx].type !== new_t);
    bands[b_idx].type = new_t;
    outlet(1, "b" + (b_idx + 1) + "_type", new_t);
    if (changed && !bands[b_idx].active) {
        bands[b_idx].active = 1;
        outlet(1, "b" + (b_idx + 1) + "_on", 1);
    }
    sync_band_to_ui(b_idx);
    update_power_gating();
    if (selected_band !== b_idx) {
        select_band(b_idx);
    } else {
        sync_inspector_visual_state(false);
        save_state_now();
    }
}

// --- Handlers from Dedicated Global & Sidechain Controls ---
function ui_dyn_scale(v) {
    if (!device_ready || is_syncing_controls) return;
    global_scale = clamp(v, 0.0, 200.0);
    outlet(1, "dyn_scale", global_scale / 100.0);
    outlet(0, "set_scale", global_scale);
    save_state();
}

function ui_scale(v) {
    ui_dyn_scale(v);
}

function ui_out_gain(v) {
    if (!device_ready || is_syncing_controls) return;
    out_gain = clamp(v, -24.0, 24.0);
    outlet(1, "out_gain", out_gain);
    save_state();
}

function ui_adapt_q(v) {
    if (!device_ready || is_syncing_controls) return;
    adaptive_q = v ? 1 : 0;
    outlet(1, "adapt_q", adaptive_q);
    outlet(0, "set_adaptive_q", adaptive_q);
    save_state_now();
}

function ui_rta_on(v) {
    if (!device_ready || is_syncing_controls) return;
    rta_on = v ? 1 : 0;
    outlet(0, "set_rta_on", rta_on);
    update_power_gating();
    save_state_now();
}

function ui_solo(v) {
    if (!device_ready || is_syncing_controls) return;
    solo_band = v ? 1 : 0;
    if (solo_band && sc_listen) {
        sc_listen = 0;
    }
    is_syncing_controls = 1;
    update_solo_dsp();
    is_syncing_controls = 0;
    save_state_now();
}

function ui_sc_listen(v) {
    if (!device_ready || is_syncing_controls) return;
    sc_listen = v ? 1 : 0;
    if (sc_listen && solo_band) {
        solo_band = 0;
    }
    is_syncing_controls = 1;
    update_solo_dsp();
    is_syncing_controls = 0;
    save_state_now();
}

function ui_sc_a_en(v) {
    if (!device_ready || is_syncing_controls) return;
    sc1_enable = v ? 1 : 0;
    update_sc_dsp();
    if (sc_listen) update_solo_dsp();
    save_state_now();
}

function ui_sc1_mix(v) {
    if (!device_ready || is_syncing_controls) return;
    sc1_mix = clamp(v, 0.0, 100.0);
    update_sc_dsp();
    save_state();
}

function ui_sc1_gain(v) {
    if (!device_ready || is_syncing_controls) return;
    sc1_gain = clamp(v, -24.0, 24.0);
    outlet(1, "sc1_gain", sc1_gain);
    save_state();
}

function ui_sc_b_en(v) {
    if (!device_ready || is_syncing_controls) return;
    sc2_enable = v ? 1 : 0;
    update_sc_dsp();
    if (sc_listen) update_solo_dsp();
    save_state_now();
}

function ui_sc2_mix(v) {
    if (!device_ready || is_syncing_controls) return;
    sc2_mix = clamp(v, 0.0, 100.0);
    update_sc_dsp();
    save_state();
}

function ui_sc2_gain(v) {
    if (!device_ready || is_syncing_controls) return;
    sc2_gain = clamp(v, -24.0, 24.0);
    outlet(1, "sc2_gain", sc2_gain);
    save_state();
}

// --- Sidechain live.routing Handlers ---
function apply_umenu_sym(varname, sym, items, idx_map) {
    if (sym === null || sym === undefined) return;
    var menu = get_box(varname);
    if (!menu || !idx_map || idx_map.length === 0) return;

    var ui_idx = -1;
    if (typeof sym === "number") {
        for (var i = 0; i < idx_map.length; i++) {
            if (idx_map[i] === sym) {
                ui_idx = i;
                break;
            }
        }
    } else {
        for (var j = 0; j < idx_map.length; j++) {
            var orig = idx_map[j];
            if (orig >= 0 && orig < items.length && items[orig] === sym) {
                ui_idx = j;
                break;
            }
        }
    }
    if (ui_idx >= 0) {
        is_syncing_routing = 1;
        menu.message("set", ui_idx);
        is_syncing_routing = 0;
    }
}

function populate_umenu(varname, items, cur_sym, idx_map) {
    var menu = get_box(varname);
    if (!menu) return;
    is_syncing_routing = 1;
    menu.message("clear");
    idx_map.length = 0;
    if (items && items.length > 0) {
        for (var i = 0; i < items.length; i++) {
            if (items[i] !== "<none>") {
                menu.message("append", items[i]);
                idx_map.push(i);
            }
        }
    }
    if (idx_map.length === 0) {
        menu.message("append", "No Input");
        menu.message("set", 0);
        is_syncing_routing = 0;
        return;
    }
    is_syncing_routing = 0;
    if (cur_sym !== null && cur_sym !== undefined) {
        apply_umenu_sym(varname, cur_sym, items, idx_map);
    }
}

function rt1_types() {
    rt1_type_list = arrayfromargs(arguments);
    populate_umenu("sc1_track_menu", rt1_type_list, rt1_cur_type_sym, rt1_type_map);
}

function rt1_chans() {
    rt1_chan_list = arrayfromargs(arguments);
    populate_umenu("sc1_chan_menu", rt1_chan_list, rt1_cur_chan_sym, rt1_chan_map);
}

function rt1_cur_type(v) {
    rt1_cur_type_sym = v;
    apply_umenu_sym("sc1_track_menu", v, rt1_type_list, rt1_type_map);
}

function rt1_cur_chan(v) {
    rt1_cur_chan_sym = v;
    apply_umenu_sym("sc1_chan_menu", v, rt1_chan_list, rt1_chan_map);
}

function set_sc1_track(ui_idx) {
    if (!device_ready || is_syncing_controls || is_syncing_routing) return;
    dd_notify_selected();
    var real_idx = (ui_idx >= 0 && ui_idx < rt1_type_map.length) ? rt1_type_map[ui_idx] : ui_idx;
    outlet(3, "type", real_idx);
    var chosen = (real_idx >= 0 && real_idx < rt1_type_list.length) ? String(rt1_type_list[real_idx]) : "";
    if (chosen && chosen !== "No Input" && chosen !== "<none>" && !sc1_enable) {
        sc1_enable = 1;
        is_syncing_controls = 1;
        set_named_val("sc_a_btn", 1);
        is_syncing_controls = 0;
        update_sc_dsp();
        save_state_now();
    }
}

function set_sc1_chan(ui_idx) {
    if (!device_ready || is_syncing_controls || is_syncing_routing) return;
    dd_notify_selected();
    var real_idx = (ui_idx >= 0 && ui_idx < rt1_chan_map.length) ? rt1_chan_map[ui_idx] : ui_idx;
    outlet(3, "channel", real_idx);
}

function rt2_types() {
    rt2_type_list = arrayfromargs(arguments);
    populate_umenu("sc2_track_menu", rt2_type_list, rt2_cur_type_sym, rt2_type_map);
}

function rt2_chans() {
    rt2_chan_list = arrayfromargs(arguments);
    populate_umenu("sc2_chan_menu", rt2_chan_list, rt2_cur_chan_sym, rt2_chan_map);
}

function rt2_cur_type(v) {
    rt2_cur_type_sym = v;
    apply_umenu_sym("sc2_track_menu", v, rt2_type_list, rt2_type_map);
}

function rt2_cur_chan(v) {
    rt2_cur_chan_sym = v;
    apply_umenu_sym("sc2_chan_menu", v, rt2_chan_list, rt2_chan_map);
}

function set_sc2_track(ui_idx) {
    if (!device_ready || is_syncing_controls || is_syncing_routing) return;
    dd_notify_selected();
    var real_idx = (ui_idx >= 0 && ui_idx < rt2_type_map.length) ? rt2_type_map[ui_idx] : ui_idx;
    outlet(4, "type", real_idx);
    var chosen = (real_idx >= 0 && real_idx < rt2_type_list.length) ? String(rt2_type_list[real_idx]) : "";
    if (chosen && chosen !== "No Input" && chosen !== "<none>" && !sc2_enable) {
        sc2_enable = 1;
        is_syncing_controls = 1;
        set_named_val("sc_b_btn", 1);
        is_syncing_controls = 0;
        update_sc_dsp();
        save_state_now();
    }
}

function set_sc2_chan(ui_idx) {
    if (!device_ready || is_syncing_controls || is_syncing_routing) return;
    dd_notify_selected();
    var real_idx = (ui_idx >= 0 && ui_idx < rt2_chan_map.length) ? rt2_chan_map[ui_idx] : ui_idx;
    outlet(4, "channel", real_idx);
}

// --- Handlers from Shared Single-Band Inspector Controls ---
function ui_freq(v) {
    if (!device_ready || is_syncing_controls) return;
    var b = bands[selected_band];
    b.freq = clamp(v, 20.0, 20000.0);
    outlet(1, "b" + (selected_band + 1) + "_freq", b.freq);
    send_band_to_graph(selected_band);
    save_state();
}

function ui_gain(v) {
    if (!device_ready || is_syncing_controls) return;
    var b = bands[selected_band];
    b.gain = clamp(v, -15.0, 15.0);
    outlet(1, "b" + (selected_band + 1) + "_gain", b.gain);
    send_band_to_graph(selected_band);
    save_state();
}

function ui_q(v) {
    if (!device_ready || is_syncing_controls) return;
    var b = bands[selected_band];
    b.q = clamp(v, 0.1, 18.0);
    outlet(1, "b" + (selected_band + 1) + "_q", b.q);
    send_band_to_graph(selected_band);
    save_state();
}

function ui_type(v) {
    if (!device_ready || is_syncing_controls) return;
    var b = bands[selected_band];
    b.type = clamp(Math.round(v), 0, 7);
    outlet(1, "b" + (selected_band + 1) + "_type", b.type);
    sync_band_to_ui(selected_band);
    update_power_gating();
    save_state_now();
}

function ui_dyn_on(v) {
    if (!device_ready || is_syncing_controls) return;
    var b = bands[selected_band];
    b.dyn_on = v ? 1 : 0;
    outlet(1, "b" + (selected_band + 1) + "_dyn_on", b.dyn_on);
    sync_band_to_ui(selected_band);
    update_power_gating();
    save_state_now();
}

function ui_dyndepth(v) {
    if (!device_ready || is_syncing_controls) return;
    var b = bands[selected_band];
    b.range = clamp(v, -15.0, 15.0);
    if (Math.abs(b.range) > 0.05 && !b.dyn_on) {
        b.dyn_on = 1;
        outlet(1, "b" + (selected_band + 1) + "_dyn_on", 1);
        is_syncing_controls = 1;
        set_named_val("band_dyn_on", 1);
        is_syncing_controls = 0;
        sync_band_strip_widgets(selected_band);
    }
    outlet(1, "b" + (selected_band + 1) + "_dyn_range", b.range);
    send_band_to_graph(selected_band);
    update_power_gating();
    save_state();
}

function ui_thresh(v) {
    if (!device_ready || is_syncing_controls) return;
    var b = bands[selected_band];
    b.thresh = clamp(v, -60.0, 0.0);
    outlet(1, "b" + (selected_band + 1) + "_thresh", b.thresh);
    send_band_to_graph(selected_band);
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
    if (b.sc_src === 1 && !sc1_enable) {
        sc1_enable = 1;
        is_syncing_controls = 1;
        set_named_val("sc_a_btn", 1);
        is_syncing_controls = 0;
        update_sc_dsp();
    } else if (b.sc_src === 2 && !sc2_enable) {
        sc2_enable = 1;
        is_syncing_controls = 1;
        set_named_val("sc_b_btn", 1);
        is_syncing_controls = 0;
        update_sc_dsp();
    }
    if (sc_listen) {
        update_solo_dsp();
    }
    save_state_now();
}

// --- Handlers from JSUI Curve Editor ---
function select_band(idx) {
    var next_sel = clamp(idx, 0, NUM_BANDS - 1);
    if (next_sel === selected_band) {
        return;
    }
    selected_band = next_sel;
    outlet(0, "select", selected_band);
    if (solo_band || sc_listen) update_solo_dsp();
    sync_selected_band_controls();
    save_state_now();
}

function drag_start() {
    is_graph_dragging = 1;
    drag_tick = 0;
}

function band_fg(idx, f, g) {
    if (idx < 0 || idx >= NUM_BANDS) return;
    is_graph_dragging = 1;
    var b = bands[idx];
    b.freq = clamp(f, 20.0, 20000.0);
    b.gain = clamp(g, -15.0, 15.0);
    var p = "b" + (idx + 1) + "_";
    outlet(1, p + "freq", b.freq);
    outlet(1, p + "gain", b.gain);
    if (idx === selected_band) {
        drag_tick = (drag_tick + 1) & 3;
        if (drag_tick === 0) {
            is_syncing_controls = 1;
            set_named_val("band_freq", b.freq);
            set_named_val("band_gain", b.gain);
            is_syncing_controls = 0;
        }
    }
}

function band_q(idx, q_val) {
    if (idx < 0 || idx >= NUM_BANDS) return;
    var b = bands[idx];
    b.q = clamp(q_val, 0.1, 18.0);
    outlet(1, "b" + (idx + 1) + "_q", b.q);
    if (idx === selected_band) {
        if (is_graph_dragging) {
            drag_tick = (drag_tick + 1) & 3;
            if (drag_tick === 0) {
                is_syncing_controls = 1;
                set_named_val("band_q", b.q);
                is_syncing_controls = 0;
            }
        } else {
            is_syncing_controls = 1;
            set_named_val("band_q", b.q);
            is_syncing_controls = 0;
            save_state();
        }
    } else if (!is_graph_dragging) {
        save_state();
    }
}

function band_range(idx, r_val) {
    if (idx < 0 || idx >= NUM_BANDS) return;
    var b = bands[idx];
    b.range = clamp(r_val, -15.0, 15.0);
    var prev_dyn = b.dyn_on;
    b.dyn_on = (Math.abs(b.range) > 0.05) ? 1 : b.dyn_on;
    var p = "b" + (idx + 1) + "_";
    outlet(1, p + "dyn_range", b.range);
    if (b.dyn_on !== prev_dyn) {
        outlet(1, p + "dyn_on", b.dyn_on);
        sync_band_strip_widgets(idx);
        update_power_gating();
    }
    if (idx === selected_band) {
        drag_tick = (drag_tick + 1) & 3;
        if (!is_graph_dragging || drag_tick === 0 || b.dyn_on !== prev_dyn) {
            is_syncing_controls = 1;
            set_named_val("band_dyndepth", b.range);
            if (b.dyn_on !== prev_dyn) {
                set_named_val("band_dyn_on", b.dyn_on);
            }
            is_syncing_controls = 0;
        }
    }
    if (!is_graph_dragging) {
        update_power_gating();
        save_state();
    }
}

function drag_end(idx) {
    is_graph_dragging = 0;
    update_power_gating();
    if (idx === selected_band) {
        is_syncing_controls = 1;
        var b = bands[selected_band];
        set_named_val("band_freq", b.freq);
        set_named_val("band_gain", b.gain);
        set_named_val("band_q", b.q);
        set_named_val("band_dyndepth", b.range);
        set_named_val("band_dyn_on", b.dyn_on);
        is_syncing_controls = 0;
    }
    save_state_task.cancel();
    save_state_now();
}

function band_dyn_on(idx, state) {
    if (idx < 0 || idx >= NUM_BANDS) return;
    bands[idx].dyn_on = state ? 1 : 0;
    outlet(1, "b" + (idx + 1) + "_dyn_on", bands[idx].dyn_on);
    sync_band_strip_widgets(idx);
    update_power_gating();
    if (idx === selected_band) {
        is_syncing_controls = 1;
        set_named_val("band_dyn_on", bands[idx].dyn_on);
        is_syncing_controls = 0;
    }
    save_state_now();
}

function band_active(idx, state) {
    if (idx < 0 || idx >= NUM_BANDS) return;
    bands[idx].active = state ? 1 : 0;
    outlet(1, "b" + (idx + 1) + "_on", bands[idx].active);
    sync_band_to_ui(idx);
    update_power_gating();
    if (idx === selected_band) {
        sync_selected_band_controls();
    }
    save_state_now();
}

function band_type(idx, t) {
    if (idx < 0 || idx >= NUM_BANDS) return;
    bands[idx].type = clamp(Math.round(t), 0, 7);
    outlet(1, "b" + (idx + 1) + "_type", bands[idx].type);
    sync_band_to_ui(idx);
    update_power_gating();
    save_state_now();
}

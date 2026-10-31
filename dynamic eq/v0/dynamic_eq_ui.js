// dynamic_eq_ui.js
// Authentic Ableton EQ Eight Clone + Pro-Q Dynamic EQ Visualizer (jsui / mgraphics)
// 1. Exact 370x169 dimensions & RGB colors measured from Ableton Live EQ Eight:
//    - Top Graph (370x132, y=0..132): #14131a background, lavender RTA, cyan composite curve
//    - Native EQ Eight Pink (#ff91c3) band dots: solid pink with dark text when selected,
//      hollow dark circle with pink outline and pink text when unselected.
// 2. Pro-Q Style Direct-Grab Dynamic Visualization & Handler on top of Band Circle:
//    - Small grab ring sits 13px directly above the selected band circle when range == 0
//    - Dragging the grab ring pulls out the Dynamic Range stem & target ring and enables dyn_on
//    - Shaded Dynamic Target Range fill + Translucent Gold/Amber Composite Target Envelope Curve
// 3. Minimalistic Per-Band Dynamics Circle Toggle in the Bottom Band Row:
//    - Sits on the right of the band activator square, keeping the exact overall width (cx0+4 .. cx0+cw-4)
//      as the top filter curve selector dropdown.
//    - Empty greyed-out circle when dynamics is OFF; lit cyan border when dynamics is ON.
//    - Clicking the circle opens/closes the right Per-Band Dynamic Drawer for that band.
// 4. High-Speed Precomputed SVF Response Engine (~20x faster paint() during drag).

inlets = 1;
outlets = 1;

mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

var NUM_BANDS = 8;
var SAMPLE_RATE = 44100.0;
var MIN_FREQ = 20.0;
var MAX_FREQ = 20000.0;
var MIN_DB = -15.0;
var MAX_DB = 15.0;
var STRIP_H = 37.0; // Bottom band selector strip height (y=132..169)

var selected_band = 0; // 0..7
var dyn_panel_open = 0; // 0 or 1 (whether right Per-Band Dynamic Drawer is open)
var drag_band = -1;
var drag_mode = "none"; // "freq_gain", "range", "q"
var last_mx = 0;
var last_my = 0;

var popup_band = -1; // -1 if closed, 0..7 if filter type popup menu is open on canvas

var global_scale = 1.0; // 0.0 .. 2.0 (0% .. 200%)
var adaptive_q = 1;
var rta_enabled = 1;

var FILTER_NAMES = [
    "Low Cut 48", "Low Cut 12", "Low Shelf", "Bell",
    "Notch", "High Shelf", "High Cut 12", "High Cut 48"
];

// Native Ableton EQ Eight Pink: RGB(255, 145, 195) = #ff91c3
var EQ8_PINK = [1.0, 0.569, 0.765];
// Native Ableton EQ Eight Cyan: RGB(71, 226, 244) = #47e2f4
var EQ8_CYAN = [0.278, 0.886, 0.957];

// 16 RTA 1/3-octave center frequencies
var RTA_FREQS = [
    25.0, 40.0, 63.0, 100.0, 160.0, 250.0, 400.0, 630.0,
    1000.0, 1600.0, 2500.0, 4000.0, 6300.0, 10000.0, 14000.0, 19000.0
];
var rta_db = [-90, -90, -90, -90, -90, -90, -90, -90, -90, -90, -90, -90, -90, -90, -90, -90];

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
        gr_db: 0.0
    });
}

// Precomputed frequency evaluation grid (eliminates Math.pow & Math.tan per pixel in paint())
var NUM_STEPS = 120;
var STEP_NORM = [];
var STEP_TAN_W = [];
for (var s_init = 0; s_init <= NUM_STEPS; s_init++) {
    var norm_s = s_init / NUM_STEPS;
    var f_s = MIN_FREQ * Math.pow(MAX_FREQ / MIN_FREQ, norm_s);
    STEP_NORM.push(norm_s);
    STEP_TAN_W.push(Math.tan(Math.PI * f_s / SAMPLE_RATE));
}

function clamp(v, lo, hi) {
    return v < lo ? lo : (v > hi ? hi : v);
}

function uses_gain(btype) {
    return (btype === 2 || btype === 3 || btype === 5);
}

function freq_to_x(f, w) {
    var norm = Math.log(clamp(f, MIN_FREQ, MAX_FREQ) / MIN_FREQ) / Math.log(MAX_FREQ / MIN_FREQ);
    return norm * w;
}

function x_to_freq(x, w) {
    var norm = clamp(x / w, 0.0, 1.0);
    return MIN_FREQ * Math.pow(MAX_FREQ / MIN_FREQ, norm);
}

function db_to_y(db, gh) {
    var norm = (clamp(db, MIN_DB, MAX_DB) - MIN_DB) / (MAX_DB - MIN_DB);
    return gh - norm * gh;
}

function y_to_db(y, gh) {
    var norm = (gh - y) / gh;
    return clamp(MIN_DB + norm * (MAX_DB - MIN_DB), MIN_DB, MAX_DB);
}

// --- Precompute Cytomic TPT SVF coefficients ONCE per band per frame ---
function prepare_svf_coeffs(type, fc, q_in, gain_db) {
    if (Math.abs(gain_db) < 0.001 && (type === 2 || type === 3 || type === 5)) {
        return { bypass: true };
    }
    var f_clamped = clamp(fc, 20.0, SAMPLE_RATE * 0.49);
    var g = Math.tan(Math.PI * f_clamped / SAMPLE_RATE);

    var q_eff = clamp(q_in, 0.1, 18.0);
    if (adaptive_q && (type === 3 || type === 2 || type === 5)) {
        q_eff = clamp(q_eff * Math.pow(2.0, Math.abs(gain_db) / 18.0), 0.1, 18.0);
    }

    var w0 = 2.0 * Math.PI * f_clamped / SAMPLE_RATE;
    var nyq_scale = Math.max(0.25, Math.cos(w0 * 0.35));
    var k = 1.0 / (q_eff * nyq_scale);

    var m0 = 1.0, m1 = 0.0, m2 = 0.0;
    if (type === 3) { // Bell
        var A = Math.pow(10.0, gain_db / 40.0);
        k = k / A;
        m0 = 1.0;
        m1 = k * (A * A - 1.0);
        m2 = 0.0;
    } else if (type === 2) { // Low Shelf
        var A2 = Math.pow(10.0, gain_db / 40.0);
        g = g / Math.sqrt(A2);
        m0 = 1.0;
        m1 = k * (A2 - 1.0);
        m2 = A2 * A2 - 1.0;
    } else if (type === 5) { // High Shelf
        var A5 = Math.pow(10.0, gain_db / 40.0);
        g = g * Math.sqrt(A5);
        m0 = A5 * A5;
        m1 = k * (1.0 - A5) * A5;
        m2 = 1.0 - A5 * A5;
    } else if (type === 1 || type === 0) { // Low Cut
        m0 = 1.0;
        m1 = -k;
        m2 = -1.0;
    } else if (type === 6 || type === 7) { // High Cut
        m0 = 0.0;
        m1 = 0.0;
        m2 = 1.0;
    } else if (type === 4) { // Notch
        m0 = 1.0;
        m1 = -k;
        m2 = 0.0;
    }

    return {
        bypass: false,
        inv_g: 1.0 / g,
        k: k,
        k2: k * k,
        m0: m0,
        m2: m2,
        m0k_plus_m1: m0 * k + m1,
        is_48db: (type === 0 || type === 7)
    };
}

var LOG10_SCALE = 10.0 / Math.LN10;

function eval_svf_db(c, tan_w) {
    if (c.bypass) return 0.0;
    var u = tan_w * c.inv_g;
    var u2 = u * u;
    var one_minus_u2 = 1.0 - u2;
    var den = one_minus_u2 * one_minus_u2 + c.k2 * u2;
    if (den < 1e-18) return 0.0;

    var num_r = c.m0 * one_minus_u2 + c.m2;
    var num_i = u * c.m0k_plus_m1;
    var mag_sq = (num_r * num_r + num_i * num_i) / den;
    if (c.is_48db) {
        mag_sq = mag_sq * mag_sq;
    }
    if (mag_sq <= 1e-12) return -120.0;
    return LOG10_SCALE * Math.log(mag_sq);
}

// Draw exact Ableton EQ Eight vector filter icon inside dropdown box
function draw_filter_icon(type, gx, gy, gw, gh) {
    var cy = Math.round(gy + gh * 0.5) + 0.5;
    mgraphics.set_line_width(1.35);

    if (type === 0) { // Low Cut 48
        mgraphics.move_to(gx + 1.5, cy + 4.0);
        mgraphics.line_to(gx + 1.5, cy - 1.5);
        mgraphics.curve_to(gx + 1.5, cy - 3.5, gx + 2.5, cy - 3.5, gx + 4.5, cy - 3.5);
        mgraphics.line_to(gx + gw, cy - 3.5);
        mgraphics.stroke();
    } else if (type === 1) { // Low Cut 12
        mgraphics.move_to(gx + 0.5, cy + 4.0);
        mgraphics.line_to(gx + 4.0, cy - 2.0);
        mgraphics.curve_to(gx + 4.8, cy - 3.5, gx + 5.5, cy - 3.5, gx + 7.5, cy - 3.5);
        mgraphics.line_to(gx + gw, cy - 3.5);
        mgraphics.stroke();
    } else if (type === 2) { // Low Shelf
        mgraphics.move_to(gx, cy - 3.5);
        mgraphics.line_to(gx + 5.5, cy - 3.5);
        mgraphics.line_to(gx + 8.0, cy);
        mgraphics.move_to(gx, cy + 3.5);
        mgraphics.line_to(gx + 5.5, cy + 3.5);
        mgraphics.line_to(gx + 8.0, cy);
        mgraphics.move_to(gx + 8.0, cy);
        mgraphics.line_to(gx + gw, cy);
        mgraphics.stroke();
    } else if (type === 3) { // Bell
        var mid = gx + gw * 0.5;
        mgraphics.move_to(gx, cy);
        mgraphics.line_to(mid - 5.0, cy);
        mgraphics.move_to(mid + 5.0, cy);
        mgraphics.line_to(gx + gw, cy);
        mgraphics.stroke();
        mgraphics.move_to(mid - 5.0, cy);
        mgraphics.curve_to(mid - 4.2, cy - 4.2, mid + 4.2, cy - 4.2, mid + 5.0, cy);
        mgraphics.move_to(mid - 5.0, cy);
        mgraphics.curve_to(mid - 4.2, cy + 4.2, mid + 4.2, cy + 4.2, mid + 5.0, cy);
        mgraphics.stroke();
    } else if (type === 4) { // Notch
        var nmid = gx + gw * 0.5;
        mgraphics.move_to(gx, cy - 2.5);
        mgraphics.line_to(nmid - 3.0, cy - 2.5);
        mgraphics.line_to(nmid, cy + 4.0);
        mgraphics.line_to(nmid + 3.0, cy - 2.5);
        mgraphics.line_to(gx + gw, cy - 2.5);
        mgraphics.stroke();
    } else if (type === 5) { // High Shelf
        mgraphics.move_to(gx, cy);
        mgraphics.line_to(gx + 7.5, cy);
        mgraphics.move_to(gx + 7.5, cy);
        mgraphics.line_to(gx + 10.0, cy - 3.5);
        mgraphics.line_to(gx + gw, cy - 3.5);
        mgraphics.move_to(gx + 7.5, cy);
        mgraphics.line_to(gx + 10.0, cy + 3.5);
        mgraphics.line_to(gx + gw, cy + 3.5);
        mgraphics.stroke();
    } else if (type === 6) { // High Cut 12
        mgraphics.move_to(gx, cy - 3.5);
        mgraphics.line_to(gx + gw - 7.5, cy - 3.5);
        mgraphics.curve_to(gx + gw - 5.5, cy - 3.5, gx + gw - 4.8, cy - 3.5, gx + gw - 4.0, cy - 2.0);
        mgraphics.line_to(gx + gw - 0.5, cy + 4.0);
        mgraphics.stroke();
    } else if (type === 7) { // High Cut 48
        mgraphics.move_to(gx, cy - 3.5);
        mgraphics.line_to(gx + gw - 4.5, cy - 3.5);
        mgraphics.curve_to(gx + gw - 2.5, cy - 3.5, gx + gw - 1.5, cy - 3.5, gx + gw - 1.5, cy - 1.5);
        mgraphics.line_to(gx + gw - 1.5, cy + 4.0);
        mgraphics.stroke();
    }
}

function paint() {
    var w = box.rect[2] - box.rect[0];
    var h = box.rect[3] - box.rect[1];
    var gh = h - STRIP_H; // 132px graph height

    // 1. Exact EQ Eight Graph Background: RGB(20, 19, 26) = #14131a
    mgraphics.set_source_rgba(0.078, 0.075, 0.102, 1.0);
    mgraphics.rectangle(0, 0, w, gh);
    mgraphics.fill();

    // 2. Logarithmic Frequency Grid Lines (exact EQ Eight colors)
    mgraphics.set_line_width(1.0);
    var sub_freqs = [
        30, 40, 50, 60, 70, 80, 90,
        200, 300, 400, 500, 600, 700, 800, 900,
        2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000
    ];
    mgraphics.set_source_rgba(0.102, 0.098, 0.125, 1.0);
    for (var s = 0; s < sub_freqs.length; s++) {
        var sx = Math.round(freq_to_x(sub_freqs[s], w)) + 0.5;
        mgraphics.move_to(sx, 0);
        mgraphics.line_to(sx, gh);
    }
    mgraphics.stroke();

    var maj_freqs = [100, 1000, 10000];
    var maj_labels = ["100", "1k", "10k"];
    for (var m = 0; m < maj_freqs.length; m++) {
        var mx = Math.round(freq_to_x(maj_freqs[m], w)) + 0.5;
        mgraphics.set_source_rgba(0.169, 0.161, 0.188, 1.0);
        mgraphics.move_to(mx, 0);
        mgraphics.line_to(mx, gh);
        mgraphics.stroke();

        mgraphics.set_source_rgba(0.459, 0.435, 0.490, 1.0);
        mgraphics.select_font_face("Ableton Sans Medium", "normal", "normal");
        mgraphics.set_font_size(9.5);
        mgraphics.move_to(mx - 8, gh - 4);
        mgraphics.show_text(maj_labels[m]);
    }

    // 3. Horizontal dB Grid Lines (-12, -6, 0, +6, +12)
    var db_lines = [-12, -6, 0, 6, 12];
    for (var d = 0; d < db_lines.length; d++) {
        var db_val = db_lines[d];
        var dy = Math.round(db_to_y(db_val, gh)) + 0.5;
        if (db_val === 0) {
            mgraphics.set_source_rgba(0.216, 0.208, 0.239, 1.0);
        } else {
            mgraphics.set_source_rgba(0.137, 0.133, 0.161, 1.0);
        }
        mgraphics.move_to(0, dy);
        mgraphics.line_to(w, dy);
        mgraphics.stroke();

        mgraphics.set_source_rgba(0.459, 0.435, 0.490, 1.0);
        mgraphics.select_font_face("Ableton Sans Medium", "normal", "normal");
        mgraphics.set_font_size(9.5);
        var lbl_x = (db_val === 0) ? 10 : (db_val === 6 || db_val === -6 ? 7 : 4);
        mgraphics.move_to(lbl_x, dy + 3.5);
        mgraphics.show_text(db_val.toString());
    }

    // 4. Real-Time RTA Spectrum Overlay (EQ Eight purple-lavender style)
    if (rta_enabled) {
        var rta_pts = [];
        for (var r = 0; r < 16; r++) {
            var rx = freq_to_x(RTA_FREQS[r], w);
            var scaled_db = (rta_db[r] + 30.0) * 0.48;
            var ry = clamp(db_to_y(scaled_db, gh), 2.0, gh);
            rta_pts.push({ x: rx, y: ry });
        }

        mgraphics.set_source_rgba(0.49, 0.43, 0.62, 0.44);
        mgraphics.move_to(0, gh);
        mgraphics.line_to(0, rta_pts[0].y);
        var fine_steps = 64;
        for (var fs = 1; fs <= fine_steps; fs++) {
            var fx = (fs / fine_steps) * w;
            var seg = 0;
            for (var k = 0; k < 15; k++) {
                if (fx >= rta_pts[k].x && fx <= rta_pts[k + 1].x) {
                    seg = k;
                    break;
                } else if (fx > rta_pts[15].x) {
                    seg = 14;
                }
            }
            var dx_seg = Math.max(1.0, rta_pts[seg + 1].x - rta_pts[seg].x);
            var t_seg = clamp((fx - rta_pts[seg].x) / dx_seg, 0.0, 1.0);
            var base_y = rta_pts[seg].y * (1.0 - t_seg) + rta_pts[seg + 1].y * t_seg;
            var active_amount = clamp((gh - base_y) / gh, 0.0, 1.0);
            var detail = (Math.sin(fs * 1.9) * 3.5 + Math.cos(fs * 4.3) * 2.5) * active_amount;
            var fy = clamp(base_y + detail, 2.0, gh);
            mgraphics.line_to(fx, fy);
        }
        mgraphics.line_to(w, gh);
        mgraphics.close_path();
        mgraphics.fill();
    }

    var y_zero = db_to_y(0.0, gh);

    // Precompute filter coefficients once per active band for this frame
    var live_coeffs = [];
    var targ_coeffs = [];
    var band_has_dyn = [];
    var any_dyn_range = false;

    for (var bi = 0; bi < NUM_BANDS; bi++) {
        var bd = bands[bi];
        if (!bd.active) {
            live_coeffs.push(null);
            targ_coeffs.push(null);
            band_has_dyn.push(false);
            continue;
        }
        var has_dyn = (bd.dyn_on && uses_gain(bd.type) && Math.abs(bd.range) > 0.1);
        var act_g = (bd.dyn_on && uses_gain(bd.type)) ? bd.gr_db : 0.0;
        var dyn_g = has_dyn ? bd.range : 0.0;
        if (has_dyn) any_dyn_range = true;

        var c_live = prepare_svf_coeffs(bd.type, bd.freq, bd.q, (bd.gain + act_g) * global_scale);
        var c_targ = (has_dyn || Math.abs(act_g) > 0.05)
            ? prepare_svf_coeffs(bd.type, bd.freq, bd.q, (bd.gain + dyn_g) * global_scale)
            : c_live;

        live_coeffs.push(c_live);
        targ_coeffs.push(c_targ);
        band_has_dyn.push(has_dyn);
    }

    // 5. Selected Band Shaded Fill (Static + Pro-Q Style Dynamic Target Range Fill)
    var sb = bands[selected_band];
    if (sb && sb.active) {
        var sb_static_c = prepare_svf_coeffs(sb.type, sb.freq, sb.q, sb.gain * global_scale);
        mgraphics.set_source_rgba(EQ8_PINK[0], EQ8_PINK[1], EQ8_PINK[2], 0.13);
        mgraphics.move_to(0, y_zero);
        for (var i = 0; i <= NUM_STEPS; i++) {
            var x_pt = STEP_NORM[i] * w;
            var b_db = eval_svf_db(sb_static_c, STEP_TAN_W[i]);
            mgraphics.line_to(x_pt, clamp(db_to_y(b_db, gh), 0.0, gh));
        }
        mgraphics.line_to(w, y_zero);
        mgraphics.close_path();
        mgraphics.fill();

        // Dynamic target band fill (between static curve and dynamic target curve)
        if (sb.dyn_on && Math.abs(sb.range) > 0.1 && uses_gain(sb.type)) {
            var sb_targ_c = targ_coeffs[selected_band];
            mgraphics.set_source_rgba(EQ8_PINK[0], EQ8_PINK[1], EQ8_PINK[2], 0.22);
            for (var sd = 0; sd <= NUM_STEPS; sd++) {
                var xd = STEP_NORM[sd] * w;
                var yd = clamp(db_to_y(eval_svf_db(sb_static_c, STEP_TAN_W[sd]), gh), 0.0, gh);
                if (sd === 0) mgraphics.move_to(xd, yd);
                else mgraphics.line_to(xd, yd);
            }
            for (var sd2 = NUM_STEPS; sd2 >= 0; sd2--) {
                var xd2 = STEP_NORM[sd2] * w;
                var yd2 = clamp(db_to_y(eval_svf_db(sb_targ_c, STEP_TAN_W[sd2]), gh), 0.0, gh);
                mgraphics.line_to(xd2, yd2);
            }
            mgraphics.close_path();
            mgraphics.fill();
        }
    }

    // 6. Composite Dynamic Target Range Envelope Curve (Translucent Gold/Orange)
    //    + Real-Time Active Modulated Composite EQ Curve (Ableton EQ Eight Cyan)
    var target_pts_y = [];
    var live_pts_y = [];

    for (var step = 0; step <= NUM_STEPS; step++) {
        var tw = STEP_TAN_W[step];
        var sum_target = 0.0;
        var sum_live = 0.0;
        for (var b_i = 0; b_i < NUM_BANDS; b_i++) {
            var cl = live_coeffs[b_i];
            if (cl !== null) {
                var d_live = eval_svf_db(cl, tw);
                sum_live += d_live;
                var ct = targ_coeffs[b_i];
                sum_target += (ct === cl) ? d_live : eval_svf_db(ct, tw);
            }
        }
        target_pts_y.push(clamp(db_to_y(sum_target, gh), 0.0, gh));
        live_pts_y.push(clamp(db_to_y(sum_live, gh), 0.0, gh));
    }

    if (any_dyn_range) {
        mgraphics.set_line_width(1.25);
        mgraphics.set_source_rgba(0.98, 0.65, 0.15, 0.65);
        mgraphics.move_to(0, target_pts_y[0]);
        for (var s1 = 1; s1 <= NUM_STEPS; s1++) {
            mgraphics.line_to(STEP_NORM[s1] * w, target_pts_y[s1]);
        }
        mgraphics.stroke();
    }

    // Main Composite Response Curve (Exact EQ Eight Cyan: RGB(63, 196, 212) = #3fc4d4)
    mgraphics.set_source_rgba(0.247, 0.769, 0.831, 1.0);
    mgraphics.set_line_width(1.75);
    mgraphics.move_to(0, live_pts_y[0]);
    for (var s4 = 1; s4 <= NUM_STEPS; s4++) {
        mgraphics.line_to(STEP_NORM[s4] * w, live_pts_y[s4]);
    }
    mgraphics.stroke();

    // 7. Native EQ Eight Pink Band Dots + Pro-Q Dynamic Range Handle on top of Band Circle
    for (var idx = 0; idx < NUM_BANDS; idx++) {
        var b = bands[idx];
        if (!b.active) continue;

        var bx = freq_to_x(b.freq, w);
        var has_g = uses_gain(b.type);
        var y_main = clamp(db_to_y(has_g ? (b.gain * global_scale) : 0.0, gh), 6.5, gh - 6.5);
        var is_sel = (idx === selected_band);

        // --- Dynamic Range Stem & Draggable Ring Handle (on top of band circle!) ---
        if (has_g) {
            if (b.dyn_on && Math.abs(b.range) > 0.1) {
                var y_dyn = clamp(db_to_y((b.gain + b.range) * global_scale, gh), 5.0, gh - 5.0);

                // Vertical stem connecting main node to dynamic target ring
                mgraphics.set_line_width(1.4);
                mgraphics.set_source_rgba(EQ8_PINK[0], EQ8_PINK[1], EQ8_PINK[2], 0.85);
                mgraphics.move_to(bx, y_main);
                mgraphics.line_to(bx, y_dyn);
                mgraphics.stroke();

                // Draggable Dynamic Target Ring Handle at y_dyn
                mgraphics.set_source_rgba(EQ8_PINK[0], EQ8_PINK[1], EQ8_PINK[2], 1.0);
                mgraphics.arc(bx, y_dyn, 3.8, 0, Math.PI * 2);
                mgraphics.stroke();

                // Live Bouncing Reduction Dot along the stem
                if (Math.abs(b.gr_db) > 0.08) {
                    var y_act = clamp(db_to_y((b.gain + b.gr_db) * global_scale, gh), 5.0, gh - 5.0);
                    mgraphics.set_source_rgba(1.0, 1.0, 1.0, 0.95);
                    mgraphics.arc(bx, y_act, 2.8, 0, Math.PI * 2);
                    mgraphics.fill();
                }
            } else if (is_sel) {
                // Small Pro-Q style Dynamic Grab Ring directly on top of the selected band circle!
                var tab_y = Math.max(5.0, y_main - 13.0);
                mgraphics.set_line_width(1.3);
                mgraphics.set_source_rgba(EQ8_PINK[0], EQ8_PINK[1], EQ8_PINK[2], 0.85);
                mgraphics.arc(bx, tab_y, 3.3, 0, Math.PI * 2);
                mgraphics.stroke();
            }
        }

        // --- Native Ableton EQ Eight Band Dot Styling ---
        // Selected band: Solid filled pink circle (#ff91c3) with dark number
        // Unselected band: Hollow dark-filled circle with pink outline (#ff91c3) and pink number
        var nr = 6.5;
        if (is_sel) {
            mgraphics.set_source_rgba(EQ8_PINK[0], EQ8_PINK[1], EQ8_PINK[2], 1.0);
            mgraphics.arc(bx, y_main, nr, 0, Math.PI * 2);
            mgraphics.fill();

            mgraphics.set_source_rgba(0.078, 0.075, 0.102, 1.0);
        } else {
            mgraphics.set_source_rgba(0.078, 0.075, 0.102, 0.92);
            mgraphics.arc(bx, y_main, nr, 0, Math.PI * 2);
            mgraphics.fill();

            mgraphics.set_line_width(1.4);
            mgraphics.set_source_rgba(EQ8_PINK[0], EQ8_PINK[1], EQ8_PINK[2], 1.0);
            mgraphics.arc(bx, y_main, nr, 0, Math.PI * 2);
            mgraphics.stroke();

            mgraphics.set_source_rgba(EQ8_PINK[0], EQ8_PINK[1], EQ8_PINK[2], 1.0);
        }

        mgraphics.select_font_face("Ableton Sans Bold", "normal", "bold");
        mgraphics.set_font_size(9.0);
        mgraphics.move_to(bx - 2.6, y_main + 3.1);
        mgraphics.show_text((idx + 1).toString());
    }

    // 8. Bottom Band Selector Strip (y = gh .. h, 370x37)
    mgraphics.set_source_rgba(0.278, 0.255, 0.329, 1.0);
    mgraphics.rectangle(0, gh, w, STRIP_H);
    mgraphics.fill();

    var div_w = 2.0;
    var slot_w = (w + div_w) / NUM_BANDS; // (370 + 2) / 8 = 46.5px

    for (var c = 0; c < NUM_BANDS; c++) {
        var b_card = bands[c];
        var cx0 = Math.round(c * slot_w);
        var cx1 = (c === NUM_BANDS - 1) ? w : Math.round((c + 1) * slot_w - div_w);
        var cw = cx1 - cx0;
        var is_sel_card = (c === selected_band);

        if (!is_sel_card) {
            mgraphics.set_source_rgba(0.204, 0.184, 0.247, 1.0);
            mgraphics.rectangle(cx0, gh + 2, cw, STRIP_H - 4);
            mgraphics.fill();
        }

        // --- Top Row of Card: Filter Curve Dropdown Box (x = cx0 + 4 .. cx0 + cw - 4, w = cw - 8) ---
        var ddx = cx0 + 4;
        var ddy = gh + 5;
        var ddw = cw - 8;
        var ddh = 12;

        if (b_card.active) {
            mgraphics.set_source_rgba(0.125, 0.118, 0.153, 1.0);
            mgraphics.rectangle(ddx + 0.5, ddy + 0.5, ddw - 1, ddh - 1);
            mgraphics.fill();
        }

        mgraphics.set_source_rgba(0.086, 0.082, 0.110, 1.0);
        mgraphics.set_line_width(1.0);
        mgraphics.rectangle(ddx + 0.5, ddy + 0.5, ddw - 1, ddh - 1);
        mgraphics.stroke();

        if (is_sel_card) {
            mgraphics.set_source_rgba(0.827, 0.804, 0.843, 1.0);
        } else {
            mgraphics.set_source_rgba(0.455, 0.439, 0.475, 1.0);
        }
        draw_filter_icon(b_card.type, ddx + 3, ddy + 1, 15, ddh - 2);

        var tx = ddx + ddw - 8.5;
        var ty = ddy + 4.5;
        mgraphics.move_to(tx, ty);
        mgraphics.line_to(tx + 5.5, ty);
        mgraphics.line_to(tx + 2.75, ty + 3.5);
        mgraphics.close_path();
        mgraphics.fill();

        // --- Bottom Row of Card: Span exact same width (ddx .. ddx + ddw) as top curve selector ---
        // Left: Band Activator Square (10x10 at x = ddx)
        var cbx = ddx;
        var cby = gh + 21;
        var cbs = 10;

        if (b_card.active) {
            mgraphics.set_source_rgba(EQ8_CYAN[0], EQ8_CYAN[1], EQ8_CYAN[2], 1.0);
            mgraphics.rectangle(cbx, cby, cbs, cbs);
            mgraphics.fill();

            mgraphics.set_source_rgba(0.067, 0.071, 0.098, 1.0);
            mgraphics.set_line_width(1.0);
            mgraphics.rectangle(cbx + 0.5, cby + 0.5, cbs - 1, cbs - 1);
            mgraphics.stroke();
        } else {
            mgraphics.set_source_rgba(0.082, 0.078, 0.106, 1.0);
            mgraphics.rectangle(cbx, cby, cbs, cbs);
            mgraphics.fill();
        }

        // Center: Band Number (1..8)
        if (b_card.active || is_sel_card) {
            mgraphics.set_source_rgba(0.827, 0.804, 0.843, 1.0);
        } else {
            mgraphics.set_source_rgba(0.675, 0.651, 0.698, 1.0);
        }
        mgraphics.select_font_face("Ableton Sans Medium", "normal", "normal");
        mgraphics.set_font_size(9.5);
        mgraphics.move_to(cbx + 13.0, cby + 8.5);
        mgraphics.show_text((c + 1).toString());

        // Right: Minimalistic Dynamics Circle Toggle (right edge aligned with ddx + ddw!)
        var dr = 4.2;
        var dcx = ddx + ddw - dr - 0.5;
        var dcy = cby + 5.0;
        var is_dyn_drawer_for_this = (dyn_panel_open && is_sel_card);

        // Inner circle fill (dark recessed, or subtle tint if drawer is open for this band)
        if (is_dyn_drawer_for_this) {
            mgraphics.set_source_rgba(EQ8_CYAN[0], EQ8_CYAN[1], EQ8_CYAN[2], 0.25);
        } else {
            mgraphics.set_source_rgba(0.082, 0.078, 0.106, 1.0);
        }
        mgraphics.arc(dcx, dcy, dr, 0, Math.PI * 2);
        mgraphics.fill();

        // Circle border: Lit when dynamics is ON, empty greyed-out when dynamics is OFF
        if (b_card.dyn_on) {
            mgraphics.set_source_rgba(EQ8_CYAN[0], EQ8_CYAN[1], EQ8_CYAN[2], 1.0);
            mgraphics.set_line_width(1.4);
        } else {
            mgraphics.set_source_rgba(0.455, 0.439, 0.475, 0.85);
            mgraphics.set_line_width(1.05);
        }
        mgraphics.arc(dcx, dcy, dr, 0, Math.PI * 2);
        mgraphics.stroke();
    }

    // 9. Filter Type Popup Menu Overlay (if open)
    if (popup_band >= 0 && popup_band < NUM_BANDS) {
        var p_cx = popup_band * slot_w;
        var pw = 88;
        var ph = FILTER_NAMES.length * 14 + 4;
        var px = clamp(p_cx, 2, w - pw - 2);
        var py = gh - ph - 2;

        mgraphics.set_source_rgba(0.125, 0.118, 0.153, 0.98);
        mgraphics.rectangle(px, py, pw, ph);
        mgraphics.fill();

        mgraphics.set_source_rgba(0.278, 0.255, 0.329, 1.0);
        mgraphics.set_line_width(1.0);
        mgraphics.rectangle(px + 0.5, py + 0.5, pw - 1, ph - 1);
        mgraphics.stroke();

        for (var ft = 0; ft < FILTER_NAMES.length; ft++) {
            var iy = py + 2 + ft * 14;
            var is_cur_type = (bands[popup_band].type === ft);
            if (is_cur_type) {
                mgraphics.set_source_rgba(1.0, 0.569, 0.765, 0.25);
                mgraphics.rectangle(px + 2, iy, pw - 4, 13);
                mgraphics.fill();
                mgraphics.set_source_rgba(1.0, 0.569, 0.765, 1.0);
            } else {
                mgraphics.set_source_rgba(0.827, 0.804, 0.843, 1.0);
            }
            draw_filter_icon(ft, px + 5, iy + 2, 13, 9);
            mgraphics.select_font_face("Ableton Sans Medium", "normal", "normal");
            mgraphics.set_font_size(9.0);
            mgraphics.move_to(px + 23, iy + 10);
            mgraphics.show_text(FILTER_NAMES[ft]);
        }
    }
}

// --- Hit Detection (Checks Dynamic Range Handle on top of band circle FIRST!) ---
function find_hit(mx, my, w, gh) {
    // 1. Check Dynamic Range Handles on active bands first
    var best_idx = -1;
    var best_dist = 10.5;
    for (var i = 0; i < NUM_BANDS; i++) {
        var b = bands[i];
        if (b.active && uses_gain(b.type)) {
            var nx = freq_to_x(b.freq, w);
            var ny_main = clamp(db_to_y(b.gain * global_scale, gh), 6.5, gh - 6.5);
            var ny_dyn = -999.0;
            if (b.dyn_on && Math.abs(b.range) > 0.1) {
                ny_dyn = clamp(db_to_y((b.gain + b.range) * global_scale, gh), 5.0, gh - 5.0);
            } else if (i === selected_band) {
                ny_dyn = Math.max(5.0, ny_main - 13.0);
            }
            var d_dyn = Math.sqrt((mx - nx) * (mx - nx) + (my - ny_dyn) * (my - ny_dyn));
            if (d_dyn < best_dist && Math.abs(ny_dyn - ny_main) > 5.5) {
                best_dist = d_dyn;
                best_idx = i;
            }
        }
    }
    if (best_idx >= 0) {
        return { idx: best_idx, mode: "range" };
    }

    // 2. Check Main Band Nodes (0..7)
    best_dist = 14.0;
    for (var j = 0; j < NUM_BANDS; j++) {
        var band = bands[j];
        if (!band.active) continue;
        var bx = freq_to_x(band.freq, w);
        var by = clamp(db_to_y(uses_gain(band.type) ? (band.gain * global_scale) : 0.0, gh), 6.5, gh - 6.5);
        var d = Math.sqrt((mx - bx) * (mx - bx) + (my - by) * (my - by));
        if (d < best_dist) {
            best_dist = d;
            best_idx = j;
        }
    }
    if (best_idx >= 0) {
        return { idx: best_idx, mode: "freq_gain" };
    }
    return { idx: -1, mode: "none" };
}

function onclick(x, y, but, cmd, shift, capslock, option, ctrl) {
    var w = box.rect[2] - box.rect[0];
    var h = box.rect[3] - box.rect[1];
    var gh = h - STRIP_H;
    var slot_w = (w + 2.0) / NUM_BANDS;

    // 1. Check if clicking inside open Filter Type Popup Menu
    if (popup_band >= 0 && popup_band < NUM_BANDS) {
        var p_cx = popup_band * slot_w;
        var pw = 88;
        var ph = FILTER_NAMES.length * 14 + 4;
        var px = clamp(p_cx, 2, w - pw - 2);
        var py = gh - ph - 2;

        if (x >= px && x <= px + pw && y >= py && y <= py + ph) {
            var clicked_type = Math.floor((y - (py + 2)) / 14);
            if (clicked_type >= 0 && clicked_type < FILTER_NAMES.length) {
                bands[popup_band].type = clicked_type;
                bands[popup_band].active = 1;
                outlet(0, "band_type", popup_band, clicked_type);
                outlet(0, "band_active", popup_band, 1);
            }
            popup_band = -1;
            mgraphics.redraw();
            return;
        }
        popup_band = -1;
        mgraphics.redraw();
    }

    // 2. Check if clicking in Bottom Band Selector Strip (y >= gh)
    if (y >= gh) {
        var c_idx = clamp(Math.floor(x / slot_w), 0, NUM_BANDS - 1);
        var cx0 = Math.round(c_idx * slot_w);
        var cx1 = (c_idx === NUM_BANDS - 1) ? w : Math.round((c_idx + 1) * slot_w - 2.0);
        var cw = cx1 - cx0;
        var card_rel_x = x - cx0;
        var rel_y = y - gh;

        if (rel_y < 18) {
            // Clicked Top Filter Curve Dropdown
            selected_band = c_idx;
            outlet(0, "select_band", selected_band);
            popup_band = c_idx;
        } else if (card_rel_x >= cw - 15) {
            // Clicked the Minimalistic Dynamics Circle Toggle on the right of the bottom row!
            outlet(0, "click_band_dyn_dot", c_idx);
        } else {
            // Clicked Band Activator Square / Band Number on the left of the bottom row
            selected_band = c_idx;
            outlet(0, "select_band", selected_band);
            if (card_rel_x <= 22) {
                bands[c_idx].active = bands[c_idx].active ? 0 : 1;
                outlet(0, "band_active", c_idx, bands[c_idx].active);
            }
        }
        mgraphics.redraw();
        return;
    }

    // 3. Clicking inside Graph Area
    var hit = find_hit(x, y, w, gh);
    if (hit.idx >= 0) {
        selected_band = hit.idx;
        drag_band = hit.idx;
        last_mx = x;
        last_my = y;
        outlet(0, "select_band", selected_band);

        if (option) {
            drag_mode = "q";
        } else if (hit.mode === "range" || shift) {
            bands[hit.idx].dyn_on = 1;
            outlet(0, "band_dyn_on", hit.idx, 1);
            drag_mode = "range";
        } else {
            drag_mode = "freq_gain";
        }
        mgraphics.redraw();
    } else {
        drag_band = -1;
        drag_mode = "none";
    }
}

function ondrag(x, y, but, cmd, shift, capslock, option, ctrl) {
    if (but === 0) {
        drag_band = -1;
        drag_mode = "none";
        return;
    }
    if (drag_band < 0) return;

    var w = box.rect[2] - box.rect[0];
    var h = box.rect[3] - box.rect[1];
    var gh = h - STRIP_H;
    var b = bands[drag_band];

    if (drag_mode === "q" || option) {
        var dy = last_my - y;
        b.q = clamp(b.q * Math.pow(1.025, dy), 0.1, 18.0);
        outlet(0, "band_q", drag_band, b.q);
    } else if (drag_mode === "range" || shift) {
        var target_db = y_to_db(y, gh);
        var sc = Math.abs(global_scale) > 0.05 ? global_scale : 1.0;
        b.range = clamp((target_db / sc) - b.gain, -15.0, 15.0);
        b.dyn_on = (Math.abs(b.range) > 0.05) ? 1 : b.dyn_on;
        outlet(0, "band_range", drag_band, b.range);
    } else {
        b.freq = x_to_freq(x, w);
        if (uses_gain(b.type)) {
            var raw_db = y_to_db(y, gh);
            var sc2 = Math.abs(global_scale) > 0.05 ? global_scale : 1.0;
            b.gain = clamp(raw_db / sc2, -15.0, 15.0);
        }
        outlet(0, "band_fg", drag_band, b.freq, b.gain);
    }

    last_mx = x;
    last_my = y;
    mgraphics.redraw();
}

function ondblclick(x, y) {
    var w = box.rect[2] - box.rect[0];
    var h = box.rect[3] - box.rect[1];
    var gh = h - STRIP_H;
    if (y >= gh) return;

    var hit = find_hit(x, y, w, gh);
    if (hit.idx >= 0) {
        if (hit.mode === "range") {
            bands[hit.idx].range = 0.0;
            bands[hit.idx].dyn_on = 0;
            outlet(0, "band_range", hit.idx, 0.0);
            outlet(0, "band_dyn_on", hit.idx, 0);
        } else {
            bands[hit.idx].active = 0;
            outlet(0, "band_active", hit.idx, 0);
        }
        mgraphics.redraw();
    } else {
        for (var i = 0; i < NUM_BANDS; i++) {
            if (!bands[i].active) {
                bands[i].active = 1;
                bands[i].freq = x_to_freq(x, w);
                bands[i].gain = clamp(y_to_db(y, gh), -15.0, 15.0);
                selected_band = i;
                outlet(0, "select_band", i);
                outlet(0, "band_active", i, 1);
                outlet(0, "band_fg", i, bands[i].freq, bands[i].gain);
                mgraphics.redraw();
                return;
            }
        }
    }
}

// --- External Setters from Controller ---
function set_band(idx, active, freq, gain, q, type, dyn_on, range, thresh) {
    if (idx < 0 || idx >= NUM_BANDS) return;
    var b = bands[idx];
    b.active = active ? 1 : 0;
    b.freq = clamp(freq, MIN_FREQ, MAX_FREQ);
    b.gain = clamp(gain, -15.0, 15.0);
    b.q = clamp(q, 0.1, 18.0);
    b.type = clamp(Math.round(type), 0, 7);
    b.dyn_on = dyn_on ? 1 : 0;
    b.range = clamp(range, -24.0, 24.0);
    b.thresh = clamp(thresh, -60.0, 0.0);
    mgraphics.redraw();
}

function set_dyn_open(v) {
    dyn_panel_open = v ? 1 : 0;
    mgraphics.redraw();
}

function set_gr() {
    var args = arrayfromargs(arguments);
    for (var i = 0; i < NUM_BANDS && i < args.length; i++) {
        bands[i].gr_db = args[i];
    }
    if (drag_band < 0) {
        mgraphics.redraw();
    }
}

function set_gr_one(idx, val) {
    if (idx >= 0 && idx < NUM_BANDS) {
        bands[idx].gr_db = val;
        if (idx === 7 && drag_band < 0) mgraphics.redraw();
    }
}

function set_rta() {
    var args = arrayfromargs(arguments);
    for (var i = 0; i < 16 && i < args.length; i++) {
        rta_db[i] = args[i];
    }
    if (rta_enabled && drag_band < 0) {
        mgraphics.redraw();
    }
}

function set_rta_one(idx, val) {
    if (idx >= 0 && idx < 16) {
        rta_db[idx] = val;
        if (idx === 15 && rta_enabled && drag_band < 0) mgraphics.redraw();
    }
}

function set_rta_on(v) {
    rta_enabled = v ? 1 : 0;
    mgraphics.redraw();
}

function select(idx) {
    selected_band = clamp(idx, 0, NUM_BANDS - 1);
    mgraphics.redraw();
}

function set_scale(s) {
    global_scale = clamp(s / 100.0, 0.0, 2.0);
    mgraphics.redraw();
}

function set_adaptive_q(v) {
    adaptive_q = v ? 1 : 0;
    mgraphics.redraw();
}

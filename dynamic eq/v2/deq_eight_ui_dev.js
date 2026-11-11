// deq_eight_ui_dev.js
// Authentic Ableton EQ Eight Graph + High-Resolution 4096-Point FFT RTA + Pro-Q Dynamic EQ Visualizer (370x132)
// - Fills its background with `THEME.lcd_bg` (#14131a, updated dynamically from Ableton's theme)
// - Reads 2048 Hann-windowed FFT bins directly from native C++ `fft~ 4096 4096 0` -> `poke~ ---rta_fft` (`Buffer`)
//   and plots them on the exact 3-decade 12 Hz .. 22 kHz logarithmic grid (including while dragging band dots!).
// - Optimized inner loop: precomputed FFT bin lookup tables, precomputed pixel grid lines, and linear mag_sq
//   accumulation (1 `Math.log` per frequency step instead of 8) for ultra-smooth 60fps curve dragging.

inlets = 1;
outlets = 1;

mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

var NUM_BANDS = 8;
var SAMPLE_RATE = 44100.0;
var FFT_SIZE = 4096.0;
var MIN_FREQ = 12.0;
var MAX_FREQ = 22000.0;
var MIN_DB = -15.0;
var MAX_DB = 15.0;
var LOG_FREQ_RATIO = Math.log(MAX_FREQ / MIN_FREQ);

var selected_band = 2; // Default selected band = Band 3 (1.00 kHz), matching EQ Eight
var drag_band = -1;
var drag_mode = "none"; // "freq_gain", "range", "q"
var last_mx = 0;
var last_my = 0;

var global_scale = 1.0; // 0.0 .. 2.0 (0% .. 200%)
var adaptive_q = 1;
var rta_on = 1;
var rta_buf = null;

// Dynamic Theme Palette (defaults to Ableton Live 12 Default Dark Theme, updated live via `set_theme_color`)
var THEME = {
    lcd_bg:        [0.078, 0.075, 0.102, 1.0], // live_lcd_bg (#14131a)
    lcd_frame:     [0.278, 0.255, 0.329, 1.0], // live_lcd_frame (#474154)
    scale_text:    [0.540, 0.520, 0.580, 1.0], // live_display_scale_text
    control_fg:    [0.224, 0.824, 0.894, 1.0], // live_lcd_control_fg_alt (#39d2e4 Cyan)
    handle_one:    [1.000, 0.569, 0.765, 1.0], // live_display_handle_one (#ff91c3 Pink)
    spectrum_fill: [0.333, 0.314, 0.404, 1.0]  // live_spectrum_default_color (#555067)
};

var DEFAULT_FREQS = [30.0, 200.0, 1000.0, 5000.0, 100.0, 1000.0, 5000.0, 18000.0];
var DEFAULT_TYPES = [2, 3, 3, 5, 3, 3, 3, 6];
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
        thresh: -22.0,
        gr_db: 0.0
    });
}

function clamp(v, lo, hi) {
    return v < lo ? lo : (v > hi ? hi : v);
}

function uses_gain(btype) {
    return (btype === 2 || btype === 3 || btype === 5);
}

function freq_to_x(f, w) {
    var norm = Math.log(clamp(f, MIN_FREQ, MAX_FREQ) / MIN_FREQ) / LOG_FREQ_RATIO;
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

// Precomputed frequency evaluation grid (96 steps across 12 Hz .. 22 kHz = ~3.8px per segment)
var NUM_STEPS = 96;
var STEP_NORM = [];
var STEP_TAN_W = [];
for (var s_init = 0; s_init <= NUM_STEPS; s_init++) {
    var norm_s = s_init / NUM_STEPS;
    var f_s = MIN_FREQ * Math.pow(MAX_FREQ / MIN_FREQ, norm_s);
    STEP_NORM.push(norm_s);
    STEP_TAN_W.push(Math.tan(Math.PI * f_s / SAMPLE_RATE));
}

// High-Resolution 4096-Point FFT RTA Logarithmic Grid (124 points across 12 Hz .. 22 kHz)
// Precomputes all bin indices and Catmull-Rom cubic interpolation weights once at init!
var NUM_RTA_PTS = 124;
var RTA_NORM_X = [];
var RTA_TILT_DB = [];
var RTA_IS_CUBIC = [];
var RTA_IDX0 = [];
var RTA_IDX_M1 = [];
var RTA_IDX_P1 = [];
var RTA_IDX_P2 = [];
var RTA_W_M1 = [];
var RTA_W_0 = [];
var RTA_W_P1 = [];
var RTA_W_P2 = [];
var RTA_FRAC = [];
var RTA_B_START = [];
var RTA_B_END = [];
var rta_db_smooth = [];
var rta_y_norm = [];

(function init_rta_tables() {
    var bin_scale = FFT_SIZE / SAMPLE_RATE;
    var rta_freqs = [];
    for (var ri = 0; ri <= NUM_RTA_PTS; ri++) {
        var rn = ri / NUM_RTA_PTS;
        var rf = MIN_FREQ * Math.pow(MAX_FREQ / MIN_FREQ, rn);
        RTA_NORM_X.push(rn);
        rta_freqs.push(rf);
        RTA_TILT_DB.push(3.5 * (Math.log(rf / 250.0) / Math.LN10));
        rta_db_smooth.push(-90.0);
        rta_y_norm.push(1.0);
    }
    for (var i = 0; i <= NUM_RTA_PTS; i++) {
        var f0 = rta_freqs[i];
        var f1 = (i < NUM_RTA_PTS) ? rta_freqs[i + 1] : MAX_FREQ;
        var k0_f = f0 * bin_scale;
        var k1_f = f1 * bin_scale;
        if (k1_f - k0_f <= 1.25) {
            var idx0 = clamp(Math.floor(k0_f), 1, 2046);
            var t = k0_f - idx0;
            var t2 = t * t;
            var t3 = t2 * t;
            RTA_IS_CUBIC.push(1);
            RTA_IDX0.push(idx0);
            RTA_IDX_M1.push(idx0 - 1 > 0 ? idx0 - 1 : 1);
            RTA_IDX_P1.push(idx0 + 1);
            RTA_IDX_P2.push(idx0 + 2 <= 2047 ? idx0 + 2 : 2047);
            // Catmull-Rom basis weights for m_prev, m_curr, m_next, m_next2:
            RTA_W_M1.push(-0.5 * t + t2 - 0.5 * t3);
            RTA_W_0.push(1.0 - 2.5 * t2 + 1.5 * t3);
            RTA_W_P1.push(0.5 * t + 2.0 * t2 - 1.5 * t3);
            RTA_W_P2.push(-0.5 * t2 + 0.5 * t3);
            RTA_FRAC.push(t);
            RTA_B_START.push(0);
            RTA_B_END.push(0);
        } else {
            var b_start = clamp(Math.floor(k0_f), 1, 2047);
            var b_end = clamp(Math.ceil(k1_f), b_start, 2047);
            RTA_IS_CUBIC.push(0);
            RTA_IDX0.push(0);
            RTA_IDX_M1.push(0);
            RTA_IDX_P1.push(0);
            RTA_IDX_P2.push(0);
            RTA_W_M1.push(0.0);
            RTA_W_0.push(0.0);
            RTA_W_P1.push(0.0);
            RTA_W_P2.push(0.0);
            RTA_FRAC.push(0.0);
            RTA_B_START.push(b_start);
            RTA_B_END.push(b_end);
        }
    }
})();

// Precompute Grid Line X norms once (12 Hz .. 22 kHz matching Ableton EQ Eight)
var SUB_FREQS = [
    20, 30, 40, 50, 60, 70, 80, 90,
    200, 300, 400, 500, 600, 700, 800, 900,
    2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000,
    20000
];
var SUB_NORM_X = [];
for (var sfi = 0; sfi < SUB_FREQS.length; sfi++) {
    SUB_NORM_X.push(Math.log(SUB_FREQS[sfi] / MIN_FREQ) / LOG_FREQ_RATIO);
}

var MAJ_FREQS = [100, 1000, 10000];
var MAJ_NORM_X = [];
for (var mfi = 0; mfi < MAJ_FREQS.length; mfi++) {
    MAJ_NORM_X.push(Math.log(MAJ_FREQS[mfi] / MIN_FREQ) / LOG_FREQ_RATIO);
}

// Cached pixel-snapped grid coordinates (recomputed only if canvas size changes)
var cached_w = -1;
var cached_gh = -1;
var SUB_X_PX = [];
var MAJ_X_PX = [];
var DB_Y_PX = [];
var STEP_X_PX = [];
var RTA_X_PX = [];

function update_cached_coords(w, gh) {
    if (w === cached_w && gh === cached_gh) return;
    cached_w = w;
    cached_gh = gh;
    SUB_X_PX = [];
    for (var s = 0; s < SUB_NORM_X.length; s++) {
        SUB_X_PX.push(Math.round(SUB_NORM_X[s] * w) + 0.5);
    }
    MAJ_X_PX = [];
    for (var m = 0; m < MAJ_NORM_X.length; m++) {
        MAJ_X_PX.push(Math.round(MAJ_NORM_X[m] * w) + 0.5);
    }
    var db_lines = [-12, -6, 0, 6, 12];
    DB_Y_PX = [];
    for (var d = 0; d < db_lines.length; d++) {
        DB_Y_PX.push(Math.round(db_to_y(db_lines[d], gh)) + 0.5);
    }
    STEP_X_PX = [];
    for (var st = 0; st <= NUM_STEPS; st++) {
        STEP_X_PX.push(STEP_NORM[st] * w);
    }
    RTA_X_PX = [];
    for (var rt = 0; rt <= NUM_RTA_PTS; rt++) {
        RTA_X_PX.push(RTA_NORM_X[rt] * w);
    }
}

// --- Sample 2048 FFT bins from native `buffer~` onto our exact log grid ---
var LOG10_20 = 20.0 / Math.LN10;

function update_rta_from_buffer() {
    if (!rta_on || !rta_buf) return false;
    var bins = rta_buf.peek(1, 0, 2048);
    if (!bins || bins.length < 2048) return false;

    var any_change = false;
    for (var i = 0; i <= NUM_RTA_PTS; i++) {
        var mag = 0.0;
        if (RTA_IS_CUBIC[i]) {
            var m_curr = bins[RTA_IDX0[i]];
            var m_next = bins[RTA_IDX_P1[i]];
            mag = RTA_W_M1[i] * bins[RTA_IDX_M1[i]]
                + RTA_W_0[i]  * m_curr
                + RTA_W_P1[i] * m_next
                + RTA_W_P2[i] * bins[RTA_IDX_P2[i]];
            if (mag < 0.0) {
                var frac = RTA_FRAC[i];
                mag = (1.0 - frac) * m_curr + frac * m_next;
            }
        } else {
            var b_start = RTA_B_START[i];
            var b_end = RTA_B_END[i];
            for (var b = b_start; b <= b_end; b++) {
                var bv = bins[b];
                if (bv > mag) mag = bv;
            }
        }

        var raw_db = (mag > 1e-6) ? (LOG10_20 * Math.log(mag) + RTA_TILT_DB[i]) : -90.0;
        var prev_db = rta_db_smooth[i];
        var next_db = (raw_db > prev_db)
            ? (0.32 * prev_db + 0.68 * raw_db)
            : (0.82 * prev_db + 0.18 * raw_db);
        if (next_db < -90.0) next_db = -90.0;

        if (Math.abs(next_db - prev_db) > 0.12) {
            any_change = true;
        }
        rta_db_smooth[i] = next_db;
        var norm_amp = clamp((next_db + 68.0) / 66.0, 0.0, 1.0);
        rta_y_norm[i] = 1.0 - norm_amp;
    }
    return any_change;
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

// Pure arithmetic magnitude-squared evaluation (zero Math.log inside inner band loop!)
function eval_svf_mag_sq(c, tan_w) {
    if (c.bypass) return 1.0;
    var u = tan_w * c.inv_g;
    var u2 = u * u;
    var one_minus_u2 = 1.0 - u2;
    var den = one_minus_u2 * one_minus_u2 + c.k2 * u2;
    if (den < 1e-18) return 1.0;

    var num_r = c.m0 * one_minus_u2 + c.m2;
    var num_i = u * c.m0k_plus_m1;
    var mag_sq = (num_r * num_r + num_i * num_i) / den;
    if (c.is_48db) {
        mag_sq = mag_sq * mag_sq;
    }
    return mag_sq;
}

function eval_svf_db(c, tan_w) {
    if (c.bypass) return 0.0;
    var mag_sq = eval_svf_mag_sq(c, tan_w);
    if (mag_sq <= 1e-12) return -120.0;
    return LOG10_SCALE * Math.log(mag_sq);
}

function paint() {
    var w = box.rect[2] - box.rect[0];
    var gh = box.rect[3] - box.rect[1]; // Full 132px height is the graph
    update_cached_coords(w, gh);

    var fg = THEME.control_fg;
    var pk = THEME.handle_one;
    var sc_col = THEME.scale_text;
    var bg_col = THEME.lcd_bg;

    // 1. Dynamic Theme LCD Graph Background (`live_lcd_bg`)
    mgraphics.set_source_rgba(bg_col[0], bg_col[1], bg_col[2], 1.0);
    mgraphics.rectangle(0, 0, w, gh);
    mgraphics.fill();

    // 2. High-Resolution 4096-Point FFT Spectrum Analyzer
    //    Single solid fill color (`live_spectrum_default_color`) with no border line, matching Vanilla EQ Eight!
    if (rta_on) {
        var sp_col = THEME.spectrum_fill;
        mgraphics.set_source_rgba(sp_col[0], sp_col[1], sp_col[2], 0.85);
        mgraphics.move_to(0, gh);
        for (var r = 0; r <= NUM_RTA_PTS; r++) {
            mgraphics.line_to(RTA_X_PX[r], rta_y_norm[r] * gh);
        }
        mgraphics.line_to(w, gh);
        mgraphics.close_path();
        mgraphics.fill();
    }

    // 3. Logarithmic Frequency Grid Lines (drawn subtly over the spectrum like Ableton EQ Eight!)
    mgraphics.set_line_width(1.0);
    mgraphics.set_source_rgba(sc_col[0], sc_col[1], sc_col[2], 0.12);
    for (var s = 0; s < SUB_X_PX.length; s++) {
        var sx = SUB_X_PX[s];
        mgraphics.move_to(sx, 0);
        mgraphics.line_to(sx, gh);
    }
    mgraphics.stroke();

    mgraphics.set_source_rgba(sc_col[0], sc_col[1], sc_col[2], 0.24);
    for (var m = 0; m < MAJ_X_PX.length; m++) {
        var mx = MAJ_X_PX[m];
        mgraphics.move_to(mx, 0);
        mgraphics.line_to(mx, gh);
    }
    mgraphics.stroke();

    // 4. Horizontal dB Grid Lines (-12, -6, 0, +6, +12) -> indices 0, 1, 2 (0dB), 3, 4
    mgraphics.set_source_rgba(sc_col[0], sc_col[1], sc_col[2], 0.16);
    for (var d = 0; d < DB_Y_PX.length; d++) {
        if (d === 2) continue;
        var dy = DB_Y_PX[d];
        mgraphics.move_to(0, dy);
        mgraphics.line_to(w, dy);
    }
    mgraphics.stroke();

    mgraphics.set_source_rgba(sc_col[0], sc_col[1], sc_col[2], 0.34);
    mgraphics.move_to(0, DB_Y_PX[2]);
    mgraphics.line_to(w, DB_Y_PX[2]);
    mgraphics.stroke();

    // 5. Precompute filter coefficients once per active non-bypassed band for this frame
    var active_live_c = [];
    var active_targ_c = [];
    var targ_by_band = [];
    var any_dyn_range = false;

    for (var bi = 0; bi < NUM_BANDS; bi++) {
        var bd = bands[bi];
        if (!bd.active) {
            targ_by_band.push(null);
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

        targ_by_band.push(c_targ);
        if (!c_live.bypass) active_live_c.push(c_live);
        if (!c_targ.bypass) active_targ_c.push(c_targ);
    }

    // 6. Shaded Range Indicator ONLY for Dynamic Ranges
    if (any_dyn_range) {
        for (var dbi = 0; dbi < NUM_BANDS; dbi++) {
            var dbd = bands[dbi];
            if (dbd.active && dbd.dyn_on && Math.abs(dbd.range) > 0.1 && uses_gain(dbd.type)) {
                var db_static_c = prepare_svf_coeffs(dbd.type, dbd.freq, dbd.q, dbd.gain * global_scale);
                var db_targ_c = targ_by_band[dbi];
                var fill_alpha = (dbi === selected_band) ? 0.24 : 0.15;
                mgraphics.set_source_rgba(fg[0], fg[1], fg[2], fill_alpha);
                for (var sd = 0; sd <= NUM_STEPS; sd++) {
                    var xd = STEP_X_PX[sd];
                    var yd = clamp(db_to_y(eval_svf_db(db_static_c, STEP_TAN_W[sd]), gh), 0.0, gh);
                    if (sd === 0) mgraphics.move_to(xd, yd);
                    else mgraphics.line_to(xd, yd);
                }
                for (var sd2 = NUM_STEPS; sd2 >= 0; sd2--) {
                    var xd2 = STEP_X_PX[sd2];
                    var yd2 = clamp(db_to_y(eval_svf_db(db_targ_c, STEP_TAN_W[sd2]), gh), 0.0, gh);
                    mgraphics.line_to(xd2, yd2);
                }
                mgraphics.close_path();
                mgraphics.fill();
            }
        }
    }

    // 7. Composite Dynamic Target Range Envelope Curve + Active Modulated Composite EQ Curve
    var n_live = active_live_c.length;
    var n_targ = active_targ_c.length;
    var mid_y = DB_Y_PX[2];

    if (any_dyn_range) {
        mgraphics.set_line_width(1.1);
        mgraphics.set_source_rgba(fg[0], fg[1], fg[2], 0.50);
        for (var st_t = 0; st_t <= NUM_STEPS; st_t++) {
            var tw_t = STEP_TAN_W[st_t];
            var prod_t = 1.0;
            for (var bt = 0; bt < n_targ; bt++) {
                prod_t *= eval_svf_mag_sq(active_targ_c[bt], tw_t);
            }
            var db_t = (prod_t <= 1e-12) ? -120.0 : (LOG10_SCALE * Math.log(prod_t));
            var yt = clamp(db_to_y(db_t, gh), 0.0, gh);
            if (st_t === 0) mgraphics.move_to(0, yt);
            else mgraphics.line_to(STEP_X_PX[st_t], yt);
        }
        mgraphics.stroke();
    }

    // Main Composite Response Curve (`live_lcd_control_fg_alt` Cyan, 1.35px width)
    mgraphics.set_source_rgba(fg[0], fg[1], fg[2], 1.0);
    mgraphics.set_line_width(1.35);
    if (n_live === 0) {
        mgraphics.move_to(0, mid_y);
        mgraphics.line_to(w, mid_y);
    } else {
        for (var step = 0; step <= NUM_STEPS; step++) {
            var tw = STEP_TAN_W[step];
            var prod_l = 1.0;
            for (var bl = 0; bl < n_live; bl++) {
                prod_l *= eval_svf_mag_sq(active_live_c[bl], tw);
            }
            var db_l = (prod_l <= 1e-12) ? -120.0 : (LOG10_SCALE * Math.log(prod_l));
            var yl = clamp(db_to_y(db_l, gh), 0.0, gh);
            if (step === 0) mgraphics.move_to(0, yl);
            else mgraphics.line_to(STEP_X_PX[step], yl);
        }
    }
    mgraphics.stroke();

    // 8. Dynamic Theme Band Dots (`live_display_handle_one`) + Offset-Right Dynamic Range Handle
    mgraphics.select_font_face("Ableton Sans Small Bold", "normal", "bold");
    mgraphics.set_font_size(8.8);

    for (var idx = 0; idx < NUM_BANDS; idx++) {
        var b = bands[idx];
        if (!b.active) continue;

        var bx = freq_to_x(b.freq, w);
        var has_g = uses_gain(b.type);
        var y_main = clamp(db_to_y(has_g ? b.gain : 0.0, gh), 6.0, gh - 6.0);
        var is_sel = (idx === selected_band);
        var nr = 5.8;

        // --- Dynamic Range Stem & Draggable Ring Handle (Offset to the right of the band dot) ---
        if (has_g) {
            var dx_off = (bx > w - 16.0) ? -11.0 : 11.0;
            var dx = bx + dx_off;
            var edge_x = bx + (dx_off > 0 ? nr : -nr);

            if (b.dyn_on && Math.abs(b.range) > 0.1) {
                var y_dyn = clamp(db_to_y(b.gain + b.range, gh), 5.0, gh - 5.0);

                mgraphics.set_line_width(1.25);
                mgraphics.set_source_rgba(fg[0], fg[1], fg[2], 0.85);
                mgraphics.move_to(edge_x, y_main);
                mgraphics.line_to(dx, y_main);
                mgraphics.line_to(dx, y_dyn);
                mgraphics.stroke();

                mgraphics.set_source_rgba(fg[0], fg[1], fg[2], 1.0);
                mgraphics.arc(dx, y_dyn, 3.3, 0, Math.PI * 2);
                mgraphics.stroke();

                if (Math.abs(b.gr_db) > 0.08) {
                    var y_act = clamp(db_to_y(b.gain + b.gr_db, gh), 5.0, gh - 5.0);
                    mgraphics.set_source_rgba(1.0, 1.0, 1.0, 0.95);
                    mgraphics.arc(dx, y_act, 2.5, 0, Math.PI * 2);
                    mgraphics.fill();
                }
            } else if (is_sel) {
                var ring_edge = dx - (dx_off > 0 ? 3.0 : -3.0);
                mgraphics.set_line_width(1.1);
                mgraphics.set_source_rgba(fg[0], fg[1], fg[2], 0.65);
                mgraphics.move_to(edge_x, y_main);
                mgraphics.line_to(ring_edge, y_main);
                mgraphics.stroke();

                mgraphics.set_line_width(1.2);
                mgraphics.set_source_rgba(fg[0], fg[1], fg[2], 0.90);
                mgraphics.arc(dx, y_main, 3.0, 0, Math.PI * 2);
                mgraphics.stroke();
            }
        }

        // --- Theme-Cohesive EQ Eight Band Dot (`live_display_handle_one`) ---
        if (is_sel) {
            mgraphics.set_source_rgba(pk[0], pk[1], pk[2], 1.0);
            mgraphics.arc(bx, y_main, nr, 0, Math.PI * 2);
            mgraphics.fill();

            mgraphics.set_source_rgba(bg_col[0], bg_col[1], bg_col[2], 1.0);
        } else {
            mgraphics.set_source_rgba(bg_col[0], bg_col[1], bg_col[2], 0.18);
            mgraphics.arc(bx, y_main, nr, 0, Math.PI * 2);
            mgraphics.fill();

            mgraphics.set_line_width(1.2);
            mgraphics.set_source_rgba(pk[0], pk[1], pk[2], 1.0);
            mgraphics.arc(bx, y_main, nr, 0, Math.PI * 2);
            mgraphics.stroke();

            mgraphics.set_source_rgba(pk[0], pk[1], pk[2], 1.0);
        }

        mgraphics.move_to(bx - 2.5, y_main + 3.0);
        mgraphics.show_text((idx + 1).toString());
    }
}

// --- Hit Detection (Checks Offset-Right Dynamic Range Handle FIRST!) ---
function find_hit(mx, my, w, gh) {
    var best_idx = -1;
    var best_dist = 9.5;
    for (var i = 0; i < NUM_BANDS; i++) {
        var b = bands[i];
        if (b.active && uses_gain(b.type)) {
            var has_active_dyn = (b.dyn_on && Math.abs(b.range) > 0.1);
            if (has_active_dyn || i === selected_band) {
                var bx = freq_to_x(b.freq, w);
                var dx = bx + ((bx > w - 16.0) ? -11.5 : 11.5);
                var eff_range = has_active_dyn ? b.range : 0.0;
                var ny_dyn = clamp(db_to_y(b.gain + eff_range, gh), 5.0, gh - 5.0);
                var d_dyn = Math.sqrt((mx - dx) * (mx - dx) + (my - ny_dyn) * (my - ny_dyn));
                if (d_dyn < best_dist) {
                    best_dist = d_dyn;
                    best_idx = i;
                }
            }
        }
    }
    if (best_idx >= 0) {
        return { idx: best_idx, mode: "range" };
    }

    best_dist = 13.0;
    for (var j = 0; j < NUM_BANDS; j++) {
        var band = bands[j];
        if (!band.active) continue;
        var bx2 = freq_to_x(band.freq, w);
        var by2 = clamp(db_to_y(uses_gain(band.type) ? band.gain : 0.0, gh), 6.5, gh - 6.5);
        var d = Math.sqrt((mx - bx2) * (mx - bx2) + (my - by2) * (my - by2));
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
    var gh = box.rect[3] - box.rect[1];

    var hit = find_hit(x, y, w, gh);
    if (hit.idx >= 0) {
        var prev_sel = selected_band;
        selected_band = hit.idx;
        drag_band = hit.idx;
        last_mx = x;
        last_my = y;
        if (selected_band !== prev_sel) {
            outlet(0, "select_band", selected_band);
        }

        if (option) {
            drag_mode = "q";
        } else if (hit.mode === "range" || shift) {
            if (!bands[hit.idx].dyn_on) {
                bands[hit.idx].dyn_on = 1;
                outlet(0, "band_dyn_on", hit.idx, 1);
            }
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
        if (drag_band >= 0) {
            outlet(0, "drag_end", drag_band);
        }
        drag_band = -1;
        drag_mode = "none";
        return;
    }
    if (drag_band < 0) return;

    if (Math.abs(x - last_mx) < 0.15 && Math.abs(y - last_my) < 0.15) return;

    var w = box.rect[2] - box.rect[0];
    var gh = box.rect[3] - box.rect[1];
    var b = bands[drag_band];

    last_mx = x;
    last_my = y;

    if (drag_mode === "q" || option) {
        var dy = last_my - y;
        b.q = clamp(b.q * Math.pow(1.025, dy), 0.1, 18.0);
        mgraphics.redraw();
        outlet(0, "band_q", drag_band, b.q);
    } else if (drag_mode === "range" || shift) {
        var target_db = y_to_db(y, gh);
        b.range = clamp(target_db - b.gain, -15.0, 15.0);
        b.dyn_on = (Math.abs(b.range) > 0.05) ? 1 : b.dyn_on;
        mgraphics.redraw();
        outlet(0, "band_range", drag_band, b.range);
    } else {
        b.freq = x_to_freq(x, w);
        if (uses_gain(b.type)) {
            b.gain = clamp(y_to_db(y, gh), -15.0, 15.0);
        }
        mgraphics.redraw();
        outlet(0, "band_fg", drag_band, b.freq, b.gain);
    }
}

function onwheel(x, y, amt1, amt2, cmd, shift, capslock, option, ctrl) {
    var w = box.rect[2] - box.rect[0];
    var gh = box.rect[3] - box.rect[1];

    var delta = (Math.abs(amt2) >= Math.abs(amt1)) ? amt2 : amt1;
    if (Math.abs(delta) < 0.0001) return;

    var target_idx = selected_band;
    var best_dist = 24.0;
    for (var i = 0; i < NUM_BANDS; i++) {
        var b = bands[i];
        if (!b.active) continue;
        var bx = freq_to_x(b.freq, w);
        var by = clamp(db_to_y(uses_gain(b.type) ? b.gain : 0.0, gh), 6.5, gh - 6.5);
        var d = Math.sqrt((x - bx) * (x - bx) + (y - by) * (y - by));
        if (d < best_dist) {
            best_dist = d;
            target_idx = i;
        }
    }

    if (target_idx < 0 || target_idx >= NUM_BANDS || !bands[target_idx].active) return;
    if (target_idx !== selected_band) {
        selected_band = target_idx;
        outlet(0, "select_band", selected_band);
    }

    var dir = delta > 0 ? 1.0 : -1.0;
    var mag = clamp(Math.abs(delta), 0.25, 3.0);
    bands[target_idx].q = clamp(bands[target_idx].q * Math.pow(1.10, dir * mag), 0.1, 18.0);
    mgraphics.redraw();
    outlet(0, "band_q", target_idx, bands[target_idx].q);
}

function ondblclick(x, y) {
    var w = box.rect[2] - box.rect[0];
    var gh = box.rect[3] - box.rect[1];

    var hit = find_hit(x, y, w, gh);
    if (hit.idx >= 0) {
        if (hit.mode === "range") {
            bands[hit.idx].range = 0.0;
            bands[hit.idx].dyn_on = 0;
            mgraphics.redraw();
            outlet(0, "band_range", hit.idx, 0.0);
            outlet(0, "band_dyn_on", hit.idx, 0);
        } else {
            bands[hit.idx].active = 0;
            mgraphics.redraw();
            outlet(0, "band_active", hit.idx, 0);
        }
    } else {
        for (var i = 0; i < NUM_BANDS; i++) {
            if (!bands[i].active) {
                bands[i].active = 1;
                bands[i].freq = x_to_freq(x, w);
                bands[i].gain = clamp(y_to_db(y, gh), -15.0, 15.0);
                selected_band = i;
                mgraphics.redraw();
                outlet(0, "select_band", i);
                outlet(0, "band_active", i, 1);
                outlet(0, "band_fg", i, bands[i].freq, bands[i].gain);
                return;
            }
        }
    }
}

// --- Dynamic Theme Color Receiver (from `live.colors` in patcher) ---
function set_theme_color(token, r, g, b, a) {
    if (THEME[token] !== undefined) {
        THEME[token] = [r, g, b, (a !== undefined) ? a : 1.0];
        mgraphics.redraw();
    }
}

// --- Bind Native C++ FFT `buffer~` Instance Name ---
function set_rta_buf(buf_name) {
    if (typeof Buffer !== "undefined") {
        rta_buf = new Buffer(buf_name);
    }
}

function set_rta_on(v) {
    rta_on = v ? 1 : 0;
    mgraphics.redraw();
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

function set_gr() {
    var args = arrayfromargs(arguments);
    var changed = false;
    for (var i = 0; i < NUM_BANDS && i < args.length; i++) {
        if (Math.abs(bands[i].gr_db - args[i]) > 0.03) {
            bands[i].gr_db = args[i];
            changed = true;
        }
    }
    // Always sample the 2048 FFT bins at 30fps, including while dragging band dots!
    if (update_rta_from_buffer()) {
        changed = true;
    }
    if (changed) {
        mgraphics.redraw();
    }
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

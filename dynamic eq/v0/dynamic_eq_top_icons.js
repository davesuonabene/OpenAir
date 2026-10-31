// dynamic_eq_top_icons.js
// Exact Ableton EQ Eight top-right icon buttons (44x13 total):
// Left button (20x13, x=0..20): Headphone Solo Band toggle (wide crisp vector headphones)
// 4px gap (x=20..24): exact device body background #342f3f
// Right button (20x13, x=24..44): RTA Analyzer toggle (vector 6-bar spectrum icon)

inlets = 1;
outlets = 1; // Outlet 0 -> dynamic_eq_lom.js ("ui_solo", "ui_rta_on")

mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

var solo_on = 0;
var rta_on = 1;

function paint() {
    var w = box.rect[2] - box.rect[0];
    var h = box.rect[3] - box.rect[1];

    // Fill entire canvas with exact Ableton device body background: RGB(52, 47, 63) = #342f3f
    // so the 4px gap between the two buttons blends seamlessly with the Right Strip!
    mgraphics.set_source_rgba(0.204, 0.184, 0.247, 1.0);
    mgraphics.rectangle(0, 0, w, h);
    mgraphics.fill();

    var bw = 20;
    var gap = 4;
    var rx = bw + gap; // 24

    // --- Left Button: Headphone Solo (x=0..20, y=0..h) ---
    if (solo_on) {
        // Active EQ Eight cyan or pink highlight
        mgraphics.set_source_rgba(0.278, 0.886, 0.957, 1.0);
    } else {
        // Exact EQ Eight dark button background: RGB(27, 24, 33) = #1b1821
        mgraphics.set_source_rgba(0.106, 0.094, 0.129, 1.0);
    }
    mgraphics.rectangle(0.5, 0.5, bw - 1, h - 1);
    mgraphics.fill();

    // 1px dark border: RGB(17, 16, 22) = #111016
    mgraphics.set_source_rgba(0.067, 0.063, 0.086, 1.0);
    mgraphics.set_line_width(1.0);
    mgraphics.rectangle(0.5, 0.5, bw - 1, h - 1);
    mgraphics.stroke();

    // Draw wide crisp headphones centered in left button (cx = 10, cy = 6.5)
    var hcx = 10.0;
    var hcy = 6.5;
    if (solo_on) {
        mgraphics.set_source_rgba(0.08, 0.08, 0.10, 1.0);
    } else {
        mgraphics.set_source_rgba(0.68, 0.66, 0.71, 1.0);
    }
    mgraphics.set_line_width(1.35);
    // Wide arch
    mgraphics.arc(hcx, hcy + 0.5, 3.8, Math.PI * 1.02, Math.PI * 1.98);
    mgraphics.stroke();
    // Left earcup
    mgraphics.rectangle(hcx - 4.5, hcy + 0.2, 2.0, 3.2);
    mgraphics.fill();
    // Right earcup
    mgraphics.rectangle(hcx + 2.5, hcy + 0.2, 2.0, 3.2);
    mgraphics.fill();

    // --- Right Button: RTA Spectrum Icon (x=24..44, y=0..h) ---
    if (rta_on) {
        // Exact EQ Eight pink: RGB(255, 145, 195) = #ff91c3
        mgraphics.set_source_rgba(1.0, 0.569, 0.765, 1.0);
    } else {
        mgraphics.set_source_rgba(0.106, 0.094, 0.129, 1.0);
    }
    mgraphics.rectangle(rx + 0.5, 0.5, bw - 1, h - 1);
    mgraphics.fill();

    // 1px dark border: RGB(17, 16, 22) = #111016
    mgraphics.set_source_rgba(0.067, 0.063, 0.086, 1.0);
    mgraphics.set_line_width(1.0);
    mgraphics.rectangle(rx + 0.5, 0.5, bw - 1, h - 1);
    mgraphics.stroke();

    // Draw 6-bar RTA spectrum icon inside right button
    if (rta_on) {
        mgraphics.set_source_rgba(0.14, 0.10, 0.14, 1.0);
    } else {
        mgraphics.set_source_rgba(0.68, 0.66, 0.71, 1.0);
    }
    var bar_x0 = rx + 4.0;
    var base_y = h - 2.5;
    var heights = [3.5, 6.5, 4.5, 8.0, 5.5, 2.5];
    for (var i = 0; i < 6; i++) {
        var bx = bar_x0 + i * 2.1;
        var bh = heights[i];
        mgraphics.rectangle(bx, base_y - bh, 1.3, bh);
        mgraphics.fill();
    }
}

function onclick(x, y) {
    if (x <= 21) {
        solo_on = solo_on ? 0 : 1;
        outlet(0, "ui_solo", solo_on);
        mgraphics.redraw();
    } else if (x >= 23) {
        rta_on = rta_on ? 0 : 1;
        outlet(0, "ui_rta_on", rta_on);
        mgraphics.redraw();
    }
}

function set_solo(v) {
    solo_on = v ? 1 : 0;
    mgraphics.redraw();
}

function set_rta(v) {
    rta_on = v ? 1 : 0;
    mgraphics.redraw();
}

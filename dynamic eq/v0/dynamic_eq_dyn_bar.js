// dynamic_eq_dyn_bar.js
// Native Ableton Live style vertical Dynamic Strip (right of EQ Eight core, 22x169)
// Mirrors the Sidechain vertical strip on the left:
// - Left 2px #474154 frame divider separating EQ Eight Right Strip from Dynamic strip
// - Top: circular (▶) expand/collapse toggle for Per-Band Dynamic Drawer
// - Below: circular (🎧) Band Solo toggle
// - Bottom: vertical rotated "Dynamic" label + status indicator dot

inlets = 1;
outlets = 1; // Outlet 0 -> dynamic_eq_lom.js ("set_dyn_panel", "ui_solo")

mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

var dyn_open = 0;
var solo_on = 0;
var dyn_active = 0; // 1 if selected band has Dyn ON

function paint() {
    var w = box.rect[2] - box.rect[0];
    var h = box.rect[3] - box.rect[1];

    // 1. Exact Ableton device body background: RGB(52, 47, 63) = #342f3f
    mgraphics.set_source_rgba(0.204, 0.184, 0.247, 1.0);
    mgraphics.rectangle(0, 0, w, h);
    mgraphics.fill();

    // Left 2px frame divider separating EQ Eight Right Strip from Dynamic Strip: #474154
    mgraphics.set_source_rgba(0.278, 0.255, 0.329, 1.0);
    mgraphics.rectangle(0, 0, 2, h);
    mgraphics.fill();

    // Bottom 2px frame border: #474154
    mgraphics.set_source_rgba(0.278, 0.255, 0.329, 1.0);
    mgraphics.rectangle(0, h - 2, w, 2);
    mgraphics.fill();

    // Right vertical divider:
    // When open, 1px dark #0e0e13 inner divider separating Dynamic strip from Dynamic drawer.
    // When closed, 2px #474154 right edge border.
    if (dyn_open) {
        mgraphics.set_source_rgba(0.055, 0.055, 0.075, 1.0);
        mgraphics.rectangle(w - 1, 3, 1, h - 8);
        mgraphics.fill();
    } else {
        mgraphics.set_source_rgba(0.278, 0.255, 0.329, 1.0);
        mgraphics.rectangle(w - 2, 0, 2, h);
        mgraphics.fill();
    }

    var cx = 11.5;

    // 2. Top Circular Expand/Collapse Button (▶) at y = 5..21 (center 13, radius 7.5)
    var cy1 = 13.0;
    var r1 = 7.5;
    mgraphics.set_source_rgba(0.106, 0.094, 0.129, 1.0);
    mgraphics.arc(cx, cy1, r1, 0, Math.PI * 2);
    mgraphics.fill();

    // Outer ring (bright #d3cdd7 when open, subtle #8d8892 when closed)
    if (dyn_open) {
        mgraphics.set_source_rgba(0.827, 0.804, 0.843, 1.0);
        mgraphics.set_line_width(1.3);
    } else {
        mgraphics.set_source_rgba(0.553, 0.533, 0.573, 1.0);
        mgraphics.set_line_width(1.1);
    }
    mgraphics.arc(cx, cy1, r1 - 0.6, 0, Math.PI * 2);
    mgraphics.stroke();

    // Play/Expand Triangle inside circle
    if (dyn_open) {
        mgraphics.set_source_rgba(0.90, 0.88, 0.92, 1.0);
    } else {
        mgraphics.set_source_rgba(0.78, 0.76, 0.80, 1.0);
    }
    mgraphics.move_to(cx - 2.2, cy1 - 3.6);
    mgraphics.line_to(cx + 3.6, cy1);
    mgraphics.line_to(cx - 2.2, cy1 + 3.6);
    mgraphics.close_path();
    mgraphics.fill();

    // 3. Second Circular Headphone Button (🎧 Band Solo) at y = 24..38 (center 31, radius 7.0)
    var cy2 = 31.0;
    var r2 = 7.0;
    if (solo_on) {
        mgraphics.set_source_rgba(0.278, 0.886, 0.957, 1.0);
        mgraphics.arc(cx, cy2, r2, 0, Math.PI * 2);
        mgraphics.fill();
        mgraphics.set_source_rgba(0.08, 0.08, 0.11, 1.0);
    } else {
        mgraphics.set_source_rgba(0.106, 0.094, 0.129, 1.0);
        mgraphics.arc(cx, cy2, r2, 0, Math.PI * 2);
        mgraphics.fill();
        mgraphics.set_source_rgba(0.75, 0.73, 0.78, 1.0);
    }

    // Wide crisp headphones inside circle
    mgraphics.set_line_width(1.35);
    mgraphics.arc(cx, cy2 + 0.5, 4.1, Math.PI * 1.05, Math.PI * 1.95);
    mgraphics.stroke();
    mgraphics.rectangle(cx - 4.7, cy2 + 0.2, 2.0, 3.3);
    mgraphics.fill();
    mgraphics.rectangle(cx + 2.7, cy2 + 0.2, 2.0, 3.3);
    mgraphics.fill();

    // 4. Vertical Rotated "Dynamic" text (90 deg CCW)
    mgraphics.save();
    mgraphics.translate(15.0, 143);
    mgraphics.rotate(-Math.PI / 2);
    mgraphics.select_font_face("Ableton Sans Medium", "normal", "normal");
    mgraphics.set_font_size(10.0);
    mgraphics.set_source_rgba(0.827, 0.804, 0.843, 1.0);
    mgraphics.move_to(0, 0);
    mgraphics.show_text("Dynamic");
    mgraphics.restore();

    // 5. Status dot at bottom (center cx, 155)
    var cy3 = 155.0;
    if (dyn_active) {
        mgraphics.set_source_rgba(0.278, 0.886, 0.957, 1.0);
    } else {
        mgraphics.set_source_rgba(0.106, 0.094, 0.129, 1.0);
    }
    mgraphics.arc(cx, cy3, 3.5, 0, Math.PI * 2);
    mgraphics.fill();
}

function onclick(x, y) {
    if (y >= 2 && y <= 22) {
        dyn_open = dyn_open ? 0 : 1;
        outlet(0, "set_dyn_panel", dyn_open);
        mgraphics.redraw();
    } else if (y >= 23 && y <= 41) {
        solo_on = solo_on ? 0 : 1;
        outlet(0, "ui_solo", solo_on);
        mgraphics.redraw();
    } else if (y > 41) {
        dyn_open = dyn_open ? 0 : 1;
        outlet(0, "set_dyn_panel", dyn_open);
        mgraphics.redraw();
    }
}

function set_open(v) {
    dyn_open = v ? 1 : 0;
    mgraphics.redraw();
}

function set_solo(v) {
    solo_on = v ? 1 : 0;
    mgraphics.redraw();
}

function set_active(v) {
    dyn_active = v ? 1 : 0;
    mgraphics.redraw();
}


// dynamic_eq_sc_bar.js
// Native Ableton Live style vertical Sidechain Strip (left edge of device, 22x169)
// Top: circular (▶) expand/collapse toggle
// Below: circular (🎧) Sidechain Listen toggle
// Bottom-left: vertical rotated "Sidechain" label + status indicator dot

inlets = 1;
outlets = 1; // Outlet 0 -> dynamic_eq_lom.js ("set_sc_panel", "ui_sc_listen")

mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

var sc_open = 0;
var sc_listen = 0;
var sc_active = 0; // 1 if either Ext. A or Ext. B is enabled

function paint() {
    var w = box.rect[2] - box.rect[0];
    var h = box.rect[3] - box.rect[1];

    // 1. Exact Ableton device body background: RGB(52, 47, 63) = #342f3f
    mgraphics.set_source_rgba(0.204, 0.184, 0.247, 1.0);
    mgraphics.rectangle(0, 0, w, h);
    mgraphics.fill();

    // Bottom 2px frame border: RGB(71, 65, 84) = #474154
    mgraphics.set_source_rgba(0.278, 0.255, 0.329, 1.0);
    mgraphics.rectangle(0, h - 2, w, 2);
    mgraphics.fill();

    // Right vertical divider:
    // When closed, 2px #474154 frame divider separating SC strip from Left Strip.
    // When open, 1px dark #0e0e13 inner divider separating SC strip from Ext. A column.
    if (sc_open) {
        mgraphics.set_source_rgba(0.055, 0.055, 0.075, 1.0);
        mgraphics.rectangle(w - 1, 3, 1, h - 8);
        mgraphics.fill();
    } else {
        mgraphics.set_source_rgba(0.278, 0.255, 0.329, 1.0);
        mgraphics.rectangle(w - 2, 0, 2, h);
        mgraphics.fill();
    }

    var cx = 10.0;

    // 2. Top Circular Expand/Collapse Button (▶) at y = 5..21 (center 13, radius 7.5)
    var cy1 = 13.0;
    var r1 = 7.5;
    // Inner dark circle: RGB(27, 24, 33) = #1b1821
    mgraphics.set_source_rgba(0.106, 0.094, 0.129, 1.0);
    mgraphics.arc(cx, cy1, r1, 0, Math.PI * 2);
    mgraphics.fill();

    // Outer ring (bright #d3cdd7 when open, subtle #8d8892 when closed)
    if (sc_open) {
        mgraphics.set_source_rgba(0.827, 0.804, 0.843, 1.0);
        mgraphics.set_line_width(1.3);
    } else {
        mgraphics.set_source_rgba(0.553, 0.533, 0.573, 1.0);
        mgraphics.set_line_width(1.1);
    }
    mgraphics.arc(cx, cy1, r1 - 0.6, 0, Math.PI * 2);
    mgraphics.stroke();

    // Play/Expand Triangle inside circle (rotates 90 deg clockwise ▶ -> ▼ when open)
    if (sc_open) {
        mgraphics.set_source_rgba(0.92, 0.90, 0.94, 1.0);
    } else {
        mgraphics.set_source_rgba(0.78, 0.76, 0.80, 1.0);
    }
    mgraphics.save();
    mgraphics.translate(cx, cy1);
    if (sc_open) {
        mgraphics.rotate(Math.PI * 0.5);
    }
    mgraphics.move_to(-2.2, -3.6);
    mgraphics.line_to(3.6, 0.0);
    mgraphics.line_to(-2.2, 3.6);
    mgraphics.close_path();
    mgraphics.fill();
    mgraphics.restore();

    // 3. Second Circular Headphone Button (🎧 Sidechain Listen) at y = 24..38 (center 31, radius 7.0)
    var cy2 = 31.0;
    var r2 = 7.0;
    if (sc_listen) {
        // Active cyan highlight
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

    // Draw wide crisp headphones inside circle (cx, cy2)
    mgraphics.set_line_width(1.35);
    // Headband arch
    mgraphics.arc(cx, cy2 + 0.5, 4.1, Math.PI * 1.05, Math.PI * 1.95);
    mgraphics.stroke();
    // Left earcup
    mgraphics.rectangle(cx - 4.7, cy2 + 0.2, 2.0, 3.3);
    mgraphics.fill();
    // Right earcup
    mgraphics.rectangle(cx + 2.7, cy2 + 0.2, 2.0, 3.3);
    mgraphics.fill();

    // 4. Vertical Rotated "Sidechain" text (90 deg CCW)
    mgraphics.save();
    mgraphics.translate(13.5, 143);
    mgraphics.rotate(-Math.PI / 2);
    mgraphics.select_font_face("Ableton Sans Medium", "normal", "normal");
    mgraphics.set_font_size(10.0);
    mgraphics.set_source_rgba(0.827, 0.804, 0.843, 1.0);
    mgraphics.move_to(0, 0);
    mgraphics.show_text("Sidechain");
    mgraphics.restore();

    // 5. Status dot at bottom (center 10, 155)
    // In Ableton's Sidechain strip, this dot is dark recessed #1b1821 when inactive, lit when SC is active
    var cy3 = 155.0;
    if (sc_active) {
        mgraphics.set_source_rgba(0.278, 0.886, 0.957, 1.0);
    } else {
        mgraphics.set_source_rgba(0.106, 0.094, 0.129, 1.0);
    }
    mgraphics.arc(cx, cy3, 3.5, 0, Math.PI * 2);
    mgraphics.fill();
}

function onclick(x, y) {
    if (y >= 2 && y <= 22) {
        sc_open = sc_open ? 0 : 1;
        outlet(0, "set_sc_panel", sc_open);
        mgraphics.redraw();
    } else if (y >= 23 && y <= 41) {
        sc_listen = sc_listen ? 0 : 1;
        outlet(0, "ui_sc_listen", sc_listen);
        mgraphics.redraw();
    } else if (y > 41) {
        sc_open = sc_open ? 0 : 1;
        outlet(0, "set_sc_panel", sc_open);
        mgraphics.redraw();
    }
}

function set_open(v) {
    sc_open = v ? 1 : 0;
    mgraphics.redraw();
}

function set_listen(v) {
    sc_listen = v ? 1 : 0;
    mgraphics.redraw();
}

function set_active(v) {
    sc_active = v ? 1 : 0;
    mgraphics.redraw();
}

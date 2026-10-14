"""
Automated screenshot generator for OpenAir Max for Live devices.
Captures pixel-perfect device presentation views directly from Cycling '74 Max 9
without Max window frames, menu bars, or toolbars.
Outputs Retina (2x) resolution PNGs directly into media/v0.0.1/
"""

import subprocess
import time
import os
import glob
import json
import struct
import sys
import ctypes
from ctypes import wintypes
from PIL import Image

sys.path.insert(0, '.')
from tools.inspector import parse_amxd_patcher

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

PW_CLIENTONLY = 1
PW_RENDERFULLCONTENT = 2

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3)
    ]

def capture_window_client(hwnd):
    cr = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(cr))
    w, h = cr.right, cr.bottom
    if w <= 0 or h <= 0:
        return None

    hwnd_dc = user32.GetDC(hwnd)
    mfc_dc = gdi32.CreateCompatibleDC(hwnd_dc)
    bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, w, h)
    gdi32.SelectObject(mfc_dc, bitmap)

    user32.PrintWindow(hwnd, mfc_dc, PW_RENDERFULLCONTENT | PW_CLIENTONLY)

    bmpinfo = BITMAPINFO()
    bmpinfo.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmpinfo.bmiHeader.biWidth = w
    bmpinfo.bmiHeader.biHeight = -h # top-down
    bmpinfo.bmiHeader.biPlanes = 1
    bmpinfo.bmiHeader.biBitCount = 32
    bmpinfo.bmiHeader.biCompression = 0

    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mfc_dc, bitmap, 0, h, buf, ctypes.byref(bmpinfo), 0)

    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(mfc_dc)
    user32.ReleaseDC(hwnd, hwnd_dc)

    return Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1)

DEVICE_CONFIGS = {
    'OA_totape8.amxd': (192, 179),
    'OA_galactic.amxd': (142, 179),
    'OA_Air4.amxd': (133, 179),
    'OA_BassKit.amxd': (133, 179),
    'OA_clipsoftly.amxd': (133, 179),
    'OA_console0bus.amxd': (133, 179),
    'OA_console0channel.amxd': (133, 179),
    'OA_distance3.amxd': (133, 179),
    'OA_purestconsolebus.amxd': (133, 179),
    'OA_purestconsolechannel2.amxd': (133, 179),
}

def render_plugin_screenshot(dev_name, out_dir="media/v0.0.1"):
    amxd_path = os.path.join("m4lplugins", dev_name)
    if not os.path.isfile(amxd_path):
        print(f"File not found: {amxd_path}")
        return False

    w, h = DEVICE_CONFIGS.get(dev_name, (133, 179))
    base_name = os.path.splitext(dev_name)[0]
    out_png = os.path.join(out_dir, f"{base_name}.png")

    patcher = parse_amxd_patcher(amxd_path)
    if not patcher:
        print(f"Failed to parse {amxd_path}")
        return False

    p = json.loads(json.dumps(patcher))
    p['toolbarvisible'] = 0
    p['lefttoolbarpinned'] = 0
    p['righttoolbarpinned'] = 0
    p['toptoolbarpinned'] = 0
    p['bottomtoolbarpinned'] = 0
    p['devicewidth'] = float(w)
    p['rect'] = [100.0, 100.0, float(w), float(h)]
    p['openrect'] = [0.0, 0.0, float(w), float(h)]

    json_bytes = json.dumps({'patcher': p}, indent=4).encode('utf-8')
    ampf_hdr = (
        b'ampf\x04\x00\x00\x00aaaameta\x04\x00\x00\x00\x00\x00\x00\x00ptch'
        + struct.pack('<I', len(json_bytes))
    )
    temp_amxd = os.path.abspath(f'tools/_render_{dev_name}')
    with open(temp_amxd, 'wb') as f:
        f.write(ampf_hdr + json_bytes)

    # Ensure no running Max process conflicts
    subprocess.run(['taskkill', '/F', '/IM', 'Max.exe'], capture_output=True)
    time.sleep(0.5)

    max_exe = "C:/Program Files/Cycling '74/Max 9/Max.exe"
    proc = subprocess.Popen([max_exe, temp_amxd])

    target_hwnd = None
    for _ in range(35):
        time.sleep(0.15)
        def enum_cb(hwnd, lParam):
            nonlocal target_hwnd
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == proc.pid:
                buff = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(hwnd, buff, 512)
                t = buff.value.lower()
                if 'presentation' in t or '_render_' in t or base_name.lower() in t:
                    cr = wintypes.RECT()
                    user32.GetClientRect(hwnd, ctypes.byref(cr))
                    if cr.right > 50 and cr.bottom > 50:
                        target_hwnd = hwnd
            return True
        user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(enum_cb), 0)
        if target_hwnd:
            break

    success = False
    if target_hwnd:
        # Allow GUI elements to finish initial paint
        time.sleep(0.5)
        img = capture_window_client(target_hwnd)
        if img:
            iw, ih = img.size
            crop_w = min(iw, w)
            crop_h = min(ih, h)
            cropped = img.crop((0, 0, crop_w, crop_h))

            # Upscale 2x for crisp Retina display on Web / GitHub
            retina_img = cropped.resize((crop_w * 2, crop_h * 2), Image.Resampling.LANCZOS)
            os.makedirs(out_dir, exist_ok=True)
            retina_img.save(out_png)
            print(f"Successfully generated {out_png} ({retina_img.size[0]}x{retina_img.size[1]})")
            success = True
    else:
        print(f"Failed to find presentation window for {dev_name}")

    proc.terminate()
    try:
        proc.wait(timeout=2)
    except:
        proc.kill()

    try:
        os.remove(temp_amxd)
    except:
        pass

    return success

def main():
    print("=" * 65)
    print("OpenAir Toolchain: Rendering High-Res Device Screenshots")
    print("=" * 65)

    plugins = sorted(list(DEVICE_CONFIGS.keys()))
    success_count = 0
    for p in plugins:
        if render_plugin_screenshot(p):
            success_count += 1
        time.sleep(0.5)

    # Final cleanup
    subprocess.run(['taskkill', '/F', '/IM', 'Max.exe'], capture_output=True)

    print(f"\nRender complete: {success_count}/{len(plugins)} screenshots generated successfully.")

if __name__ == '__main__':
    main()

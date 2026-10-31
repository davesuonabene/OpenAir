# OA_Delta — Research, Concepts & Architectural Scratchpad

*macchinette / OpenAir Project*  
*Location: `delta/ideas.md`*

---

## 1. What is OA_Delta?

**OA_Delta** is an advanced Max for Live (M4L) comparative monitoring and diagnostic device. It allows producers and mixing engineers to compare the **Before** (unprocessed / dry) and **After** (processed / wet) audio signals across any plugin chain or mastering chain in Ableton Live, using **real-time phase inversion**, **difference (delta) listening**, **precision delay alignment**, and **multi-mode visual analyzers**.

### The Core Philosophy
In mixing and mastering, psychoacoustics frequently play tricks on our ears:
1. **The Loudness Trap**: A plugin that makes a signal 0.5 dB louder almost always sounds "better" or "richer" until level-matched.
2. **The Masking Problem**: It is difficult to hear what a subtle analog saturator, console emulation, or tape machine actually adds to the harmonic structure without isolating the change.
3. **The Carve/Cut Audit**: When using dynamic EQs, de-essers, or multiband limiters, you need to hear exactly what is being carved away without the remaining material distracting you.

OA_Delta solves all three problems by taking two stereo streams:
- **Stream A ("Before" / Pre-FX)**: Tapped before the processing chain.
- **Stream B ("After" / Post-FX)**: Tapped after the processing chain (where OA_Delta sits).

Using sample-accurate polarity inversion:
$$\text{Delta} = \text{After} - \text{Before} = \text{Wet} + (-\text{Dry})$$

When $\text{Wet}$ and $\text{Dry}$ are identical, the result is complete silence ($-\infty\text{ dB}$, null). When processing is applied, **Delta audition plays ONLY the difference introduced by the plugins**!

---

## 2. Signal Topologies in Ableton Live

How does OA_Delta capture both "Before" and "After" in Ableton Live?

### Topology Option 1: Native Live Routing / Sidechain (Single Device)
- **Object**: `plugin~ 1 2 3 4` + `live.routing`
- **Signal Flow**:
  - Inlets 1 & 2: Main audio input from the track (sitting Post-FX).
  - Inlets 3 & 4: Auxiliary/Sidechain input from `live.routing` set to **Pre FX** on the same track.
- **Advantages**:
  - Single device footprint on the track.
  - Takes advantage of Live's native routing engine (Live 10, 11, 12).
  - Can tap from *any* track in the project or external inputs.
- **User Experience**:
  - Insert `OA_Delta` at the end of the chain.
  - Select "Pre FX" on the device's routing dropdown (or Live's sidechain chooser).
  - Immediately compare and analyze.

### Topology Option 2: 2-Device Modular Pair (Sender + Receiver)
- **Device A (`OA_Delta_Send.amxd`)**: Drops at the very beginning of the track/chain.
- **Device B (`OA_Delta_Monitor.amxd`)**: Drops at the end of the chain.
- **Routing**: In Live, Device A routes out or Device B routes in via Live's routing matrix.

### Recommended Direction:
Primary device as **Single-Device with Live Routing / Sidechain** (Option 1), with clean routing selectors right on the front panel!

---

## 3. Audition & Monitoring Modes

1. **AFTER (Post-FX / Wet)**:
   - Normal track playback (the processed sound).
2. **BEFORE (Pre-FX / Dry)**:
   - Instant audition of the raw original track.
3. **DELTA (Difference / Added Material)**:
   - $\text{After} - \text{Before}$
   - Audition pure saturation harmonics, compression artifacts, EQ boosts, reverb tails.
4. **INVERSE DELTA (Subtracted Material)**:
   - $\text{Before} - \text{After}$
   - Audition what was cut or removed (useful for de-essers, transient shapers, peak limiters).
5. **A/B COMPARISON TOGGLE**:
   - One-click or automated alternating between Before and After for direct comparative listening.
6. **DELTA GAIN BOOST (+0 dB to +36 dB)**:
   - Difference signals are often very low in level (-24 dB to -40 dB).
   - A dedicated clean boost dial lets the user audition subtle analog console or tape nuances clearly without touching their master fader.
7. **SAMPLE DELAY ALIGNMENT (0 to 4096 samples)**:
   - Third-party VSTs or oversampled plugins may introduce slight latency or phase shift.
   - Precise sub-millisecond / sample-level delay trimmer (`delay~`) with `+1`, `-1`, `+10`, `-10` sample nudge buttons ensures a perfect phase null.

---

## 4. Visual Analyzers & Display Modes

The visualizer section will feature 3 switchable screens or a split display:

1. **Spectral Analyzer (`spectroscope~`)**:
   - Real-time FFT display with logarithmic frequency curve (20 Hz - 20 kHz).
   - Display modes:
     - **Before Curve**: Muted lilac (`#9e94ab`)
     - **After Curve**: Crisp light lavender (`#d3cdd7`)
     - **Delta Curve**: Signature neon pink (`#ff91c3`) showing the exact frequency response changes!
2. **Stereo Phase Scope / Goniometer (`phasescope~`)**:
   - Real-time Lissajous XY pattern showing stereo width and mono compatibility.
   - Numerical Phase Correlation meter (-1.00 to +1.00):
     - $+1.0$: Fully mono in-phase.
     - $0.0$: Wide stereo / uncorrelated.
     - $-1.0$: Fully out-of-phase (potential cancellation).
3. **Oscilloscope / Waveform Scope (`live.scope~`)**:
   - Dual-channel waveform comparison showing transient shape changes and peak shaving.
4. **Precision Level Meters (`live.meter~`)**:
   - Dedicated peak/RMS meters for Before, After, and Delta.

---

## 5. Visual Styling & Design System (Matching OpenAir / macchinette)

Strict adherence to the established OpenAir aesthetic seen in `media/screenshots/` and `m4lplugins/`:

- **Color Palette**:
  - Canvas / Panel Background: `[0.0784, 0.0745, 0.102, 1.0]` (`#14131a` — deep obsidian violet)
  - Bottom Bar Strip: `[0.0784, 0.0745, 0.102, 1.0]`
  - Body Text & Outlines: `[0.8275, 0.8039, 0.8431, 1.0]` (`#d3cdd7` — soft lilac grey)
  - Primary Accent & Dials: `[1.0, 0.5686, 0.7647, 1.0]` (`#ff91c3` — macchinette hot pink)
  - Inactive / Track Arcs: `[0.6196, 0.5804, 0.6706, 1.0]` (`#9e94ab` — muted slate)
- **Typography**:
  - Title: `delta ~` (20-22pt, lowercase, clean sans)
  - Subtitle / Mode: Small uppercase badge (e.g. `MONITOR`, `DELTA`)
  - Bottom strip: `Pre`, `Delta`, `Post` with pink dB readouts.
- **Physical Dimensions**:
  - Height: `169.0` px (Standard Ableton Live device rack height)
  - Width: `246.0` px (Dual-wide layout: Left side = Routing & Controls, Right side = Visual Analyzer & Scope)


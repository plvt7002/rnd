"""
╔══════════════════════════════════════════════════════════════╗
║       AIR DEFENCE SYSTEM — Combined Dashboard + Controller   ║
║       Arduino Uno | HC-SR04 | 3x Servo | L298N | 4WD        ║
╚══════════════════════════════════════════════════════════════╝

HOW TO RUN:
  1. Find your port:  ls /dev/tty.*
  2. Set PORT below
  3. Run: python3 air_defence_combined.py
  4. Type commands in the terminal while radar shows in window

COMMANDS:
  CAR    : W / A / S / D / X
  TURRET : PAN:0-180   TILT:45-135
  RADAR  : SCAN
  SPEED  : SPEED:0-255
  QUIT   : Q
"""

import serial
import matplotlib
matplotlib.use('TkAgg')  # works best on Mac for input + plot together
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import numpy as np
import threading
import time
import sys
import queue

# ══════════════════════════════════════════════
#  CONFIG — change PORT to match yours
# ══════════════════════════════════════════════
PORT      = '/dev/tty.usbmodem14101'
BAUD      = 9600
THREAT_CM = 100   # threat detection threshold in cm

# ══════════════════════════════════════════════
#  CONNECT
# ══════════════════════════════════════════════
try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)
    print(f"✅  Connected to Arduino on {PORT}")
except Exception as e:
    print(f"❌  Could not connect: {e}")
    print("    Run:  ls /dev/tty.*   and update PORT in this file.")
    sys.exit(1)

# ══════════════════════════════════════════════
#  SHARED STATE
# ══════════════════════════════════════════════
state = {
    'angles':        [],
    'distances':     [],
    'threat_angles': [],
    'threat_dists':  [],
    'last_pan':      90,
    'last_tilt':     90,
    'last_dist':     999,
    'status':        'SCANNING',
    'threat_count':  0,
    'log':           [],        # command log lines shown on dashboard
}
log_lock   = threading.Lock()
cmd_queue  = queue.Queue()

# ══════════════════════════════════════════════
#  HELPER — add to on-screen log
# ══════════════════════════════════════════════
def log(msg):
    with log_lock:
        state['log'].append(msg)
        state['log'] = state['log'][-8:]   # keep last 8 lines

# ══════════════════════════════════════════════
#  THREAD 1 — read serial from Arduino
# ══════════════════════════════════════════════
def read_serial():
    while True:
        try:
            raw  = ser.readline()
            if not raw:
                continue
            line = raw.decode('utf-8', errors='ignore').strip()
            if not line:
                continue

            if line == "THREAT_DETECTED":
                state['status']       = 'THREAT DETECTED'
                state['threat_count'] += 1
                log("⚠️  THREAT DETECTED!")
                continue

            if line == "READY":
                log("✅  Arduino ready")
                continue

            if line.startswith("LOCK_ON"):
                log(f"🎯  {line}")
                continue

            if line.startswith("Moving") or line.startswith("Turning") or \
               line.startswith("STOPPED") or line.startswith("PAN") or \
               line.startswith("TILT") or line.startswith("Speed") or \
               line.startswith("Scan") or line.startswith("Unknown"):
                log(f"↩  {line}")
                continue

            # Main data format: pan,tilt,distance
            parts = line.split(',')
            if len(parts) == 3:
                try:
                    pan  = int(parts[0])
                    tilt = int(parts[1])
                    dist = int(parts[2])
                except ValueError:
                    continue

                state['last_pan']  = pan
                state['last_tilt'] = tilt
                state['last_dist'] = dist

                if dist > 0 and dist < THREAT_CM:
                    state['status'] = 'THREAT DETECTED'
                else:
                    state['status'] = 'SCANNING'

                rad = np.radians(pan)
                state['angles'].append(rad)
                state['distances'].append(min(dist if dist > 0 else 300, 300))

                if dist > 0 and dist < THREAT_CM:
                    state['threat_angles'].append(rad)
                    state['threat_dists'].append(dist)
                    state['threat_angles'] = state['threat_angles'][-20:]
                    state['threat_dists']  = state['threat_dists'][-20:]

                state['angles']    = state['angles'][-100:]
                state['distances'] = state['distances'][-100:]

        except Exception:
            pass

# ══════════════════════════════════════════════
#  THREAD 2 — keyboard input (runs in terminal)
# ══════════════════════════════════════════════
def keyboard_input():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║       AIR DEFENCE CONTROLLER TERMINAL        ║")
    print("╠══════════════════════════════════════════════╣")
    print("║  CAR      W / A / S / D / X (stop)          ║")
    print("║  TURRET   PAN:90   TILT:60                   ║")
    print("║  RADAR    SCAN                               ║")
    print("║  SPEED    SPEED:150  (0-255)                 ║")
    print("║  QUIT     Q                                  ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    cmd_descriptions = {
        'W': 'Forward', 'S': 'Backward',
        'A': 'Left',    'D': 'Right',
        'X': 'STOP',    'SCAN': 'Scanning...',
        'Q': 'Quit'
    }

    while True:
        try:
            raw = input(">> ").strip()
            if not raw:
                continue

            cmd = raw.upper()

            if cmd == 'Q':
                ser.write(b'X\n')
                log("🛑  Stopped & quit")
                print("Car stopped. Closing...")
                time.sleep(0.5)
                import os
                os._exit(0)

            ser.write((raw + '\n').encode())

            # Nice print
            desc = cmd_descriptions.get(cmd, raw)
            if cmd.startswith('PAN:'):
                desc = f"Turret pan → {cmd[4:]}°"
            elif cmd.startswith('TILT:'):
                desc = f"Missile tilt → {cmd[5:]}°"
            elif cmd.startswith('SPEED:'):
                desc = f"Speed → {cmd[6:]}"

            print(f"   ✈  Sent: {raw}  ({desc})")
            log(f"▶  {raw}  →  {desc}")

        except (KeyboardInterrupt, EOFError):
            ser.write(b'X\n')
            print("\nStopped.")
            import os
            os._exit(0)

# ══════════════════════════════════════════════
#  BUILD FIGURE
# ══════════════════════════════════════════════
fig = plt.figure(figsize=(15, 8), facecolor='#0d1117')
fig.canvas.manager.set_window_title('Air Defence System — Live Dashboard')

gs = gridspec.GridSpec(
    2, 3,
    figure=fig,
    width_ratios=[1.4, 1, 1],
    height_ratios=[1, 0.55],
    hspace=0.08,
    wspace=0.25
)

ax_radar = fig.add_subplot(gs[:, 0], polar=True)   # radar — full left column
ax_status = fig.add_subplot(gs[0, 1])               # status panel — top middle
ax_log    = fig.add_subplot(gs[1, 1])               # command log — bottom middle
ax_ctrl   = fig.add_subplot(gs[0, 2])               # controls reference — top right
ax_data   = fig.add_subplot(gs[1, 2])               # live data — bottom right

for ax in [ax_status, ax_log, ax_ctrl, ax_data]:
    ax.set_facecolor('#0d1117')
    ax.axis('off')
ax_radar.set_facecolor('#0d1117')

# ══════════════════════════════════════════════
#  ANIMATION UPDATE
# ══════════════════════════════════════════════
def update(frame):
    is_threat = state['status'] != 'SCANNING'
    sweep_color = '#ff4444' if is_threat else '#00ff88'

    # ── RADAR ──────────────────────────────────
    ax_radar.cla()
    ax_radar.set_facecolor('#0d1117')
    ax_radar.set_theta_zero_location('N')
    ax_radar.set_theta_direction(-1)
    ax_radar.set_thetamin(0)
    ax_radar.set_thetamax(180)
    ax_radar.set_ylim(0, 300)
    ax_radar.set_yticks([50, 100, 150, 200, 300])
    ax_radar.set_yticklabels(
        ['50cm', '100cm', '150cm', '200cm', '300cm'],
        color='#3d4f5c', fontsize=8
    )
    ax_radar.tick_params(colors='#3d4f5c')
    ax_radar.spines['polar'].set_color('#1e2d3d')
    ax_radar.grid(color='#1e2d3d', linewidth=0.6)

    # Threat zone ring
    theta_fill = np.linspace(0, np.pi, 100)
    ax_radar.fill_between(theta_fill, 0, THREAT_CM,
                           color='#ff4444', alpha=0.06)
    ax_radar.plot(theta_fill, [THREAT_CM]*100,
                  color='#ff4444', linewidth=0.8, alpha=0.4, linestyle='--')

    # Scan trail (fading dots)
    if len(state['angles']) > 1:
        n = len(state['angles'])
        alphas = np.linspace(0.05, 0.5, n)
        for i in range(n):
            ax_radar.scatter(state['angles'][i], state['distances'][i],
                             c=sweep_color, s=8, alpha=alphas[i])

    # Threat hits
    if state['threat_angles']:
        ax_radar.scatter(
            state['threat_angles'], state['threat_dists'],
            c='#ff4444', s=120, marker='*', zorder=5, alpha=0.9
        )

    # Live sweep line
    pan_rad = np.radians(state['last_pan'])
    ax_radar.plot([pan_rad, pan_rad], [0, 300],
                  color=sweep_color, linewidth=2.5, alpha=0.95)
    ax_radar.scatter([pan_rad], [state['last_dist'] if 0 < state['last_dist'] < 300 else 300],
                     c=sweep_color, s=40, zorder=6)

    ax_radar.set_title(
        f"RADAR SWEEP  —  Pan {state['last_pan']}°  |  {state['last_dist']} cm",
        color=sweep_color, fontsize=11, pad=14, fontweight='bold'
    )

    # ── STATUS PANEL ───────────────────────────
    ax_status.cla()
    ax_status.set_facecolor('#0d1117')
    ax_status.set_xlim(0, 10)
    ax_status.set_ylim(0, 10)
    ax_status.axis('off')

    ax_status.text(5, 9.5, 'AIR DEFENCE SYSTEM',
                   color='white', fontsize=13, ha='center',
                   fontweight='bold', va='center')

    # Status box
    sc = '#ff4444' if is_threat else '#00ff88'
    ax_status.add_patch(mpatches.FancyBboxPatch(
        (0.3, 7.8), 9.4, 1.4,
        boxstyle="round,pad=0.15",
        linewidth=1.5, edgecolor=sc, facecolor='#111820'
    ))
    ax_status.text(5, 8.52, state['status'],
                   color=sc, fontsize=15, ha='center',
                   fontweight='bold', va='center')

    metrics = [
        ('Distance',     f"{state['last_dist']} cm",     '#63b3ed'),
        ('Pan  (S1+S2)', f"{state['last_pan']}°",        '#63b3ed'),
        ('Tilt  (S3)',   f"{state['last_tilt']}°",        '#63b3ed'),
        ('Threats',      str(state['threat_count']),      '#ff4444'),
    ]
    for i, (lbl, val, col) in enumerate(metrics):
        y = 6.5 - i * 1.55
        ax_status.plot([0.5, 9.5], [y + 0.8, y + 0.8],
                       color='#1e2d3d', linewidth=0.5)
        ax_status.text(0.6, y + 0.3, lbl,
                       color='#4a5568', fontsize=10, va='center')
        ax_status.text(9.4, y + 0.3, val,
                       color=col, fontsize=12, ha='right',
                       fontweight='bold', va='center')

    # Connection dot
    ax_status.add_patch(plt.Circle((0.7, 0.5), 0.2, color='#00ff88'))
    ax_status.text(1.1, 0.5, f'USB  {PORT}',
                   color='#4a5568', fontsize=8, va='center')

    # ── COMMAND LOG ────────────────────────────
    ax_log.cla()
    ax_log.set_facecolor('#111820')
    ax_log.set_xlim(0, 10)
    ax_log.set_ylim(0, 10)
    ax_log.axis('off')

    ax_log.text(0.4, 9.2, 'COMMAND LOG',
                color='#4a5568', fontsize=8, fontweight='bold')

    with log_lock:
        lines = list(state['log'])

    for i, line in enumerate(reversed(lines[-7:])):
        col = '#ff4444' if '⚠️' in line or 'THREAT' in line else \
              '#00ff88' if '✅' in line or '🎯' in line else '#718096'
        ax_log.text(0.4, 7.8 - i * 1.15, line,
                    color=col, fontsize=8.5, va='center')

    # ── CONTROLS REFERENCE ─────────────────────
    ax_ctrl.cla()
    ax_ctrl.set_facecolor('#0d1117')
    ax_ctrl.set_xlim(0, 10)
    ax_ctrl.set_ylim(0, 10)
    ax_ctrl.axis('off')

    ax_ctrl.text(5, 9.5, 'KEYBOARD COMMANDS',
                 color='white', fontsize=10, ha='center', fontweight='bold')

    cmds = [
        ('CAR',    'W / A / S / D',   'Move Forward/Left/Back/Right'),
        ('',       'X',               'Stop car'),
        ('TURRET', 'PAN:90',          'Rotate turret to angle'),
        ('',       'TILT:60',         'Tilt missile up/down'),
        ('RADAR',  'SCAN',            'Manual 180° sweep'),
        ('SPEED',  'SPEED:180',       'Set motor speed 0-255'),
        ('QUIT',   'Q',               'Stop car & exit'),
    ]
    for i, (cat, key, desc) in enumerate(cmds):
        y = 8.1 - i * 1.15
        if cat:
            ax_ctrl.text(0.3, y, cat,
                         color='#1ABC9C', fontsize=8,
                         fontweight='bold', va='center')
        ax_ctrl.add_patch(mpatches.FancyBboxPatch(
            (1.8, y - 0.25), 1.8, 0.52,
            boxstyle="round,pad=0.05",
            facecolor='#1e2d3d', edgecolor='#2d4a5e', linewidth=0.5
        ))
        ax_ctrl.text(2.7, y, key,
                     color='#00ff88', fontsize=8.5,
                     ha='center', fontfamily='monospace', va='center')
        ax_ctrl.text(3.8, y, desc,
                     color='#718096', fontsize=8, va='center')

    # ── LIVE DATA BAR ──────────────────────────
    ax_data.cla()
    ax_data.set_facecolor('#111820')
    ax_data.set_xlim(0, 10)
    ax_data.set_ylim(0, 10)
    ax_data.axis('off')

    ax_data.text(0.4, 9.2, 'LIVE DATA',
                 color='#4a5568', fontsize=8, fontweight='bold')

    # Pan bar
    pan_pct = state['last_pan'] / 180
    ax_data.add_patch(mpatches.FancyBboxPatch(
        (0.4, 7.5), 9.2, 0.7,
        boxstyle="round,pad=0.05", facecolor='#1e2d3d', edgecolor='none'))
    ax_data.add_patch(mpatches.FancyBboxPatch(
        (0.4, 7.5), max(0.2, 9.2 * pan_pct), 0.7,
        boxstyle="round,pad=0.05", facecolor='#1a5276', edgecolor='none'))
    ax_data.text(0.6, 7.86, f"Pan  {state['last_pan']}°",
                 color='#63b3ed', fontsize=9, va='center')

    # Tilt bar
    tilt_pct = (state['last_tilt'] - 45) / 90
    ax_data.add_patch(mpatches.FancyBboxPatch(
        (0.4, 6.3), 9.2, 0.7,
        boxstyle="round,pad=0.05", facecolor='#1e2d3d', edgecolor='none'))
    ax_data.add_patch(mpatches.FancyBboxPatch(
        (0.4, 6.3), max(0.2, 9.2 * tilt_pct), 0.7,
        boxstyle="round,pad=0.05", facecolor='#1a5276', edgecolor='none'))
    ax_data.text(0.6, 6.66, f"Tilt  {state['last_tilt']}°",
                 color='#63b3ed', fontsize=9, va='center')

    # Distance bar
    dist_capped = min(state['last_dist'], 300) if state['last_dist'] > 0 else 300
    dist_pct    = 1 - (dist_capped / 300)
    dist_col    = '#ff4444' if dist_capped < THREAT_CM else '#00ff88'
    ax_data.add_patch(mpatches.FancyBboxPatch(
        (0.4, 5.1), 9.2, 0.7,
        boxstyle="round,pad=0.05", facecolor='#1e2d3d', edgecolor='none'))
    ax_data.add_patch(mpatches.FancyBboxPatch(
        (0.4, 5.1), max(0.2, 9.2 * dist_pct), 0.7,
        boxstyle="round,pad=0.05", facecolor=dist_col, edgecolor='none'))
    ax_data.text(0.6, 5.46,
                 f"Dist  {state['last_dist']} cm  {'⚠ THREAT' if dist_capped < THREAT_CM else '✓ CLEAR'}",
                 color=dist_col, fontsize=9, va='center')

    # Tip
    ax_data.text(5, 0.6,
                 'Type commands in terminal below ↓',
                 color='#2d3748', fontsize=8, ha='center')

# ══════════════════════════════════════════════
#  START THREADS & RUN
# ══════════════════════════════════════════════
threading.Thread(target=read_serial,   daemon=True).start()
threading.Thread(target=keyboard_input, daemon=True).start()

log("System initialised — awaiting Arduino...")

ani = animation.FuncAnimation(
    fig, update, interval=100, cache_frame_data=False
)

plt.tight_layout(pad=1.5)
plt.show()

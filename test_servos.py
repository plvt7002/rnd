"""
╔══════════════════════════════════════════════════════╗
║   SERVO + AIR DEFENCE TEST — Radar Dashboard         ║
║   Tests Servo1(radar) + Servo2(missile pan)          ║
║   + Servo3(missile tilt) + HC-SR04 sensor            ║
╚══════════════════════════════════════════════════════╝
COMMANDS:
  PAN:0-180   TILT:45-135   SCAN   RESET   Q
"""

import serial
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import numpy as np
import threading
import time
import sys

# ── CONFIG ─────────────────────────────────────
PORT      = '/dev/tty.usbmodem14101'   # ← change this
BAUD      = 9600
THREAT_CM = 100
# ───────────────────────────────────────────────

try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)
    print(f"✅  Connected on {PORT}")
except Exception as e:
    print(f"❌  {e}\n    Run: ls /dev/tty.*")
    sys.exit(1)

# ── STATE ───────────────────────────────────────
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
    'log':           [],
}

def log(msg):
    state['log'].append(msg)
    state['log'] = state['log'][-8:]

# ══════════════════════════════════════════════
# ARDUINO CODE TO UPLOAD FOR THIS TEST:
# ──────────────────────────────────────────────
# #include <Servo.h>
# #define TRIG 8
# #define ECHO 10
# #define SERVO_PAN_PIN      3
# #define SERVO_MISSILE_PIN  9
# #define SERVO_TILT_PIN     11
# Servo panServo, missileServo, tiltServo;
# int panAngle=90, tiltAngle=90;
#
# long getDist() {
#   digitalWrite(TRIG,LOW); delayMicroseconds(2);
#   digitalWrite(TRIG,HIGH); delayMicroseconds(10); digitalWrite(TRIG,LOW);
#   long d = pulseIn(ECHO,HIGH,30000);
#   return d*0.034/2;
# }
# void setup() {
#   Serial.begin(9600);
#   panServo.attach(SERVO_PAN_PIN);
#   missileServo.attach(SERVO_MISSILE_PIN);
#   tiltServo.attach(SERVO_TILT_PIN);
#   panServo.write(90); missileServo.write(90); tiltServo.write(90);
#   pinMode(TRIG,OUTPUT); pinMode(ECHO,INPUT);
#   Serial.println("SERVO_READY");
# }
# void lockOn(int pan, int dist) {
#   missileServo.write(pan);
#   int tilt = dist<50?60:(dist<100?75:90);
#   tiltServo.write(tilt);
#   Serial.println("THREAT_DETECTED");
# }
# void loop() {
#   if (Serial.available()) {
#     String cmd = Serial.readStringUntil('\n'); cmd.trim(); cmd.toUpperCase();
#     if (cmd.startsWith("PAN:"))  { panAngle=constrain(cmd.substring(4).toInt(),0,180); panServo.write(panAngle); missileServo.write(panAngle); Serial.print("PAN:"); Serial.println(panAngle); }
#     else if (cmd.startsWith("TILT:")) { tiltAngle=constrain(cmd.substring(5).toInt(),45,135); tiltServo.write(tiltAngle); Serial.print("TILT:"); Serial.println(tiltAngle); }
#     else if (cmd=="RESET") { panAngle=90; tiltAngle=90; panServo.write(90); missileServo.write(90); tiltServo.write(90); Serial.println("RESET"); }
#     else if (cmd=="SCAN") {
#       for(int a=0;a<=180;a+=5){ panServo.write(a); missileServo.write(a); delay(40);
#         long d=getDist(); if(d==0)d=300;
#         Serial.print(a); Serial.print(",90,"); Serial.println(d);
#         if(d>0&&d<100){lockOn(a,d);delay(1500);}
#       }
#       for(int a=180;a>=0;a-=5){ panServo.write(a); missileServo.write(a); delay(40);
#         long d=getDist(); if(d==0)d=300;
#         Serial.print(a); Serial.print(",90,"); Serial.println(d);
#         if(d>0&&d<100){lockOn(a,d);delay(1500);}
#       }
#     }
#   }
#   // Continuous auto scan
#   for(int a=0;a<=180;a+=5){
#     panServo.write(a); missileServo.write(a); delay(40);
#     long d=getDist(); if(d==0)d=300;
#     Serial.print(a); Serial.print(","); Serial.print(tiltAngle); Serial.print(","); Serial.println(d);
#     if(d>0&&d<100){lockOn(a,d);delay(1500);}
#   }
#   for(int a=180;a>=0;a-=5){
#     panServo.write(a); missileServo.write(a); delay(40);
#     long d=getDist(); if(d==0)d=300;
#     Serial.print(a); Serial.print(","); Serial.print(tiltAngle); Serial.print(","); Serial.println(d);
#     if(d>0&&d<100){lockOn(a,d);delay(1500);}
#   }
# }
# ══════════════════════════════════════════════

# ── SERIAL READ THREAD ──────────────────────────
def read_serial():
    while True:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if not line:
                continue

            if line == "SERVO_READY":
                log("✅ Arduino ready — scanning")
                continue

            if line == "THREAT_DETECTED":
                state['status'] = 'THREAT DETECTED'
                state['threat_count'] += 1
                log("⚠️  THREAT DETECTED — missile locked!")
                continue

            if line.startswith("PAN:"):
                log(f"↩  Turret panned to {line[4:]}°")
                continue
            if line.startswith("TILT:"):
                log(f"↩  Missile tilt → {line[5:]}°")
                continue
            if line == "RESET":
                log("↩  All servos reset to 90°")
                continue

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
                state['status'] = 'THREAT DETECTED' \
                    if 0 < dist < THREAT_CM else 'SCANNING'

                rad = np.radians(pan)
                state['angles'].append(rad)
                state['distances'].append(min(dist if dist > 0 else 300, 300))

                if 0 < dist < THREAT_CM:
                    state['threat_angles'].append(rad)
                    state['threat_dists'].append(dist)
                    state['threat_angles'] = state['threat_angles'][-20:]
                    state['threat_dists']  = state['threat_dists'][-20:]

                state['angles']    = state['angles'][-100:]
                state['distances'] = state['distances'][-100:]
        except:
            pass

threading.Thread(target=read_serial, daemon=True).start()

# ── KEYBOARD INPUT THREAD ───────────────────────
def keyboard_input():
    print("\n╔══════════════════════════════════════╗")
    print("║   SERVO / AIR DEFENCE TEST           ║")
    print("╠══════════════════════════════════════╣")
    print("║  PAN:90      Rotate radar+missile    ║")
    print("║  TILT:60     Tilt missile up/down    ║")
    print("║  SCAN        Trigger manual sweep    ║")
    print("║  RESET       All servos back to 90°  ║")
    print("║  Q           Quit                    ║")
    print("╚══════════════════════════════════════╝\n")
    while True:
        try:
            raw = input(">> ").strip()
            if not raw:
                continue
            cmd = raw.upper()
            if cmd == 'Q':
                ser.write(b'RESET\n')
                time.sleep(0.3)
                import os; os._exit(0)
            ser.write((raw + '\n').encode())
            descs = {'SCAN':'Manual sweep triggered','RESET':'Servos centered'}
            desc = descs.get(cmd, raw)
            if cmd.startswith('PAN:'):
                desc = f"Turret → {cmd[4:]}°"
            elif cmd.startswith('TILT:'):
                desc = f"Missile tilt → {cmd[5:]}°"
            print(f"   ✈  Sent: {raw}  ({desc})")
            log(f"▶  {raw}  →  {desc}")
        except (KeyboardInterrupt, EOFError):
            ser.write(b'RESET\n')
            import os; os._exit(0)

threading.Thread(target=keyboard_input, daemon=True).start()

# ── FIGURE ──────────────────────────────────────
fig = plt.figure(figsize=(14, 7), facecolor='#0d1117')
fig.canvas.manager.set_window_title('Air Defence Servo Test — Radar Dashboard')

gs = gridspec.GridSpec(2, 2, figure=fig,
                       width_ratios=[1.5, 1],
                       height_ratios=[1, 0.6],
                       hspace=0.1, wspace=0.25)

ax_radar  = fig.add_subplot(gs[:, 0], polar=True)
ax_status = fig.add_subplot(gs[0, 1])
ax_log    = fig.add_subplot(gs[1, 1])

ax_radar.set_facecolor('#0d1117')
for ax in [ax_status, ax_log]:
    ax.set_facecolor('#0d1117')
    ax.axis('off')

# ── UPDATE ──────────────────────────────────────
def update(frame):
    is_threat   = state['status'] != 'SCANNING'
    sweep_color = '#ff4444' if is_threat else '#00ff88'

    # ── RADAR ──
    ax_radar.cla()
    ax_radar.set_facecolor('#0d1117')
    ax_radar.set_theta_zero_location('N')
    ax_radar.set_theta_direction(-1)
    ax_radar.set_thetamin(0)
    ax_radar.set_thetamax(180)
    ax_radar.set_ylim(0, 300)
    ax_radar.set_yticks([50, 100, 150, 200, 300])
    ax_radar.set_yticklabels(
        ['50cm','100cm','150cm','200cm','300cm'],
        color='#3d4f5c', fontsize=8)
    ax_radar.tick_params(colors='#3d4f5c')
    ax_radar.spines['polar'].set_color('#1e2d3d')
    ax_radar.grid(color='#1e2d3d', linewidth=0.6)

    # Threat zone ring
    theta_fill = np.linspace(0, np.pi, 100)
    ax_radar.fill_between(theta_fill, 0, THREAT_CM,
                           color='#ff4444', alpha=0.07)
    ax_radar.plot(theta_fill, [THREAT_CM]*100,
                  color='#ff4444', linewidth=0.8, alpha=0.4, linestyle='--')
    ax_radar.text(np.radians(10), THREAT_CM + 15,
                  f'Threat zone <{THREAT_CM}cm',
                  color='#ff4444', fontsize=7, alpha=0.7)

    # Scan trail
    if len(state['angles']) > 1:
        n = len(state['angles'])
        alphas = np.linspace(0.05, 0.5, n)
        for i in range(n):
            ax_radar.scatter(state['angles'][i], state['distances'][i],
                             c=sweep_color, s=10, alpha=float(alphas[i]))

    # Threat stars
    if state['threat_angles']:
        ax_radar.scatter(state['threat_angles'], state['threat_dists'],
                         c='#ff4444', s=140, marker='*',
                         zorder=5, alpha=0.9, label='Threat')

    # Sweep line
    pan_rad = np.radians(state['last_pan'])
    ax_radar.plot([pan_rad, pan_rad], [0, 300],
                  color=sweep_color, linewidth=2.5, alpha=0.95)
    dist_plot = state['last_dist'] if 0 < state['last_dist'] < 300 else 280
    ax_radar.scatter([pan_rad], [dist_plot],
                     c=sweep_color, s=50, zorder=6)

    ax_radar.set_title(
        f"RADAR  —  Pan {state['last_pan']}°  "
        f"|  Dist {state['last_dist']}cm  "
        f"|  Tilt {state['last_tilt']}°",
        color=sweep_color, fontsize=11, pad=14, fontweight='bold')

    # ── STATUS ──
    ax_status.cla()
    ax_status.set_facecolor('#0d1117')
    ax_status.set_xlim(0, 10)
    ax_status.set_ylim(0, 10)
    ax_status.axis('off')

    ax_status.text(5, 9.6, 'AIR DEFENCE — SERVO TEST',
                   color='white', fontsize=12, ha='center', fontweight='bold')

    sc = '#ff4444' if is_threat else '#00ff88'
    ax_status.add_patch(mpatches.FancyBboxPatch(
        (0.3, 8.0), 9.4, 1.2,
        boxstyle="round,pad=0.1",
        linewidth=1.5, edgecolor=sc, facecolor='#111820'))
    ax_status.text(5, 8.63, state['status'],
                   color=sc, fontsize=15, ha='center',
                   fontweight='bold', va='center')

    metrics = [
        ('Distance',      f"{state['last_dist']} cm",    '#63b3ed', 7.0),
        ('Servo 1 Pan',   f"{state['last_pan']}°",       '#1ABC9C', 6.0),
        ('Servo 2 Pan',   f"{state['last_pan']}° (mirror)",'#1ABC9C',5.0),
        ('Servo 3 Tilt',  f"{state['last_tilt']}°",      '#e67e22', 4.0),
        ('Threats Found', str(state['threat_count']),     '#ff4444', 3.0),
    ]
    for lbl, val, col, y in metrics:
        ax_status.plot([0.5, 9.5], [y+0.7, y+0.7],
                       color='#1e2d3d', linewidth=0.4)
        ax_status.text(0.6, y+0.25, lbl,
                       color='#4a5568', fontsize=10, va='center')
        ax_status.text(9.4, y+0.25, val,
                       color=col, fontsize=11, ha='right',
                       fontweight='bold', va='center')

    # servo diagram mini
    ax_status.text(5, 1.8, '[ S1:radar pan ] → [ S2:missile pan ] + [ S3:tilt ]',
                   color='#2d3748', fontsize=8.5, ha='center')
    ax_status.add_patch(plt.Circle((0.7, 0.5), 0.18, color='#00ff88'))
    ax_status.text(1.1, 0.5, f'Connected  {PORT}',
                   color='#4a5568', fontsize=8, va='center')

    # ── LOG ──
    ax_log.cla()
    ax_log.set_facecolor('#111820')
    ax_log.set_xlim(0, 10)
    ax_log.set_ylim(0, 10)
    ax_log.axis('off')

    ax_log.text(0.5, 9.3, 'COMMAND LOG',
                color='#4a5568', fontsize=8, fontweight='bold')

    for i, line in enumerate(reversed(state['log'][-8:])):
        col = '#ff4444' if '⚠️' in line or 'THREAT' in line else \
              '#00ff88' if '✅' in line else '#718096'
        ax_log.text(0.5, 8.1 - i * 1.0, line,
                    color=col, fontsize=8.5, va='center')

log("System ready — auto scanning airspace")

ani = animation.FuncAnimation(fig, update, interval=100, cache_frame_data=False)
plt.tight_layout(pad=1.5)
plt.show()

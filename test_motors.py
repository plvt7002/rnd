"""
╔══════════════════════════════════════════════╗
║     DC MOTOR TEST — Dashboard + Controller   ║
║     Tests ONLY the 4 DC motors via L298N     ║
╚══════════════════════════════════════════════╝
COMMANDS:  W / A / S / D / X  |  SPEED:0-255  |  Q
"""

import serial
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as mpatches
import threading
import time
import sys

# ── CONFIG ─────────────────────────────────────
PORT = '/dev/tty.usbmodem14101'   # ← change this
BAUD = 9600
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
    'direction': 'STOPPED',
    'speed':     150,
    'log':       [],
    'left_on':   False,
    'right_on':  False,
}

def log(msg):
    state['log'].append(msg)
    state['log'] = state['log'][-10:]

# ══════════════════════════════════════════════
# ARDUINO CODE TO UPLOAD FOR THIS TEST:
# ──────────────────────────────────────────────
# #define IN1 4
# #define IN2 7
# #define IN3 12
# #define IN4 13
# #define ENA 5
# #define ENB 6
# int spd = 150;
# void setup() {
#   Serial.begin(9600);
#   pinMode(IN1,OUTPUT); pinMode(IN2,OUTPUT);
#   pinMode(IN3,OUTPUT); pinMode(IN4,OUTPUT);
#   pinMode(ENA,OUTPUT); pinMode(ENB,OUTPUT);
#   Serial.println("MOTOR_READY");
# }
# void stopCar()     { digitalWrite(IN1,LOW);  digitalWrite(IN2,LOW);  digitalWrite(IN3,LOW);  digitalWrite(IN4,LOW); }
# void forward()     { analogWrite(ENA,spd); analogWrite(ENB,spd); digitalWrite(IN1,HIGH); digitalWrite(IN2,LOW);  digitalWrite(IN3,HIGH); digitalWrite(IN4,LOW); }
# void backward()    { analogWrite(ENA,spd); analogWrite(ENB,spd); digitalWrite(IN1,LOW);  digitalWrite(IN2,HIGH); digitalWrite(IN3,LOW);  digitalWrite(IN4,HIGH); }
# void turnLeft()    { analogWrite(ENA,spd); analogWrite(ENB,spd); digitalWrite(IN1,LOW);  digitalWrite(IN2,HIGH); digitalWrite(IN3,HIGH); digitalWrite(IN4,LOW); }
# void turnRight()   { analogWrite(ENA,spd); analogWrite(ENB,spd); digitalWrite(IN1,HIGH); digitalWrite(IN2,LOW);  digitalWrite(IN3,LOW);  digitalWrite(IN4,HIGH); }
# void loop() {
#   if (Serial.available()) {
#     String cmd = Serial.readStringUntil('\n'); cmd.trim(); cmd.toUpperCase();
#     if      (cmd=="W")            { forward();   Serial.println("FORWARD"); }
#     else if (cmd=="S")            { backward();  Serial.println("BACKWARD"); }
#     else if (cmd=="A")            { turnLeft();  Serial.println("LEFT"); }
#     else if (cmd=="D")            { turnRight(); Serial.println("RIGHT"); }
#     else if (cmd=="X")            { stopCar();   Serial.println("STOPPED"); }
#     else if (cmd.startsWith("SPEED:")) { spd=cmd.substring(6).toInt(); Serial.print("SPEED:"); Serial.println(spd); }
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
            if line == "MOTOR_READY":
                log("✅ Arduino ready")
                return
            if line in ["FORWARD","BACKWARD","LEFT","RIGHT","STOPPED"]:
                state['direction'] = line
                state['left_on']   = line in ["FORWARD","BACKWARD","RIGHT"]
                state['right_on']  = line in ["FORWARD","BACKWARD","LEFT"]
                log(f"↩  {line}")
            elif line.startswith("SPEED:"):
                state['speed'] = int(line.split(":")[1])
                log(f"↩  Speed set to {state['speed']}")
            else:
                log(f"   {line}")
        except:
            pass

threading.Thread(target=read_serial, daemon=True).start()

# ── KEYBOARD INPUT THREAD ───────────────────────
def keyboard_input():
    print("\n╔════════════════════════════════╗")
    print("║    DC MOTOR TEST CONTROLLER    ║")
    print("╠════════════════════════════════╣")
    print("║  W = Forward   S = Backward    ║")
    print("║  A = Left      D = Right       ║")
    print("║  X = Stop      Q = Quit        ║")
    print("║  SPEED:150  (0-255)            ║")
    print("╚════════════════════════════════╝\n")
    while True:
        try:
            raw = input(">> ").strip()
            if not raw:
                continue
            cmd = raw.upper()
            if cmd == 'Q':
                ser.write(b'X\n')
                time.sleep(0.3)
                import os; os._exit(0)
            ser.write((raw + '\n').encode())
            labels = {'W':'Forward','S':'Backward','A':'Left','D':'Right','X':'STOP'}
            desc = labels.get(cmd, raw)
            if cmd.startswith("SPEED:"):
                desc = f"Speed → {cmd[6:]}"
            print(f"   ✈  Sent: {raw}  ({desc})")
        except (KeyboardInterrupt, EOFError):
            ser.write(b'X\n'); import os; os._exit(0)

threading.Thread(target=keyboard_input, daemon=True).start()

# ── FIGURE ──────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 6), facecolor='#0d1117')
fig.canvas.manager.set_window_title('DC Motor Test Dashboard')
ax_car, ax_log = axes
for ax in axes:
    ax.set_facecolor('#0d1117')
    ax.axis('off')

# ── DRAW CAR (top view) ─────────────────────────
def draw_car(ax, direction, spd):
    ax.cla()
    ax.set_facecolor('#0d1117')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')

    ax.text(5, 9.5, 'CAR — TOP VIEW',
            color='white', fontsize=13, ha='center', fontweight='bold')

    dir_colors = {
        'FORWARD':  '#00ff88',
        'BACKWARD': '#ff9900',
        'LEFT':     '#63b3ed',
        'RIGHT':    '#63b3ed',
        'STOPPED':  '#4a5568',
    }
    col = dir_colors.get(direction, '#4a5568')

    # Car body
    ax.add_patch(mpatches.FancyBboxPatch(
        (3.2, 3.2), 3.6, 4.5,
        boxstyle="round,pad=0.2",
        facecolor='#1e2d3d', edgecolor=col, linewidth=2
    ))

    # Arrow showing direction
    arrows = {
        'FORWARD':  (5, 6.5, 0,  1.2),
        'BACKWARD': (5, 4.5, 0, -1.2),
        'LEFT':     (4, 5.5, -1.2, 0),
        'RIGHT':    (6, 5.5,  1.2, 0),
        'STOPPED':  None,
    }
    arr = arrows.get(direction)
    if arr:
        ax.annotate('', xy=(arr[0]+arr[2], arr[1]+arr[3]),
                    xytext=(arr[0], arr[1]),
                    arrowprops=dict(arrowstyle='->', color=col,
                                   lw=3, mutation_scale=25))

    # 4 wheels
    wheel_pos = [(2.2,6.8),(7.2,6.8),(2.2,4.0),(7.2,4.0)]
    wheel_labels = ['FL','FR','RL','RR']
    active = {
        'FORWARD':  [True, True, True, True],
        'BACKWARD': [True, True, True, True],
        'LEFT':     [False,True, False,True],
        'RIGHT':    [True, False,True, False],
        'STOPPED':  [False,False,False,False],
    }.get(direction, [False]*4)

    for i, ((wx, wy), lbl) in enumerate(zip(wheel_pos, wheel_labels)):
        wc = '#00ff88' if active[i] else '#2d3748'
        ax.add_patch(mpatches.FancyBboxPatch(
            (wx-0.55, wy-0.45), 1.1, 0.9,
            boxstyle="round,pad=0.05",
            facecolor=wc, edgecolor='#1a1a2e', linewidth=1, alpha=0.85
        ))
        ax.text(wx, wy, lbl, color='white', fontsize=9,
                ha='center', va='center', fontweight='bold')

    # Status box
    ax.add_patch(mpatches.FancyBboxPatch(
        (2.5, 1.0), 5.0, 1.2,
        boxstyle="round,pad=0.1",
        facecolor='#111820', edgecolor=col, linewidth=1.5
    ))
    ax.text(5, 1.62, direction,
            color=col, fontsize=16, ha='center',
            fontweight='bold', va='center')
    ax.text(5, 0.4, f'Speed: {spd}/255  ({round(spd/255*100)}%)',
            color='#718096', fontsize=10, ha='center')

# ── UPDATE ──────────────────────────────────────
def update(frame):
    draw_car(ax_car, state['direction'], state['speed'])

    ax_log.cla()
    ax_log.set_facecolor('#0d1117')
    ax_log.set_xlim(0, 10)
    ax_log.set_ylim(0, 10)
    ax_log.axis('off')

    ax_log.text(5, 9.5, 'COMMAND LOG',
                color='white', fontsize=13, ha='center', fontweight='bold')

    # Command reference
    cmds = [('W','Forward'),('S','Backward'),('A','Left'),
            ('D','Right'),('X','Stop'),('SPEED:n','Set speed')]
    for i, (k, v) in enumerate(cmds):
        y = 8.2 - i * 0.7
        ax_log.add_patch(mpatches.FancyBboxPatch(
            (0.5, y-0.22), 1.6, 0.48,
            boxstyle="round,pad=0.04",
            facecolor='#1e2d3d', edgecolor='#2d4a5e', linewidth=0.5
        ))
        ax_log.text(1.3, y, k, color='#00ff88', fontsize=9,
                    ha='center', fontfamily='monospace', va='center')
        ax_log.text(2.4, y, v, color='#718096', fontsize=9, va='center')

    # Log lines
    ax_log.plot([0.4, 9.6], [3.6, 3.6], color='#1e2d3d', linewidth=0.8)
    ax_log.text(0.5, 3.3, 'Recent:', color='#4a5568', fontsize=8)
    for i, line in enumerate(reversed(state['log'][-7:])):
        col = '#00ff88' if '✅' in line else \
              '#ff4444' if '❌' in line else '#718096'
        ax_log.text(0.5, 2.8 - i * 0.42, line,
                    color=col, fontsize=9, va='center')

    # Connection
    ax_log.add_patch(plt.Circle((0.7, 0.4), 0.18, color='#00ff88'))
    ax_log.text(1.1, 0.4, f'Connected  {PORT}',
                color='#4a5568', fontsize=8, va='center')

log("System ready — type commands below")

ani = animation.FuncAnimation(fig, update, interval=150, cache_frame_data=False)
plt.tight_layout(pad=1.5)
plt.show()

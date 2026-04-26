#include <Servo.h>

// ── Ultrasonic ──────────────────────────────
#define TRIG_PIN  8
#define ECHO_PIN  10

// ── Servos ──────────────────────────────────
#define SERVO_PAN_PIN      3
#define SERVO_MISSILE_PIN  9
#define SERVO_TILT_PIN     11

// ── Motor Driver (L298N) ────────────────────
#define IN1  4
#define IN2  7
#define IN3  12
#define IN4  13
#define ENA  5   // Left motors speed  (PWM)
#define ENB  6   // Right motors speed (PWM)

#define MOTOR_SPEED 180  // 0-255, tune this

Servo panServo;
Servo missileServo;
Servo tiltServo;

int panAngle  = 90;
int tiltAngle = 90;

// ── Motor functions ─────────────────────────
void stopCar() {
  digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
}

void moveForward() {
  analogWrite(ENA, MOTOR_SPEED);
  analogWrite(ENB, MOTOR_SPEED);
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
}

void moveBackward() {
  analogWrite(ENA, MOTOR_SPEED);
  analogWrite(ENB, MOTOR_SPEED);
  digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);
  digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);
}

void turnLeft() {
  analogWrite(ENA, MOTOR_SPEED);
  analogWrite(ENB, MOTOR_SPEED);
  digitalWrite(IN1, LOW);  digitalWrite(IN2, HIGH); // left reverse
  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);  // right forward
}

void turnRight() {
  analogWrite(ENA, MOTOR_SPEED);
  analogWrite(ENB, MOTOR_SPEED);
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);  // left forward
  digitalWrite(IN3, LOW);  digitalWrite(IN4, HIGH); // right reverse
}

// ── Distance ────────────────────────────────
long getDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long dur = pulseIn(ECHO_PIN, HIGH, 30000);
  return dur * 0.034 / 2;
}

// ── Setup ────────────────────────────────────
void setup() {
  Serial.begin(9600);

  // Servo setup
  panServo.attach(SERVO_PAN_PIN);
  missileServo.attach(SERVO_MISSILE_PIN);
  tiltServo.attach(SERVO_TILT_PIN);
  panServo.write(90);
  missileServo.write(90);
  tiltServo.write(90);

  // Motor pins
  pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);
  pinMode(ENA, OUTPUT); pinMode(ENB, OUTPUT);

  // Ultrasonic
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  stopCar();
  Serial.println("READY");
  Serial.println("Commands: W A S D X | PAN:90 TILT:45 SCAN");
}

// ── Command handler ──────────────────────────
void handleCommand(String cmd) {
  cmd.trim();
  cmd.toUpperCase();

  // ── CAR MOVEMENT ──
  if (cmd == "W") { moveForward();  Serial.println("Moving FORWARD");  }
  else if (cmd == "S") { moveBackward(); Serial.println("Moving BACKWARD"); }
  else if (cmd == "A") { turnLeft();    Serial.println("Turning LEFT");    }
  else if (cmd == "D") { turnRight();   Serial.println("Turning RIGHT");   }
  else if (cmd == "X") { stopCar();     Serial.println("STOPPED");         }

  // ── TURRET PAN ──
  else if (cmd.startsWith("PAN:")) {
    panAngle = cmd.substring(4).toInt();
    panAngle = constrain(panAngle, 0, 180);
    panServo.write(panAngle);
    missileServo.write(panAngle);
    Serial.print("PAN → "); Serial.println(panAngle);
  }

  // ── TURRET TILT ──
  else if (cmd.startsWith("TILT:")) {
    tiltAngle = cmd.substring(5).toInt();
    tiltAngle = constrain(tiltAngle, 45, 135);
    tiltServo.write(tiltAngle);
    Serial.print("TILT → "); Serial.println(tiltAngle);
  }

  // ── AUTO SCAN ──
  else if (cmd == "SCAN") {
    Serial.println("Scanning...");
    for (int a = 0; a <= 180; a += 5) {
      panServo.write(a);
      missileServo.write(a);
      delay(40);
      long dist = getDistance();
      Serial.print(a); Serial.print(",90,"); Serial.println(dist);
    }
    panServo.write(90);
    missileServo.write(90);
  }

  // ── SPEED ──
  else if (cmd.startsWith("SPEED:")) {
    int spd = cmd.substring(6).toInt();
    // Store as global — simple approach
    analogWrite(ENA, spd);
    analogWrite(ENB, spd);
    Serial.print("Speed → "); Serial.println(spd);
  }

  else {
    Serial.println("Unknown command");
  }
}

// ── Loop ─────────────────────────────────────
void loop() {
  // Always read distance and send to laptop
  long dist = getDistance();
  Serial.print(panAngle);
  Serial.print(",");
  Serial.print(tiltAngle);
  Serial.print(",");
  Serial.println(dist);

  // Check for incoming commands
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    handleCommand(cmd);
  }

  delay(80);
}
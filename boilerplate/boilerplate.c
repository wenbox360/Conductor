#include <Servo.h>

Servo turretServo;

char inputBuffer[32];     // buffer for incoming serial data
byte bufferIndex = 0;

unsigned long lastIrSend = 0;    // timer for IR reporting
const unsigned long irInterval = 200; // send IR data every 200ms

void setup() {
  Serial.begin(9600);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  turretServo.attach(SERVO_PIN);
}

void servo_write(int angle) {
  turretServo.write(angle);
}

int irSensorReading() {
  return analogRead(IR_PIN);
}

void buzzer_duration(int duration) {
  tone(BUZZER_PIN, 1000);
  delay(duration);
  noTone(BUZZER_PIN);
}

void led_on() {
  digitalWrite(LED_PIN, HIGH);
}

void led_off() {
  digitalWrite(LED_PIN, LOW);
}

void processCommand(char *cmd) {
  // Find comma if present
  char *comma = strchr(cmd, ',');
  int command = 0;
  int param   = 0;

  if (comma) {
    *comma = '\0'; // split string into two parts
    command = atoi(cmd);
    param   = atoi(comma + 1);
  } else {
    command = atoi(cmd);
  }

  // ---- Command handling ----
  if (command == 2) {           // Piezo test (no param)
    buzzer_duration(200);
    Serial.println("A");
  }
  else if (command == 20) {     // Servo write (needs param)
    servo_write(param);
    Serial.println("A");
  }
  else if (command == 30) {     // LED write (needs param)
    if (param == 1) led_on();
    else led_off();
    Serial.println("A");
  }
  else {
    Serial.println("E");        // Unknown command
  }
}

void loop() {
  // Handle incoming serial commands
  while (Serial.available() > 0) {
    char inChar = (char)Serial.read();

    if (inChar == ';') { // end of command
      inputBuffer[bufferIndex] = '\0';  // null terminate
      processCommand(inputBuffer);
      bufferIndex = 0;
    }
    else {
      if (bufferIndex < sizeof(inputBuffer) - 1) {
        inputBuffer[bufferIndex++] = inChar;
      }
    }
  }

  // ---- Always stream IR values ----
  unsigned long now = millis();
  if (now - lastIrSend >= irInterval) {
    lastIrSend = now;
    int irValue = irSensorReading();
    Serial.print("40,");
    Serial.println(irValue);
  }
}

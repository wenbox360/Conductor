#ifdef MICRO_SERVO_SG90_PIN
#include <Servo.h>
Servo turretServo;
#endif

char inputBuffer[32];     // buffer for incoming serial data
byte bufferIndex = 0;

#ifdef IR_GP2Y0A21YK0F_PIN
unsigned long lastIrSend = 0;
const unsigned long irInterval = 200;
#endif

void setup() {
  Serial.begin(9600);
#ifdef LED_PIN
  pinMode(LED_PIN, OUTPUT);
#endif
#ifdef PIEZO_BUZZER_PIN
  pinMode(PIEZO_BUZZER_PIN, OUTPUT);
#endif
#ifdef MICRO_SERVO_SG90_PIN
  turretServo.attach(MICRO_SERVO_SG90_PIN);
#endif
}

#ifdef MICRO_SERVO_SG90_PIN
void servo_write(int angle) {
  turretServo.write(angle);
}
#endif

#ifdef IR_GP2Y0A21YK0F_PIN
int irSensorReading() {
  int raw = analogRead(IR_GP2Y0A21YK0F_PIN);
  float voltage = raw * (5.0 / 1023.0);  // convert ADC to voltage (assuming 5V ref)

  if (voltage <= 0.42) {
    return -1; // out of range / invalid
  }

  float distance_cm = 27.86 / (voltage - 0.42);
  return (int)distance_cm;
}
#endif

#ifdef PIEZO_BUZZER_PIN
void buzzer_duration(int duration) {
  tone(PIEZO_BUZZER_PIN, 1000, duration);
}
#endif

#ifdef LED_PIN
void led_on() {
  digitalWrite(LED_PIN, HIGH);
}

void led_off() {
  digitalWrite(LED_PIN, LOW);
}
#endif

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

#ifdef PIEZO_BUZZER_PIN
  if (command == 2) {           // Piezo test (no param)
    buzzer_duration(constrain(param > 0 ? param : 200, 1, 5000));
    Serial.println("A");
    return;
  }
#endif
#ifdef MICRO_SERVO_SG90_PIN
  if (command == 20) {          // Servo write (needs param)
    servo_write(param);
    Serial.println("A");
    return;
  }
#endif
#ifdef LED_PIN
  if (command == 30) {          // LED write (needs param)
    if (param == 1) led_on();
    else led_off();
    Serial.println("A");
    return;
  }
#endif
  Serial.println("E");          // Unknown or unavailable command
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

#ifdef IR_GP2Y0A21YK0F_PIN
  unsigned long now = millis();
  if (now - lastIrSend >= irInterval) {
    lastIrSend = now;
    int irValue = irSensorReading();
    Serial.print("40,");
    Serial.println(irValue);
  }
#endif
}

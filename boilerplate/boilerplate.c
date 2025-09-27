#include <Servo.h>

Servo turretServo;

void setup() {
  Serial.begin(9600);
#ifdef SERVO_PIN
    turretServo.attach(SERVO_PIN);
#endif
}

void servo_write(int angle){
    turretServo.writeMicroseconds(angle);
}

int irSensorReading(){
    return analogRead(IR_PIN);
}

void buzzer_duration(int duration){
    tone(BUZZER_PIN, 1000);
    delay(duration);
    noTone(BUZZER_PIN);
}

void buzzer_on(){
    tone(BUZZER_PIN, 1000);
}

void buzzer_off(){
    noTone(BUZZER_PIN);
}

void led_on(){
    digitalWrite(LED_PIN, HIGH);
}

void led_off(){
    digitalWrite(LED_PIN, LOW);
}

void loop() {

//main loop code here

//read serial input
if (Serial.available() > 0) {
    int command = Serial.parseInt();
    int param = Serial.parseInt();
}

if(command == 2) { //Piezo command
    buzzer_duration(param);
    Serial.print("A");
    command = 0; //reset command
}
else if (command == 20) { //SERVO command
    servo_write(param);
    Serial.print("A");
    command = 0; //reset command
}
else if (command == 30) { //LED command
    if(param == 1) {
        led_on();
    } else {
        led_off();
    }
    Serial.print("A");
    command = 0; //reset command
}
 
//IR Sensor command
int irValue = irSensorReading();
Serial.print(40);
Serial.print(irValue);
Serial.print("\x00");

//end of main loop
}
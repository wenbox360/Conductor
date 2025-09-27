#include <Servo.h>

Servo turretServo;
int turretCommand=1000;
int irReading;
int commandStep=20;
int sweepDirection=1;


//additional variables for tracking machineState
int detectedFlag=0;
int machineState=0; //0='normal' , 1='ACTIVE DETECTION', 2='upgrade state'
int cycleCounter=0;


void setup() {
  turretServo.attach(8);
  Serial.begin(9600);
}

void loop() {

//////////////////////////////Process inputs///////
irReading=analogRead(A0);
if (irReading>300){detectedFlag=1;}
else {detectedFlag=0;}


/////////////////////////Decide what state the machine should be in /////
if(detectedFlag==1){machineState=1;} //active detection

else if(detectedFlag==0 && cycleCounter >0  ){machineState=2;} //high-alert mode

else{ machineState=0;} //normal scanning

///////////////////////// Process outputs based on state for this 30ms interval////
if (machineState==0){  //Normal scanning
  //turn off spotlight
  digitalWrite(7,LOW);
  //turn off alarm
  noTone(6);
  //Sweep turret normally
  turretCommand=turretCommand+commandStep*sweepDirection;
  //check sweep limits
  if (turretCommand<=1000){sweepDirection=1;}
  if (turretCommand>=2000){sweepDirection=-1;}
  turretServo.writeMicroseconds(turretCommand);
  //do nothing about cycleCounter
  cycleCounter = cycleCounter;

}


if (machineState==1){  //Active detection
  //Set spotlight on/off
  digitalWrite(7,HIGH);

  //Set alarm on/off
  tone(6,500);
    delay(500);
    noTone(6);
    delay(500);

  //Sweep turret appropriately
  turretCommand=turretCommand;
  if (turretCommand<=1000){sweepDirection=1;}
  if (turretCommand>=2000){sweepDirection=-1;}
  turretServo.writeMicroseconds(turretCommand);

  //Update cycleCounter
  cycleCounter++;

}


if (machineState==2){ //upgrade state
  //Set spotlight on/off
  digitalWrite(7,HIGH);

  //Set alarm on/off
    tone(6,1000);
    delay(500);
    noTone(6);
    delay(30);

  //Sweep turret appropriately

  turretCommand=turretCommand+commandStep*20*sweepDirection;
  //check sweep limits
  if (turretCommand<=1000){sweepDirection=1;}
  if (turretCommand>=2000){sweepDirection=-1;}
  turretServo.writeMicroseconds(turretCommand);
  cycleCounter++;
  //Update cycleCounter
  if(cycleCounter>10)
  {cycleCounter=0;
  }

}


delay(15);
noTone(6);  //// set tone to OFF after 15ms to create alarm sound if it was triggered.
delay(15);
//total delay still at 30ms

//end of main loop
}
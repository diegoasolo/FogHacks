/*************************************************************
/* Simple Arduino program to demonstrate input and output triggers
/* for Ajile devices. 
/* The Arduino LED blinks when a trigger signal from the Ajile device appears,
/* and it generates a trigger signal to the Ajile device at a serial port
/* configurable time inverval (in milliseconds).
**************************************************************/

// constants won't change. Used here to set a pin number :
const int ledPin =  13;      // the number of the LED pin
const int triggerFromDMDPin = 50;
const int triggerToDMDPin = 48;

// Variables will change :
int ledState = LOW;             // ledState used to set the LED
int triggerFromDMDStateCurr = 0;
int triggerFromDMDStatePrev = 0;

// Generally, you shuould use "unsigned long" for variables that hold time
// The value will quickly become too large for an int to store
unsigned long endLedTime = 0;        // will store last time LED was updated

unsigned long triggerToDMDIntervalMillis = 250;
unsigned long prevTriggerToDMDIntervalMillis = 0;
int triggerToDMDState = LOW;

// constants won't change :
const long ledInterval = 50;           // interval at which to blink (milliseconds)

void setup() {

  Serial.begin(9600);

  // set the digital pin as output:
  pinMode(ledPin, OUTPUT);
  pinMode(triggerToDMDPin, OUTPUT);

  pinMode(triggerFromDMDPin, INPUT);

}

void loop()
{

  unsigned long currentMillis = millis();

  if (Serial.available()) {
    // read the most recent byte (which will be from 0 to 255):
    triggerToDMDIntervalMillis = Serial.parseInt();
  }

  if (currentMillis - prevTriggerToDMDIntervalMillis >= triggerToDMDIntervalMillis) {
    // save the last time you blinked the LED
    prevTriggerToDMDIntervalMillis = currentMillis;

    if (triggerToDMDState == LOW)
      triggerToDMDState = HIGH;
    else
      triggerToDMDState = LOW;

    // set the LED with the ledState of the variable:
    digitalWrite(triggerToDMDPin, triggerToDMDState);
  }

  if (currentMillis >= endLedTime) {
    ledState = LOW;
  }

  triggerFromDMDStateCurr = digitalRead(triggerFromDMDPin);

  // set the LED with the ledState of the variable:
  if (triggerFromDMDStateCurr == 1 && triggerFromDMDStatePrev == 0) {
    ledState = HIGH;
    endLedTime = currentMillis + ledInterval;
  }

  triggerFromDMDStatePrev = triggerFromDMDStateCurr;

  digitalWrite(ledPin, ledState);

}


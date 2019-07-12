// basic outline of the reader taken from
// http://forum.arduino.cc/index.php?topic=396450.0

#include <Arduino.h>
#include <string.h>

#include "interface.cpp"

int pin = 52;

void setup() {
    Serial.begin(9600);
    Serial.println("<Arduino is ready to receive commands>");
}

void loop() {
    digitalWrite(pin, HIGH);
    delay(t_high);
    digitalWrite(pin, LOW);
    delay(t_low);

    // put state machine here

    // and finish loop with those two commands
    getSerialData();
    processSerialData();
}

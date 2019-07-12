// basic outline of the reader taken from
// http://forum.arduino.cc/index.php?topic=396450.0

#include <Arduino.h>
#include <string.h>
#include <event_codes.h>

#include "interface.cpp"

int pin = 52;
int state = UP_STATE;

void finite_state_machine() {
    switch (state) {
        case UP_STATE:
            // log state entry
            Serial.println(state);

            // state actions
            digitalWrite(pin, HIGH);
            delay(t_high);

            // state transition
            state = DOWN_STATE;
            
        case DOWN_STATE:
            // log state entry
            Serial.println(state);

            // state actions
            digitalWrite(pin, LOW);
            delay(t_low);

            // state transition
            state = UP_STATE;
    }
}

void setup() {
    Serial.begin(9600);
    Serial.println("<Arduino is ready to receive commands>");
}

void loop() {
    // put state machine here
    finite_state_machine();

    // and finish loop with those two commands
    getSerialData();
    processSerialData();
}

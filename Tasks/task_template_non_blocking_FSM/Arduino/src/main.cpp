// basic outline of the reader taken from
// http://forum.arduino.cc/index.php?topic=396450.0

#include <Arduino.h>
#include <string.h>
#include <event_codes.h>

#include "interface.cpp"


int pin = 52;
int current_state = UP_STATE;
int last_state = INI_STATE;

unsigned long state_entry = 2147483647; // max future

void finite_state_machine() {
    switch (current_state) {
        case UP_STATE:
            // state entry
            if (current_state != last_state){
                // log state entry
                Serial.println(millis());
                last_state = current_state;

                // entry actions
                digitalWrite(pin, HIGH);
                state_entry = millis();
            }

            // update
            if (last_state == current_state){
                // state actions
                // delay(t_high);
            }

            // exit condition
            if (millis() - state_entry > t_high) {
                current_state = DOWN_STATE;
            }
            
        case DOWN_STATE:
            // state entry
            if (current_state != last_state){
                // log state entry
                Serial.println(millis());
                last_state = current_state;

                // entry actions
                digitalWrite(pin, LOW);
                state_entry = millis();
            }

            // update
            if (last_state == current_state){
                // state actions
                // delay(t_high);
            }

            // exit condition
            if (millis() - state_entry > t_low) {
                current_state = UP_STATE;
            }
    }
}

void setup() {
    Serial.begin(9600);
    Serial.println("<Arduino is ready to receive commands>");
}

void loop() {
    // put state machine(s) here
    finite_state_machine();

    // and finish loop with those two commands
    getSerialData();
    processSerialData();
}

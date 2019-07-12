// basic outline of the reader taken from
// http://forum.arduino.cc/index.php?topic=396450.0

#include <Arduino.h>
#include <string.h>
#include <event_codes.h>
#include <pin_map.h>

// probably forward declaration of functions necessary
void run();
#include "interface.cpp"

void run() {
    for (int i = 0; i < n_reps; i++){
        digitalWrite(REWARD_VALVE_PIN,HIGH);
        Serial.println(String(millis()) + "\t" + REWARD_ON);
        delay(reward_valve_time);
        digitalWrite(REWARD_VALVE_PIN,LOW);
        Serial.println(String(millis()) + "\t" + REWARD_OFF);
        delay(500);
    }
}

void setup() {
    Serial.begin(9600);
    Serial.println("<Arduino is ready to receive commands>");
    Serial.println("running valve calibration once");
    run();
}

void loop() {
    // and finish loop with those two commands
    getSerialData();
    processSerialData();
}

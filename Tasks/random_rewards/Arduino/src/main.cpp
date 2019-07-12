// basic outline of the reader taken from
// http://forum.arduino.cc/index.php?topic=396450.0

#include <Arduino.h>
#include <string.h>
#include <event_codes.h>
#include <pin_map.h>
#include "interface.cpp"

float T;

float expon_dist(float lam){
    // return a draw x from an expon distr with rate param lam
    // inversion method

    float res = 10000.0;  // hardcoded resolution
    float r = random(res) / res;
    float x = log(1-r) / (-1 * lam);
    return x;
}

void setup() {
    Serial.begin(9600);
    Serial.println("<Arduino is ready to receive commands>");
}

void loop() {
    T = expon_dist(reward_poisson_lambda);
    // delay(T*1000-reward_valve_time);
    if ((T*1000)-reward_valve_time > 0) {
        delay((T*1000)-reward_valve_time);
    }
    digitalWrite(REWARD_VALVE_PIN,HIGH);
    digitalWrite(NI_COM_PIN,HIGH);
    Serial.println(String(millis()) + "\t" + REWARD_ON);
    delay(reward_valve_time);
    digitalWrite(REWARD_VALVE_PIN,LOW);
    digitalWrite(NI_COM_PIN,LOW);
    Serial.println(String(millis()) + "\t" + REWARD_OFF);

    // and finish loop with those two commands
    getSerialData();
    processSerialData();
}

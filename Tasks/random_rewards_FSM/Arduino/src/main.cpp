// a template for a FSM based task with a nonblocking state machine

#include <Arduino.h>
#include <string.h>

#include <event_codes.h> // check if ""
#include "interface.cpp"
#include "pin_map.h"

int current_state = IDLE_STATE;
int last_state = INI_STATE;
int t_exit;

unsigned long state_entry = 2147483647; // max future - why?

// void read_lick_IR(){
//   // samples the IR beam for licks
//   if (lick_in == false && digitalRead(lick_pin) == true){
//     print_code(lick_code);
//     lick_in = true;
//     digitalWrite(lick_monitor_pin,HIGH);
//     if (reward_collected == false){
//       reward_collected = true;
//     }
//   }
//   if (lick_in == true && digitalRead(lick_pin) == false){
//     print_code(lick_code+1);
//     lick_in = false;
//     digitalWrite(lick_monitor_pin,LOW);
//   }
// }

float expon_dist(float lam){
    // return a draw x from an expon distr with rate param lam
    // inversion method

    float res = 10000.0;  // hardcoded resolution
    float r = random(res) / res;
    float x = log(1-r) / (-1 * lam);
    return x;
}

// TODO
// logging functions: tstamp, state, value (opt)
// log_state()
// log_value()

// TODO -> commons.cpp
void log_current_state(){
    Serial.println(String(current_state) + '\t' + String(millis()));  // two column version
}

void finite_state_machine() {
    switch (current_state) {
        case REWARD_STATE:
            // state entry
            if (current_state != last_state){
                // log state entry
                last_state = current_state;
                log_current_state();

                // entry actions
                digitalWrite(REWARD_VALVE_PIN, HIGH);
                digitalWrite(NI_COM_PIN, HIGH);
                state_entry = millis();
            }

            // update
            if (last_state == current_state){
                // state actions
            }

            // exit condition
            if (millis() - state_entry > reward_valve_time) {
                digitalWrite(REWARD_VALVE_PIN, LOW);
                digitalWrite(NI_COM_PIN, LOW);
                current_state = IDLE_STATE;
            }
            
        case IDLE_STATE:
            // state entry
            if (current_state != last_state){
                // log state entry
                last_state = current_state;
                log_current_state();

                // entry actions
                state_entry = millis();
                t_exit = state_entry + expon_dist(reward_poisson_lambda) * 1000;
            }

            // update
            if (last_state == current_state){
                // state actions
            }

            // exit condition
            if (millis() > t_exit) {
                current_state = REWARD_STATE;
            }
    }
}

void setup() {
    Serial.begin(9600);
    Serial.println("<Arduino is ready to receive commands>");
}

void loop() {
    if (run == true){
        // execute state machine(s)
        finite_state_machine();

        // sample sensors
        // sample_rotary_encoder();
        // read_lick_IR();
    }

    // serial communication
    getSerialData();
    processSerialData();
}

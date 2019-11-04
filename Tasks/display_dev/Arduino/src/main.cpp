// a template for a FSM based task with a nonblocking state machine

// think about this


#include <Arduino.h>
#include <string.h>

#include <event_codes.h>
#include "interface.cpp"
#include "raw_interface.cpp"
#include "pin_map.h"


/*
 _______   _______   ______  __          ___      .______          ___   .___________. __    ______   .__   __.      _______.
|       \ |   ____| /      ||  |        /   \     |   _  \        /   \  |           ||  |  /  __  \  |  \ |  |     /       |
|  .--.  ||  |__   |  ,----'|  |       /  ^  \    |  |_)  |      /  ^  \ `---|  |----`|  | |  |  |  | |   \|  |    |   (----`
|  |  |  ||   __|  |  |     |  |      /  /_\  \   |      /      /  /_\  \    |  |     |  | |  |  |  | |  . `  |     \   \
|  '--'  ||  |____ |  `----.|  `----./  _____  \  |  |\  \----./  _____  \   |  |     |  | |  `--'  | |  |\   | .----)   |
|_______/ |_______| \______||_______/__/     \__\ | _| `._____/__/     \__\  |__|     |__|  \______/  |__| \__| |_______/

*/
int current_state = IDLE_STATE;
int last_state = INI_STATE;
unsigned long t_state_duration;
unsigned long state_entry = 2147483647; // max future - why?
bool lick_in = false;

/*
.___  ___.      ___   .___________. __    __
|   \/   |     /   \  |           ||  |  |  |
|  \  /  |    /  ^  \ `---|  |----`|  |__|  |
|  |\/|  |   /  /_\  \    |  |     |   __   |
|  |  |  |  /  _____  \   |  |     |  |  |  |
|__|  |__| /__/     \__\  |__|     |__|  |__|

*/

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

/*
 __        ______     _______
|  |      /  __  \   /  _____|
|  |     |  |  |  | |  |  __
|  |     |  |  |  | |  | |_ |
|  `----.|  `--'  | |  |__| |
|_______| \______/   \______|

*/
void log_current_state(){
    Serial.println(String(current_state) + '\t' + String(micros()));
}

void log_code(int code){
    Serial.println(String(code) + '\t' + String(micros()));
}

/*
     _______. _______ .__   __.      _______.  ______   .______          _______.
    /       ||   ____||  \ |  |     /       | /  __  \  |   _  \        /       |
   |   (----`|  |__   |   \|  |    |   (----`|  |  |  | |  |_)  |      |   (----`
    \   \    |   __|  |  . `  |     \   \    |  |  |  | |      /        \   \
.----)   |   |  |____ |  |\   | .----)   |   |  `--'  | |  |\  \----.----)   |
|_______/    |_______||__| \__| |_______/     \______/  | _| `._____|_______/

*/
void read_lick_IR(){
  // samples the IR beam for licks
  if (lick_in == false && digitalRead(LICK_PIN) == true){
    log_code(LICK_ON);
    lick_in = true;
    // if (reward_collected == false){
    //   reward_collected = true;
    // }
  }
  if (lick_in == true && digitalRead(LICK_PIN) == false){
    log_code(LICK_OFF);
    lick_in = false;
  }
}

/*
 _______     _______..___  ___.
|   ____|   /       ||   \/   |
|  |__     |   (----`|  \  /  |
|   __|     \   \    |  |\/|  |
|  |    .----)   |   |  |  |  |
|__|    |_______/    |__|  |__|

to be taken into account when these are written 
https://arduino.stackexchange.com/questions/12587/how-can-i-handle-the-millis-rollover
exit condition has to include condition || last_state != current_state
so it can get called when state is manually changed
will not work as exit functions contain transition to next state ... 
*/
void finite_state_machine() {
    switch (current_state) {
        case REWARD_STATE:
            // state entry
            if (current_state != last_state){
                // log state entry
                last_state = current_state;
                log_current_state();
                state_entry = micros();

                // entry actions
                digitalWrite(REWARD_VALVE_PIN, HIGH);
            }

            // update
            if (last_state == current_state){
                // state actions
            }

            // exit condition
            if (micros() - state_entry > reward_valve_time) {
                digitalWrite(REWARD_VALVE_PIN, LOW);
                current_state = IDLE_STATE;
            }
            
        case IDLE_STATE:
            // state entry
            if (current_state != last_state){
                // log state entry
                last_state = current_state;
                log_current_state();
                state_entry = micros();

                // entry actions
                // t_exit = state_entry + expon_dist(reward_poisson_lambda) * 1000;
                t_state_duration = 1000000;
                // t_exit = state_entry + 10000;

                // if (t_exit <= state_entry) {
                //     Serial.println("it happened!");
                //     t_exit = micros()+1;
                //     current_state = REWARD_STATE;
                // }
            }

            // update
            if (last_state == current_state){
                // state actions
            }

            // exit condition
            if (micros() - state_entry > t_state_duration) {
                current_state = REWARD_STATE;
            }
    }
}

/*
.___  ___.      ___       __  .__   __.
|   \/   |     /   \     |  | |  \ |  |
|  \  /  |    /  ^  \    |  | |   \|  |
|  |\/|  |   /  /_\  \   |  | |  . `  |
|  |  |  |  /  _____  \  |  | |  |\   |
|__|  |__| /__/     \__\ |__| |__| \__|

*/
void setup() {
    Serial.begin(115200);
    Serial1.begin(115200);
    Serial.println("<Arduino is ready to receive commands>");
}

void loop() {
    if (run == true){
        // execute state machine(s)
        finite_state_machine();

        // sample sensors
        // sample_rotary_encoder();
        read_lick_IR();
    }

    // serial communication
    getSerialData();
    processSerialData();

    // raw data via serial
    getRawData();
    processRawData();
}
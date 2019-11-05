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
int current_state = HOLD_STATE; // starting at this
int last_state = ITI_STATE; // whatever other state
unsigned long max_future = 2147483647;
unsigned long state_entry = max_future
// this is max future actually 4294967295

// flow control flags
bool lick_in = false;
bool on_target = false;

// distance between target and cursor
float D; 
float D_X;
float D_Y;

// target coordinates (could also be exposed to have them offcenter)
float T_X = 0.0;
float T_Y = 0.0;

/*
.___  ___.      ___   .___________. __    __
|   \/   |     /   \  |           ||  |  |  |
|  \  /  |    /  ^  \ `---|  |----`|  |__|  |
|  |\/|  |   /  /_\  \    |  |     |   __   |
|  |  |  |  /  _____  \   |  |     |  |  |  |
|__|  |__| /__/     \__\  |__|     |__|  |__|

*/

// float expon_dist(float lam){
//     // return a draw x from an expon distr with rate param lam
//     // inversion method

//     float res = 10000.0;  // hardcoded resolution
//     float r = random(res) / res;
//     float x = log(1-r) / (-1 * lam);
//     return x;
// }

float euclid_dist(float X, float Y){
    return sqrt(X**2 + Y**2);
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
void read_lick(){
  // samples the IR beam for licks
  if (lick_in == false && digitalRead(LICK_PIN) == true){
    log_code(LICK_ON);
    lick_in = true;
  }
  if (lick_in == true && digitalRead(LICK_PIN) == false){
    log_code(LICK_OFF);
    lick_in = false;
  }
}

void process_LoadCell(){
    // calculate distance between target and current cursor pos
    D_X = T_X - X;
    D_Y = T_Y - Y;
    D = euclid_dist(D_X, D_Y);

    if (D < max_dist && on_target == false){
        on_target = true;
        log_code(ON_TARGET_ON);
    }

    if (D > max_dist && on_target == true){
        on_target = false;
        log_code(ON_TARGET_OFF);
    }

}

/*
____    ____  ___       __      ____    ____  _______
\   \  /   / /   \     |  |     \   \  /   / |   ____|
 \   \/   / /  ^  \    |  |      \   \/   /  |  |__
  \      / /  /_\  \   |  |       \      /   |   __|
   \    / /  _____  \  |  `----.   \    /    |  |____
    \__/ /__/     \__\ |_______|    \__/     |_______|

*/

bool reward_valve_closed = true;
bool deliver_reward = false;
unsigned long reward_valve_open_time = max_future;

void RewardValveController(){
    // self terminating digital pin blink
    if (reward_valve_closed == true && deliver_reward == true) {
        digitalWrite(REWARD_VALVE_PIN,HIGH);
        reward_valve_closed = false;
        // reward_valve_dur = ul2time(reward_magnitude);
        reward_valve_open_time = micros();
        deliver_reward = false;
    }

    if (reward_valve_closed == false && micros() - reward_valve_open_time > reward_valve_dur) {
        digitalWrite(REWARD_VALVE_PIN,LOW);
        reward_valve_closed = true;
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

void state_entry_common(){
    // common tasks to do at state entry for all states
    last_state = current_state;
    state_entry = micros();
    log_current_state();
}

void finite_state_machine() {
    // the main FSM
    switch (current_state) {

        case TRIAL_AVAILABLE_STATE:
            //state entry
            if (current_state != last_state){
                state_entry_common();
            }

            // update
            if (last_state == current_state){
            
            }

            // exit condition
            if (micros() - state_entry > ...) {
                // successfully withhold movement for enough time:
                // go to reward available state
                current_state = HOLD_STATE;
            }

        case HOLD_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                // entry actions
                // cue state
            }

            // update
            if (last_state == current_state){
                // state actions
                // if movement exceeds bounds, timeout
                if (on_target == false){
                    current_state = TIMEOUT_STATE;
                    log_code(BROKEN_FIXATION);
                }
                // if premature lick, timeout
                if (lick_in == true){
                    current_state = TIMEOUT_STATE;
                    log_code(BROKEN_FIXATION);
                }
            }

            // exit condition
            if (micros() - state_entry > hold_dur) {
                // successfully withhold movement for enough time:
                // go to reward available state
                current_state = REWARD_AVAILABLE_STATE;
                log_code(SUCCESSFUL_FIXATION);
            }
            
        case REWARD_AVAILABLE_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                // entry actions
                // play sound

            }

            // update
            if (last_state == current_state){
                // state actions
                // if lick_in, open valve
                if (lick_in == true and reward_collected == false){
                    deliver_reward = true;
                    reward_collected = true;
                    log_code(REWARD_COLLECTED_EVENT);
                    // if here
                    // current_state = ITI_STATE
                    // -> incentive to lick as early as possible
                }
            }

            // exit condition
            if (micros() - state_entry > reward_available_dur) {
                // transit to ITI after certain time
                current_state = ITI_STATE;
                reward_collected = false;
            }
            

        case ITI_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                // entry actions
                // set screen blank
            }

            // update
            if (last_state == current_state){
                // state actions
            }

            // exit condition
            if (micros() - state_entry > ITI_dur) {
                // after ITI, transit to hold
                current_state = TRIAL_AVAILABLE_STATE;
            }

        case TIMEOUT_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();

                // entry actions
                // play punish sound

            }

            // update
            if (last_state == current_state){
                // state actions
            }

            // exit condition
            if (micros() - state_entry > timeout_dur) {
                // after ITI, transit to hold
                current_state = TRIAL_AVAILABLE_STATE;
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
        read_lick();

        // valve controllers
        RewardValveController();
    }

    // serial communication
    getSerialData();
    processSerialData();

    // raw data via serial
    getRawData();
    processRawData();
}

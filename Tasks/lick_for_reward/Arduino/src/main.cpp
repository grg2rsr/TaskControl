#include <Arduino.h>
#include <string.h>
#include <Tone.h>

#include <event_codes.h> // <>?
#include "interface.cpp"
#include "pin_map.h"

/*
 _______   _______   ______  __          ___      .______          ___   .___________. __    ______   .__   __.      _______.
|       \ |   ____| /      ||  |        /   \     |   _  \        /   \  |           ||  |  /  __  \  |  \ |  |     /       |
|  .--.  ||  |__   |  ,----'|  |       /  ^  \    |  |_)  |      /  ^  \ `---|  |----`|  | |  |  |  | |   \|  |    |   (----`
|  |  |  ||   __|  |  |     |  |      /  /_\  \   |      /      /  /_\  \    |  |     |  | |  |  |  | |  . `  |     \   \
|  '--'  ||  |____ |  `----.|  `----./  _____  \  |  |\  \----./  _____  \   |  |     |  | |  `--'  | |  |\   | .----)   |
|_______/ |_______| \______||_______/__/     \__\ | _| `._____/__/     \__\  |__|     |__|  \______/  |__| \__| |_______/

*/

// int current_state = INI_STATE; // starting at this, aleady declared in interface.cpp
int last_state = ITI_STATE; // whatever other state
unsigned long max_future = 4294967295; // 2**32 -1
unsigned long state_entry = max_future;

// flow control flags
bool lick_in = false;
bool reward_collected = false;

// speakers
Tone tone_controller;
unsigned long tone_duration = 200;


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

void log_msg(String Message){
    Serial.println(Message);
}

// for future implementation: do all time based things on float base?
// should be the same in memory, one operation more per micros() call
// more human readable times to set
// take care that vars taken from the UI are cast correctly

// float now(){
//     return (float) micros() / 1000.0;
// }

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

new idea to this: make a req_state variable (requested state) and check if
req and the current state are different

# exit function
if (exit_condition || req_state != current_state) {
    current_state = req_state
}
but then this needs to get deactivated after one execution, so extra flag is needed

if (exit_condition || (req_state != current_state && state_change_requested == True) ) {
    current_state = req_state;
    state_change_requested = False;
}
then, state change is requested by 
<SET req_state state>
<SET state_change_requested true>
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

        case INI_STATE:
            // nothing
            break;

        case REWARD_AVAILABLE_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                // entry actions
                reward_collected = false;
                // play sound check up on nonblocking tone library
                tone_controller.play(reward_tone_freq, tone_duration);
            }

            // update
            if (last_state == current_state){
                // state actions
                // if lick_in, open valve
                if (lick_in == true and reward_collected == false){
                    deliver_reward = true;
                    reward_collected = true;
                    log_code(REWARD_COLLECTED_EVENT);
                }
            }

            // exit condition
            if (micros() - state_entry > reward_available_dur) {
                // transit to ITI after certain time
                current_state = ITI_STATE;
            }
            break;
            
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
                // after ITI, transit to trial available
                current_state = REWARD_AVAILABLE_STATE;
            }
            break;

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
    tone_controller.begin(SPEAKER_PIN);
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
}
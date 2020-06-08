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
int last_state = REWARD_AVAILABLE_STATE; // whatever other state
unsigned long max_future = 4294967295; // 2**32 -1
unsigned long state_entry = max_future;

// flow control flags
bool lick_in = false;
bool reward_collected = false;

// speakers
Tone tone_controller;
unsigned long tone_duration = 200; // FIXME CHECK THIS / expose this

//
unsigned long this_ITI_dur;

/*
 __        ______     _______
|  |      /  __  \   /  _____|
|  |     |  |  |  | |  |  __
|  |     |  |  |  | |  | |_ |
|  `----.|  `--'  | |  |__| |
|_______| \______/   \______|

*/

float now(){
    return (unsigned long) micros() / 1000;
}

void log_code(int code){
    Serial.println(String(code) + '\t' + String(micros()/1000.0));
}

void log_msg(String Message){
    Serial.println("<MSG "+Message+" >");
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

float ul2time(unsigned long reward_volume){
    return (float) reward_volume / valve_ul_ms;
}

bool reward_valve_closed = true;
// bool deliver_reward = false; // already forward declared in interface_template.cpp
unsigned long reward_valve_open_time = max_future;
float reward_valve_dur = 0;

void RewardValveController(){
    // practically a self terminating digital pin blink
    if (reward_valve_closed == true && deliver_reward == true) {
        tone_controller.play(reward_tone_freq, tone_duration);
        digitalWrite(REWARD_VALVE_PIN,HIGH);
        log_code(REWARD_VALVE_ON);
        reward_valve_closed = false;
        reward_valve_dur = ul2time(reward_magnitude);
        reward_valve_open_time = now();
        deliver_reward = false;
    }

    if (reward_valve_closed == false && now() - reward_valve_open_time > reward_valve_dur) {
        digitalWrite(REWARD_VALVE_PIN,LOW);
        log_code(REWARD_VALVE_OFF);
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

*/

void state_entry_common(){
    // common tasks to do at state entry for all states
    last_state = current_state;
    state_entry = now();
    log_code(current_state);
}

void finite_state_machine() {
    // the main FSM
    switch (current_state) {

        case INI_STATE:
            current_state = ITI_STATE;
            break;
             
        case REWARD_AVAILABLE_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                reward_collected = false;
                log_code(REWARD_AVAILABLE_EVENT);
                tone_controller.play(reward_cue_freq, tone_duration);
            }

            // update
            if (last_state == current_state){
                // if lick_in and reward not yet collected, deliver it
                if (lick_in == true and reward_collected == false){
                    log_code(REWARD_COLLECTED_EVENT);
                    deliver_reward = true;
                    reward_collected = true;
                }
            }

            // exit condition
            if (now() - state_entry > reward_available_dur || reward_collected == true) {
                // transit to ITI after certain time (reward not collected) or after reward collection
                if (reward_collected == false) {
                    log_code(REWARD_MISSED_EVENT);
                }
                current_state = ITI_STATE;
            }
            break;
            
        case ITI_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                // calculate length of this ITI
                this_ITI_dur = random(ITI_dur_min, ITI_dur_max);
                log_msg(String("this_ITI_dur "+String(this_ITI_dur)));
            }

            // update
            if (last_state == current_state){
                // nothing
            }

            // exit condition
            if (now() - state_entry > this_ITI_dur) {
                // ITI has to be long enough to not make the mice lick themselves into a timeout
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
    delay(5000);
}

void loop() {
    if (run == true){
        // execute state machine(s)
        finite_state_machine();
    }
    // sample sensors
    read_lick();

    // valve controllers
    RewardValveController();

    // serial communication
    getSerialData();
    processSerialData();
}
#include <Arduino.h>
#include <string.h>
#include <Tone.h>

#include <event_codes.h> // <>?
#include "interface.cpp"
#include "pin_map.h"

/*
########  ########  ######  ##          ###    ########     ###    ######## ####  #######  ##    ##  ######
##     ## ##       ##    ## ##         ## ##   ##     ##   ## ##      ##     ##  ##     ## ###   ## ##    ##
##     ## ##       ##       ##        ##   ##  ##     ##  ##   ##     ##     ##  ##     ## ####  ## ##
##     ## ######   ##       ##       ##     ## ########  ##     ##    ##     ##  ##     ## ## ## ##  ######
##     ## ##       ##       ##       ######### ##   ##   #########    ##     ##  ##     ## ##  ####       ##
##     ## ##       ##    ## ##       ##     ## ##    ##  ##     ##    ##     ##  ##     ## ##   ### ##    ##
########  ########  ######  ######## ##     ## ##     ## ##     ##    ##    ####  #######  ##    ##  ######
*/

// int current_state = INI_STATE; // starting at this, aleady declared in interface.cpp
int last_state = -1; // whatever other state
unsigned long max_future = 4294967295; // 2**32 -1
unsigned long state_entry = max_future;
unsigned long this_ITI_dur;

// flow control flags
bool lick_in = false;

// speaker
Tone tone_controller;
unsigned long tone_duration = 100;

/*
##        #######   ######    ######   #### ##    ##  ######
##       ##     ## ##    ##  ##    ##   ##  ###   ## ##    ##
##       ##     ## ##        ##         ##  ####  ## ##
##       ##     ## ##   #### ##   ####  ##  ## ## ## ##   ####
##       ##     ## ##    ##  ##    ##   ##  ##  #### ##    ##
##       ##     ## ##    ##  ##    ##   ##  ##   ### ##    ##
########  #######   ######    ######   #### ##    ##  ######
*/

float now(){
    return (unsigned long) micros() / 1000;
}

void log_code(int code){
    Serial.println(String(code) + '\t' + String(micros()/1000.0));
}

void log_msg(String Message){
    Serial.println("<MSG " + Message + " "+String(micros()/1000.0)+">");
}

void log_var(String name, String value){
    Serial.println("<VAR " + name + " " + value + " "+String(micros()/1000.0)+">");
}

/*
 ######  ######## ##    ##  ######   #######  ########   ######
##    ## ##       ###   ## ##    ## ##     ## ##     ## ##    ##
##       ##       ####  ## ##       ##     ## ##     ## ##
 ######  ######   ## ## ##  ######  ##     ## ########   ######
      ## ##       ##  ####       ## ##     ## ##   ##         ##
##    ## ##       ##   ### ##    ## ##     ## ##    ##  ##    ##
 ######  ######## ##    ##  ######   #######  ##     ##  ######
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
 ######  ##     ## ########  ######
##    ## ##     ## ##       ##    ##
##       ##     ## ##       ##
##       ##     ## ######    ######
##       ##     ## ##             ##
##    ## ##     ## ##       ##    ##
 ######   #######  ########  ######
*/

bool error_sound_off = true;
bool play_error_sound = false;
unsigned long error_sound_on_time = max_future;

void correct_choice_cue(){
    // beep
    tone_controller.play(correct_choice_cue_freq, tone_duration);
}

void incorrect_choice_cue(){
    // beep
    tone_controller.play(incorrect_choice_cue_freq, tone_duration);
}

/*
##     ##    ###    ##       ##     ## ########
##     ##   ## ##   ##       ##     ## ##
##     ##  ##   ##  ##       ##     ## ##
##     ## ##     ## ##       ##     ## ######
 ##   ##  ######### ##        ##   ##  ##
  ## ##   ##     ## ##         ## ##   ##
   ###    ##     ## ########    ###    ########
*/

float ul2time(unsigned long reward_volume){
    return (float) reward_volume / valve_ul_ms;
}

bool reward_valve_closed = true;
// bool deliver_reward = false; // already forward declared in interface.cpp
unsigned long reward_valve_open_time = max_future;
float reward_valve_dur;

void RewardValveController(){
    // a self terminating digital pin switch
    // flipped by setting deliver_reward to true somewhere in the FSM

    if (reward_valve_closed == true && deliver_reward == true) {
        digitalWrite(REWARD_VALVE_PIN, HIGH);
        log_code(REWARD_VALVE_ON);
        reward_valve_closed = false;
        reward_valve_dur = ul2time(reward_magnitude);
        reward_valve_open_time = now();
        deliver_reward = false;
            
        // present cue? (this is necessary for keeping the keyboard reward functionality)
        if (present_reward_cue == true){
            correct_choice_cue();
            present_reward_cue = false;
        }
    }

    if (reward_valve_closed == false && now() - reward_valve_open_time > reward_valve_dur) {
        digitalWrite(REWARD_VALVE_PIN, LOW);
        log_code(REWARD_VALVE_OFF);
        reward_valve_closed = true;
    }
}

/*
########  ######  ##     ##
##       ##    ## ###   ###
##       ##       #### ####
######    ######  ## ### ##
##             ## ##     ##
##       ##    ## ##     ##
##        ######  ##     ##
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
                log_code(REWARD_AVAILABLE_EVENT);
                
                // play the sound
                correct_choice_cue();
            }

            // update
            if (last_state == current_state){
                if (lick_in == true){
                    correct_choice_cue();
                    // deliver reward?
                    float r = random(0,1000) / 1000.0;
                    if (p_reward > r){
                        log_code(REWARD_COLLECTED_EVENT);
                        deliver_reward = true;
                        current_state = ITI_STATE;
                        break;
                    }
                    else {
                        log_code(REWARD_OMITTED_EVENT);
                        current_state = ITI_STATE;
                        break;
                    }
                }
            }

            // exit condition
            if (now() - state_entry > reward_available_dur) {
                // transit to ITI after certain time
                log_code(REWARD_MISSED_EVENT);
                current_state = ITI_STATE;
                break; // not necessary
            }
            break; 

        case NO_REWARD_AVAILABLE_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                log_code(NO_REWARD_AVAILABLE_EVENT);
                
                // play the sound
                incorrect_choice_cue();
            }

            // update
            if (last_state == current_state){
                
            }

            // exit condition
            if (now() - state_entry > reward_available_dur) {
                // transit to ITI after certain time
                current_state = ITI_STATE;
                break; // not necessary
            }
            break; 
            
        case ITI_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                this_ITI_dur = random(ITI_dur_min, ITI_dur_max);
            }

            // update
            if (last_state == current_state){

            }

            // exit condition
            if (now() - state_entry > this_ITI_dur) {
                // determine which cue is next
                float r = random(0,1000) / 1000.0;
                if (p_rewarded_cue > r){
                    current_state = REWARD_AVAILABLE_STATE;
                    break;
                }
                else {
                    current_state = NO_REWARD_AVAILABLE_STATE;
                    break;
                }
            }
            break;
    }
}

/*
##     ##    ###    #### ##    ##
###   ###   ## ##    ##  ###   ##
#### ####  ##   ##   ##  ####  ##
## ### ## ##     ##  ##  ## ## ##
##     ## #########  ##  ##  ####
##     ## ##     ##  ##  ##   ###
##     ## ##     ## #### ##    ##
*/

void setup() {
    delay(100);
    Serial.begin(115200); // main serial communication with computer
    Serial1.begin(115200); // serial line for receiving (processed) loadcell X,Y

    pinMode(SPEAKER_PIN,OUTPUT);
    tone_controller.begin(SPEAKER_PIN);

    Serial.println("<Arduino is ready to receive commands>");
    delay(1000);
}

void loop() {
    if (run == true){
        // execute state machine(s)
        finite_state_machine();
    }
    // Controllers
    RewardValveController();

    // sample sensors
    read_lick();

    // serial communication with main PC
    getSerialData();
    processSerialData();

}
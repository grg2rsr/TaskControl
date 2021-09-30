#include <Arduino.h>
#include <Tone.h>
#include <event_codes.h> // <>?
#include "interface.cpp"
#include "pin_map.h"
#include "logging.cpp"

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
unsigned long t_state_entry = max_future;
unsigned long this_ITI_dur;

// for random
float r;


/*
 ######  ######## ##    ##  ######   #######  ########   ######
##    ## ##       ###   ## ##    ## ##     ## ##     ## ##    ##
##       ##       ####  ## ##       ##     ## ##     ## ##
 ######  ######   ## ## ##  ######  ##     ## ########   ######
      ## ##       ##  ####       ## ##     ## ##   ##         ##
##    ## ##       ##   ### ##    ## ##     ## ##    ##  ##    ##
 ######  ######## ##    ##  ######   #######  ##     ##  ######
*/

bool reward_available = false;

bool is_reaching = false;
bool reach_in = false;
bool is_grasping = false;

unsigned long t_last_reach_on = max_future;
unsigned long t_last_reach_off = max_future;

void read_reaches(){
    // left
    reach_in = digitalRead(REACH_PIN);
    // reach on
    if (is_reaching == false && reach_in == true){
        log_code(REACH_ON);
        is_reaching = true;
        t_last_reach_on = now();
    }

    // reach off
    if (is_reaching == true && reach_in == false){
        t_last_reach_off = now();
        log_code(REACH_OFF);
        is_reaching = false;

        if (is_grasping){
            log_code(GRASP_OFF);
            is_grasping = false;
        }
    }

    // grasp
    if (is_reaching && now() - t_last_reach_on > min_grasp_dur && is_grasping == false){
        log_code(GRASP_ON);
        is_grasping = true;
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

// speaker
Tone tone_controller;

// buzzer
// Tone buzz_controller;

void reward_available_cue(){
    tone_controller.play(tone_freq, tone_dur);
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

unsigned long ul2time(float reward_volume, float valve_ul_ms){
    return (unsigned long) reward_volume / valve_ul_ms;
}

bool reward_valve_is_open = false;
// bool deliver_reward = false; // already forward declared in interface.cpp
unsigned long t_reward_valve_open = max_future;
unsigned long reward_valve_dur;

void open_reward_valve(){
    tone_controller.play(tone_freq, tone_dur);
    digitalWrite(REWARD_VALVE_PIN, HIGH);
    log_code(REWARD_VALVE_ON);
    reward_valve_is_open = true;
    reward_valve_dur = ul2time(reward_magnitude, valve_ul_ms);
    t_reward_valve_open = now();
    deliver_reward = false;
}

void close_reward_valve(){
    digitalWrite(REWARD_VALVE_PIN, LOW);
    log_code(REWARD_VALVE_OFF);
    reward_valve_is_open = false;
}

void reward_valve_controller(){
    // a self terminating digital pin switch with a delay between cue and reward
    // flipped by setting deliver_reward to true somewhere in the FSM
      
    if (reward_valve_is_open == false && deliver_reward == true) {
        open_reward_valve();
    }

    if (reward_valve_is_open == true && now() - t_reward_valve_open > reward_valve_dur) {
        close_reward_valve();
    }
}

/*
 
  ######  ##    ## ##    ##  ######  
 ##    ##  ##  ##  ###   ## ##    ## 
 ##         ####   ####  ## ##       
  ######     ##    ## ## ## ##       
       ##    ##    ##  #### ##       
 ##    ##    ##    ##   ### ##    ## 
  ######     ##    ##    ##  ######  
 
*/

// bool switch_sync_pin = false;
// bool sync_pin_is_on = false;
// unsigned long t_last_sync_pin_on = max_future;
// unsigned long sync_pulse_dur = 100;

// void sync_pin_controller(){
//     // switch on
//     if (switch_sync_pin == true){
//         digitalWrite(CAM_SYNC_PIN, HIGH);
//         digitalWrite(LC_SYNC_PIN, HIGH);
//         sync_pin_is_on = true;
//         switch_sync_pin = false;
//         t_last_sync_pin_on = now();
//     }
//     // switch off
//     if (sync_pin_is_on == true && now() - t_last_sync_pin_on > sync_pulse_dur){
//         digitalWrite(CAM_SYNC_PIN, LOW);
//         digitalWrite(LC_SYNC_PIN, LOW);
//         sync_pin_is_on = false;
//     }
// }



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
    t_state_entry = now();
    log_code(current_state);
}

void finite_state_machine() {
    // the main FSM
    switch (current_state) {

        case INI_STATE:
            current_state = ITI_STATE;
            break;

        case ITI_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                this_ITI_dur = (unsigned long) random(ITI_dur_min, ITI_dur_max);
            }

            // update
            if (last_state == current_state){

            }

            // exit condition
            if (now() - t_state_entry > this_ITI_dur && now() - t_last_reach_off > reach_block_dur && is_grasping == false) {
                current_state = REWARD_AVAILABLE_STATE;
                break;
            }
            break;

        case REWARD_AVAILABLE_STATE:
            // state entry
            if (current_state != last_state){
                if (cue_reward_available){
                    reward_available_cue();
                }
                state_entry_common();
                // switch_sync_pin = true;
                // deliver_reward = true;
            }

            // update
            if (last_state == current_state){

            }

            // exit condition
            if (autodeliver_rewards == false){
                if (is_grasping) {
                    // grasping
                    log_code(REWARD_COLLECTED_EVENT);
                    deliver_reward = true;
                    current_state = ITI_STATE;
                    break;
                }
                if (now() - t_state_entry > reward_available_dur){
                    // reward missed
                    log_code(REWARD_MISSED_EVENT);
                    current_state = ITI_STATE;
                    break;
                }
            }
            else{
                log_code(REWARD_AUTODELIVERED_EVENT);
                deliver_reward = true;
                current_state = ITI_STATE;
                break;
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
    delay(1000);
    Serial.begin(115200); // main serial communication with computer

    // TTL com with firmata
    pinMode(REACH_PIN, INPUT);
    
    // TTL COM w camera
    // pinMode(CAM_SYNC_PIN,OUTPUT);
    // pinMode(LC_SYNC_PIN,OUTPUT);

     // ini speakers and buzzers
    pinMode(SPEAKER_PIN, OUTPUT);
    tone_controller.begin(SPEAKER_PIN);
    // pinMode(BUZZER_PIN, OUTPUT);
    // buzz_controller.begin(BUZZER_PIN);

    Serial.println("<Arduino is ready to receive commands>");
    delay(1000);
}

void loop() {
    if (run == true){
        // execute state machine(s)
        finite_state_machine();
    }
    // Controllers
    reward_valve_controller();

    // sample sensors
    read_reaches();

    // serial communication with main PC
    getSerialData();
    processSerialData();

    // non-blocking cam sync pin
    // sync_pin_controller();

}
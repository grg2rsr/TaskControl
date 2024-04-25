#include <Arduino.h>
#include <event_codes.h> // <>?
#include "pin_map.h"
#include "interface.cpp"
#include "logging.cpp"
#include <time.h>

// int current_state = INI_STATE; // starting at this, aleady declared in interface.cpp
int last_state = -1; // whatever other state
unsigned long max_future = 4294967295; // 2**32 -1
unsigned long t_state_entry = max_future;

// programmatic vars
unsigned long this_ITI_dur;
unsigned long this_delay_dur;

/*
 ######  ######## ##    ##  ######   #######  ########   ######
##    ## ##       ###   ## ##    ## ##     ## ##     ## ##    ##
##       ##       ####  ## ##       ##     ## ##     ## ##
 ######  ######   ## ## ##  ######  ##     ## ########   ######
      ## ##       ##  ####       ## ##     ## ##   ##         ##
##    ## ##       ##   ### ##    ## ##     ## ##    ##  ##    ##
 ######  ######## ##    ##  ######   #######  ##     ##  ######
*/

bool poke_in = false;
bool is_pokeing = false;
unsigned long t_last_poke_in = max_future;
unsigned long t_last_poke_out = max_future;

void read_poke(){
    // left
    poke_in = digitalRead(POKE_PIN);
    // lick on
    if (is_pokeing == false && poke_in == true){
        log_code(POKE_IN);
        t_last_poke_in = now();
        is_pokeing = true;
    }

    // poke out
    if (is_pokeing == true && poke_in == false){
        log_code(POKE_OUT);
        t_last_poke_out = now();
        is_pokeing = false;
    }
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

unsigned long ul2time(float reward_volume){
    return (unsigned long) reward_volume / valve_ul_ms;
}

bool reward_valve_is_closed = true;
// bool deliver_reward = false; // requires to be forward declared in interface.cpp
unsigned long t_reward_valve_open = max_future;
unsigned long reward_valve_dur;

void reward_valve_controller(){
    // a self terminating digital pin switch
    // flipped by setting deliver_reward to true somewhere in the FSM
    
    if (reward_valve_is_closed == true && deliver_reward == true) {
        digitalWrite(REWARD_VALVE_PIN, HIGH);
        log_code(REWARD_VALVE_ON);
        reward_valve_is_closed = false;
        reward_valve_dur = ul2time(reward_magnitude);
        t_reward_valve_open = now();
        deliver_reward = false;
    }

    if (reward_valve_is_closed == false && now() - t_reward_valve_open > reward_valve_dur) {
        digitalWrite(REWARD_VALVE_PIN, LOW);
        log_code(REWARD_VALVE_OFF);
        reward_valve_is_closed = true;
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

bool switch_sync_pin = false;
bool sync_pin_is_on = false;
unsigned long t_last_sync_pin_on = max_future;
unsigned long sync_pulse_dur = 100;

void sync_pin_controller(){
    // switch on
    if (switch_sync_pin == true){
        digitalWrite(CAM_SYNC_PIN, HIGH);
        sync_pin_is_on = true;
        switch_sync_pin = false;
        t_last_sync_pin_on = now();
    }

    // switch off
    if (sync_pin_is_on == true && now() - t_last_sync_pin_on > sync_pulse_dur){
        digitalWrite(CAM_SYNC_PIN, LOW);
        sync_pin_is_on = false;
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
                this_ITI_dur = random(ITI_min_dur, ITI_max_dur);
            }

            // the update loop
            // if (current_state == last_state){
            // }

            // exit
            if (now() - t_state_entry > this_ITI_dur && is_pokeing == false){
                current_state = TRIAL_AVAILABLE_STATE;
                break;
            }
            
            break;
        
        case TRIAL_AVAILABLE_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                switch_sync_pin = true;
                digitalWrite(POKE_LED_PIN, HIGH);
            }

            // the update loop
            // if (current_state == last_state){
            // }

            // exit
            if (is_pokeing == true){
                current_state = DELAY_STATE;
                break;
            }
            
            break;

        case DELAY_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                this_delay_dur = random(delay_min_dur, delay_max_dur);
            }

            // the update loop
            if (current_state == last_state){
                if (is_pokeing == false){
                    log_code(BROKEN_FIXATION_EVENT);
                    current_state = TIMEOUT_STATE;
                    break;
                }
            }

            // exit
            if (is_pokeing == true && now() - t_last_poke_in > this_delay_dur){
                deliver_reward = true;
                current_state = ITI_STATE;
                digitalWrite(POKE_LED_PIN, LOW);
                break;
            }
            
            break;

        case TIMEOUT_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
            }

            // the update loop
            // if (current_state == last_state){
            // }

            // exit
            if (now() - t_state_entry > timeout_dur){
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
    delay(100);
    Serial.begin(115200); // main serial communication with computer
    
    // in pins
    pinMode(POKE_PIN, INPUT);

    // out pins
    pinMode(LED_PIN, OUTPUT);
    pinMode(POKE_LED_PIN, OUTPUT);
    pinMode(REWARD_VALVE_PIN, OUTPUT);
    pinMode(CAM_SYNC_PIN, OUTPUT);

    Serial.println("<Arduino is ready to receive commands>");
    Serial.flush();
    delay(100);
}

void loop() {
    if (run == true){
        // execute state machine(s)
        finite_state_machine();
    }
    // Controllers
    reward_valve_controller();
    sync_pin_controller();
    
    // sample sensors
    read_poke();

    // serial communication with main PC
    getSerialData();
    processSerialData();
}

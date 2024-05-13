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

unsigned long r;
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
            current_state = LED_OFF_STATE;
            break;

        case LED_OFF_STATE:
            // state entry
            if (current_state != last_state){
                digitalWrite(LED_PIN, LOW);
                state_entry_common();
                r = random(0,1000);
                log_ulong("r", r);
            }

            // the update loop
            if (current_state == last_state){
                
            }

            // exit
            if (now() - t_state_entry > LED_OFF_dur){
                current_state = LED_ON_STATE;
                break;
            }
            
            break;
        
        case LED_ON_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                digitalWrite(LED_PIN, HIGH);
            }

            // the update loop
            if (current_state == last_state){

            }

            // exit
            if (now() - t_state_entry > LED_ON_dur){
                current_state = LED_OFF_STATE;
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
    
    // out pins
    pinMode(LED_PIN, OUTPUT);
    
    Serial.println("<Arduino is ready to receive commands>");
    delay(1000);
}

void loop() {
    if (run == true){
        // execute state machine(s)
        finite_state_machine();
    }

    // serial communication with main PC
    getSerialData();
    processSerialData();
    
}

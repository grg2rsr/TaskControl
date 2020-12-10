#include <Arduino.h>

#include <event_codes.h> // <>?
#include "interface.cpp"
#include "raw_interface.cpp"
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
unsigned long t_state_entry = max_future;

/*
##        #######   ######    ######   #### ##    ##  ######
##       ##     ## ##    ##  ##    ##   ##  ###   ## ##    ##
##       ##     ## ##        ##         ##  ####  ## ##
##       ##     ## ##   #### ##   ####  ##  ## ## ## ##   ####
##       ##     ## ##    ##  ##    ##   ##  ##  #### ##    ##
##       ##     ## ##    ##  ##    ##   ##  ##   ### ##    ##
########  #######   ######    ######   #### ##    ##  ######
*/


// time
unsigned long now(){
    return millis();
}

// VAR reporters
char s[128]; // message buffer

void log_bool(const char name[], bool value){
    if (value==true){
        snprintf(s, sizeof(s), "<VAR %s %s %lu>", name, "true", now());
    }
    else {
        snprintf(s, sizeof(s), "<VAR %s %s %lu>", name, "false", now());
    }
    Serial.println(s);
}

void log_int(const char name[], int value){
    snprintf(s, sizeof(s), "<VAR %s %i %lu>", name, value, now());
    Serial.println(s);
}

// void log_long(const char name[], long value){
//     snprintf(s, sizeof(s), "<VAR %s %u %lu>", name, value, now());
//     Serial.println(s);
// }

void log_ulong(const char name[], unsigned long value){
    snprintf(s, sizeof(s), "<VAR %s %lu %lu>", name, value, now());
    Serial.println(s);
}

void log_float(const char name[], float value){
    snprintf(s, sizeof(s), "<VAR %s ", name);
    Serial.print(s);
    Serial.print(value);
    snprintf(s, sizeof(s), " %lu>", now());
    Serial.println(s);
}

// specific

void log_code(int code){
    // Serial.println(String(code) + '\t' + String(now()));
    snprintf(s, sizeof(s), "%u\t%lu", code, now());
    Serial.println(s);
}

void log_msg(const char Message[]){
    // Serial.println("<MSG " + Message + " "+String(now())+">");
    snprintf(s, sizeof(s), "<MSG %s %lu>", Message, now());
    Serial.println(s);
}

void send_sync_pulse(){
    // sync w load cell
    digitalWrite(LC_SYNC_PIN,HIGH);
    delay(1); // 1 ms unavoidable blindness - TODO delayMicroseconds - test!
    digitalWrite(LC_SYNC_PIN,LOW);
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

bool lick_in = false;
bool lick = false;
unsigned long t_last_lick_in = max_future;

void read_lick(){
    lick = digitalRead(LICK_PIN);
    if (lick_in == false && lick == true){
        log_code(LICK_ON);
        lick_in = true;
        t_last_lick_in = now();
    }
    if (lick_in == true && lick == false){
        log_code(LICK_OFF);
        lick_in = false;
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

        case TRIAL_ENTRY_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                log_code(TRIAL_ENTRY_EVENT);

                // sync at trial entry
                send_sync_pulse();
            }
            
            // exit condition 
            if (now() - t_state_entry > Trial_dur) {
                current_state = ITI_STATE;
            }
            break;

    

        case ITI_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
            }

            // exit condition
            if (now() - t_state_entry > ITI_dur) {
                current_state = TRIAL_ENTRY_STATE;
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
    Serial.println("<Arduino is ready to receive commands>");
    delay(1000);

}

void loop() {
    if (run == true){
        // execute state machine(s)
        finite_state_machine();
    }

    // sample sensors
    read_lick();

    // serial communication with main PC
    getSerialData();
    processSerialData();

    // raw data via serial - the loadcell data - process only if not controlled
    getRawData();
    
    // process loadcell data
    // process_loadcell();

}
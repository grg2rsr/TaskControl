#include <Arduino.h>
#include <string.h>

#include <event_codes.h> // <>?
#include "logging.cpp"
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
int last_state = RUN_STATE; // whatever other state
unsigned long max_future = 4294967295; // 2**32 -1
unsigned long state_entry = max_future;
int pin;

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
    // log_current_state();
}

void finite_state_machine() {
    // the main FSM
    switch (current_state) {

        case INI_STATE:
            if (current_state != last_state){
                state_entry_common();
                current_state = RUN_STATE;
            }
            break;

        case RUN_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();

                if (use_left == true){
                    pin = REWARD_VALVE_LEFT_PIN;
                }
                else {
                    pin = REWARD_VALVE_RIGHT_PIN;
                }

                // opening the valve 
                for (unsigned int i = 0; i < reward_valve_switches; i++) {
                    digitalWrite(pin,HIGH);
                    // log_code(REWARD_VALVE_ON);
                    delay(reward_valve_open_dur);
                    digitalWrite(pin,LOW);
                    // log_code(REWARD_VALVE_OFF);
                    delay(reward_valve_closed_dur);
                }

                current_state = DONE_STATE;
            }
            break;

        case DONE_STATE:
            if (current_state != last_state){
                state_entry_common();
                current_state = INI_STATE;
                run = false;
                Serial.println("<Arduino is halted>");
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
    Serial.println("<Arduino is ready to receive commands>");
    delay(10);
}

void loop() {
    if (run == true){
        // execute state machine(s)
        finite_state_machine();
    }

    // serial communication
    getSerialData();
    processSerialData();
}
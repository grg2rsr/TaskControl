#include <Arduino.h>
#include <string.h>

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

// int current_state = LED_ON_STATE; // starting at this, aleady declared in interface.cpp
int last_state = LED_OFF_STATE; // whatever other state
unsigned long max_future = 4294967295; // 2**32 -1
unsigned long state_entry = max_future;


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
    state_entry = micros();
    log_current_state();
}

void finite_state_machine() {
    // the main FSM
    switch (current_state) {

        case INI_STATE:
            break;

        case LED_ON_STATE:
            //state entry
            if (current_state != last_state){
                state_entry_common();
                digitalWrite(LED_PIN,HIGH);
            }

            // update
            if (last_state == current_state){
            
            }

            // exit condition
            if (micros() - state_entry > LED_ON_TIME) {
                current_state = LED_OFF_STATE;
            }
            break;

        case LED_OFF_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                digitalWrite(LED_PIN,LOW);
            }

            // update
            if (last_state == current_state){

            }

            // exit condition
            if (micros() - state_entry > LED_OFF_TIME) {
                current_state = LED_ON_STATE;

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
    pinMode(LED_PIN,OUTPUT);
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
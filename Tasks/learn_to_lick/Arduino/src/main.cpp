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
int last_state = FIXATE_STATE; // whatever other state
unsigned long max_future = 4294967295; // 2**32 -1
unsigned long state_entry = max_future;
unsigned long this_ITI_dur = ITI_dur;

// flow control flags
bool lick_in = false;
bool reward_collected = false;

// speakers
Tone reward_tone_controller;
Tone punish_tone_controller;
unsigned long tone_duration = 200;

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
        reward_tone_controller.play(reward_tone_freq, tone_duration);
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
    // exit actions
    .
    .
    .
    
    if (req_state != current_state && state_change_requested == True) {
        // forced transition
        current_state = req_state;
        state_change_requested = False;
    }
}
then, state change is requested by 
<SET req_state state>
<SET state_change_requested true>
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

        case TRIAL_AVAILABLE_STATE:
            // state entry
            // "autostart"
            if (current_state != last_state){
                state_entry_common();
                // reward_tone_controller.play(trial_avail_cue_freq, tone_duration);
            }

            // update
            if (last_state == current_state){
                // nothing
            }
            
            // exit condition
            if (true) {
                log_code(TRIAL_ENTRY_EVENT); // just for plotting purposes (align on this)
                // draw next trial
                if (random() < reward_prob){
                    current_state = REWARD_AVAILABLE_STATE;
                }
                else {
                    current_state = NO_REWARD_AVAILABLE_STATE;
                }
            }
            break;
             
        case NO_REWARD_AVAILABLE_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                log_code(NO_REWARD_AVAILABLE_EVENT);
                punish_tone_controller.play(punish_cue_freq, tone_duration);
            }

            // update
            if (last_state == current_state){
                // nothing
            }

            // exit condition
            if (true){
                // auto exit
                current_state = ITI_STATE;
            }
            break;

        case REWARD_AVAILABLE_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                reward_collected = false;
                log_code(REWARD_AVAILABLE_EVENT);
                reward_tone_controller.play(reward_cue_freq, tone_duration);
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
            }

            // update
            if (last_state == current_state){
                // nothing
            }

            // exit condition
            if (now() - state_entry > ITI_dur) {
                // ITI has to be long enough to not make the mice lick themselves into a timeout
                current_state = TRIAL_AVAILABLE_STATE;
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
    reward_tone_controller.begin(REWARD_SPEAKER_PIN);
    punish_tone_controller.begin(PUNISH_SPEAKER_PIN);
    Serial.println("<Arduino is ready to receive commands>");
    delay(5000);
}

bool toggle = false;

void loop() {
    if (run == true){
        // execute state machine(s)
        finite_state_machine();
    }
    // valve controllers
    RewardValveController();

    // sample sensors
    read_lick();

    // serial communication
    getSerialData();
    processSerialData();

    // punish
    if (punish == true){
        punish_tone_controller.play(punish_tone_freq, tone_duration);
        punish = false;
    }

    // for clocking execution speed
    // if (toggle == false){
    //     digitalWrite(7,HIGH);
    //     toggle = true;
    // }
    // else {
    //     digitalWrite(7,LOW);
    //     toggle = false;
    // }
}
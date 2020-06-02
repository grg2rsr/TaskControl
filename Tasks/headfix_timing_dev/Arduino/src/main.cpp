#include <Arduino.h>
#include <string.h>
#include <Tone.h>

#include <event_codes.h> // <>?
#include "interface.cpp"
#include "raw_interface.cpp"
#include "pin_map.h"

/*
 _______   _______   ______  __          ___      .______          ___   .___________. __    ______   .__   __.      _______.
|       \ |   ____| /      ||  |        /   \     |   _  \        /   \  |           ||  |  /  __  \  |  \ |  |     /       |
|  .--.  ||  |__   |  ,----'|  |       /  ^  \    |  |_)  |      /  ^  \ `---|  |----`|  | |  |  |  | |   \|  |    |   (----`
|  |  |  ||   __|  |  |     |  |      /  /_\  \   |      /      /  /_\  \    |  |     |  | |  |  |  | |  . `  |     \   \
|  '--'  ||  |____ |  `----.|  `----./  _____  \  |  |\  \----./  _____  \   |  |     |  | |  `--'  | |  |\   | .----)   |
|_______/ |_______| \______||_______/__/     \__\ | _| `._____/__/     \__\  |__|     |__|  \______/  |__| \__| |_______/

*/

// for checking loop speed
bool toggle = false;

// int current_state = INI_STATE; // starting at this, aleady declared in interface.cpp
int last_state = TIMEOUT_STATE; // whatever other state
unsigned long max_future = 4294967295; // 2**32 -1
unsigned long state_entry = max_future;

// flow control flags
bool lick_in = false;
bool reward_collected = false;

// speaker
Tone tone_controller;
unsigned long tone_duration = 50; 

// unexposed interval tones
int n_intervals = 6;
unsigned long tone_intervals[] = {400, 800, 1400, 1600, 2200, 2600}; // in ms, bc will be compared to now()
unsigned long interval_boundary = 1500;
unsigned long this_interval;

int ix; // trial index


// loadcell related
unsigned int zone; // 0=left, 1=center, 2=right

unsigned int left = 0;
unsigned int center = 1;
unsigned int right = 2;

unsigned int choice;
unsigned int correct_side;

bool left_short = true; // TODO expose or change to non-bool

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

void log_choice(){
    if (zone == right){
        log_code(CHOICE_RIGHT_EVENT);
    }
    if (zone == left){
        log_code(CHOICE_LEFT_EVENT);
    }
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

void process_loadcell() {
    // for now, just bins X into zones
    zone = center;
    
    if (X < X_left_thresh){
        zone = left;
    }

    if (X > X_right_thresh){
        zone = right;
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
// bool deliver_reward = false; // already forward declared in interface.cpp
unsigned long reward_valve_open_time = max_future;
float reward_valve_dur;

void RewardValveController(){
    // a self terminating digital pin switch
    // flipped by setting deliver_reward to true somewhere in the FSM
    if (reward_valve_closed == true && deliver_reward == true) {
        tone_controller.play(reward_tone_freq, tone_duration);
        digitalWrite(REWARD_VALVE_PIN, HIGH);
        log_code(REWARD_VALVE_ON);
        reward_valve_closed = false;
        reward_valve_dur = ul2time(reward_magnitude);
        reward_valve_open_time = now();
        deliver_reward = false;
    }

    if (reward_valve_closed == false && now() - reward_valve_open_time > reward_valve_dur) {
        digitalWrite(REWARD_VALVE_PIN, LOW);
        log_code(REWARD_VALVE_OFF);
        reward_valve_closed = true;
    }
}

/*
.___  ___.   ______   ____    ____  __  .__   __.   _______    ____    ____  ___      .______          _______.
|   \/   |  /  __  \  \   \  /   / |  | |  \ |  |  /  _____|   \   \  /   / /   \     |   _  \        /       |
|  \  /  | |  |  |  |  \   \/   /  |  | |   \|  | |  |  __      \   \/   / /  ^  \    |  |_)  |      |   (----`
|  |\/|  | |  |  |  |   \      /   |  | |  . `  | |  | |_ |      \      / /  /_\  \   |      /        \   \
|  |  |  | |  `--'  |    \    /    |  | |  |\   | |  |__| |       \    / /  _____  \  |  |\  \----.----)   |
|__|  |__|  \______/      \__/     |__| |__| \__|  \______|        \__/ /__/     \__\ | _| `._____|_______/


this is an entire topic in itself - let it rest for now and do random trials
*/

float p_interval[6] = {1,1,1,1,1,1};
float p_interval_cs[6];

// int[n_intervals] n_trials = [0,0,0,0,0,0];
// float[n_trials] n_trials_succ = [0,0,0,0,0,0];
// float[n_trials] succ_rate = [0,0,0,0,0,0];

void normalize_stim_probs(){
    // sum
    float p_sum = 0;
    for (int i = 0; i < n_intervals; i++){
        p_sum += p_interval[i];
    }

    // normalize
    for (int i = 0; i < n_intervals; i++){
        p_interval[i] = p_interval[i] / p_sum;
    }
}

void cumsum_stim_probs(){
    p_interval_cs[0] = 0.0;
    for (int i = 1; i < n_intervals; i++){
        p_interval_cs[i] = p_interval_cs[i-1] + p_interval[i-1];
    }
}

int get_interval_index(){
    normalize_stim_probs();
    cumsum_stim_probs();
    float r = random(1000) / 1000.0;
    // determine the corresponding bin
    for (int i = 0; i < n_intervals-1; i++){
        if (r > p_interval_cs[i] && r < p_interval_cs[i+1]){
            return i;
        }
    }
    return n_intervals-1; // return the last
}

// // adjust probabilities based on performance
// void update_stim_probs(){
//     for (int i = 0; i < (n_intervals/2); i++){
//         if (succ_rate[i] > 0.8){
//             p_interval[i+1] = constrain(p_interval[i+1] + 0.1, 0, 1);
//         }
//     }
//     for (int i = n_intervals-1; i > (n_intervals/2), i--){
//         if (succ_rate[i] > 0.8){
//             p_interval[i-1] = constrain(p_interval[i-1] - 0.1, 0, 1);
//         }
//     }
// }

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

        case TRIAL_AVAILABLE_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                // change this to a small LED?
                // tone_controller.play(trial_avail_cue_freq, tone_duration);
                Serial.println("<RET LOADCELL CURSOR_RESET>");
            }

            // update
            if (last_state == current_state){

            }
            
            // exit condition
            if (now() - state_entry > autostart_dur) {
                // currently "autostarts" after some time
                // for future: push/pull on manipulandum?
                current_state = PRESENT_INTERVAL_STATE;
            }
            break;

        case PRESENT_INTERVAL_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                log_code(TRIAL_ENTRY_EVENT);

                // draw stimulus from list of intervals at random
                // ix = random(0,n_intervals);
                
                // for future: weighted
                ix = get_interval_index();
                // n_trials[ix] += 1;
                // Serial.println(ix);

                this_interval = tone_intervals[ix];

                // report interval for this trial
                log_msg(String("this_interval "+String(this_interval)));

                // present first tone
                log_code(FIRST_TONE_EVENT);
                tone_controller.play(stim_tone_freq, tone_duration);
            }

            // update
            if (last_state == current_state){

            }
            
            // exit conditions
            if (now() - state_entry > this_interval || zone != center) {
            
                // premature choice
                if (zone != center) {
                    log_choice();
                    log_code(TRIAL_ABORTED_EVENT);
                    
                    // TODO punish cue?
                    tone_controller.play(punish_tone_freq, tone_duration);
                    current_state = TIMEOUT_STATE;
                }

                // interval has passed
                if (now() - state_entry > this_interval){
                    // play second tone
                    log_code(SECOND_TONE_EVENT);
                    tone_controller.play(stim_tone_freq, tone_duration);
                    current_state = CHOICE_STATE;
                }
            }
            break;        
        
        case CHOICE_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();

                // determine what would be a correct answer
                if (left_short == true){
                    if (this_interval < interval_boundary){
                        correct_side = left;
                    }
                    else {
                        correct_side = right;
                    }
                }
                else {
                    if (this_interval < interval_boundary){
                        correct_side = right;
                    }
                    else {
                        correct_side = left;
                    }
                }
                // for future:
                // choice availability could be cued also
            }

            // update
            if (last_state == current_state){
            
            }
            
            // exit conditions
            if (zone != center || now() - state_entry > choice_dur){
                // no report, timeout
                if (now() - state_entry > choice_dur){
                    log_code(CHOICE_MISSED_EVENT);
                    // TODO cues? play noise?
                    tone_controller.play(punish_tone_freq, tone_duration);
                    current_state = TIMEOUT_STATE;
                }
                
                // choice was made
                if (zone != center) {
                    log_choice();

                    // determine success
                    if (zone == correct_side){
                        // correct trial
                        log_code(CHOICE_CORRECT_EVENT);
                        current_state = REWARD_AVAILABLE_STATE;
                        
                    }
                    else {
                        // wrong trial
                        log_code(CHOICE_WRONG_EVENT);
                        current_state = ITI_STATE; // or timeout?
                        tone_controller.play(punish_tone_freq, tone_duration);
                    }
                }
            }
            break;        
        
        case REWARD_AVAILABLE_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                log_code(REWARD_AVAILABLE_EVENT);
                tone_controller.play(reward_cue_freq, tone_duration);
                reward_collected = false;
            }

            // update
            if (last_state == current_state){
                // if lick_in and reward not yet collected, deliver it
                if (lick_in == true and reward_collected == false){
                    log_code(REWARD_COLLECTED_EVENT);
                    deliver_reward = true;
                    reward_collected = true;

                    // update the correct trials and the rates
                    // TODO this could have div by 0 problems
                    // n_trials_succ[ix] =+ 1;
                    // for (int i; i < n_intervals; i++){
                    //     succ_rate[i] = n_trials_succ[i] / n_trials[i];
                    // }
                    // update_stim_probs();
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

        case TIMEOUT_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                // TODO turn off the ambient light
            }

            // update
            if (last_state == current_state){
                // state actions
            }

            // exit condition
            if (now() - state_entry > timeout_dur) {
                // after timeout, transit to trial available again
                current_state = TRIAL_AVAILABLE_STATE;
            }
            break;            

        case ITI_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
            }

            // update
            if (last_state == current_state){
                // state actions
            }

            // exit condition
            if (now() - state_entry > ITI_dur) {
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
    Serial.begin(115200); // main serial communication with computer
    Serial1.begin(115200); // serial line for receiving (processed) loadcell X,Y

    tone_controller.begin(SPEAKER_PIN);
    Serial.println("<Arduino is ready to receive commands>");
    delay(1000);
}

void loop() {
    if (run == true){
        // execute state machine(s)
        finite_state_machine();
    }
    // valve controllers
    RewardValveController();

    // sample sensors
    read_lick();

    // serial communication with main PC
    getSerialData();
    processSerialData();

    // raw data via serial - the loadcell data
    getRawData();
    processRawData();
    
    process_loadcell();

    // for clocking execution speed
    if (toggle == false){
        digitalWrite(LOOP_PIN, HIGH);
        toggle = true;
    }
    else {
        digitalWrite(LOOP_PIN, LOW);
        toggle = false;
    }
}
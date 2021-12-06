#include <Arduino.h>
#include <Tone.h>
#include <FastLED.h>

#include <event_codes.h> // <>?
#include "interface.cpp"
// #include "raw_interface.cpp"
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
unsigned long this_pause;
unsigned long this_kamin_block_protect_dur;

// for random
float r;

// int left = 4; // fwd declared now in the interface_template
// int right = 6; // fwd declared now in the interface_template

int choice;
// int correct_side; // fwd declared now in the interface_template

// laterality related 
int last_correct_side = left;
// int this_correct_side = right;

// fwd declare necessary
bool timing_trial = false;

// bias related
// float bias = 0.5; // exposed in interface_variables.h
int n_choices_left = 1;
int n_choices_right = 1;

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
bool reward_left_available = false;
bool reward_right_available = false;

// bool reach_left = false;
// bool reach_right = false;

bool touch_left = false;
bool touch_right = false;

bool is_touching = false;
bool is_touching_left = false;
bool is_touching_right = false;

unsigned long t_last_touch_on = max_future;
unsigned long t_last_touch_off = max_future;

// bool is_reaching = false;
// bool is_reaching_left = false;
// bool is_reaching_right = false;

bool is_grasping = false;
bool is_grasping_left = false;
bool is_grasping_right = false;

// unsigned long t_last_reach_on = max_future;
// unsigned long t_last_reach_off = max_future;

unsigned long t_last_trial_entry = max_future;

// fwd declarartions
void go_cue_left(); 
void go_cue_right();

void read_touches(){
    // left
    touch_left = digitalRead(TOUCH_LEFT_PIN);
    // touch on
    if (is_touching_left == false && touch_left == true){
        log_code(TOUCH_LEFT_ON);
        is_touching_left = true;
        t_last_touch_on = now();
    }

    // grasp
    if (is_touching_left && now() - t_last_touch_on > min_grasp_dur && is_grasping_left == false){
        log_code(GRASP_LEFT_ON);
        is_grasping_left = true;
    }

    // touch off
    if (is_touching_left == true && touch_left == false){
        log_code(TOUCH_LEFT_OFF);
        is_touching_left = false;
        t_last_touch_off = now();

        // reward collected
        if (reward_left_available == true){
            reward_left_available = false;
        }

        // grasp off
        if (is_grasping_left){
            log_code(GRASP_LEFT_OFF);
            is_grasping_left = false;
        }
    }

    // right 
    touch_right = digitalRead(TOUCH_RIGHT_PIN);
    // touch on
    if (is_touching_right == false && touch_right == true){
        log_code(TOUCH_RIGHT_ON);
        is_touching_right = true;
        t_last_touch_on = now();
    }

    // grasp on
    if (is_touching_right && now() - t_last_touch_on > min_grasp_dur && is_grasping_right == false){
        log_code(GRASP_RIGHT_ON);
        is_grasping_right = true;
    }

    // touch off
    if (is_touching_right == true && touch_right == false){
        log_code(TOUCH_RIGHT_OFF);
        is_touching_right = false;
        t_last_touch_off = now();

        // reward collected
        if (reward_right_available == true){
            reward_right_available = false;
        }

        // grasp off
        if (is_grasping_right){
            log_code(GRASP_RIGHT_OFF);
            is_grasping_right = false;
        }
    }

    is_touching = (is_touching_left || is_touching_right);
    is_grasping = (is_grasping_left || is_grasping_right);
    reward_available = (reward_left_available || reward_right_available);
}

// void read_reaches(){
//     // left
//     reach_left = digitalRead(REACH_LEFT_PIN);
//     // reach on
//     if (is_reaching_left == false && reach_left == true){
//         log_code(REACH_LEFT_ON);
//         is_reaching_left = true;
//         t_last_reach_on = now();
//     }

//     // grasp
//     if (is_reaching_left && now() - t_last_reach_on > min_grasp_dur && is_grasping_left == false){
//         log_code(GRASP_LEFT_ON);
//         is_grasping_left = true;
//     }

//     // reach off
//     if (is_reaching_left == true && reach_left == false){
//         log_code(REACH_LEFT_OFF);
//         is_reaching_left = false;
//         t_last_reach_off = now();

//         // reward collected
//         if (reward_left_available == true){
//             reward_left_available = false;
//         }

//         // grasp off
//         if (is_grasping_left){
//             log_code(GRASP_LEFT_OFF);
//             is_grasping_left = false;
//         }
//     }
//     // touch
//     touch_left = digitalRead(TOUCH_LEFT_PIN);
//     // touch on
//     if (is_touching_left == false && touch_left == true){
//         log_code(TOUCH_LEFT_ON);
//         is_touching_left = true;
//     }
//     // touch off
//     if (is_touching_left == true && touch_left == false){
//         log_code(TOUCH_LEFT_OFF);
//         is_touching_left = false;
//     }

//     // right 
//     reach_right = digitalRead(REACH_RIGHT_PIN);
//     // reach on
//     if (is_reaching_right == false && reach_right == true){
//         log_code(REACH_RIGHT_ON);
//         is_reaching_right = true;
//         t_last_reach_on = now();
//     }

//     // grasp on
//     if (is_reaching_right && now() - t_last_reach_on > min_grasp_dur && is_grasping_right == false){
//         log_code(GRASP_RIGHT_ON);
//         is_grasping_right = true;
//     }

//     // reach off
//     if (is_reaching_right == true && reach_right == false){
//         log_code(REACH_RIGHT_OFF);
//         is_reaching_right = false;
//         t_last_reach_off = now();

//         // reward collected
//         if (reward_right_available == true){
//             reward_right_available = false;
//         }

//         // grasp off
//         if (is_grasping_right){
//             log_code(GRASP_RIGHT_OFF);
//             is_grasping_right = false;
//         }
//     }

//     // touch
//     touch_right = digitalRead(TOUCH_RIGHT_PIN);
//     // touch on
//     if (is_touching_right == false && touch_right == true){
//         log_code(TOUCH_RIGHT_ON);
//         is_touching_right = true;
//     }
//     // touch off
//     if (is_touching_right == true && touch_right == false){
//         log_code(TOUCH_RIGHT_OFF);
//         is_touching_right = false;
//     }

//     is_reaching = (is_reaching_left || is_reaching_right);
//     is_grasping = (is_grasping_left || is_grasping_right);
//     reward_available = (reward_left_available || reward_right_available);
// }




/*
##       ######## ########
##       ##       ##     ##
##       ##       ##     ##
##       ######   ##     ##
##       ##       ##     ##
##       ##       ##     ##
######## ######## ########
*/

// LED strip related
#define NUM_LEDS 1 // num of LEDs in strip
CRGB leds[NUM_LEDS]; // Define the array of leds

// access functions
void lights_on(){
    if (LED_enabled){
        log_code(LED_ON);
        for (int i = 0; i < NUM_LEDS; i++){
            leds[i] = CHSV(led_hsv, 255, led_brightness);
        }
        FastLED.show();
    }
}

void lights_off(){
    if (LED_enabled){
        log_code(LED_OFF);
        for (int i = 0; i < NUM_LEDS; i++){
            leds[i] = CRGB::Black;
        }
        FastLED.show();
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


bool present_touch_cue_left = false;
bool touch_cue_left_is_on = false;
unsigned long t_last_touch_cue_left = max_future;

bool present_touch_cue_right = false;
bool touch_cue_right_is_on = false;
unsigned long t_last_touch_cue_right = max_future;

unsigned long touch_cue_dur = 2;

void touch_cue_controller(){

    // left
    // switch on
    if (present_touch_cue_left == true){
        digitalWrite(TOUCH_CUE_LEFT_PIN, HIGH);
        touch_cue_left_is_on = true;
        present_touch_cue_left = false;
        t_last_touch_cue_left = now();
    }

    // switch off at end
    if (now() - t_last_touch_cue_left > touch_cue_dur && touch_cue_left_is_on){
        digitalWrite(TOUCH_CUE_LEFT_PIN, LOW);
        touch_cue_left_is_on = false;
    }

    // right
    // switch on
    if (present_touch_cue_right == true){
        digitalWrite(TOUCH_CUE_RIGHT_PIN, HIGH);
        touch_cue_right_is_on = true;
        present_touch_cue_right = false;
        t_last_touch_cue_right = now();
    }

    // switch off at end
    if (now() - t_last_touch_cue_right > touch_cue_dur && touch_cue_right_is_on){
        digitalWrite(TOUCH_CUE_RIGHT_PIN, LOW);
        touch_cue_right_is_on = false;
    }
}


// bool switch_on = false;
// bool pin_is_on = false;
// unsigned long t_begin = max_future;
// unsigned long t_last_per_on = max_future;
// unsigned long t_last_per_off = max_future;
// unsigned long total_on_dur = 6;
// unsigned long on_dur = 2;
// unsigned long off_dur = 2;
// bool is_pulsing = false;

// void touch_cue_controller(){
//     // switch on
//     if (switch_on == true){
//         log_msg("running");
//         digitalWrite(PIN, HIGH);
//         pin_is_on = true;
//         switch_on = false;
//         is_pulsing = true;
//         t_begin = now();
//         t_last_per_on = now();
//     }

//     // write low
//     if (now() - t_last_per_on > on_dur && is_pulsing && pin_is_on){
//         digitalWrite(PIN, LOW);
//         log_msg("low");
//         pin_is_on = false;
//         t_last_per_off = now();
//     }

//     // write high
//     if (now() - t_last_per_off > off_dur && is_pulsing && !pin_is_on){
//         digitalWrite(PIN, HIGH);
//         log_msg("high");
//         pin_is_on = true;
//         t_last_per_on = now();
//     }

//     // switch off at end
//     if (now() - t_begin > total_on_dur && is_pulsing){
//         // make sure that is low at end
//         log_msg("done");
//         digitalWrite(PIN, LOW);
//         pin_is_on = false;
//         is_pulsing = false;
//     }
// }

// speaker
Tone tone_controller;

// buzzer
Tone buzz_controller;

void trial_available_cue(){
    lights_off();
}

void trial_entry_cue(){     
    buzz_controller.play(buzz_center_freq, trial_entry_buzz_dur);
}

// fwd declare necessary
unsigned long t_present_left_cue = max_future;
unsigned long t_present_right_cue = max_future;

void reward_left_cue(){
    // tone_controller_left.play(go_cue_freq, tone_dur);
    t_present_left_cue = now();
    present_touch_cue_left = true;
    if (timing_trial == false){
        buzz_controller.play(buzz_low_freq, buzz_dur);
    }
    else{
        buzz_controller.play(buzz_center_freq, buzz_dur);
    }
}

void reward_right_cue(){
    // tone_controller_right.play(go_cue_freq, tone_dur);
    t_present_right_cue = now();
    present_touch_cue_right = true;
    if (timing_trial == false){
        buzz_controller.play(buzz_high_freq, buzz_dur);
    }
    else{
        buzz_controller.play(buzz_center_freq, buzz_dur);
    }
}

void go_cue_left(){
    log_code(GO_CUE_LEFT_EVENT);
    if (left_short == 1){
        log_code(GO_CUE_SHORT_EVENT);
    }
    else{
        log_code(GO_CUE_LONG_EVENT);
    }
    reward_left_cue();
}

void go_cue_right(){
    log_code(GO_CUE_RIGHT_EVENT);
    if (left_short == 1){
        log_code(GO_CUE_LONG_EVENT);
    }
    else{
        log_code(GO_CUE_SHORT_EVENT);
    }
    reward_right_cue();
}
/*
adapted from  https://arduino.stackexchange.com/questions/6715/audio-frequency-white-noise-generation-using-arduino-mini-pro
*/

#define LFSR_INIT  0xfeedfaceUL
#define LFSR_MASK  ((unsigned long)( 1UL<<31 | 1UL <<15 | 1UL <<2 | 1UL <<1  ))

unsigned int generateNoise(){ 
  // See https://en.wikipedia.org/wiki/Linear_feedback_shift_register#Galois_LFSRs
   static unsigned long int lfsr = LFSR_INIT;
   if(lfsr & 1) { lfsr =  (lfsr >>1) ^ LFSR_MASK ; return(1);}
   else         { lfsr >>= 1;                      return(0);}
}

unsigned long error_cue_start = max_future;
unsigned long error_cue_dur = tone_dur * 1000; // to save instructions - work in micros
unsigned long lastClick = max_future;

void incorrect_choice_cue(){
    // white noise - blocking arduino for tone_dur
    error_cue_start = micros();
    lastClick = micros();
    while (micros() - error_cue_start < error_cue_dur){
        if ((micros() - lastClick) > 2 ) { // Changing this value changes the frequency.
            lastClick = micros();
            digitalWrite(SPEAKER_PIN, generateNoise());
        }
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

unsigned long ul2time(float reward_volume, float valve_ul_ms){
    return (unsigned long) reward_volume / valve_ul_ms;
}

// left
bool reward_valve_left_is_open = false;
// bool deliver_reward_left = false; // already forward declared in interface.cpp
unsigned long t_reward_valve_left_open = max_future;
unsigned long reward_valve_left_dur;

void open_left_reward_valve(){
    tone_controller.play(tone_freq, tone_dur);
    digitalWrite(REWARD_LEFT_VALVE_PIN, HIGH);
    log_code(REWARD_LEFT_VALVE_ON);
    reward_valve_left_is_open = true;
    reward_valve_left_dur = ul2time(reward_magnitude, valve_ul_ms_left);
    t_reward_valve_left_open = now();
    deliver_reward_left = false;
}

void close_left_reward_valve(){
    digitalWrite(REWARD_LEFT_VALVE_PIN, LOW);
    log_code(REWARD_LEFT_VALVE_OFF);
    reward_valve_left_is_open = false;
}

// right
bool reward_valve_right_is_open = false;
// bool deliver_reward_right = false; // already forward declared in interface.cpp
unsigned long t_reward_valve_right_open = max_future;
unsigned long reward_valve_right_dur;

void open_right_reward_valve(){
    tone_controller.play(tone_freq, tone_dur);
    digitalWrite(REWARD_RIGHT_VALVE_PIN, HIGH);
    log_code(REWARD_RIGHT_VALVE_ON);
    reward_valve_right_is_open = true;
    reward_valve_right_dur = ul2time(reward_magnitude, valve_ul_ms_right);
    t_reward_valve_right_open = now();
    deliver_reward_right = false;
}

void close_right_reward_valve(){
    digitalWrite(REWARD_RIGHT_VALVE_PIN, LOW);
    log_code(REWARD_RIGHT_VALVE_OFF);
    reward_valve_right_is_open = false;
}

void reward_valve_controller(){
    // a self terminating digital pin switch with a delay between cue and reward
    // flipped by setting deliver_reward to true somewhere in the FSM
    
    // left
    
    // present cue? (this is necessary for keeping the keyboard reward functionality)
    if (present_reward_left_cue == true){
        reward_left_cue();
        present_reward_left_cue = false;
    }

    if (reward_valve_left_is_open == false && deliver_reward_left == true) {
        if (autodeliver_rewards == 1){
            // kamin block time is up - autodeliver
            if (now() - t_present_left_cue > this_kamin_block_protect_dur){
                open_left_reward_valve();
            }
        }
        else {
            open_left_reward_valve();
        }
    }

    if (reward_valve_left_is_open == true && now() - t_reward_valve_left_open > reward_valve_left_dur) {
        close_left_reward_valve();
    }

    // right

    // present cue? (this is necessary for keeping the keyboard reward functionality)
    if (present_reward_right_cue == true){
        reward_right_cue();
        present_reward_right_cue = false;
    }

    if (reward_valve_right_is_open == false && deliver_reward_right == true) {
        if (autodeliver_rewards == 1){
            // kamin block time is up - autodeliver
            if (now() - t_present_right_cue > this_kamin_block_protect_dur){
                open_right_reward_valve();
            }
        }
        else{
            open_right_reward_valve();
        }
    }

    if (reward_valve_right_is_open == true && now() - t_reward_valve_right_open > reward_valve_right_dur) {
        close_right_reward_valve();
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
        digitalWrite(LC_SYNC_PIN, HIGH);
        sync_pin_is_on = true;
        switch_sync_pin = false;
        t_last_sync_pin_on = now();
    }
    // switch off
    if (sync_pin_is_on == true && now() - t_last_sync_pin_on > sync_pulse_dur){
        digitalWrite(CAM_SYNC_PIN, LOW);
        digitalWrite(LC_SYNC_PIN, LOW);
        sync_pin_is_on = false;
    }
}

/*
######## ########  ####    ###    ##          ######## ##    ## ########  ########
   ##    ##     ##  ##    ## ##   ##             ##     ##  ##  ##     ## ##
   ##    ##     ##  ##   ##   ##  ##             ##      ####   ##     ## ##
   ##    ########   ##  ##     ## ##             ##       ##    ########  ######
   ##    ##   ##    ##  ######### ##             ##       ##    ##        ##
   ##    ##    ##   ##  ##     ## ##             ##       ##    ##        ##
   ##    ##     ## #### ##     ## ########       ##       ##    ##        ########
*/

// running bias calculation as a mechanism to combat bias
const int n_choice_hist = 10;
int past_choices[n_choice_hist] = {0,1,0,1,0,1,0,1,0,1};
// int past_choices[n_choice_hist];
// for (int i = 0; i < n_choice_hist; i++){
//     if (i % 2 == 0){
//         past_choices[i] = 1
//     }
//     else {
//         past_choices[i] = 0
//     }
// }
float bias = 0.5;

void update_bias(int choice){ // choice 0 is left, right is 1
    // roll
    for (int i = n_choice_hist-1; i > 0; i--){
        past_choices[i] = past_choices[i-1];
    }
    // update
    past_choices[0] = choice;

    // average
    float sum = 0;
    for (int i = 0; i < n_choice_hist; i++){
        sum = sum + past_choices[i];
    }
    bias = sum / n_choice_hist;
}

int trial_counter = 0;

bool in_corr_loop = false;
int left_error_counter = 0;
int right_error_counter = 0;
int succ_trial_counter = 0;

// int miss_counter = 0;
bool in_warmup = true;
bool corr_loop_reset_mode = true;

/*
resetting mode:
within correction loop, any mistake restarts the counter from the beginning
no resetting: intermediate mistakes allowed, corr loop is exited after 3 correct choices
*/

const int n_intervals = 2;
unsigned long this_interval = 1500;
unsigned long short_intervals[n_intervals] = {600, 1000};
unsigned long long_intervals[n_intervals] = {2000, 2400};
float p_short_intervals[n_intervals] = {.5, .5};
float p_long_intervals[n_intervals] = {.5, .5};
int i;
float p_cum;

unsigned long get_short_interval(){
    r = random(0,1000) / 1000.0;
    for (int i = 0; i < n_intervals; i++){
        p_cum = 0;
        for (int j = 0; j <= i; j++){
            p_cum += p_short_intervals[j];
        }
        if (r < p_cum){
            return short_intervals[i];
        }
    }
    return -1;
}

unsigned long get_long_interval(){
    r = random(0,1000) / 1000.0;
    for (int i = 0; i < n_intervals; i++){
        p_cum = 0;
        for (int j = 0; j <= i; j++){
            p_cum += p_long_intervals[j];
        }
        if (r < p_cum){
            return long_intervals[i];
        }
    }
    return -1;
}

// unsigned long get_short_interval(){
   
//     r = random(0,1000) / 1000.0;


//     if (r < p_short_intervals[0]){
//         return short_intervals[0];
//     }
//     else{
//         return short_intervals[1];
//     }
// }

// unsigned long get_long_interval(){
//     r = random(0,1000) / 1000.0;
//     if (r < p_long_intervals[0]){
//         return long_intervals[0];
//     }
//     else{
//         return long_intervals[1];
//     }
// }

void set_interval(){
    if (correct_side == right){
        if (left_short == 0){ // right short
            this_interval = get_short_interval();
        }
        else{
            this_interval = get_long_interval();
        }
    }

    if (correct_side == left){
        if (left_short == 1){
            this_interval = get_short_interval();
        }
        else {
            this_interval = get_long_interval();
        }
    }
}

void get_trial_type(){
    if (correction_loops == 1){
        // determine if enter corr loop
        if (in_corr_loop == false && (left_error_counter >= corr_loop_entry || right_error_counter >= corr_loop_entry)){
            in_corr_loop = true;
            timing_trial = false;
        }
        
        // determine if exit corr loop
        if (in_corr_loop == true && succ_trial_counter >= corr_loop_exit){
            in_corr_loop = false;
        }
    }
    
    // if not in corr loop, choose new correct side
    if (in_corr_loop == false){ 

        // probabilistic bias correction
        if (prob_bias_corr == 1){
            r = random(0,1000) / 1000.0;
            if (r > bias){ // 1 = right
                correct_side = right;
            }
            else {
                correct_side = left;
            }
        }
        // static = fixed probability bias correction
        else{
            if (r > p_left){ // 1 = right
                correct_side = right;
            }
            else {
                correct_side = left;
            }
        }
        // timing trials as catch trials
        r = random(0,1000) / 1000.0;
        if (r < p_timing_trial){
            timing_trial = true;
        }
        else {
            timing_trial = false;
        }
    }
    else{
        // if in corr loop, trial type is not updated
    }

    // switches off autodeliver rewards after warmup
    if (trial_counter <= n_warmup_trials){
        autodeliver_rewards = 1;
        // turn it off once on last
        if (trial_counter == n_warmup_trials){
            autodeliver_rewards = 0;
        }
    }
    
    // now is always called to update even in corr loop
    set_interval(); // this will produce different intervals in a correction loop

    log_int("trial_counter", trial_counter);
    log_ulong("this_interval", this_interval);
    log_int("correct_side", correct_side);
    log_int("in_corr_loop", (int) in_corr_loop);
    log_float("bias", bias);
    log_int("timing_trial", (int) timing_trial);
    log_int("autodeliver_rewards", (int) autodeliver_rewards);
    trial_counter++;
}
              
void log_choice(){
    if (is_grasping_left){
        log_code(CHOICE_LEFT_EVENT);
        n_choices_left++;
        if (left_short == 1){
            log_code(CHOICE_SHORT_EVENT);
        }
        else{
            log_code(CHOICE_LONG_EVENT);
        }
    }
    if (is_grasping_right){
        log_code(CHOICE_RIGHT_EVENT);
        n_choices_right++;
        if (left_short == 1){
            log_code(CHOICE_LONG_EVENT);
        }
        else{
            log_code(CHOICE_SHORT_EVENT);
        }
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

        case TRIAL_AVAILABLE_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                log_code(TRIAL_AVAILABLE_EVENT);
                trial_available_cue();
            }

            // the update loop
            if (current_state == last_state){
                if (trial_autostart == 0){
                    if (digitalRead(TRIAL_INIT_PIN) == true && now() - t_last_touch_off > touch_block_dur && is_touching == false){
                        current_state = TRIAL_ENTRY_STATE;
                        break;
                    }
                }
                else{
                    if (now() - t_last_touch_off > touch_block_dur && is_touching == false){
                        current_state = TRIAL_ENTRY_STATE;
                        break;
                    }
                }
            }
            break;

        case TRIAL_ENTRY_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                log_code(TRIAL_ENTRY_EVENT);
                if (present_init_cue == 1){
                    trial_entry_cue(); // which is first timing cue
                }
                t_last_trial_entry = now();
                this_ITI_dur = (unsigned long) random(ITI_dur_min, ITI_dur_max);

                // sync at trial entry
                switch_sync_pin = true;
                sync_pin_controller(); // and call sync controller for enhanced temp prec.

                // determine the type of trial:
                get_trial_type(); // updates this_correct_side
            }

            // update
            if (last_state == current_state){

            }
            
            // exit condition 
            if (true) {
                current_state = PRESENT_INTERVAL_STATE;
            }
            break;

        case PRESENT_INTERVAL_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
            }

            // update
            if (last_state == current_state){
                // learn to choose: no premature breaking possible
                if (punish_premature == 1 && is_touching){
                    // premature choice
                    log_code(CHOICE_EVENT);
                    log_code(PREMATURE_CHOICE_EVENT);
                    incorrect_choice_cue();
                    log_choice();
                    this_ITI_dur += timeout_dur;
                    current_state = ITI_STATE;
                    break;
                }
            }

            if (now() - t_state_entry > this_interval){
                // cue
                if (correct_side == left){
                    go_cue_left();
                }
                if (correct_side == right){
                    go_cue_right();
                }

                current_state = CHOICE_STATE;
                break;
            }
            break;

        case CHOICE_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                // set this once on state entry
                if (autodeliver_rewards == 1){
                    this_kamin_block_protect_dur = random(kamin_block_protect_dur_min, kamin_block_protect_dur_max);
                }
            }

            // update
            if (last_state == current_state){
                if (autodeliver_rewards == 1 && now() - t_state_entry > this_kamin_block_protect_dur){
                    current_state = REWARD_STATE;
                    log_code(REWARD_AUTODELIVERED_EVENT);
                    break;
                }
            }

            // exit conditions

            // choice was made
            if (is_grasping) {
                log_code(CHOICE_EVENT);
                log_choice();

                // update past choices buffer
                if (is_grasping_left){
                   update_bias(0);
                }
                if (is_grasping_right){
                    update_bias(1);
                }
                // update miss buffer
                // update_miss_frac(0);

                // correct choice
                if ((correct_side == left && is_grasping_left) || (correct_side == right && is_grasping_right)){
                    log_code(CHOICE_CORRECT_EVENT);

                    // play cue? // this is for autoshaping
                    if (cue_on_rewarded_touch == 1){
                        if (correct_side == left){
                            go_cue_left();
                        }
                        if (correct_side == right){
                            go_cue_right();
                        }
                    }

                    succ_trial_counter += 1;
                    if (correct_side == left){
                        left_error_counter = 0;
                    }

                    if (correct_side == right){
                        right_error_counter = 0;
                    }

                    // if autodeliver - this is a predictive touch
                    if (autodeliver_rewards == 1){
                        log_code(ANTICIPATORY_REACH_EVENT);
                        if (is_grasping_left){
                            log_code(ANTICIPATORY_REACH_LEFT_EVENT);
                        }

                        if (is_grasping_right){
                            log_code(ANTICIPATORY_REACH_RIGHT_EVENT);
                        }
                    }

                    current_state = REWARD_STATE;
                    break;
                }

                // incorrect choice
                if ((correct_side == left && is_touching_right) || (correct_side == right && is_touching_left)){
                    log_code(CHOICE_INCORRECT_EVENT);
                    incorrect_choice_cue();

                    // update counters
                    if (correct_side == left){
                        left_error_counter += 1;
                        right_error_counter = 0;
                    }
                    if (correct_side == right){
                        right_error_counter += 1;
                        left_error_counter = 0;
                    }
                    if (corr_loop_reset_mode == true){
                        succ_trial_counter = 0;
                    }

                    this_ITI_dur += timeout_dur;
                    current_state = ITI_STATE;
                    break;
                }
            }
                        
            // no choice was made
            if (now() - t_state_entry > choice_dur){
                log_code(CHOICE_MISSED_EVENT);
                
                // cue
                if (use_incorrect_cue_on_miss){
                    incorrect_choice_cue();
                }
                current_state = ITI_STATE;
                break;
            }
            break;

        case REWARD_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                log_code(REWARD_EVENT);
                if (correct_side == left){
                    log_code(REWARD_LEFT_EVENT);
                    deliver_reward_left = true;
                    reward_left_available = true;
                }
                else{
                    log_code(REWARD_RIGHT_EVENT);
                    deliver_reward_right = true;
                    reward_right_available = true;
                }
            }

            // update
            if (current_state != last_state){
                if (reward_available == false){ // reward got collected
                    log_code(REWARD_COLLECTED_EVENT);
                    if (correct_side == left){
                        log_code(REWARD_LEFT_COLLECTED_EVENT);
                    }
                    if (correct_side == right){
                        log_code(REWARD_RIGHT_COLLECTED_EVENT);
                    }
                }
            }

            // exit
            if (now() - t_state_entry > reward_collection_dur){
                // this serves as a grace period
                current_state = ITI_STATE;
                break;
            }
            break;

        case ITI_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                lights_on();
            }

            // update
            if (last_state == current_state){

            }

            // exit condition
            if (now() - t_last_trial_entry > this_ITI_dur) {
                current_state = TRIAL_AVAILABLE_STATE;
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
    // pinMode(REACH_LEFT_PIN, INPUT);
    // pinMode(REACH_RIGHT_PIN, INPUT);

    pinMode(TOUCH_LEFT_PIN, INPUT);
    pinMode(TOUCH_RIGHT_PIN, INPUT);
    
    // TTL COM w camera
    pinMode(CAM_SYNC_PIN,OUTPUT);
    pinMode(LC_SYNC_PIN,OUTPUT);

    // ini speakers and buzzers
    pinMode(SPEAKER_PIN, OUTPUT);
    pinMode(BUZZER_PIN, OUTPUT);
    buzz_controller.begin(BUZZER_PIN);
    tone_controller.begin(SPEAKER_PIN);

    pinMode(TOUCH_CUE_LEFT_PIN, OUTPUT);
    pinMode(TOUCH_CUE_RIGHT_PIN, OUTPUT);

    // LED related
    FastLED.addLeds<WS2812B, LED_PIN, GRB>(leds, NUM_LEDS);
    lights_off();
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
    // led_blink_controller();

    // sample sensors
    read_touches();

    // serial communication with main PC
    getSerialData();
    processSerialData();

    // raw data via serial - the loadcell data
    // getRawData();
    // processRawData();
    
    // process loadcell data
    // process_loadcell();
    
    // non-blocking cam sync pin
    sync_pin_controller();
    touch_cue_controller();

}
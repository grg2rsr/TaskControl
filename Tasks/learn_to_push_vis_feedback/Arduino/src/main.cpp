#include <Arduino.h>
#include <string.h>
#include <Tone.h>
#include <FastLED.h>

#include <event_codes.h> // <>?
#include "interface.cpp"
#include "raw_interface.cpp"
#include "pin_map.h"


// DEBUG
// #include <util/atomic.h>

// void setMillis(unsigned long ms)
// {
//     extern unsigned long timer0_millis;
//     ATOMIC_BLOCK (ATOMIC_RESTORESTATE) {
//         timer0_millis = ms;
//     }
// }

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
float r; // for random

// loadcell binning
int current_zone;
int last_zone;

int left = 4;
int center = 5;
int right = 6;

Tone buzz_controller;
int choice;
int correct_zone;

// laterality related
String last_correct_side = "left";
String this_correct_side = "right";

// bias related
// float bias = 0.5; // exposed in interface_variables.h
int n_choices_left = 1;
int n_choices_right = 1;

void update_bias(){
    // 0 = left bias, 1 = right bias
    bias = (float) n_choices_right / (n_choices_left + n_choices_right);
}

// probabilistic reward related
// int omit_rewards = 1; // controls reward omission or magnitude manipulation
float p_reward_left = 1.0;
float p_reward_right = 1.0;
float this_p_reward = p_reward_left;
unsigned long reward_magnitude_full = reward_magnitude;

void update_p_reward(){
    float b = (bias*2)-1; // rescale to [-1,1]
    p_reward_left = constrain(1.0 + b, 0, 1);
    p_reward_right = constrain(1.0 - b, 0, 1);
}

/*
##        #######   ######    ######   #### ##    ##  ######
##       ##     ## ##    ##  ##    ##   ##  ###   ## ##    ##
##       ##     ## ##        ##         ##  ####  ## ##
##       ##     ## ##   #### ##   ####  ##  ## ## ## ##   ####
##       ##     ## ##    ##  ##    ##   ##  ##  #### ##    ##
##       ##     ## ##    ##  ##    ##   ##  ##   ### ##    ##
########  #######   ######    ######   #### ##    ##  ######
*/

// float now(){
//     return (unsigned long) micros() / 1000;
// }

float now(){
    return (unsigned long) millis();
}

void log_code(int code){
    Serial.println(String(code) + '\t' + String(now()));
}

void log_msg(String Message){
    Serial.println("<MSG " + Message + " "+String(now())+">");
}

void log_var(String name, String value){
    Serial.println("<VAR " + name + " " + value + " "+String(now())+">");
}

void log_choice(){
    if (current_zone == right){
        log_code(CHOICE_RIGHT_EVENT);
        n_choices_right++;
        // if (left_short == true){
        //     log_code(CHOICE_LONG_EVENT);
        // }
    }
    if (current_zone == left){
        log_code(CHOICE_LEFT_EVENT);
        n_choices_left++;
        // if (left_short == true){
        //     log_code(CHOICE_SHORT_EVENT);
        // }
    }
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

unsigned long t_last_buzz = max_future;
unsigned long debounce_dur = 250;

bool in_fix_box = false;
unsigned long t_last_fix_box_entry = 0;

void process_loadcell() {

    // only regard left, center, right and fix box
    if (X < -1*X_thresh){
        current_zone = left;
    }
    if (X > -1*X_thresh && X < X_thresh){
        current_zone = center;
    }
    if (X > X_thresh){
        current_zone = right;
    }

    // fix box
    if (X > -1*XY_fix_box && X < XY_fix_box && Y > -1*XY_fix_box && Y < XY_fix_box){
        if (in_fix_box == false){
            in_fix_box = true;
            t_last_fix_box_entry = now();
        }
    }
    else{
        in_fix_box = false;
    }

    if (current_zone != last_zone){

        log_var("current_zone", String(current_zone));

        // on center leave
        if (last_zone == center) {
            if (now() - t_last_buzz > debounce_dur){
                buzz_controller.play(6,230);
                t_last_buzz = now();
            }
        }
        last_zone = current_zone;
    }
}

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
#define NUM_LEDS 71 // num of LEDs in strip
CRGB leds[NUM_LEDS]; // Define the array of leds
int center_led = (NUM_LEDS-1)/2;

void lights_off(){
    for (int i = 0; i < NUM_LEDS; i++){
        leds[i] = CRGB::Black;
    }
    FastLED.show();
}

// LED blink controller related
bool led_is_on[NUM_LEDS];
bool switch_led_on[NUM_LEDS];
unsigned long led_on_time[NUM_LEDS];
unsigned long led_on_dur = 250;
int led_hsv;

void led_blink_controller(){
    // the controller: iterate over all LEDs and set their state accordingly
    for (int i = 0; i < NUM_LEDS; i++){
        if (led_is_on[i] == false && switch_led_on[i] == true){
            // leds[i] = CRGB::Blue; // can be replaced with HSV maybe?
            leds[i] = CHSV(led_hsv,255,255);
            led_is_on[i] = true;
            led_on_time[i] = now();
            switch_led_on[i] = false;
            FastLED.show();
        }
        // turn off if on for long enough
        if (led_is_on[i] == true && now() - led_on_time[i] > led_on_dur){
            leds[i] = CRGB::Black;
            led_is_on[i] = false;
            FastLED.show();
        }
    }
}

// instructed trial related
unsigned long dt;
float dX;
bool X_controller_is_active = false; // to be set active on controlled trials
bool switch_X_controller_on = false;
unsigned long X_controller_switch_on_time;

void X_controller_update(){
    if (X_controller_is_active == false && switch_X_controller_on == true){
        X_controller_switch_on_time = now();
        X_controller_is_active = true;
        switch_X_controller_on = false;
    }

    if (X_controller_is_active == true){
        dt = now() - X_controller_switch_on_time;
        dX = instructed_cue_speed * dt;

        if (correct_zone == right){
            X = X + dX;
        }
        if (correct_zone == left){
            X = X - dX;
        }
    }
}

// run X_controller at fixed rate
unsigned long t_last_X_controller_update = 0;
void X_controller(){
    if (now() - t_last_X_controller_update > 1000 / fps){
        X_controller_update();
        t_last_X_controller_update = now();
    }
}

// LED feedback cursor
float sep = (NUM_LEDS-1)/4; // 90 deg separation
float cursor_pos = 0;
// int fps = 10;

// to be set in get_trial_type()
float left_cue_brightness;
float right_cue_brightness;
bool cursor_is_active = false; // to switch on cursor

float gaussian(float x, float mu, float sig){
    // float y =  1 / (sig * sqrt(2*PI) ) * exp( -0.5 * ((x-mu)/sig)**2 );
    float y = exp( -0.5 * pow(((x-mu)/sig),2) ); // normalized to one
    return y;
}

// float sigma = 1;
float vis_coupling = 2;

void update_led_cursor(){
    if (cursor_is_active == true){
        cursor_pos = map(X, -X_thresh * vis_coupling, X_thresh * vis_coupling, 0.0, NUM_LEDS*100.0)/100.0;
        for (int i = 0; i < NUM_LEDS; i++){
            float left_brightness = left_cue_brightness * 255 * gaussian((float) i, cursor_pos - sep, sigma); // contrast to be mult into this
            float right_brightness = right_cue_brightness * 255 * gaussian((float) i, cursor_pos + sep, sigma);
            leds[i] = CHSV(160, 255, constrain(left_brightness + right_brightness, 0, 255));
        }
        FastLED.show();
    }
}

// for updating the LED strip at a fixed rate
unsigned long t_last_cursor_update = 0;
void led_cursor_controller(){
    if (now() - t_last_cursor_update > 1000 / fps){
        update_led_cursor();
        t_last_cursor_update = now();
    }
}

/* 
// the computationally cheaper variant
int last_cursor_pos = 0;
void led_cursor_controller(){
    if (cursor_is_active == true){
        cursor_pos = (int) map(X, -X_thresh * vis_coupling, X_thresh * vis_coupling, 0.0, (float) NUM_LEDS);
        if (last_cursor_pos != cursor_pos){
            //
            for (int i = 0; i < NUM_LEDS; i++){
                leds[i] = CRGB::Black;
            }

            cursor_pos = constrain(cursor_pos,1,NUM_LEDS-2);

            // right
            leds[cursor_pos - sep]     = CHSV(160,255,255*left_cue_brightness);
            leds[cursor_pos - sep + 1] = CHSV(160,255,125*left_cue_brightness);
            leds[cursor_pos - sep - 1] = CHSV(160,255,125*left_cue_brightness);

            //left
            leds[cursor_pos + sep]     = CHSV(160,255,255*right_cue_brightness);
            leds[cursor_pos + sep + 1] = CHSV(160,255,125*right_cue_brightness);
            leds[cursor_pos + sep - 1] = CHSV(160,255,125*right_cue_brightness);

            last_cursor_pos = cursor_pos;
            FastLED.show();
        }
    }
}

*/



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
unsigned long tone_dur = 100;

// buzzer related
unsigned long buzz_dur = 10;
unsigned long choice_buzz_dur = 50;

void go_cue(){ // future timing cue 2
    log_code(GO_CUE_EVENT);
    // buzz
    buzz_controller.play(235, buzz_dur);
}

void choice_cue(){
    // buzz
    buzz_controller.play(235,choice_buzz_dur);
}

void correct_choice_cue(){
    // beep
    tone_controller.play(correct_choice_cue_freq, tone_dur);

    // center blink
    led_hsv = 32;
    switch_led_on[center_led] = true;
    switch_led_on[center_led+1] = true;
    switch_led_on[center_led-1] = true;
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
    // beep
    // tone_controller.play(incorrect_choice_cue_freq, tone_dur);

    // white noise - blocking arduino for tone_dur
    error_cue_start = micros();
    lastClick = micros();
    while (micros() - error_cue_start < error_cue_dur){
        if ((micros() - lastClick) > 2 ) { // Changing this value changes the frequency.
            lastClick = micros();
            digitalWrite (SPEAKER_PIN, generateNoise());
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

float ul2time(unsigned long reward_volume){
    return (float) reward_volume / valve_ul_ms;
}

bool reward_valve_is_closed = true;
// bool deliver_reward = false; // already forward declared in interface.cpp
unsigned long t_reward_valve_open = max_future;
float reward_valve_dur;

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
        
        // present cue? (this is necessary for keeping the keyboard reward functionality)
        if (present_reward_cue == true){
            correct_choice_cue();
            present_reward_cue = false;
        }
    }

    if (reward_valve_is_closed == false && now() - t_reward_valve_open > reward_valve_dur) {
        digitalWrite(REWARD_VALVE_PIN, LOW);
        log_code(REWARD_VALVE_OFF);
        reward_valve_is_closed = true;
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

// bool correction_loops = true;
// int correction_loops = 1;
bool in_corr_loop = false;
int left_error_counter = 0;
int right_error_counter = 0;
int succ_trial_counter = 0;
bool instructed_trial = false;
bool corr_loop_reset_mode = true;
/*
resetting mode:
within correction loop, any mistake restarts the counter from the beginning
no resetting: intermediate mistakes allowed, corr loop is exited after 3 correct choices
*/

void get_trial_type(){
    // determine if instructed trial
    r = random(0,1000) / 1000.0;
    if (r < p_instructed_trial){
        instructed_trial = true;
    }

    // determine if enter corr loop
    if (correction_loops == 1){
        if (in_corr_loop == false && (left_error_counter >= corr_loop_entry || right_error_counter >= corr_loop_entry)){
            in_corr_loop = true;
        }
        
        // determine if exit corr loop
        if (in_corr_loop == true && succ_trial_counter >= corr_loop_exit){
            in_corr_loop = false;
        }
    }
    
    if (in_corr_loop == false){
        r = random(0,1000) / 1000.0;
        if (r > bias){
            // 0 = left bias, 1 = right bias
            this_correct_side = "right";
            correct_zone = right;

            left_cue_brightness = 1.0;
            right_cue_brightness = left_cue_brightness - contrast * left_cue_brightness;
        }
        else {
            this_correct_side = "left";
            correct_zone = left;

            right_cue_brightness = 1.0;
            left_cue_brightness = right_cue_brightness - contrast * right_cue_brightness;
        }
    }
    
    log_var("correct_zone", String(correct_zone));
    log_var("in_corr_loop", String(in_corr_loop));
    log_var("instructed_trial", String(instructed_trial));
}
               
/*
 
 ##     ##  #######  ##     ## #### ##    ##  ######      ##     ##    ###    ########   ######  
 ###   ### ##     ## ##     ##  ##  ###   ## ##    ##     ##     ##   ## ##   ##     ## ##    ## 
 #### #### ##     ## ##     ##  ##  ####  ## ##           ##     ##  ##   ##  ##     ## ##       
 ## ### ## ##     ## ##     ##  ##  ## ## ## ##   ####    ##     ## ##     ## ########   ######  
 ##     ## ##     ##  ##   ##   ##  ##  #### ##    ##      ##   ##  ######### ##   ##         ## 
 ##     ## ##     ##   ## ##    ##  ##   ### ##    ##       ## ##   ##     ## ##    ##  ##    ## 
 ##     ##  #######     ###    #### ##    ##  ######         ###    ##     ## ##     ##  ######  
 
*/

void move_X_thresh(float percent_change){
    X_thresh += X_thresh * percent_change;
    X_thresh = constrain(X_thresh, X_thresh_start, X_thresh_target);
    log_var("X_thresh",String(X_thresh));
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
                // log_code(TRIAL_AVAILABLE_STATE); // for plotting purposes

                // sync at trial entry
                send_sync_pulse();

                // bias related
                update_bias();
                
                if (correction_loops == 0){
                    update_p_reward();
                }

                // log bias
                log_var("bias", String(bias));

                // determine the type of trial:
                get_trial_type(); // updates this_correct_side

            }

            // update
            if (last_state == current_state){

            }
            
            // exit condition 
            if (now() - t_state_entry > min_fix_dur && now() - t_last_fix_box_entry > min_fix_dur && in_fix_box == true) {
                current_state = CHOICE_STATE;
            }
            break;

        case CHOICE_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();

                // cue
                go_cue();
                cursor_is_active = true;

                if (instructed_trial == true){
                    switch_X_controller_on = true;
                    instructed_trial = false;
                }
            }

            // update
            // if (last_state == current_state){
            // }

            // exit conditions

            // choice was made
            if (current_zone != center) {
                log_code(CHOICE_EVENT);
                log_choice();

                cursor_is_active = false;
                lights_off();
                
                // report back to animal
                choice_cue();

                // correct choice
                if (current_zone == correct_zone) {
                    log_code(CHOICE_CORRECT_EVENT);
                    log_code(TRIAL_SUCCESSFUL_EVENT);
                    correct_choice_cue();

                    // move vars
                    move_X_thresh(X_thresh_increment);

                    // update counters
                    succ_trial_counter += 1;
                    if (correct_zone == left){
                        right_error_counter = 0;
                    }
                    if (correct_zone == right){
                        left_error_counter = 0;
                    }

                    last_correct_side = this_correct_side;
                    current_state = REWARD_AVAILABLE_STATE;

                    break;
                }

                // incorrect choice
                else {
                    log_code(CHOICE_INCORRECT_EVENT);
                    log_code(TRIAL_UNSUCCESSFUL_EVENT);

                    // update counters
                    if (current_zone == left){
                        left_error_counter += 1;
                        right_error_counter = 0;
                    }
                    if (current_zone == right){
                        right_error_counter += 1;
                        left_error_counter = 0;
                    }
                    if (corr_loop_reset_mode == true){
                        succ_trial_counter = 0;
                    }
                    
                    // report to animal
                    incorrect_choice_cue();
                    current_state = ITI_STATE;
                    break;
                }
            }
                        
            // no report, timeout
            if (now() - t_state_entry > choice_dur){
                log_code(CHOICE_MISSED_EVENT);
                log_code(TRIAL_UNSUCCESSFUL_EVENT);

                // cue
                incorrect_choice_cue();
                current_state = ITI_STATE;

                cursor_is_active = false;
                lights_off();

                // TODO this is highly debateable
                move_X_thresh(X_thresh_decrement);
                break;
            }

            break;

        case REWARD_AVAILABLE_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                log_code(REWARD_AVAILABLE_EVENT);
            }

            // update
            if (last_state == current_state){
                if (lick_in == true){

                    // deliver reward?
                    if (last_correct_side == "left"){
                        this_p_reward = p_reward_left;
                    }

                    if (last_correct_side == "right"){
                        this_p_reward = p_reward_right;
                    }

                    if (omit_rewards == 1){
                        // reward probability manipulation
                        r = random(0,1000) / 1000.0;
                        if (this_p_reward > r){
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
                    else{
                        // reward magnitude manipulation
                        log_code(REWARD_COLLECTED_EVENT);
                        reward_magnitude = reward_magnitude_full * this_p_reward;
                        deliver_reward = true;
                        current_state = ITI_STATE;
                        break;
                    }
                }
            }

            // exit condition
            if (now() - t_state_entry > reward_available_dur) {
                // transit to ITI after certain time
                log_code(REWARD_MISSED_EVENT);
                current_state = ITI_STATE;
            }
            break; 

        case ITI_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                this_ITI_dur = (unsigned long) random(ITI_dur_min, ITI_dur_max);

                // deactivate X_controller in case
                if (X_controller_is_active == true){
                    X_controller_is_active = false;
                }
            }

            // update
            if (last_state == current_state){

            }

            // exit condition
            if (now() - t_state_entry > this_ITI_dur) {
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

    tone_controller.begin(SPEAKER_PIN);
    buzz_controller.begin(BUZZ_PIN);

    // LED related
    FastLED.addLeds<WS2812B, LED_PIN, GRB>(leds, NUM_LEDS);
    for (int i = 0; i < NUM_LEDS; i++) {
        led_is_on[i] = false;
        switch_led_on[i] = false;
        led_on_time[i] = max_future;
    }

    lights_off();
    cursor_is_active = false;

    Serial.println("<Arduino is ready to receive commands>");
    delay(1000);
    // setMillis(-30000);
}

void loop() {
    if (run == true){
        // execute state machine(s)
        finite_state_machine();
    }
    // Controllers
    reward_valve_controller();
    led_blink_controller();
    led_cursor_controller();
    X_controller();

    // sample sensors
    read_lick();

    // serial communication with main PC
    getSerialData();
    processSerialData();

    // raw data via serial - the loadcell data - process only if not controlled
    getRawData();
    if (X_controller_is_active == false){
        processRawData();
    }
    
    // process loadcell data
    process_loadcell();

}
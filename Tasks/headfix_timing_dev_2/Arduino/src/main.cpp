#include <Arduino.h>
#include <string.h>
#include <Tone.h>
#include <FastLED.h>

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
int last_state = TIMEOUT_STATE; // whatever other state
unsigned long max_future = 4294967295; // 2**32 -1
unsigned long state_entry = max_future;
unsigned long this_ITI_dur;

// flow control flags
bool lick_in = false;
bool reward_collected = false;

// speaker
Tone tone_controller;
unsigned long tone_duration = 100;

// unexposed interval tones
int n_intervals = 6;
unsigned long tone_intervals[] = {400, 800, 1400, 1600, 2200, 2600}; // in ms, bc will be compared to now()
unsigned long interval_boundary = 1500;
unsigned long this_interval;

int ix; // trial index

// loadcell binning
int current_zone;
int last_zone;

int left_back = 1;
int back = 2;
int right_back = 3;
int left = 4;
int center = 5;
int right = 6;
int left_front = 7;
int front = 8;
int right_front = 9;

int choice;
int correct_side;

bool left_short = true; // TODO expose


// buzzer related
Tone buzz_controller;
unsigned long buzz_duration = 50; 

// for checking loop speed
bool toggle = false;

/*
##        #######   ######    ######   #### ##    ##  ######
##       ##     ## ##    ##  ##    ##   ##  ###   ## ##    ##
##       ##     ## ##        ##         ##  ####  ## ##
##       ##     ## ##   #### ##   ####  ##  ## ## ## ##   ####
##       ##     ## ##    ##  ##    ##   ##  ##  #### ##    ##
##       ##     ## ##    ##  ##    ##   ##  ##   ### ##    ##
########  #######   ######    ######   #### ##    ##  ######
*/

float now(){
    return (unsigned long) micros() / 1000;
}

void log_code(int code){
    Serial.println(String(code) + '\t' + String(micros()/1000.0));
}

void log_msg(String Message){
    Serial.println("<MSG " + Message + ">");
}

void log_var(String name, String value){
    Serial.println("<VAR " + name + " " + value + ">");
}

void log_choice(){
    if (current_zone == right){
        log_code(CHOICE_RIGHT_EVENT);
    }
    if (current_zone == left){
        log_code(CHOICE_LEFT_EVENT);
    }
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

unsigned long last_center_leave = max_future;
unsigned long last_buzz = max_future;
unsigned long debounce = 250;

void process_loadcell() {
    // bin zones into 9 pad
    if (X < X_left_thresh && Y < Y_back_thresh){
        current_zone = left_back;
    }

    if (X > X_left_thresh && X < X_right_thresh && Y < Y_back_thresh){
        current_zone = back;
    }

    if (X > X_right_thresh && Y < Y_back_thresh){
        current_zone = right_back;
    }
    
    if (X < X_left_thresh && Y > Y_back_thresh && Y < Y_front_thresh){
        current_zone = left;
    }

    if (X > X_left_thresh && X < X_right_thresh && Y > Y_back_thresh && Y < Y_front_thresh){
        current_zone = center;
    }

    if (X > X_right_thresh && Y > Y_back_thresh && Y < Y_front_thresh){
        current_zone = right;
    }

    if (X < X_left_thresh && Y > Y_front_thresh){
        current_zone = left_front;
    }

    if (X > X_left_thresh && X < X_right_thresh &&  Y > Y_front_thresh){
        current_zone = front;
    }

    if (X > X_right_thresh && Y > Y_front_thresh){
        current_zone = right_front;
    }

    if (current_zone != last_zone){
        log_var("current_zone", String(current_zone));

        // on center leave
        if (last_zone == center) {
            last_center_leave = now();
            if (last_center_leave - last_buzz > debounce){
                buzz_controller.play(6,235);
                last_buzz = now();
            }
        }
        last_zone = current_zone;
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
##       ######## ########
##       ##       ##     ##
##       ##       ##     ##
##       ######   ##     ##
##       ##       ##     ##
##       ##       ##     ##
######## ######## ########
*/
// LED strip related
#define NUM_LEDS 21 // num of LEDs in strip minus one, which is the cue LED
CRGB leds[NUM_LEDS]; // Define the array of leds
CRGB cue_led[NUM_LEDS]; // Define array of 1 for cue led

bool lights_are_on = false;

void lights_on_blue(){
    // turn LEDs on
    for (int i = 0; i < NUM_LEDS; i++){
        leds[i] = CRGB::Blue;
    }
    FastLED.show();
    lights_are_on = true;
}

void lights_on_orange(){
    // turn LEDs orange
    for (int i = 0; i < NUM_LEDS; i++){
        if (i % 2 == 0){
            leds[i] = CRGB::Orange;
        }
    }
    FastLED.show();
    lights_are_on = true;
}

void lights_off(){
    // turn LEDs off
    for (int i = 0; i < NUM_LEDS; i++){
        leds[i] = CRGB::Black;
    }
    FastLED.show();
    lights_are_on = false;
}
bool cue_led_is_on = false;
bool switch_cue_led_on = false;
unsigned long cue_led_on_time = max_future;
unsigned long cue_led_time = 100; // in

void CueLEDController(){
    // a self terminating digital pin switch
    if (cue_led_is_on == false && switch_cue_led_on == true) {
        log_code(CUE_LED_ON_EVENT);
        // turn cue led on
        cue_led[0] = CRGB::White;
        FastLED.show();

        cue_led_is_on = true;
        switch_cue_led_on = false;
        cue_led_on_time = now();
    }

    if (cue_led_is_on == true && now() - cue_led_on_time > cue_led_time) {
        // turn led off
        log_code(CUE_LED_OFF_EVENT);

        cue_led[0] = CRGB::Black;
        FastLED.show();
        cue_led_is_on = false;
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

void timing_cue_1(){
    log_code(FIRST_TIMING_CUE_EVENT);
    // light
    switch_cue_led_on = true;
}

void timing_cue_2(){
    log_code(SECOND_TIMING_CUE_EVENT);
    // buzz
    buzz_controller.play(235, buzz_duration);
}

/*
 
 ######## ########  ####    ###    ##           ######  ##     ##  #######  ####  ######  ######## 
    ##    ##     ##  ##    ## ##   ##          ##    ## ##     ## ##     ##  ##  ##    ## ##       
    ##    ##     ##  ##   ##   ##  ##          ##       ##     ## ##     ##  ##  ##       ##       
    ##    ########   ##  ##     ## ##          ##       ######### ##     ##  ##  ##       ######   
    ##    ##   ##    ##  ######### ##          ##       ##     ## ##     ##  ##  ##       ##       
    ##    ##    ##   ##  ##     ## ##          ##    ## ##     ## ##     ##  ##  ##    ## ##       
    ##    ##     ## #### ##     ## ########     ######  ##     ##  #######  ####  ######  ######## 
 
*/

// hardcoded for now - p_trial
// float p_interval[6] = {1,0.5,0,0,0.5,1}; // FIXME HARDCODE
float p_interval_cs[6];

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
    state_entry = now();
    log_code(current_state);
}

void finite_state_machine() {
    // the main FSM
    switch (current_state) {

        case INI_STATE:
            current_state = TRIAL_AVAILABLE_STATE;
            break;

        case TRIAL_AVAILABLE_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();

                // cue orange light
                lights_on_orange();

                // tell loadcell controller to recenter
                log_msg("LOADCELL REMOVE_OFFSET");
            }

            // update
            if (last_state == current_state){

            }
            
            // exit condition
            if (now() - state_entry > trial_avail_dur || current_zone == front) {
                if (now() - state_entry > trial_avail_dur){
                    // missed trial init -> to to ITI again
                    lights_off();
                    current_state = ITI_STATE;
                }
                if (current_zone == front){
                    // trial initiated
                    lights_on_blue();
                    current_state = PRESENT_INTERVAL_STATE;
                }
            }
            break;

        case PRESENT_INTERVAL_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                log_code(TRIAL_ENTRY_EVENT);

                // sync w load cell TODO test this!
                digitalWrite(LC_SYNC_PIN,HIGH);
                delay(5);
                digitalWrite(LC_SYNC_PIN,LOW);

                // draw trial type at random
                // ix = random(0,n_intervals);
                
                // weighted
                ix = get_interval_index();

                this_interval = tone_intervals[ix];

                // report interval for this trial
                log_msg(String("trial_index "+String(ix)));
                log_msg(String("this_interval "+String(this_interval)));

                //timing cue 1
                timing_cue_1();
            }

            // update
            if (last_state == current_state){

            }
            
            // exit conditions
            if (now() - state_entry > this_interval || current_zone == left || current_zone == right) {
            
                // premature choice
                if (current_zone == left || current_zone == right) { // OR current_zone != center!
                    log_choice();
                    log_code(TRIAL_ABORTED_EVENT);
                    
                    // punish cue - potential problem: tones are generalized
                    lights_off();
                    tone_controller.play(punish_tone_freq, tone_duration);
                    current_state = TIMEOUT_STATE;
                }

                // interval has passed
                if (now() - state_entry > this_interval){

                    // second timing cue
                    timing_cue_2();
                    current_state = CHOICE_STATE;
                }
            }
            break;        
        
        case CHOICE_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();

                // determine what would be a correct answer in this trial
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
            if (current_zone == left || current_zone == right || now() - state_entry > choice_dur){
                // no report, timeout
                if (now() - state_entry > choice_dur){
                    log_code(CHOICE_MISSED_EVENT);
                    lights_off();
                    tone_controller.play(punish_tone_freq, tone_duration);
                    current_state = TIMEOUT_STATE;
                }
                
                // choice was made
                if (current_zone == left || current_zone == right) {
                    log_choice();

                    // determine success
                    if (current_zone == correct_side){
                        // correct trial
                        log_code(CHOICE_CORRECT_EVENT);
                        log_code(TRIAL_SUCCESSFUL_EVENT);
                        current_state = REWARD_AVAILABLE_STATE;
                    }
                    else {
                        // wrong trial
                        log_code(CHOICE_WRONG_EVENT);
                        current_state = TIMEOUT_STATE;
                        lights_off();
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
                lights_off();
            }

            // update
            if (last_state == current_state){
                // state actions
            }

            // exit condition
            if (now() - state_entry > timeout_dur) {
                // after timeout, transit to trial available again
                current_state = ITI_STATE;
            }
            break;            

        case ITI_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                log_msg("REQUEST TRIAL_PROBS"); // now is a good moment?
                this_ITI_dur = random(ITI_dur_min, ITI_dur_max);
                lights_off();
            }

            // update
            if (last_state == current_state){
                // state actions
                // turn lights off 1s after state entry
                if (now() - state_entry > 1000 && lights_are_on){
                    lights_off();
                }
            }

            // exit condition
            if (now() - state_entry > this_ITI_dur) {
                current_state = TRIAL_AVAILABLE_STATE;
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

    FastLED.addLeds<WS2812B, LED_PIN, GRB>(leds, NUM_LEDS);
    FastLED.addLeds<WS2812B, CUE_LED_PIN, GRB>(cue_led, NUM_LEDS);

    lights_off();

    tone_controller.begin(SPEAKER_PIN);
    buzz_controller.begin(BUZZ_PIN);

    Serial.println("<Arduino is ready to receive commands>");
    delay(1000);
}

void loop() {
    if (run == true){
        // execute state machine(s)
        finite_state_machine();
    }
    // Controllers
    RewardValveController();
    CueLEDController();

    // sample sensors
    read_lick();

    // serial communication with main PC
    getSerialData();
    processSerialData();

    // raw data via serial - the loadcell data
    getRawData();
    processRawData();
    
    // process loadcell data
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
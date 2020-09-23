/*
to implement - probabilistic rewards
moving box -> learn to push
in learn to time -> moving var is the difficulty gap
*/

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
int last_state = -1; // whatever other state
unsigned long max_future = 4294967295; // 2**32 -1
unsigned long state_entry = max_future;
unsigned long this_ITI_dur;
unsigned long this_trial_entry_pause_dur;

// flow control flags
bool lick_in = false;

int succ_trial_counter = 0;
int n_streak = 3;
bool forced_alternating = true;

// speaker
Tone tone_controller;
unsigned long tone_duration = 100;

unsigned long this_interval;

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
int correct_zone;


// laterality related
String last_correct_side = "left";
String this_correct_side = "right";

bool left_short = true; // TODO expose
// if (left_short == true){
//     String last_correct_interval = "short";
//     String this_correct_interval = "long";
// }
// else {
//     String last_correct_interval = "long";
//     String this_correct_interval = "short";    
// }

String side_2_interval(String side){
    if (left_short == true){
        if (side == "left"){
            return "short";
        }
        if (side == "right"){
            return "long";
        }
    }
    if (left_short == false){
        if (side == "left"){
            return "long";
        }
        if (side == "right"){
            return "short";
        }
    }
    return "none";
}

// String interval_2_side(String interval){
//     if (left_short == true){
//         if (interval == "short"){
//             return "left";
//         }
//         if (interval == "long"){
//             return "right";
//         }
//     }
//     if (left_short == false){
//         if (interval == "short"){
//             return "right";
//         }
//         if (interval == "long"){
//             return "left";
//         }
//     }
// }

String last_correct_trial_type = "short";
String this_trial_type = "long";


// buzzer related
Tone buzz_controller;
unsigned long buzz_duration = 50;
unsigned long choice_buzz_duration = 100;

// probabilistic reward related
int n_choices_left = 1;
int n_choices_right = 1;

float p_reward = 1;
float this_p_reward = p_reward;

void update_p_reward(){
    this_p_reward = p_reward - (1-difficulty)/2;
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

float now(){
    return (unsigned long) micros() / 1000;
}

void log_code(int code){
    Serial.println(String(code) + '\t' + String(micros()/1000.0));
}

void log_msg(String Message){
    Serial.println("<MSG " + Message + " "+String(micros()/1000.0)+">");
}

void log_var(String name, String value){
    Serial.println("<VAR " + name + " " + value + " "+String(micros()/1000.0)+">");
}

void log_choice(){
    if (current_zone == right){
        log_code(CHOICE_RIGHT_EVENT);
        if (left_short == true){
            log_code(CHOICE_LONG_EVENT);
        }
        else{
            log_code(CHOICE_SHORT_EVENT);
        }
        n_choices_right++;
    }
    if (current_zone == left){
        log_code(CHOICE_LEFT_EVENT);
        if (left_short == true){
            log_code(CHOICE_SHORT_EVENT);
        }
        else{
            log_code(CHOICE_LONG_EVENT);
        }
        n_choices_left++;
    }
}

void send_sync_pulse(){
    // sync w load cell
    digitalWrite(LC_SYNC_PIN,HIGH);
    delay(1); // 1 ms blindness 
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

unsigned long last_center_leave = 0;
unsigned long last_zone_change = 0;
unsigned long last_buzz = max_future;
unsigned long debounce = 250;

void process_loadcell() {

    // bin zones into 9 pad
    if (X < (-1*X_thresh) && Y < (-1*Y_thresh)){
        current_zone = left_back;
    }

    if (X > (-1*X_thresh) && X < X_thresh && Y < (-1*Y_thresh)){
        current_zone = back;
    }

    if (X > X_thresh && Y < (-1*Y_thresh)){
        current_zone = right_back;
    }
    
    if (X < (-1*X_thresh) && Y > (-1*Y_thresh) && Y < Y_thresh){
        current_zone = left;
    }

    if (X > (-1*X_thresh) && X < X_thresh && Y > (-1*Y_thresh) && Y < Y_thresh){
        current_zone = center;
    }

    if (X > X_thresh && Y > (-1*Y_thresh) && Y < Y_thresh){
        current_zone = right;
    }

    if (X < (-1*X_thresh) && Y > Y_thresh){
        current_zone = left_front;
    }

    if (X > (-1*X_thresh) && X < X_thresh &&  Y > Y_thresh){
        current_zone = front;
    }

    if (X > X_thresh && Y > Y_thresh){
        current_zone = right_front;
    }

    if (current_zone != last_zone){
        last_zone_change = now();

        log_var("current_zone", String(current_zone));

        // on center leave
        if (last_zone == center) {
            last_center_leave = now();
            if (last_center_leave - last_buzz > debounce){
                buzz_controller.play(6,230);
                last_buzz = now();
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
#define NUM_LEDS 21 // num of LEDs in strip
CRGB leds[NUM_LEDS]; // Define the array of leds
bool led_is_on[NUM_LEDS];
bool switch_led_on[NUM_LEDS];
unsigned long led_on_time[NUM_LEDS];

unsigned long led_on_dur = 50;

void LEDController(){
    // the controller: iterate over all LEDs and set their state accordingly
    for (int i = 0; i < NUM_LEDS; i++){
        if (led_is_on[i] == false && switch_led_on[i] == true){
            leds[i] = CRGB::Blue;
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

/*
 ######  ##     ## ########  ######
##    ## ##     ## ##       ##    ##
##       ##     ## ##       ##
##       ##     ## ######    ######
##       ##     ## ##             ##
##    ## ##     ## ##       ##    ##
 ######   #######  ########  ######
*/

void go_cue(){ // future timing cue 2
    log_code(GO_CUE_EVENT);
    // buzz
    buzz_controller.play(235, buzz_duration);
}

void choice_cue(){
    // buzz
    buzz_controller.play(235,choice_buzz_duration);
}

void correct_choice_cue(){
    // beep
    tone_controller.play(correct_choice_cue_freq, tone_duration);
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
unsigned long error_cue_dur = tone_duration * 1000; // to save instructions - work in micros
unsigned long lastClick = max_future;

void incorrect_choice_cue(){
    // beep
    // tone_controller.play(incorrect_choice_cue_freq, tone_duration);

    // white noise - blocking arduino for tone_duration
    error_cue_start = micros();
    lastClick = micros();
    while (micros() - error_cue_start < error_cue_dur){
        if ((micros() - lastClick) > 2 ) { // Changing this value changes the frequency.
            lastClick = micros();
            digitalWrite (SPEAKER_PIN, generateNoise());
        }
    }
}

// void go_left_cue(){
//     // blink the leftmost LED
//     switch_led_on[0] = true;
//     switch_led_on[1] = true;
//     switch_led_on[2] = true;
// }

// void go_right_cue(){
//     // blink the rightmost LED
//     switch_led_on[NUM_LEDS - 1] = true;
//     switch_led_on[NUM_LEDS - 2] = true;
//     switch_led_on[NUM_LEDS - 3] = true;
// }

void timing_cue_1(){
    log_code(FIRST_TIMING_CUE_EVENT);
    // both lights light
    switch_led_on[0] = true;
    switch_led_on[NUM_LEDS - 1] = true;
}

int dist_from_center;
int center_led;

void timing_cue_2(){
    log_code(SECOND_TIMING_CUE_EVENT);
    dist_from_center = map(difficulty, 0.0, 100.0, ((NUM_LEDS - 1)/2)-1, 0);

    if (this_correct_side == "left"){
        center_led = (int) (NUM_LEDS-1)/2 - dist_from_center;
    }
    if (this_correct_side == "right"){
        center_led = (int) (NUM_LEDS-1)/2 + dist_from_center;
    }

    switch_led_on[center_led-1] = true;
    switch_led_on[center_led] = true;
    switch_led_on[center_led+1] = true;

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
        digitalWrite(REWARD_VALVE_PIN, HIGH);
        log_code(REWARD_VALVE_ON);
        reward_valve_closed = false;
        reward_valve_dur = ul2time(reward_magnitude);
        reward_valve_open_time = now();
        deliver_reward = false;

        // present cue? (this is necessary for keeping the keyboard reward functionality)
        if (present_reward_cue == true){
            correct_choice_cue();
            present_reward_cue = false;
        }
    }

    if (reward_valve_closed == false && now() - reward_valve_open_time > reward_valve_dur) {
        digitalWrite(REWARD_VALVE_PIN, LOW);
        log_code(REWARD_VALVE_OFF);
        reward_valve_closed = true;
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

void get_trial_type(){
    // determine correct side and zone

    // rule: forced alternating, but if on a streak, random
    if (succ_trial_counter < n_streak && forced_alternating == true){

        if (last_correct_side == "left"){
            this_correct_side = "right";
        }
        if (last_correct_side == "right"){
            this_correct_side = "left";
        }
    }
    else {
        float r = random(0,1000) / 1000.0;

        if (r > 0.5){
            this_correct_side = "left";
        }
        else {
            this_correct_side = "right";
        }
    }

    // set and log correct zone
    if (this_correct_side == "left"){
        correct_zone = left;
    }

    if (this_correct_side == "right"){
        correct_zone = right;
    }
    log_var("correct_zone", String(correct_zone));

    // get the corresponding time interval
    if (side_2_interval(this_correct_side) == "short"){
        this_interval = random(100, interval_boundary - interval_gap);
    }
    if (side_2_interval(this_correct_side) == "long"){
        this_interval = random(interval_boundary + interval_gap, 2900);
    }
    log_var("this_interval",String(this_interval));

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

// void move_interval_gap(float percent_change){
//     interval_gap += interval_gap * percent_change;
//     interval_gap = constrain(interval_gap, interval_gap_target, interval_gap_start);
//     log_var("interval_gap",String(interval_gap));
// }

void move_difficulty(float percent_change){
    difficulty += difficulty * percent_change;
    difficulty = constrain(difficulty, 1.0, 100.0);
    log_var("difficulty",String(difficulty));
}

// difficulty related 

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

                // log bias
                log_var("bias", String(bias));

                // determine the type of trial
                get_trial_type(); // update this_interval
                update_p_reward();
            }

            // update
            if (last_state == current_state){

            }
                        
            // exit condition 
            if (now() - state_entry > min_fix_dur && now() - last_zone_change > min_fix_dur && current_zone == center) {
                current_state = PRESENT_INTERVAL_STATE;
            }
            break;

        case PRESENT_INTERVAL_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();

                //timing cue 1
                timing_cue_1();
            }

            // update
            // premature choice
            if (current_zone != center) {
                log_code(PREMATURE_CHOICE_EVENT);
                log_code(TRIAL_ABORTED_EVENT);
                log_choice();
                
                // cues
                incorrect_choice_cue();

                current_state = ITI_STATE;
                break;
            }

            // exit conditions
            // interval has passed
            if (now() - state_entry > this_interval){
                // second timing cue
                timing_cue_2();
                current_state = CHOICE_STATE;
                break;
            }
            break;

        case CHOICE_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();

                // cue
                go_cue();
            }

            // update
            // if (last_state == current_state){
            // }

            // exit conditions

            // choice was made
            if (current_zone != center){
                log_code(CHOICE_EVENT);
                log_choice();
                
                // report back to animal
                choice_cue();

                // correct choice
                if (current_zone == correct_zone) {
                    log_code(CHOICE_CORRECT_EVENT);
                    log_code(TRIAL_SUCCESSFUL_EVENT);
                    correct_choice_cue();

                    // move vars
                    move_difficulty(difficulty_incr);

                    last_correct_side = this_correct_side;
                    current_state = REWARD_AVAILABLE_STATE;
                    break;
                }

                // incorrect choice
                else {
                    log_code(CHOICE_INCORRECT_EVENT);
                    log_code(TRIAL_UNSUCCESSFUL_EVENT);

                    // move vars
                    move_difficulty(difficulty_decr);

                    // report to animal
                    incorrect_choice_cue();
                    current_state = ITI_STATE;
                    break;
                }
            }

            // no report, timeout
            if (now() - state_entry > choice_dur){
                log_code(CHOICE_MISSED_EVENT);
                log_code(TRIAL_UNSUCCESSFUL_EVENT);

                // cue
                incorrect_choice_cue();
                current_state = ITI_STATE;
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
                    float r = random(0,1000) / 1000.0;
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
            }

            // exit condition
            if (now() - state_entry > reward_available_dur) {
                // transit to ITI after certain time
                log_code(REWARD_MISSED_EVENT);
                current_state = ITI_STATE;
                break;
            }
            break;    

        case ITI_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                this_ITI_dur = random(ITI_dur_min, ITI_dur_max);
            }

            // update
            if (last_state == current_state){

            }

            // exit condition
            if (now() - state_entry > this_ITI_dur) {
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
    LEDController();

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
    // if (toggle == false){
    //     digitalWrite(LOOP_PIN, HIGH);
    //     toggle = true;
    // }
    // else {
    //     digitalWrite(LOOP_PIN, LOW);
    //     toggle = false;
    // }
}
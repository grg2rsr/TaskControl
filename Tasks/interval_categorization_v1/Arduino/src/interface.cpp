// basic outline of the reader taken from
// http://forum.arduino.cc/index.php?topic=396450.0

#include <Arduino.h>
#include "interface_variables.h"

// this line limits total command length to 128 chars - adjust if necessary (very long var names)
const byte numChars = 128;
char receivedChars[numChars];
char buf[numChars];

boolean newData = false;
bool verbose = true;
bool run = false;
bool deliver_reward_left = false;
bool deliver_reward_right = false;
bool present_reward_left_cue = false;
bool present_reward_right_cue = false;

int left = 4; // fwd declared now in the interface_template
int right = 6; // fwd declared now in the interface_template
int correct_side;
int current_state = 0; // WATCH OUT this is ini state

// fwd declare functions for logging
unsigned long now();
void log_bool(const char name[], bool value);
void log_int(const char name[], int value);
// void log_long(const char name[], long value);
void log_ulong(const char name[], unsigned long value);
void log_float(const char name[], float value);

void getSerialData() {
    // check if command data is available and if yes read it
    // all commands are flanked by <>

    static boolean recvInProgress = false;
    static byte ndx = 0;
    char startMarker = '<';
    char endMarker = '>';
    char rc;
 
    // loop that reads the entire command
    while (Serial.available() > 0 && newData == false) {
        rc = Serial.read();

        // read until end marker
        if (recvInProgress == true) {
            if (rc != endMarker) {
                receivedChars[ndx] = rc;
                ndx++;
                if (ndx >= numChars) {
                    ndx = numChars - 1;
                }
            }
            else {
                receivedChars[ndx] = '\0'; // terminate the string
                recvInProgress = false;
                ndx = 0;
                newData = true;
            }
        }

        // enter reading if startmarker received
        else if (rc == startMarker) {
            recvInProgress = true;
        }
    }
}

void processSerialData() {
    if (newData == true) {
        // echo back command if verbose
        if (verbose==true) {
            snprintf(buf, sizeof(buf), "<Arduino received: %s>", receivedChars);
            Serial.println(buf);
        }

        // get total length of message
        unsigned int len = 0;
        for (unsigned int i = 0; i < numChars; i++){
            if (receivedChars[i] == '\0'){
                len = i;
                break;
            }
        }

        // GET SET CMD 
        char mode[4];
        strlcpy(mode, receivedChars, 4);

        // GET
        if (strcmp(mode,"GET")==0){
            char varname[len-4+1];
            strlcpy(varname, receivedChars+4, len-4+1);

        // INSERT_GETTERS

        if (strcmp(varname,"tone_dur")==0){
            log_ulong("tone_dur", tone_dur);
        }

        if (strcmp(varname,"tone_freq")==0){
            log_ulong("tone_freq", tone_freq);
        }

        if (strcmp(varname,"buzz_dur")==0){
            log_ulong("buzz_dur", buzz_dur);
        }

        if (strcmp(varname,"kamin_block_protect_dur_min")==0){
            log_ulong("kamin_block_protect_dur_min", kamin_block_protect_dur_min);
        }

        if (strcmp(varname,"kamin_block_protect_dur_max")==0){
            log_ulong("kamin_block_protect_dur_max", kamin_block_protect_dur_max);
        }

        if (strcmp(varname,"trial_entry_buzz_dur")==0){
            log_ulong("trial_entry_buzz_dur", trial_entry_buzz_dur);
        }

        if (strcmp(varname,"buzz_center_freq")==0){
            log_ulong("buzz_center_freq", buzz_center_freq);
        }

        if (strcmp(varname,"buzz_high_freq")==0){
            log_ulong("buzz_high_freq", buzz_high_freq);
        }

        if (strcmp(varname,"buzz_low_freq")==0){
            log_ulong("buzz_low_freq", buzz_low_freq);
        }

        if (strcmp(varname,"led_hsv")==0){
            log_int("led_hsv", led_hsv);
        }

        if (strcmp(varname,"led_brightness")==0){
            log_int("led_brightness", led_brightness);
        }

        if (strcmp(varname,"ITI_dur_min")==0){
            log_ulong("ITI_dur_min", ITI_dur_min);
        }

        if (strcmp(varname,"ITI_dur_max")==0){
            log_ulong("ITI_dur_max", ITI_dur_max);
        }

        if (strcmp(varname,"timeout_dur")==0){
            log_ulong("timeout_dur", timeout_dur);
        }

        if (strcmp(varname,"choice_dur")==0){
            log_ulong("choice_dur", choice_dur);
        }

        if (strcmp(varname,"reward_collection_dur")==0){
            log_ulong("reward_collection_dur", reward_collection_dur);
        }

        if (strcmp(varname,"present_init_cue")==0){
            log_int("present_init_cue", present_init_cue);
        }

        if (strcmp(varname,"LED_enabled")==0){
            log_int("LED_enabled", LED_enabled);
        }

        if (strcmp(varname,"prob_bias_corr")==0){
            log_int("prob_bias_corr", prob_bias_corr);
        }

        if (strcmp(varname,"correction_loops")==0){
            log_int("correction_loops", correction_loops);
        }

        if (strcmp(varname,"corr_loop_entry")==0){
            log_int("corr_loop_entry", corr_loop_entry);
        }

        if (strcmp(varname,"corr_loop_exit")==0){
            log_int("corr_loop_exit", corr_loop_exit);
        }

        if (strcmp(varname,"trial_autostart")==0){
            log_int("trial_autostart", trial_autostart);
        }

        if (strcmp(varname,"autodeliver_rewards")==0){
            log_int("autodeliver_rewards", autodeliver_rewards);
        }

        if (strcmp(varname,"cue_on_rewarded_touch")==0){
            log_int("cue_on_rewarded_touch", cue_on_rewarded_touch);
        }

        if (strcmp(varname,"use_warmup")==0){
            log_int("use_warmup", use_warmup);
        }

        if (strcmp(varname,"n_warmup_trials")==0){
            log_int("n_warmup_trials", n_warmup_trials);
        }

        if (strcmp(varname,"punish_premature")==0){
            log_int("punish_premature", punish_premature);
        }

        if (strcmp(varname,"use_incorrect_cue_on_miss")==0){
            log_int("use_incorrect_cue_on_miss", use_incorrect_cue_on_miss);
        }

        if (strcmp(varname,"p_left")==0){
            log_float("p_left", p_left);
        }

        if (strcmp(varname,"p_timing_trial")==0){
            log_float("p_timing_trial", p_timing_trial);
        }

        if (strcmp(varname,"touch_block_dur")==0){
            log_ulong("touch_block_dur", touch_block_dur);
        }

        if (strcmp(varname,"min_grasp_dur")==0){
            log_ulong("min_grasp_dur", min_grasp_dur);
        }

        if (strcmp(varname,"left_short")==0){
            log_int("left_short", left_short);
        }

        if (strcmp(varname,"reward_magnitude")==0){
            log_ulong("reward_magnitude", reward_magnitude);
        }

        if (strcmp(varname,"valve_ul_ms_left")==0){
            log_float("valve_ul_ms_left", valve_ul_ms_left);
        }

        if (strcmp(varname,"valve_ul_ms_right")==0){
            log_float("valve_ul_ms_right", valve_ul_ms_right);
        }

        }

        // SET
        if (strcmp(mode,"SET")==0){
            char line[len-4+1];
            strlcpy(line, receivedChars+4, len-4+1);

            // get index of space
            len = sizeof(line)/sizeof(char);
            unsigned int split = 0;
            for (unsigned int i = 0; i < numChars; i++){
                if (line[i] == ' '){
                    split = i;
                    break;
                }
            }

            // split by space
            char varname[split+1];
            strlcpy(varname, line, split+1);

            char varvalue[len-split+1];
            strlcpy(varvalue, line+split+1, len-split+1);

            // INSERT_SETTERS

        if (strcmp(varname,"tone_dur")==0){
            tone_dur = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"tone_freq")==0){
            tone_freq = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"buzz_dur")==0){
            buzz_dur = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"kamin_block_protect_dur_min")==0){
            kamin_block_protect_dur_min = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"kamin_block_protect_dur_max")==0){
            kamin_block_protect_dur_max = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"trial_entry_buzz_dur")==0){
            trial_entry_buzz_dur = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"buzz_center_freq")==0){
            buzz_center_freq = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"buzz_high_freq")==0){
            buzz_high_freq = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"buzz_low_freq")==0){
            buzz_low_freq = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"led_hsv")==0){
            led_hsv = atoi(varvalue);
        }

        if (strcmp(varname,"led_brightness")==0){
            led_brightness = atoi(varvalue);
        }

        if (strcmp(varname,"ITI_dur_min")==0){
            ITI_dur_min = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"ITI_dur_max")==0){
            ITI_dur_max = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"timeout_dur")==0){
            timeout_dur = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"choice_dur")==0){
            choice_dur = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"reward_collection_dur")==0){
            reward_collection_dur = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"present_init_cue")==0){
            present_init_cue = atoi(varvalue);
        }

        if (strcmp(varname,"LED_enabled")==0){
            LED_enabled = atoi(varvalue);
        }

        if (strcmp(varname,"prob_bias_corr")==0){
            prob_bias_corr = atoi(varvalue);
        }

        if (strcmp(varname,"correction_loops")==0){
            correction_loops = atoi(varvalue);
        }

        if (strcmp(varname,"corr_loop_entry")==0){
            corr_loop_entry = atoi(varvalue);
        }

        if (strcmp(varname,"corr_loop_exit")==0){
            corr_loop_exit = atoi(varvalue);
        }

        if (strcmp(varname,"trial_autostart")==0){
            trial_autostart = atoi(varvalue);
        }

        if (strcmp(varname,"autodeliver_rewards")==0){
            autodeliver_rewards = atoi(varvalue);
        }

        if (strcmp(varname,"cue_on_rewarded_touch")==0){
            cue_on_rewarded_touch = atoi(varvalue);
        }

        if (strcmp(varname,"use_warmup")==0){
            use_warmup = atoi(varvalue);
        }

        if (strcmp(varname,"n_warmup_trials")==0){
            n_warmup_trials = atoi(varvalue);
        }

        if (strcmp(varname,"punish_premature")==0){
            punish_premature = atoi(varvalue);
        }

        if (strcmp(varname,"use_incorrect_cue_on_miss")==0){
            use_incorrect_cue_on_miss = atoi(varvalue);
        }

        if (strcmp(varname,"p_left")==0){
            p_left = atof(varvalue);
        }

        if (strcmp(varname,"p_timing_trial")==0){
            p_timing_trial = atof(varvalue);
        }

        if (strcmp(varname,"touch_block_dur")==0){
            touch_block_dur = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"min_grasp_dur")==0){
            min_grasp_dur = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"left_short")==0){
            left_short = atoi(varvalue);
        }

        if (strcmp(varname,"reward_magnitude")==0){
            reward_magnitude = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"valve_ul_ms_left")==0){
            valve_ul_ms_left = atof(varvalue);
        }

        if (strcmp(varname,"valve_ul_ms_right")==0){
            valve_ul_ms_right = atof(varvalue);
        }

        }

        // UPD - update trial probs - HARDCODED for now, n trials
        // format UPD 0 0.031 or similar
        // if (strcmp(mode,"UPD")==0){
            
        //     char line[len-4+1];
        //     strlcpy(line, receivedChars+4, len-4+1);

        //     // get index of space
        //     len = sizeof(line)/sizeof(char);
        //     unsigned int split = 0;
        //     for (unsigned int i = 0; i < numChars; i++){
        //         if (line[i] == ' '){
        //             split = i;
        //             break;
        //         }
        //     }

        //     // split by space
        //     char varname[split+1];
        //     strlcpy(varname, line, split+1);

        //     char varvalue[len-split+1];
        //     strlcpy(varvalue, line+split+1, len-split+1);

        //     int ix = atoi(varname);
        //     float p = atof(varvalue);
        //     p_interval[ix] = p;
        // }

        // CMD
        if (strcmp(mode,"CMD")==0){
            char CMD[len-4+1];
            strlcpy(CMD, receivedChars+4, len-4+1);

            // manually implement functions here

            // Stop and Go functionality
            if (strcmp(CMD,"RUN")==0){
                run = true;
                Serial.println("<Arduino is running>");
            }

            if (strcmp(CMD,"HALT")==0){
                run = false;
                Serial.println("<Arduino is halted>");
            }

            if (strcmp(CMD,"r")==0){
                present_reward_left_cue = true;
                deliver_reward_left = true;
            }

            if (strcmp(CMD,"t")==0){
                present_reward_right_cue = true;
                deliver_reward_right = true;
            }

            if (strcmp(CMD,"g")==0){
                present_reward_left_cue = true;
            }

            if (strcmp(CMD,"f")==0){
                present_reward_right_cue = true;
            }

            if (strcmp(CMD,"b")==0){
                correct_side = right;
                current_state = CHOICE_STATE;
            }

            if (strcmp(CMD,"v")==0){
                correct_side = right;
                current_state = CHOICE_STATE;
            }


        }

        newData = false;
    }
}

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
bool deliver_reward = false;
bool present_reward_cue = false;
bool punish = false;

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

        if (strcmp(varname,"correct_choice_cue_freq")==0){
            log_int("correct_choice_cue_freq", correct_choice_cue_freq);
        }

        if (strcmp(varname,"choice_dur")==0){
            log_ulong("choice_dur", choice_dur);
        }

        if (strcmp(varname,"ITI_dur_min")==0){
            log_ulong("ITI_dur_min", ITI_dur_min);
        }

        if (strcmp(varname,"ITI_dur_max")==0){
            log_ulong("ITI_dur_max", ITI_dur_max);
        }

        if (strcmp(varname,"min_fix_dur")==0){
            log_ulong("min_fix_dur", min_fix_dur);
        }

        if (strcmp(varname,"reward_magnitude")==0){
            log_ulong("reward_magnitude", reward_magnitude);
        }

        if (strcmp(varname,"valve_ul_ms")==0){
            log_float("valve_ul_ms", valve_ul_ms);
        }

        if (strcmp(varname,"reward_available_dur")==0){
            log_ulong("reward_available_dur", reward_available_dur);
        }

        if (strcmp(varname,"X_thresh")==0){
            log_float("X_thresh", X_thresh);
        }

        if (strcmp(varname,"X_thresh_start")==0){
            log_float("X_thresh_start", X_thresh_start);
        }

        if (strcmp(varname,"X_thresh_target")==0){
            log_float("X_thresh_target", X_thresh_target);
        }

        if (strcmp(varname,"X_thresh_increment")==0){
            log_float("X_thresh_increment", X_thresh_increment);
        }

        if (strcmp(varname,"X_thresh_decrement")==0){
            log_float("X_thresh_decrement", X_thresh_decrement);
        }

        if (strcmp(varname,"XY_fix_box")==0){
            log_float("XY_fix_box", XY_fix_box);
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

        if (strcmp(varname,"omit_rewards")==0){
            log_int("omit_rewards", omit_rewards);
        }

        if (strcmp(varname,"fps")==0){
            log_int("fps", fps);
        }

        if (strcmp(varname,"bias")==0){
            log_float("bias", bias);
        }

        if (strcmp(varname,"contrast")==0){
            log_float("contrast", contrast);
        }

        if (strcmp(varname,"sigma")==0){
            log_float("sigma", sigma);
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

        if (strcmp(varname,"correct_choice_cue_freq")==0){
            correct_choice_cue_freq = atoi(varvalue);
        }

        if (strcmp(varname,"choice_dur")==0){
            choice_dur = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"ITI_dur_min")==0){
            ITI_dur_min = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"ITI_dur_max")==0){
            ITI_dur_max = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"min_fix_dur")==0){
            min_fix_dur = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"reward_magnitude")==0){
            reward_magnitude = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"valve_ul_ms")==0){
            valve_ul_ms = atof(varvalue);
        }

        if (strcmp(varname,"reward_available_dur")==0){
            reward_available_dur = strtoul(varvalue,NULL,10);
        }

        if (strcmp(varname,"X_thresh")==0){
            X_thresh = atof(varvalue);
        }

        if (strcmp(varname,"X_thresh_start")==0){
            X_thresh_start = atof(varvalue);
        }

        if (strcmp(varname,"X_thresh_target")==0){
            X_thresh_target = atof(varvalue);
        }

        if (strcmp(varname,"X_thresh_increment")==0){
            X_thresh_increment = atof(varvalue);
        }

        if (strcmp(varname,"X_thresh_decrement")==0){
            X_thresh_decrement = atof(varvalue);
        }

        if (strcmp(varname,"XY_fix_box")==0){
            XY_fix_box = atof(varvalue);
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

        if (strcmp(varname,"omit_rewards")==0){
            omit_rewards = atoi(varvalue);
        }

        if (strcmp(varname,"fps")==0){
            fps = atoi(varvalue);
        }

        if (strcmp(varname,"bias")==0){
            bias = atof(varvalue);
        }

        if (strcmp(varname,"contrast")==0){
            contrast = atof(varvalue);
        }

        if (strcmp(varname,"sigma")==0){
            sigma = atof(varvalue);
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
                deliver_reward = true;
                present_reward_cue = true;
            }

            if (strcmp(CMD,"p")==0){
                punish = true;
            }
        }

        newData = false;
    }
}

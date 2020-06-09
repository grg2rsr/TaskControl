// basic outline of the reader taken from
// http://forum.arduino.cc/index.php?topic=396450.0

#include <Arduino.h>
#include <string.h>

#include "interface_variables.h"

// this line limits total command length to 200 chars - adjust if necessary (very long var names)
const byte numChars = 200;
char receivedChars[numChars];
boolean newData = false;
bool verbose = true;
bool run = false;
bool deliver_reward = false;
// bool punish = false;

int current_state = 0; // WATCH OUT this is ini state

// HARDCODED trial type probabilites
float p_interval[6] = {1,0.5,0,0,0.5,1}; // FIXME HARDCODE

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
            Serial.print("<Arduino received: ");
            Serial.print(receivedChars);
            Serial.println(">");
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

            if (strcmp(varname,"stage")==0){
                Serial.println(String("<")+String(varname)+String("=")+String(stage)+String(">"));
            }
    
            if (strcmp(varname,"punish_tone_freq")==0){
                Serial.println(String("<")+String(varname)+String("=")+String(punish_tone_freq)+String(">"));
            }
    
            if (strcmp(varname,"stim_tone_freq")==0){
                Serial.println(String("<")+String(varname)+String("=")+String(stim_tone_freq)+String(">"));
            }
    
            if (strcmp(varname,"reward_cue_freq")==0){
                Serial.println(String("<")+String(varname)+String("=")+String(reward_cue_freq)+String(">"));
            }
    
            if (strcmp(varname,"reward_tone_freq")==0){
                Serial.println(String("<")+String(varname)+String("=")+String(reward_tone_freq)+String(">"));
            }
    
            if (strcmp(varname,"trial_avail_dur")==0){
                Serial.println(String("<")+String(varname)+String("=")+String(trial_avail_dur)+String(">"));
            }
    
            if (strcmp(varname,"choice_dur")==0){
                Serial.println(String("<")+String(varname)+String("=")+String(choice_dur)+String(">"));
            }
    
            if (strcmp(varname,"timeout_dur")==0){
                Serial.println(String("<")+String(varname)+String("=")+String(timeout_dur)+String(">"));
            }
    
            if (strcmp(varname,"ITI_dur")==0){
                Serial.println(String("<")+String(varname)+String("=")+String(ITI_dur)+String(">"));
            }
    
            if (strcmp(varname,"reward_magnitude")==0){
                Serial.println(String("<")+String(varname)+String("=")+String(reward_magnitude)+String(">"));
            }
    
            if (strcmp(varname,"valve_ul_ms")==0){
                Serial.println(String("<")+String(varname)+String("=")+String(valve_ul_ms)+String(">"));
            }
    
            if (strcmp(varname,"reward_available_dur")==0){
                Serial.println(String("<")+String(varname)+String("=")+String(reward_available_dur)+String(">"));
            }
    
            if (strcmp(varname,"X_left_thresh")==0){
                Serial.println(String("<")+String(varname)+String("=")+String(X_left_thresh)+String(">"));
            }
    
            if (strcmp(varname,"X_right_thresh")==0){
                Serial.println(String("<")+String(varname)+String("=")+String(X_right_thresh)+String(">"));
            }
    
            if (strcmp(varname,"Y_back_thresh")==0){
                Serial.println(String("<")+String(varname)+String("=")+String(Y_back_thresh)+String(">"));
            }
    
            if (strcmp(varname,"Y_front_thresh")==0){
                Serial.println(String("<")+String(varname)+String("=")+String(Y_front_thresh)+String(">"));
            }
                if (strcmp(varname,"current_state")==0){
                Serial.println(String("<")+String(varname)+String("=")+String(current_state)+String(">"));
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

            // for the state machine "force state" buttons
            if (strcmp(varname,"current_state")==0){
                current_state = atoi(varvalue);
            }

            // INSERT_SETTERS

            if (strcmp(varname,"stage")==0){
                stage = atoi(varvalue);
            }
    
            if (strcmp(varname,"punish_tone_freq")==0){
                punish_tone_freq = atoi(varvalue);
            }
    
            if (strcmp(varname,"stim_tone_freq")==0){
                stim_tone_freq = atoi(varvalue);
            }
    
            if (strcmp(varname,"reward_cue_freq")==0){
                reward_cue_freq = atoi(varvalue);
            }
    
            if (strcmp(varname,"reward_tone_freq")==0){
                reward_tone_freq = atoi(varvalue);
            }
    
            if (strcmp(varname,"trial_avail_dur")==0){
                trial_avail_dur = strtoul(varvalue,NULL,10);
            }
    
            if (strcmp(varname,"choice_dur")==0){
                choice_dur = strtoul(varvalue,NULL,10);
            }
    
            if (strcmp(varname,"timeout_dur")==0){
                timeout_dur = strtoul(varvalue,NULL,10);
            }
    
            if (strcmp(varname,"ITI_dur")==0){
                ITI_dur = strtoul(varvalue,NULL,10);
            }
    
            if (strcmp(varname,"reward_magnitude")==0){
                reward_magnitude = strtoul(varvalue,NULL,10);
            }
    
            if (strcmp(varname,"reward_available_dur")==0){
                reward_available_dur = strtoul(varvalue,NULL,10);
            }
    
            if (strcmp(varname,"valve_ul_ms")==0){
                valve_ul_ms = atof(varvalue);
            }
    
            if (strcmp(varname,"X_left_thresh")==0){
                X_left_thresh = atof(varvalue);
            }
    
            if (strcmp(varname,"X_right_thresh")==0){
                X_right_thresh = atof(varvalue);
            }
    
            if (strcmp(varname,"Y_back_thresh")==0){
                Y_back_thresh = atof(varvalue);
            }
    
            if (strcmp(varname,"Y_front_thresh")==0){
                Y_front_thresh = atof(varvalue);
            }
    
        }

        // UPD - update trial probs - HARDCODED for now, n trials
        // format UPD 0 0.031 or similar
        if (strcmp(mode,"UPD")==0){
            
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

            int ix = atoi(varname);
            float p = atof(varvalue);
            p_interval[ix] = p;
        }

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
            }

            // if (strcmp(CMD,"p")==0){
            //     punish = true;
            // }
        }

        newData = false;
    }
}

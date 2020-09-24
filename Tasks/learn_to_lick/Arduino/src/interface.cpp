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
bool present_reward_cue = false;
bool punish = false;

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

            if (strcmp(varname,"correct_choice_cue_freq")==0){
                Serial.println(String("<VAR ")+String(varname)+String("=")+String(correct_choice_cue_freq)+String(">"));
            }
    
            if (strcmp(varname,"ITI_dur_min")==0){
                Serial.println(String("<VAR ")+String(varname)+String("=")+String(ITI_dur_min)+String(">"));
            }
    
            if (strcmp(varname,"ITI_dur_max")==0){
                Serial.println(String("<VAR ")+String(varname)+String("=")+String(ITI_dur_max)+String(">"));
            }
    
            if (strcmp(varname,"reward_magnitude")==0){
                Serial.println(String("<VAR ")+String(varname)+String("=")+String(reward_magnitude)+String(">"));
            }
    
            if (strcmp(varname,"valve_ul_ms")==0){
                Serial.println(String("<VAR ")+String(varname)+String("=")+String(valve_ul_ms)+String(">"));
            }
    
            if (strcmp(varname,"reward_available_dur")==0){
                Serial.println(String("<VAR ")+String(varname)+String("=")+String(reward_available_dur)+String(">"));
            }
    
            if (strcmp(varname,"p_reward")==0){
                Serial.println(String("<VAR ")+String(varname)+String("=")+String(p_reward)+String(">"));
            }
    
            if (strcmp(varname,"p_rewarded_cue")==0){
                Serial.println(String("<VAR ")+String(varname)+String("=")+String(p_rewarded_cue)+String(">"));
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
            // if (strcmp(varname,"current_state")==0){
            //     current_state = atoi(varvalue);
            // }

            // INSERT_SETTERS

            if (strcmp(varname,"correct_choice_cue_freq")==0){
                correct_choice_cue_freq = atoi(varvalue);
            }
    
            if (strcmp(varname,"ITI_dur_min")==0){
                ITI_dur_min = strtoul(varvalue,NULL,10);
            }
    
            if (strcmp(varname,"ITI_dur_max")==0){
                ITI_dur_max = strtoul(varvalue,NULL,10);
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
    
            if (strcmp(varname,"p_reward")==0){
                p_reward = atof(varvalue);
            }
    
            if (strcmp(varname,"p_rewarded_cue")==0){
                p_rewarded_cue = atof(varvalue);
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
                present_reward_cue = true;
            }

            if (strcmp(CMD,"p")==0){
                punish = true;
            }
        }

        newData = false;
    }
}

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

int current_state = 1;

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
            Serial.print("Arduino received: ");
            Serial.println(receivedChars);
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

            if (strcmp(varname,"fix_dur")==0){
                Serial.println(String(varname)+String("=")+String(fix_dur));
            }
    
            if (strcmp(varname,"trial_entry_fix_dur")==0){
                Serial.println(String(varname)+String("=")+String(trial_entry_fix_dur));
            }
    
            if (strcmp(varname,"max_dist")==0){
                Serial.println(String(varname)+String("=")+String(max_dist));
            }
    
            if (strcmp(varname,"reward_valve_dur")==0){
                Serial.println(String(varname)+String("=")+String(reward_valve_dur));
            }
    
            if (strcmp(varname,"reward_available_dur")==0){
                Serial.println(String(varname)+String("=")+String(reward_available_dur));
            }
    
            if (strcmp(varname,"ITI_dur")==0){
                Serial.println(String(varname)+String("=")+String(ITI_dur));
            }
    
            if (strcmp(varname,"timeout_dur")==0){
                Serial.println(String(varname)+String("=")+String(timeout_dur));
            }
    
            if (strcmp(varname,"reward_tone_freq")==0){
                Serial.println(String(varname)+String("=")+String(reward_tone_freq));
            }
    
            if (strcmp(varname,"punish_tone_freq")==0){
                Serial.println(String(varname)+String("=")+String(punish_tone_freq));
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

            if (strcmp(varname,"reward_tone_freq")==0){
                reward_tone_freq = atoi(varvalue);
            }
    
            if (strcmp(varname,"punish_tone_freq")==0){
                punish_tone_freq = atoi(varvalue);
            }
    
            if (strcmp(varname,"fix_dur")==0){
                fix_dur = strtoul(varvalue,NULL,10);
            }
    
            if (strcmp(varname,"trial_entry_fix_dur")==0){
                trial_entry_fix_dur = strtoul(varvalue,NULL,10);
            }
    
            if (strcmp(varname,"reward_valve_dur")==0){
                reward_valve_dur = strtoul(varvalue,NULL,10);
            }
    
            if (strcmp(varname,"reward_available_dur")==0){
                reward_available_dur = strtoul(varvalue,NULL,10);
            }
    
            if (strcmp(varname,"ITI_dur")==0){
                ITI_dur = strtoul(varvalue,NULL,10);
            }
    
            if (strcmp(varname,"timeout_dur")==0){
                timeout_dur = strtoul(varvalue,NULL,10);
            }
    
            if (strcmp(varname,"max_dist")==0){
                max_dist = atof(varvalue);
            }
    
        }

        // CMD
        if (strcmp(mode,"CMD")==0){
            char CMD[len-4+1];
            strlcpy(CMD, receivedChars+4, len-4+1);

            // manually implement functions here

            // Stop and Go functionality
            if (strcmp(CMD,"RUN")==0){
                run = true;
                Serial.println("Arduino is running");
            }

            if (strcmp(CMD,"HALT")==0){
                run = false;
                Serial.println("Arduino is halted");
            }
        }

        newData = false;
    }
}

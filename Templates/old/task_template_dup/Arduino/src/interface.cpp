// basic outline of the reader taken from
// http://forum.arduino.cc/index.php?topic=396450.0

#include <Arduino.h>
#include <string.h>

// FIXME refactor this to something more meaningful
#include "init_variables.h" 

// this line limits total command length to 200 chars
// adjust if necessary

const byte numChars = 200;
char receivedChars[numChars];
boolean newData = false;
bool verbose = true;

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

            if (strcmp(varname,"b_low")==0){
                Serial.println(String(varname)+String("=")+String(b_low));
            }

            if (strcmp(varname,"t_low")==0){
                Serial.println(String(varname)+String("=")+String(t_low));
            }

            if (strcmp(varname,"f_low")==0){
                Serial.println(String(varname)+String("=")+String(f_low));
            }

            if (strcmp(varname,"t_high")==0){
                Serial.println(String(varname)+String("=")+String(t_high));
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

            // parse dtype
            String dtype = "unset";

            // test for bool 
            if ((dtype == "true") || (dtype == "false")) {
                dtype = "bool";
            }

            // test for float (has decimal point)
            unsigned int num_len = sizeof(varvalue)/sizeof(char);
            for (unsigned int i = 0; i < num_len; i++) {
                if (varvalue[i] == '.') {
                    // isFloat = true;
                    dtype = "float";
                }
            }

            // else must be int
            if (dtype == "unset"){
                dtype = "int";
            }

            // INSERT_SETTERS

            if (dtype == "bool") {
                if (strcmp(varname,"b_low")==0){
                    if (strcmp(varvalue,"false")==0) {
                        b_low = false;
                    }
                    else {
                        b_low = true;
                    }
                }
            }

            if (dtype == "int") {
                if (strcmp(varname,"t_low")==0){
                    t_low = atoi(varvalue);
                }
            }

            if (dtype == "int") {
                if (strcmp(varname,"t_high")==0){
                    t_high = atoi(varvalue);
                }
            }

            if (dtype == "float") {
                if (strcmp(varname,"f_low")==0){
                    f_low = atof(varvalue);
                }
            }

        }

        // CMD
        if (strcmp(mode,"CMD")==0){
            // manually implement functions here
            // problematic because forward deleration needed
        }

        newData = false;
    }
}
#include <Arduino.h>
#include <string.h>

float X;
float Y;

float x;
float y;

bool RawNewData = false;

// const byte buffer_size = 64; // to hold the entire arduino buffer
// char buffer[buffer_size];
char start_marker = '[';
char end_marker = ']';

const byte recv_bytes_size = 8; // for two floats
char recv_bytes[recv_bytes_size];

int end_ix;
int start_ix;
int ix;
int rc;
bool is_receiving = false;

void flush(){
    while (Serial1.available() > 0){
        char t = Serial1.read();
    }
}

void getRawData() {

    while (Serial1.available() > 0){
        rc = Serial1.read();

        if (is_receiving == true){
            if (ix < recv_bytes_size){
                recv_bytes[ix] = rc;
                ix++;
            }
            else{
                if (rc == end_marker){
                    // all is well
                    RawNewData = true;
                }
                is_receiving = false;
                ix = 0;
                flush();
            }
        }

        if (rc == start_marker){
            is_receiving = true;
            ix = 0;
        }
    }
}

typedef union {
    unsigned char b[4];
    float f;
} bfloat;

int error_counter = 0;
void processRawData() {

    if (RawNewData == true) {
        // in here split into two floats and store them in the corresponding arduino variables

        // the illegal union hack after  
        // https://stackoverflow.com/questions/17732630/cast-byte-array-to-float/17732822#17732822

        //Create instances of the union
        bfloat Xb;
        Xb.b[0] = recv_bytes[0]; 
        Xb.b[1] = recv_bytes[1]; 
        Xb.b[2] = recv_bytes[2]; 
        Xb.b[3] = recv_bytes[3]; 

        bfloat Yb;
        Yb.b[0] = recv_bytes[4]; 
        Yb.b[1] = recv_bytes[5]; 
        Yb.b[2] = recv_bytes[6]; 
        Yb.b[3] = recv_bytes[7];

        // store
        x = (float) Xb.f;
        y = (float) Yb.f;
        
        // float dX = X-x;
        // float dY = Y-y;

        if (x < -10000 || x > 10000 || y < -10000 || y > 10000){
            Serial.println(String("<MSG garbage read") + " "+String(micros()/1000.0)+">");
            Serial.println(String(x));
            Serial.println(String(y));
        }
        else{
            X = x;
            Y = y;
        }
        // if (error_counter > 4){
        //     flush();
        // }

        // if ((abs(dX) > 4000 || abs(dY) > 4000) && error_counter < 5){
        //     Serial.println(String(x));
        //     Serial.println(String(y));
        //     error_counter++;
        //     // X = 0;
        //     // x = 0;
        //     // Y = 0;
        //     // y = 0;
        // }
        // else{
        //     X = x;
        //     Y = y;
        //     error_counter = 0;
        // }

        // if (x < 10000 && x > -10000){
        //     if (abs(X-x) < 4000) {
        //         X = x;
        //     }
        // }
        // else {
        //     Serial.println(String("<MSG X out of bounds") + " "+String(micros()/1000.0)+">");
        // }

        // if (y < 10000 && y > -10000){
        //     if (abs(Y-y) < 4000) {
        //         Y = y;
        //     }
        // }
        // else {
        //     Serial.println(String("<MSG Y out of bounds") + " "+String(micros()/1000.0)+">");
        // }
    }
    RawNewData = false;
}

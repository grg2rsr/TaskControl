#include <Arduino.h>
#include <string.h>

float X;
float Y;

float x;
float y;

bool RawNewData = false;
char start_marker = '[';
char end_marker = ']';

const byte recv_bytes_size = 8; // for two floats
char recv_bytes[recv_bytes_size];

int end_ix;
int start_ix;
int ix;
int rc;
bool is_receiving = false;

char t;
void flush(){
    while (Serial1.available() > 0){
        t = Serial1.read();
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
        
        if (x < -10000 || x > 10000 || y < -10000 || y > 10000){
            Serial.println("LC read out of bounds");
            Serial.println(x);
            Serial.println(y);
        }
        else{
            X = x;
            Y = y;
        }
    }
    RawNewData = false;
}

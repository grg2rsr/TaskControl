// basic outline of the reader taken from
// http://forum.arduino.cc/index.php?topic=396450.0

#include <Arduino.h>
#include <string.h>

float X;
float Y;

const byte numBytes = 8; // for two floats
char receivedBytes[numBytes];
boolean RawNewData = false;

void getRawData() {
    // check if raw data is available and if yes read it
    // all raw data bytes are flanked by []
    // for future generalization: maybe include here a (data type)
    // that then can be used o infer how many bytes to read, as in (i4)bbbb

    // https://stackoverflow.com/questions/3991478/building-a-32-bit-float-out-of-its-4-composite-bytes

    // also https://www.microchip.com/forums/m590535.aspx

    static boolean RawRecvInProgress = false;
    static int raw_ndx = 0;
    char RawStartMarker = '[';
    char RawEndMarker = ']';
    int rc;
 
    // loop that reads the entire command
    while (Serial1.available() > 0 && RawNewData == false) {
        rc = Serial1.read();

        // read until end marker
        if (RawRecvInProgress == true) {
            if (rc != RawEndMarker) {
                if (raw_ndx > numBytes-1) { // this should be resistent to failed [ reads
                    RawRecvInProgress = false;
                    RawNewData = true;
                }
                else {
                    receivedBytes[raw_ndx] = rc;
                    raw_ndx++;
                }
            }
            else {
                RawRecvInProgress = false;
                raw_ndx = 0;
                RawNewData = true;
            }
        }

        // enter reading if startmarker received
        else if (rc == RawStartMarker) {
            RawRecvInProgress = true;
        }
    }
}

typedef union {
    unsigned char b[4];
    float f;
} bfloat;

void processRawData() {
    if (RawNewData == true) {
        // in here split into two floats and store them in the corresponding arduino variables

        // the illegal union hack after  
        // https://stackoverflow.com/questions/17732630/cast-byte-array-to-float/17732822#17732822

        //Create instances of the union
        bfloat Xb;
        Xb.b[0] = receivedBytes[0]; 
        Xb.b[1] = receivedBytes[1]; 
        Xb.b[2] = receivedBytes[2]; 
        Xb.b[3] = receivedBytes[3]; 

        bfloat Yb;
        Yb.b[0] = receivedBytes[4]; 
        Yb.b[1] = receivedBytes[5]; 
        Yb.b[2] = receivedBytes[6]; 
        Yb.b[3] = receivedBytes[7]; 

        X = (float) Xb.f;
        Y = (float) Yb.f;
    }
    RawNewData = false;
}


// this also looks promising
// https://stackoverflow.com/a/3991665
// float bytesToFloatA(uchar b0, uchar b1, uchar b2, uchar b3)
// {
//     float output;

//     *((uchar*)(&output) + 3) = b0;
//     *((uchar*)(&output) + 2) = b1;
//     *((uchar*)(&output) + 1) = b2;
//     *((uchar*)(&output) + 0) = b3;

//     return output;
// }
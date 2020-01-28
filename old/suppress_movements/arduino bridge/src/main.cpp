// a UART bridge
// https://www.arduino.cc/en/Tutorial/MultiSerialMega

#include <Arduino.h>

void setup() {
    Serial.begin(115200);
    Serial1.begin(115200);
    Serial2.begin(115200);
}

void loop() {
  if (Serial.available()) {
    int inByte = Serial.read();
    Serial1.write(inByte);
    Serial2.write(inByte);
  }
}

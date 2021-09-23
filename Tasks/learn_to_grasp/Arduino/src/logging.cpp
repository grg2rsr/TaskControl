#include <Arduino.h>

// time
unsigned long now(){
    return millis();
}

// VAR reporters
char s[128]; // message buffer

void log_bool(const char name[], bool value){
    if (value==true){
        snprintf(s, sizeof(s), "<VAR %s %s %lu>", name, "true", now());
    }
    else {
        snprintf(s, sizeof(s), "<VAR %s %s %lu>", name, "false", now());
    }
    Serial.println(s);
}

void log_int(const char name[], int value){
    snprintf(s, sizeof(s), "<VAR %s %i %lu>", name, value, now());
    Serial.println(s);
}

// void log_long(const char name[], long value){
//     snprintf(s, sizeof(s), "<VAR %s %u %lu>", name, value, now());
//     Serial.println(s);
// }

void log_ulong(const char name[], unsigned long value){
    snprintf(s, sizeof(s), "<VAR %s %lu %lu>", name, value, now());
    Serial.println(s);
}

void log_float(const char name[], float value){
    snprintf(s, sizeof(s), "<VAR %s ", name);
    Serial.print(s);
    Serial.print(value);
    snprintf(s, sizeof(s), " %lu>", now());
    Serial.println(s);
}

// specific

void log_code(int code){
    // Serial.println(String(code) + '\t' + String(now()));
    snprintf(s, sizeof(s), "%u\t%lu", code, now());
    Serial.println(s);
}

void log_msg(const char Message[]){
    // Serial.println("<MSG " + Message + " "+String(now())+">");
    snprintf(s, sizeof(s), "<MSG %s %lu>", Message, now());
    Serial.println(s);
}

// void send_sync_pulse(){
//     // sync w load cell
//     digitalWrite(SYNC_PIN,HIGH);
//     delay(1); // 1 ms unavoidable blindness - TODO delayMicroseconds - test!
//     digitalWrite(SYNC_PIN,LOW);
// }
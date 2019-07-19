// basic outline of the reader taken from
// http://forum.arduino.cc/index.php?topic=396450.0

#include <Arduino.h>
#include <string.h>
#include <event_codes.h>

#include "interface.cpp"


int pin = 52;
int current_state = UP_STATE;
int last_state = INI_STATE;

unsigned long state_entry = 2147483647; // max future

// example sensor read (copied from treadmill task)
// void sample_rotary_encoder(){
//   if ( (float)(millis() - t_last_sample_RE) > dt_RE) {
//     // checks if it is time to measure, if yes, do so and update current speed and pos
//     v = read_RE_calc_v();
//     v_avg = calc_v_avg();
//     // v_avg = v_avg + 0.3;
//     x = x + v_avg * dt_RE;
//     // log treadmill values
//     if (log_RE == true) {
//       print_RE();
//     }
//     t_last_sample_RE = millis();
//   }
// }

// float read_RE_calc_v() {
//   /* samples the rotary encoder, deals with the wraparound of the output pos
//   signals */
//   analog_val = analogRead(rot_enc_pin);
//   wlast = w;
//   w = ((analog_val - RE_min) / (RE_max-RE_min)) * 2*pi; // in [rad]
//   dw = (w - wlast) / (dt_RE/1000); // [rad/s] division by 1k because dt is in ms

//   // both possible wraparounds
//   if (dw < -1*dw_max){ // this happens during forward walking
//     dw = w - (wlast - 2*pi);
//   }
//   if (dw > dw_max){ // this happens during backward walking
//     dw = (w - 2*pi) - wlast;
//   }
//   // calculate current speed and pos from angular speed
//   v = dw * gear_radius; // v on circle = w'[rad/s] * r[m] * 2pi // [2pi/rad]
//   return v; // [m/s]
// }

// void read_lick_IR(){
//   // samples the IR beam for licks
//   if (lick_in == false && digitalRead(lick_pin) == true){
//     print_code(lick_code);
//     lick_in = true;
//     digitalWrite(lick_monitor_pin,HIGH);
//     if (reward_collected == false){
//       reward_collected = true;
//     }
//   }
//   if (lick_in == true && digitalRead(lick_pin) == false){
//     print_code(lick_code+1);
//     lick_in = false;
//     digitalWrite(lick_monitor_pin,LOW);
//   }
// }

// TODO
// logging functions: tstamp, state, value (opt)
// log_state()
// log_value()

void finite_state_machine() {
    switch (current_state) {
        case UP_STATE:
            // state entry
            if (current_state != last_state){
                // log state entry
                Serial.println(millis());
                last_state = current_state;

                // entry actions
                digitalWrite(pin, HIGH);
                state_entry = millis();
            }

            // update
            if (last_state == current_state){
                // state actions
                // delay(t_high);
            }

            // exit condition
            if (millis() - state_entry > t_high) {
                current_state = DOWN_STATE;
            }
            
        case DOWN_STATE:
            // state entry
            if (current_state != last_state){
                // log state entry
                Serial.println(millis());
                last_state = current_state;

                // entry actions
                digitalWrite(pin, LOW);
                state_entry = millis();
            }

            // update
            if (last_state == current_state){
                // state actions
                // delay(t_high);
            }

            // exit condition
            if (millis() - state_entry > t_low) {
                current_state = UP_STATE;
            }
    }
}

void setup() {
    Serial.begin(9600);
    Serial.println("<Arduino is ready to receive commands>");
}

void loop() {
    // put state machine(s) here
    finite_state_machine();

    // sample sensors
    // sample_rotary_encoder();
    // read_lick_IR();

    // and finish loop with those two commands
    getSerialData();
    processSerialData();
}

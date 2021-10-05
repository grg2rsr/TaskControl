#include <Arduino.h>
#include <Tone.h>

#include <event_codes.h> // <>?
#include "interface.cpp"
#include "pin_map.h"
#include "logging.cpp"

/*
.########..########..######..##..........###....########.....###....########.####..#######..##....##..######.
.##.....##.##.......##....##.##.........##.##...##.....##...##.##......##.....##..##.....##.###...##.##....##
.##.....##.##.......##.......##........##...##..##.....##..##...##.....##.....##..##.....##.####..##.##......
.##.....##.######...##.......##.......##.....##.########..##.....##....##.....##..##.....##.##.##.##..######.
.##.....##.##.......##.......##.......#########.##...##...#########....##.....##..##.....##.##..####.......##
.##.....##.##.......##....##.##.......##.....##.##....##..##.....##....##.....##..##.....##.##...###.##....##
.########..########..######..########.##.....##.##.....##.##.....##....##....####..#######..##....##..######.
*/
unsigned long i = 0;
int last_state = REWARD_STATE; 
unsigned long max_future = 4294967295; // 2**32 -1
unsigned long t_state_entry = max_future;

/*
 ######  ######## ##    ##  ######   #######  ########   ######
##    ## ##       ###   ## ##    ## ##     ## ##     ## ##    ##
##       ##       ####  ## ##       ##     ## ##     ## ##
 ######  ######   ## ## ##  ######  ##     ## ########   ######
      ## ##       ##  ####       ## ##     ## ##   ##         ##
##    ## ##       ##   ### ##    ## ##     ## ##    ##  ##    ##
 ######  ######## ##    ##  ######   #######  ##     ##  ######
*/
bool reach = false;
bool is_reaching = false;
bool reward_available = false;
unsigned long t_last_reach_on = max_future;
unsigned long t_last_reach_off = max_future;

void read_reaches(){
    
    reach = digitalRead(REACH_PIN);
    // reach on
    if (is_reaching == false && reach == true){
        log_code(REACH_ON);
        is_reaching = true;
        t_last_reach_on = now();
    }

    // reach off
    if (is_reaching == true && reach == false){
        log_code(REACH_OFF);
        is_reaching = false;
        t_last_reach_off = now();

    }
}

/*
##     ##    ###    ##       ##     ## ########
##     ##   ## ##   ##       ##     ## ##
##     ##  ##   ##  ##       ##     ## ##
##     ## ##     ## ##       ##     ## ######
 ##   ##  ######### ##        ##   ##  ##
  ## ##   ##     ## ##         ## ##   ##
   ###    ##     ## ########    ###    ########
*/

// speaker
Tone tone_controller;

// Magnitude to valve opening time conversion
unsigned long ul2time(float reward_volume, float valve_ul_ms){
    return (unsigned long) reward_volume / valve_ul_ms;
}

bool reward_valve_is_open = false;
unsigned long t_reward_valve_open = max_future;
unsigned long reward_valve_dur;

// Actuates on valve and logs
void open_reward_valve(){
    tone_controller.play(tone_freq, tone_dur);

    digitalWrite(REWARD_VALVE_PIN, HIGH);
    log_code(REWARD_VALVE_ON);
    reward_valve_is_open = true;
    reward_valve_dur = ul2time(reward_magnitude, valve_ul_ms);
    t_reward_valve_open = now();
    deliver_reward = false;
}

void close_reward_valve(){
    digitalWrite(REWARD_VALVE_PIN, LOW);
    log_code(REWARD_VALVE_OFF);
    reward_valve_is_open = false;
}

// Controls the flow 
void reward_valve_controller(){
    
    if (reward_valve_is_open == false && deliver_reward == true) {
        open_reward_valve();
    }

    if (reward_valve_is_open == true && now() - t_reward_valve_open > reward_valve_dur) {
        close_reward_valve();
    }

}

/*
.########..######..##.....##
.##.......##....##.###...###
.##.......##.......####.####
.######....######..##.###.##
.##.............##.##.....##
.##.......##....##.##.....##
.##........######..##.....##
*/
void state_entry_common(){
    // common tasks to do at state entry for all states
    last_state = current_state;
    t_state_entry = now();
    log_code(current_state);
}

void finite_state_machine() {
    // the main FSM
    switch (current_state) {

        case INI_STATE:
            if (current_state != last_state){
                state_entry_common();
                current_state = REWARD_STATE;
            }
            break;

        case REWARD_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();

                if (i > n_trials) {
                    current_state = DONE_STATE;
                    break;
                }
                else{
                    deliver_reward = true;
                    current_state = REWARD_AVAIL_STATE;
                    i++;
                    break;
                }
            }
            break;

        case REWARD_AVAIL_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
            }  
            
            // exit condition
            if (now() - t_state_entry > rew_avail_dur) {
                current_state = REWARD_STATE;
                break;
            }
            break;

        case DONE_STATE:
            if (current_state != last_state){
                state_entry_common();
                current_state = INI_STATE;
                run = false;
                Serial.println("<Arduino is halted>");
            }
            break;
    }
}

/*
.##.....##....###....####.##....##
.###...###...##.##....##..###...##
.####.####..##...##...##..####..##
.##.###.##.##.....##..##..##.##.##
.##.....##.#########..##..##..####
.##.....##.##.....##..##..##...###
.##.....##.##.....##.####.##....##
*/

void setup() {
    delay(1000);

    // ini speakers 
    pinMode(SPEAKER_PIN, OUTPUT);
    tone_controller.begin(SPEAKER_PIN);

    Serial.begin(115200);
    Serial.println("<Arduino is ready to receive commands>");
    delay(1000);
}

void loop() {
    if (run == true){
        // execute state machine(s)
        finite_state_machine();
    }

    // Controllers
    reward_valve_controller();

    // sample sensors
    read_reaches();

    // serial communication
    getSerialData();
    processSerialData();
}
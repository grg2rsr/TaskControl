#include <Arduino.h>
#include <event_codes.h> // <>?
#include "pin_map.h"
#include "interface.cpp"
#include "logging.cpp"
#include <time.h>

// int current_state = INI_STATE; // starting at this, aleady declared in interface.cpp
int last_state = -1; // whatever other state
unsigned long max_future = 4294967295; // 2**32 -1
unsigned long t_state_entry = max_future;
unsigned long this_ITI_dur;

// for random
float r;

// for indexing
int i;
int j;

// for trials
unsigned long this_lick_block_dur = max_future;
unsigned long t_last_trial_entry = max_future;
unsigned long this_delay;
int this_odor;

/*
 ######  ######## ##    ##  ######   #######  ########   ######
##    ## ##       ###   ## ##    ## ##     ## ##     ## ##    ##
##       ##       ####  ## ##       ##     ## ##     ## ##
 ######  ######   ## ## ##  ######  ##     ## ########   ######
      ## ##       ##  ####       ## ##     ## ##   ##         ##
##    ## ##       ##   ### ##    ## ##     ## ##    ##  ##    ##
 ######  ######## ##    ##  ######   #######  ##     ##  ######
*/

bool lick_in = false;
bool is_licking = false;
unsigned long t_last_lick_on = max_future;
unsigned long t_last_lick_off = max_future;

void read_lick(){
    // left
    lick_in = digitalRead(LICK_PIN);
    // lick on
    if (is_licking == false && lick_in == true){
        log_code(LICK_ON);
        is_licking = true;
        t_last_lick_on = now();
    }

    // lick off
    if (is_licking == true && lick_in == false){
        log_code(LICK_OFF);
        is_licking = false;
        t_last_lick_off = now();
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

unsigned long ul2time(float reward_volume){
    return (unsigned long) reward_volume / valve_ul_ms;
}

bool reward_valve_is_closed = true;
// bool deliver_reward = false; // requires to be forward declared in interface.cpp
unsigned long t_reward_valve_open = max_future;
unsigned long reward_valve_dur;

void reward_valve_controller(){
    // a self terminating digital pin switch
    // flipped by setting deliver_reward to true somewhere in the FSM
    
    if (reward_valve_is_closed == true && deliver_reward == true) {
        digitalWrite(REWARD_VALVE_PIN, HIGH);
        log_code(REWARD_VALVE_ON);
        reward_valve_is_closed = false;
        reward_valve_dur = ul2time(reward_magnitude);
        t_reward_valve_open = now();
        deliver_reward = false;
    }

    if (reward_valve_is_closed == false && now() - t_reward_valve_open > reward_valve_dur) {
        digitalWrite(REWARD_VALVE_PIN, LOW);
        log_code(REWARD_VALVE_OFF);
        reward_valve_is_closed = true;
    }
}

// odor valves - similar to the above, self terminating pins
// olfactometer related
int flip[][N_ODORS] = {{0, 1, 2, 3, 4},
                       {4, 0, 1, 2, 3},
                       {3, 4, 0, 1, 2},
                       {2, 3, 4, 0, 1},
                       {1, 2, 3, 4, 0}};

int this_odor_flipped; // this is after flipping
bool odor_is_on[N_ODORS];
// bool switch_odor_on[N_ODORS]; fwd declared in interface
unsigned long t_odor_on[N_ODORS];

void odor_valve_controller(){
    // the controller: iterate over all odorant valves and set their state accordingly
    for (int i = 0; i < N_ODORS; i++){
        if (odor_is_on[i] == false && switch_odor_on[i] == true){
            digitalWrite(ODOR_PINS[i], HIGH);
            digitalWrite(ODOR_BALANCE_PIN, LOW);
            log_int("this_odor", this_odor);
            log_int("this_odor_flipped", this_odor_flipped);
            log_code(ODOR_ON); // odor on
            odor_is_on[i] = true;
            t_odor_on[i] = now();
            switch_odor_on[i] = false;
        }

        // turn off if on for long enough
        if (odor_is_on[i] == true && now() - t_odor_on[i] > odor_on_dur){
            odor_is_on[i] = false;
            digitalWrite(ODOR_PINS[i], LOW);
            digitalWrite(ODOR_BALANCE_PIN, HIGH);
            log_code(ODOR_OFF); // odor on
        }
    }
}

/*
 
  ######  ##    ## ##    ##  ######  
 ##    ##  ##  ##  ###   ## ##    ## 
 ##         ####   ####  ## ##       
  ######     ##    ## ## ## ##       
       ##    ##    ##  #### ##       
 ##    ##    ##    ##   ### ##    ## 
  ######     ##    ##    ##  ######  
 
*/

bool switch_sync_pin = false;
bool sync_pin_is_on = false;
unsigned long t_last_sync_pin_on = max_future;
unsigned long sync_pulse_dur = 100;

void sync_pin_controller(){
    // switch on
    if (switch_sync_pin == true){
        digitalWrite(CAM_SYNC_PIN, HIGH);
        sync_pin_is_on = true;
        switch_sync_pin = false;
        t_last_sync_pin_on = now();
    }
    // switch off
    if (sync_pin_is_on == true && now() - t_last_sync_pin_on > sync_pulse_dur){
        digitalWrite(CAM_SYNC_PIN, LOW);
        sync_pin_is_on = false;
    }
}

/*
######## ########  ####    ###    ##          ######## ##    ## ########  ########
   ##    ##     ##  ##    ## ##   ##             ##     ##  ##  ##     ## ##
   ##    ##     ##  ##   ##   ##  ##             ##      ####   ##     ## ##
   ##    ########   ##  ##     ## ##             ##       ##    ########  ######
   ##    ##   ##    ##  ######### ##             ##       ##    ##        ##
   ##    ##    ##   ##  ##     ## ##             ##       ##    ##        ##
   ##    ##     ## #### ##     ## ########       ##       ##    ##        ########
*/

unsigned long TruncExpDist(unsigned long minimum, unsigned long mean, unsigned long maximum) {

    double e = -double(mean) * log(double(random(1000000) + 1) / double(1000000));
    if (e > maximum || e < minimum) {
        e = TruncExpDist(minimum, mean, maximum);
    }
    return round(e);

}

unsigned int sample_p(float* p, int n){
    // samples discrete prob dist
    // returns index

    float r = rand() / (float) RAND_MAX;
    float p_cumsum;
    
    for (int i = 0; i < n; i++){
        p_cumsum = 0;
        for (int j = 0; j <= i; j++){
            p_cumsum += p[j];
        }
        if (r < p_cumsum){
            return i;
        }
    }
    return n-1;
}

void normalize_p(float* p, int n){
    // in place normalization
    // sums to 1 -> turns into dist
    float p_sum = 0;
    for (int i = 0; i < n; i++){
        p_sum += p[i];
    }
    for (int i = 0; i < n; i++){
        p[i] = p[i] / p_sum;
    }
}

void clip_p(float* p, int n){
    // in place clipping
    // from 0,1
    // for dist only makes sense if afterwards renormalized

    for (int i = 0; i < n; i++){
        if (p[i] < 0){
            p[i] = 0.0;
        }
        if (p[i] > 1){
            p[i] = 1.0;
        }
    }
    normalize_p(p, n); // also inplace
}

void calc_p_obs(int* counts, float* res, int n){
    // turns counts into a prob dist
    // res = p_obs

    float sum = 0;
    for (int i = 0; i < n; i++){
        sum += counts[i];
    }

    for (int i = 0; i < n; i++){
        res[i] = counts[i] / sum;
    }
}

void calc_p_adj(float* p_obs, float* p_des, float* res, int n){
    // p_des = p_desired
    // p_obs = p_observed
    // n = number of elements
    // res to store result

    for (int i = 0; i < n; i++){
        res[i] = (float) p_des[i] - p_obs[i];
    }
    clip_p(res, n);
}

int sample_p_adj(float* p_des, int* counts, int n){
    // adjusted sampling inspired by marga
    // faster convergence towards p_des

    float p_obs[n];
    calc_p_obs(counts, p_obs, n);

    float p_adj[n];
    calc_p_adj(p_obs, p_des, p_adj, n);
    
    int j = sample_p(p_adj, n);
    return j;
}

int sample(float* p_des, int* counts, int n, int trial_counter, int adj_trial_thresh){
    int i;
    if (trial_counter < adj_trial_thresh){
        i = sample_p(p_des, n);
    }
    else{
        i = sample_p_adj(p_des, counts, n);
    }
    return i;
}

// move these to new file?
// these need to be redefined
unsigned long CS_US_time_delay[] = {0, 150, 300, 600}; 
float weights_delay[] = {0.25, 0.25, 0.25, 0.25}; 
float reward_magnitudes[] = {1, 2.75, 4.5, 6.25, 8}; 
float weights_distribution[] = {0.55, 0, 0.45};  // distributions -> either no distribution, unimodal or bimodal
float weights_uni[] = {0.125, 0.225, 0.3, 0.225, 0.125}; 
float weights_bi[] = {0.25, 0.167, 0.167, 0.167, 0.25};

int odor_uni = 1;
int odor_bi = 2;

int n_delays = sizeof(weights_delay) / sizeof(weights_delay[0]);
int n_distribution = sizeof(weights_distribution) / sizeof(weights_distribution[0]);
int n_uni = sizeof(weights_uni) / sizeof(weights_uni[0]);
int n_bi = sizeof(weights_bi) / sizeof(weights_bi[0]);

// double weights_distribution[] = {0.55, 0, 0.45};

int counts_distr[] = {0, 0, 0};
int counts_delays[] = {0, 0, 0, 0};
int counts_uni[] = {0, 0, 0, 0 ,0};
int counts_bi[] = {0, 0, 0, 0, 0};

int trial_counter = 0;
bool context_is_switched = false;

void get_trial_type(){
    /* sets :
    this_delay
    this_odor -> does not resolve the flip
    reward_magnitude
    */

    i = sample(weights_distribution, counts_distr, n_distribution, trial_counter, adj_trial_thresh);
    counts_distr[i] += 1;

    if (i == 0){
        /*
        fixed reward magnitude, variable delay
        sample odor - delay combo
        */
        j = sample(weights_delay, counts_delays, n_delays, trial_counter, adj_trial_thresh);
        this_delay = CS_US_time_delay[j];
        this_odor = j;
        reward_magnitude = reward_magnitudes[fixed_reward_ix];
        counts_delays[j] += 1;
    }

    if (i == 1){
        /*
        fixed delay
        sample from unimodal reward magnitudes
        */
        j = sample(weights_uni, counts_uni, n_uni, trial_counter, adj_trial_thresh);
        this_delay = CS_US_time_delay[fixed_delay_ix];
        reward_magnitude = reward_magnitudes[j];
        this_odor = odor_uni;
        counts_uni[j] += 1;
    }

    if (i == 2){
        /*
        fixed delay
        sample from bimodal reward magnitudes
        */
        j = sample(weights_bi, counts_bi, n_bi, trial_counter, adj_trial_thresh);
        this_delay = CS_US_time_delay[fixed_delay_ix];
        reward_magnitude = reward_magnitudes[j];
        this_odor = odor_bi;
        counts_bi[j] += 1;
    }
    log_int("this_trial_type", i);
    log_ulong("this_delay", this_delay);
    log_float("reward_magnitude", reward_magnitude);
}

/*
########  ######  ##     ##
##       ##    ## ###   ###
##       ##       #### ####
######    ######  ## ### ##
##             ## ##     ##
##       ##    ## ##     ##
##        ######  ##     ##
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
            current_state = ITI_STATE;
            break;

        case TRIAL_AVAILABLE_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                log_code(TRIAL_AVAILABLE_EVENT);
                if (trial_autostart == 0){
                    this_lick_block_dur = TruncExpDist(Lick_block_dur_min, Lick_block_dur_mean, Lick_block_dur_max);
                }
            }

            // the update loop
            if (current_state == last_state){
                if (trial_autostart == 1){
                    current_state = TRIAL_ENTRY_STATE;
                    break;
                }
                else { // check for lick block
                    if (now() - t_last_lick_on > this_lick_block_dur && is_licking == false){
                        current_state = TRIAL_ENTRY_STATE;
                        break;
                    }
                }
            }
            break;

        case TRIAL_ENTRY_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                log_code(TRIAL_ENTRY_EVENT);
                
                t_last_trial_entry = now();
                this_ITI_dur = TruncExpDist(ITI_dur_min, ITI_dur_mean, ITI_dur_max);

                // sync at trial entry
                switch_sync_pin = true;
                sync_pin_controller(); // and call sync controller for enhanced temp prec.

                // determine the type of trial:
                get_trial_type(); // updates this_correct_side

                // check for context switch
                if (trial_counter > context_switch_trial && !context_is_switched) {
                    context_is_switched = true;
                    log_code(CONTEXT_SWITCH_EVENT);
                    weights_delay[remove_stim_ix] = 0;
                    normalize_p(weights_delay, n_delays);
                }
                trial_counter++;
                log_int("trial_counter", trial_counter);
            }
            
            // exit condition 
            if (true) {
                current_state = PRESENT_STIMULUS_STATE;
            }
            break;

        case PRESENT_STIMULUS_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                // FIXME do some logging here
                this_odor_flipped = flip[odorflip][this_odor];
                switch_odor_on[this_odor_flipped] = true;
            }

            // exit
            if (now() - t_state_entry > this_delay){
                if (autodeliver_rewards == true){
                    current_state = REWARD_STATE;
                    break;
                }
                else {
                    current_state = REWARD_AVAILABLE_STATE;
                    break;
                }
            }
            break;

        case REWARD_AVAILABLE_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                log_code(REWARD_AVAILABLE_EVENT);
            }

            // update
            if (current_state != last_state){
                if (is_licking){
                    log_code(REWARD_COLLECTED_EVENT);
                    current_state = REWARD_STATE;
                    break;
                }
            }

            // exit
            if (now() - t_state_entry > reward_collection_dur){
                log_code(REWARD_MISSED_EVENT);
                current_state = ITI_STATE;
                break;
            }
            break;

        case REWARD_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
                log_code(REWARD_EVENT);
                deliver_reward = true;
            }

            // exit
            if (true){
                current_state = ITI_STATE;
            }
            break;

        case ITI_STATE:
            // state entry
            if (current_state != last_state){
                state_entry_common();
            }

            // exit condition
            if (now() - t_last_trial_entry > this_ITI_dur) {
                current_state = TRIAL_AVAILABLE_STATE;
            }
            break;
    }
}

/*
##     ##    ###    #### ##    ##
###   ###   ## ##    ##  ###   ##
#### ####  ##   ##   ##  ####  ##
## ### ## ##     ##  ##  ## ## ##
##     ## #########  ##  ##  ####
##     ## ##     ##  ##  ##   ###
##     ## ##     ## #### ##    ##
*/

void setup() {
    delay(100);
    Serial.begin(115200); // main serial communication with computer
    //  Serial1.begin(115200); // serial line for receiving (processed) loadcell X,Y
    srand(random(0,10000));

    Serial.println("<AArduino is ready to receive commands>");
    delay(1000);
}

void loop() {
    if (run == true){
        // execute state machine(s)
        finite_state_machine();
    }
    // Controllers
    reward_valve_controller();
    odor_valve_controller();

    // sample sensors
    read_lick();

    // serial communication with main PC
    getSerialData();
    processSerialData();

}
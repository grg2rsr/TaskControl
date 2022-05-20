#include "Arduino.h"
#include "externalVariables.h"
#include "pinOUT.h"
#include "declareStates.h"
#include "init_variables.h"

//Task parameters
//BASIC SETTINGS
const int nRwd = sizeof(distribution_Amount) / sizeof(double);
double current_ITI;
int current_CS;
int current_RWD_IDX;
double current_rwd_amount;
int current_rwd_valve_time;
int currentTrialNumber;
int currentTrialNumber_control;
int state;
unsigned long rwdAvailTime;
unsigned long swInCheck;
bool isLick;
int CS_US_DELAY;
int current_time_delay_idx;//  0 1 2 3
int current_dist_idx; //  0 1 2
int current_trial_reward_idx; // 0 1 2 3 4
int idx_ports;
int trial_type; // From 0-13
int emp_sum_counts;
int emp_sum_counts_control;

// Probability of each trial type happening
double prob[] = {weights_distribution[0] * weights_delay[0],
                 weights_distribution[0] * weights_delay[1],
                 weights_distribution[0] * weights_delay[2],
                 weights_distribution[0] * weights_delay[3],
                 weights_distribution[1] * weights_uni[0],
                 weights_distribution[1] * weights_uni[1],
                 weights_distribution[1] * weights_uni[2],
                 weights_distribution[1] * weights_uni[3],
                 weights_distribution[1] * weights_uni[4],
                 weights_distribution[2] * weights_uniform[0],
                 weights_distribution[2] * weights_uniform[1],
                 weights_distribution[2] * weights_uniform[2],
                 weights_distribution[2] * weights_uniform[3],
                 weights_distribution[2] * weights_uniform[4]
                };

//int flip[][n_odors] = {{0, 1, 2, 3, 4}, {1, 0, 3, 2, 4}, {1, 3, 0, 4, 2}, {3, 4, 0, 2, 1}};
int flip[][n_odors] = {{0, 1, 2, 3, 4}, {1, 0, 3, 2, 4}, {2, 0, 4, 1, 3}, {3, 4, 0, 2, 1}}; // Q what is this
const int odorflip = stimWeights[0]; // Q and this? - stimWeights 0 is 0.0

// N of possible trial types
const int n_trial_types = (sizeof(prob) / sizeof(prob[0]));

// probability x 100
double Counts[n_trial_types];
double prob_end[n_trial_types];

const int rows_mi = 4*3*5; // Q what is this
const int columns = 3; // Q unused var?

// Go from trial type to reward, delay and distribution
int Indices[rows_mi][3]; // Q how do these exist?
int Map_Of_Indices[n_trial_types][3];

// MOVED TO THE SEPARATE HEADER FILEs FOR CLARITY:
// the header contains two functions that print vectors (int and double type, respectively)
#include "Print_Array.h"
// the header contains a function that outputs an array of indexes -> idx_time, idx_dist, idx_amount
#include "Map_of_indices.h"
// the header contains a function that outputs an array of the trials' types
//#include "Types_of_trials.h"
//Get a sample from a distribution
#include "DrawStimIdx.h"

//Exponential decay
double Avg;
double alpha;
unsigned long startTrialTime;
int countAVG;

char s[128]; // message buffer

// String stringConstructor(int idToPrint) { // Q unused function
//     String strToPrint = String(idToPrint) + '\t' + String(millis()) + '\t' + String(1);
//     return strToPrint;
// }

void log_int(int event, int value) {
    snprintf(s, sizeof(s), "%i \t %lu \t %i", event, millis(), value);
    Serial.println(s);
}

void giveReward(int pinReward, int amount) {
    digitalWrite(pinReward, HIGH);
    log_int(RWD_ON_EVENT, 0);
    delay(amount);
    digitalWrite(pinReward, LOW);
    log_int(RWD_OFF_EVENT, 0);
}

unsigned long TruncExpDist(unsigned long minimum, unsigned long mean, unsigned long maximum) {
    if (maximum == 0) {
        return 0;
    }

    else {
        double e = -double(mean) * log(double(random(1000000) + 1) / double(1000000));
        if (e > maximum || e < minimum) {
            e = TruncExpDist(minimum, mean, maximum);
        }
    return round(e);
    }
}

unsigned long convertAmountToTime(double rwdAmount) {
    return (  (int) ((rwdAmount - calibrationIntercept) / calibrationSlope));
}


void Odor_Delivery(int odorflip, int trial_type, int current_time_delay_idx, byte ports[]) {

    int idx_ports;
    const int constant_flow =  continuous_flow; // Q ?
    if ( trial_type > 0 && trial_type < 4) {
        idx_ports = flip[odorflip][current_time_delay_idx-1]; // 0,1,2
    }
    else if (trial_type == 0) {
        idx_ports = flip[odorflip][3]; // 3
    }
    else {
        idx_ports = flip[odorflip][4]; // 3
    }

    log_int(ODOR_NUMBER, int(idx_ports + 1));

    const int odor_pin_2_use = ports[idx_ports];

    log_int(PIN_VALVE, int(odor_pin_2_use));

    digitalWrite(constant_flow, LOW);
    delay(3); // Q why
    digitalWrite(odor_pin_2_use, HIGH);
    log_int(CS_ON, current_dist_idx);
    delay(CS_DURATION + 3);
    digitalWrite(odor_pin_2_use, LOW);
    log_int(CS_OFF, current_dist_idx);
    digitalWrite(constant_flow, HIGH);
}


void Odor_Reward_Delivery(int odorflip, int trial_type, int current_time_delay_idx, byte ports[],int pinReward, int amount) {
    int idx_ports;
    const int constant_flow =  continuous_flow;

    if ( trial_type > 0 && trial_type < 4) {
        idx_ports = flip[odorflip][current_time_delay_idx-1]; // 0,1,2
    }
    else if (trial_type == 0) {
        idx_ports = flip[odorflip][3]; // 3
    }
    else {
        idx_ports = flip[odorflip][4]; // 4
    }
    log_int(ODOR_NUMBER, int(idx_ports + 1));
    const int odor_pin_2_use = ports[idx_ports];
    log_int(PIN_VALVE, int(odor_pin_2_use));

    if(amount<CS_DURATION){
        const int dif_time=CS_DURATION-amount;
        digitalWrite(constant_flow, LOW);
        delay(3);
        digitalWrite(odor_pin_2_use, HIGH);
        log_int(CS_ON, current_dist_idx);
        digitalWrite(pinReward, HIGH);
        log_int(RWD_ON_EVENT, 0);
        delay(amount);
        digitalWrite(pinReward, LOW);
        log_int(RWD_OFF_EVENT, 0);
        delay(dif_time);
        digitalWrite(odor_pin_2_use, LOW);
        log_int(CS_OFF, current_dist_idx);
        digitalWrite(constant_flow, HIGH);
        }

    else{
        const int dif_time=CS_DURATION-amount;
        digitalWrite(constant_flow, LOW);
        delay(3);
        digitalWrite(odor_pin_2_use, HIGH);
        log_int(CS_ON, current_dist_idx);
        digitalWrite(pinReward, HIGH);
        log_int(RWD_ON_EVENT, 0);
        delay(CS_DURATION);
        digitalWrite(odor_pin_2_use, LOW);
        log_int(CS_OFF, current_dist_idx);
        digitalWrite(constant_flow, HIGH);
        delay(dif_time);
        digitalWrite(pinReward, LOW);
        log_int(RWD_OFF_EVENT, 0);
    }
}



int runStateMachine(int state) {

  switch (state) {

    case TRIAL_AVAIL_STATE:
        currentTrialNumber += 1;

        log_int(TRIAL_NUMBER_EVENT, currentTrialNumber);

        // Sample trial type
        if (currentTrialNumber <= max_trials) {
            trial_type = DrawStimIdx(Counts, n_trial_types);
            Counts[trial_type] = Counts[trial_type] - 1;
        }
      
        else {
            if(currentTrialNumber <= trials_context_switch){
                trial_type = DrawStimIdx(prob, n_trial_types);}

            else{
                if(currentTrialNumber == trials_context_switch+1){
                    log_int(SWITCH_CONTEXT,0);
                }
                trial_type = DrawStimIdx(prob_end, n_trial_types);
            }
        }

        log_int(TRIAL_TYPE, trial_type);

        //Go from trial types to time delay, distribution and reward
        current_time_delay_idx = Map_Of_Indices[trial_type][0]; // time
        current_dist_idx = Map_Of_Indices[trial_type][1]; // dist
        current_RWD_IDX = Map_Of_Indices[trial_type][2]; // reward amount
        current_rwd_amount = distribution_Amount[current_RWD_IDX];

        if (printAll) {
            log_int(TIME_DELAY_IDX, current_time_delay_idx);
            log_int(DIST_IDX, current_dist_idx);
            log_int(REWARD_IDX, current_RWD_IDX);
        }

        CS_US_DELAY = CS_US_time_delay[current_time_delay_idx];
        log_int(TRIAL_CURRENT_DELAY, CS_US_DELAY );

        current_rwd_valve_time = convertAmountToTime(current_rwd_amount);

        if (current_rwd_valve_time < 0) {
            current_rwd_valve_time = 0;
        }

        log_int(TRIAL_CURRENT_RWD_AMOUNT, int(current_rwd_amount * 100));

        current_ITI = TruncExpDist(ITI_min, ITI_exp_mean, ITI_max);
        log_int(TRIAL_CURRENT_ITI_DURATION, int(current_ITI));

        digitalWrite(SyncTrialAvailablePin, 1);
        delay(100);
        digitalWrite(SyncTrialAvailablePin, 0);
        state = GIVE_CUE_STATE;

        log_int(CURRENT_STATE_STATE, state);

        if(current_time_delay_idx == 0){
            state = GIVE_CUE_REWARD_STATE;
            log_int(CURRENT_STATE_STATE, GIVE_REWARD_STATE); //Artificial GIVE_REWARD_STATE
            log_int(CURRENT_STATE_STATE, state);
        }

        break;

    case GIVE_CUE_STATE:

        startTrialTime = millis();

        //Give CS
        Odor_Delivery(odorflip, trial_type, current_time_delay_idx, ports);

        delay(CS_US_DELAY - CS_DURATION); // Q this creates blindness

        if (isRewardcont) { // reward delivery contingent on licking
            state = CHECK_RESPONSE;
            rwdAvailTime = millis();
        }

        else {
            state = GIVE_REWARD_STATE;
        }

        log_int(CURRENT_STATE_STATE, state);
        break;

    case GIVE_CUE_REWARD_STATE: // Q what is this?
        startTrialTime = millis(); 
        Odor_Reward_Delivery(odorflip, trial_type, current_time_delay_idx, ports,pinValve, current_rwd_valve_time);
        state = ITI_STATE;
        log_int(CURRENT_STATE_STATE, state);
        break;


    case CHECK_RESPONSE:
        while ((millis() - rwdAvailTime < timeToCollectReward) & (millis() - rwdAvailTime < (current_ITI - 0)) ) { // Q - 0?
            isLick = digitalRead(lickPort);
            if (isLick) {
                break;
            }
            delay(1); // Q ? why?
        }

        if (isLick) {
            state = GIVE_REWARD_STATE;
            Avg = 1 * alpha + Avg * (1 - alpha);
            countAVG = countAVG + 1;
        }

        else {
            state = ITI_STATE;
            Avg = 0 * alpha + Avg * (1 - alpha);
            countAVG = countAVG + 1;

            if (Replace && (currentTrialNumber < max_trials)) { // Q ?
            Counts[trial_type] = Counts[trial_type] + 1;
            }
        }

        log_int(CURRENT_STATE_STATE, state);
        break;

    case GIVE_REWARD_STATE:
        giveReward(pinValve, current_rwd_valve_time);
        state = ITI_STATE;
        log_int(CURRENT_STATE_STATE, state);
        break;

    case ITI_STATE:
        if (timeWithoutLicking > 0) { // Q if bigger than 0 replaced by bigger value? Is this a flag and var at the same time?
            timeWithoutLicking = TruncExpDist(waitMin, waitMean, waitMax);
        }

        log_int(TIME_WITHOUT_LICKING, int(timeWithoutLicking));

        while (current_ITI > millis() - startTrialTime) {
            delay(1);
        }

        state = CHECK_TRIAL_RESTART_CONDITION;
        log_int(CURRENT_STATE_STATE, state);
        break;

    case CHECK_TRIAL_RESTART_CONDITION:
        if ((thrTimeout > Avg) && (countAVG > 100) && (isRewardcont)) {
            log_int(TIMEOUT_ON, int(Avg * 10));
            delay(timeout);
            countAVG = 0;
            log_int(TIMEOUT_OFF, int(Avg * 10));
        }

        if (timeWithoutLicking == 0) {
            state = TRIAL_AVAIL_STATE;
            log_int(CURRENT_STATE_STATE, state);
            break;
        }

        else {
            swInCheck = millis();
            isLick = digitalRead(lickPort);

            /* = " if animal is not licking " & " time since start of checking is smaller 
            than total requested non-licking time "

            False False when no lick and time is passed, otherwise FSM hangs here 
            and polls pin once per ms

            */
            while (!isLick & (millis() - swInCheck < timeWithoutLicking)) {
                delay(1);
                isLick = digitalRead(lickPort);
            }
            /*
            if time is passed:
            the above isLick is sampled again -  if no lick, go to trial
            */
            if (!isLick) {
                state = TRIAL_AVAIL_STATE;
                log_int(CURRENT_STATE_STATE, state);
                break;
            }
            else {
                log_int(ANIMAL_LICKED, 0);
                break;
            }
        }
    }

    return state;
}

void setup() {
    Serial.begin(115200);

    while (!Serial); // wait for serial monitor to open
    delay(5000);

    for (int i = 0; i < n_trial_types; i++) {
        Counts[i] = round(prob[i] * (max_trials));
        emp_sum_counts += (int) Counts[i];
    }

    index_map(Indices); // Q Check whats going on - Indices is empty, this function both returns and writes Map_Of_Indices?

    for (int i = 0; i < n_odors; i++) {
        pinMode(ports[i], OUTPUT);
        digitalWrite(ports[i], LOW);
    }

    pinMode(continuous_flow, OUTPUT);
    digitalWrite(continuous_flow, HIGH);

    pinMode(pinValve, OUTPUT);
    pinMode(SyncTrialAvailablePin, OUTPUT);
    pinMode(lickPort, INPUT);

    digitalWrite(pinValve, LOW);
    digitalWrite(SyncTrialAvailablePin, LOW);

    while (Serial.read() != 115) { //make sure bonsai is ready to receive data
    }
    randomSeed(analogRead(A0) + millis());

    // PLEASE DO NOT DELETE COMMENTED PART
    // for ( int i = 0; i < rows_mi; ++i ) {
    //    // loop through columns of current row
    //    for ( int j = 0; j < columns; ++j )
    //    Serial.print(Indices[ i ][ j ] );
    //    Serial.println() ; // start new line of output
    // } 

    //for ( int i = 0; i < n_trial_types; ++i ) {
    //   // loop through columns of current row
    //  for ( int j = 0; j < columns; ++j )
    //     Serial.print(Map_Of_Indices[ i ][ j ] );
    //     Serial.println() ; // start new line of output
    // } 
    //  

    state = TRIAL_AVAIL_STATE;
    log_int(CURRENT_STATE_STATE, state);

    currentTrialNumber = 0;
    Avg = 0; // Q I guess these are used for the lick block in ITI
    alpha = 0.1;
    countAVG = 0;

    log_int(ODOR_1, int(flip[odorflip][0] + 1));
    log_int(ODOR_2, int(flip[odorflip][1] + 1));
    log_int(ODOR_3, int(flip[odorflip][2] + 1));
    log_int(ODOR_4, int(flip[odorflip][3] + 1));
    log_int(ODOR_5, int(flip[odorflip][4] + 1));

    //Take longest delay
    if(context_switch_type % 2 == 0){
        prob_end[0]=0.333;
        prob_end[1]=0.333;
        prob_end[2]=0.334;
    }

    //Take shortest delay
    else {
        prob_end[1]=0.333;
        prob_end[2]=0.333;
        prob_end[3]=0.334;
    }

    log_int(SWITCH_CONTEXT_TYPE, context_switch_type);
}

void loop() { //detect the state of all inputs
    state = runStateMachine(state);
}

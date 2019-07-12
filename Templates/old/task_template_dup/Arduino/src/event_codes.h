// OBSOLETE FILE 

// event codes template file
// all are const unsigned int

// _STATE are events for state machine states (entry)
// _ON _OFF are for events that have a start and a stop -> going to be spans
// _EVENT are for actual events -> going to be time stamts
// think about how to implement things that have a value ... 


// ONCE REPORTED EVENTCODES
const unsigned int SESSION_START = 0;
const unsigned int TRAINING_STAGE = 1;
const unsigned int RANDOM_SEED = 2;

// STATE EVENTSCODES
const unsigned int A_STATE = 10;
const unsigned int TRIAL_INIT_WAIT_FOR_MOV_CUE_STATE = 120;
const unsigned int WAIT_FOR_TRIAL_INIT_STATE = 11;
const unsigned int WAIT_FOR_MOV_CUE_STATE = 12;
const unsigned int WAIT_FOR_GO_CUE_STATE = 13;
const unsigned int WAIT_FOR_REPORT_STATE = 14;
const unsigned int WAIT_FOR_FEEDBACK_STATE = 15;
const unsigned int GIVE_REWARD_STATE =  16;
const unsigned int RESPONSE_MISS_STATE = 17;
const unsigned int ERROR_TIME_OUT_STATE = 18;
const unsigned int ITOI_STATE = 19;
const unsigned int RESTART_TRIAL_STATE = 9;

// EVENTS & REPORTS FOR TRIALS EVENTSCODES
const unsigned int SYNC_PULSE_ON = 20;
const unsigned int SYNC_PULSE_OFF = 21;
const unsigned int CORRECTION_LOOP_TRIAL = 22;
const unsigned int CURRENT_BLOCK_LENGTH = 23;
const unsigned int TRIAL_NUM_IN_SESSION = 24;
const unsigned int TRIAL_NUM_IN_BLOCK = 25;
const unsigned int CURRENT_BLOCK_NUM = 26;
const unsigned int GO_CUE_ON = 27;
const unsigned int GO_CUE_OFF = 28;

const unsigned int TIME_2_INIT_DELAY = 29;
const unsigned int MOV_CUE_DELAY = 30;
const unsigned int GO_CUE_DELAY = 31;
const unsigned int RWD_LOCATION = 32;
const unsigned int MOV_DIRECTION = 33;
const unsigned int CONGRUENCY = 34;
const unsigned int TONE_ON = 35;
const unsigned int TONE_OFF = 36;
const unsigned int HAPTIC_ON = 37;
const unsigned int HAPTIC_OFF = 38;

const unsigned int BIG_REWARD_EVENT = 40;
const unsigned int SMALL_REWARD_EVENT = 41;
const unsigned int RWD_ON_EVENT = 42;
const unsigned int RWD_OFF_EVENT = 43;
const unsigned int ERROR_EVENT = 44;
const unsigned int BROKE_FIX_EVENT = 45;
const unsigned int JITTER_START = 46;
const unsigned int JITTER_STOP = 47;
const unsigned int ERROR_TONE_ON = 48;
const unsigned int ERROR_TONE_OFF = 49;

const unsigned int VAL_REPORT_EVENT = 50;
const unsigned int LEFT_REPORT_EVENT = 51;
const unsigned int LEFT_ERROR_EVENT = 52;
const unsigned int RIGHT_REPORT_EVENT = 53;
const unsigned int RIGHT_ERROR_EVENT = 54;
const unsigned int MISS_REPORT_EVENT = 55;

// LED STRIP & LOLLYPOP EVENT2S
const unsigned int CURRENT_TRIAL_LIGHTRATIO = 61;
const unsigned int RIGHT_ON_EVENT = 62;
const unsigned int RIGHT_OFF_EVENT = 63;
const unsigned int LEFT_ON_EVENT = 64;
const unsigned int LEFT_OFF_EVENT = 65;
const unsigned int VERTICAL_ON_EVENT = 66;
const unsigned int VERTICAL_OFF_EVENT = 67;
const unsigned int PUSH_ON_EVENT = 68;
const unsigned int PUSH_OFF_EVENT = 69;

// ROI EVENT2S
const unsigned int LEFT_OUTSIDE_ROI = 56;
const unsigned int RIGHT_OUTSIDE_ROI = 57;
const unsigned int PUSH_OUTSIDE_ROI = 58;
const unsigned int VERTICAL_OUTSIDE_ROI = 59;
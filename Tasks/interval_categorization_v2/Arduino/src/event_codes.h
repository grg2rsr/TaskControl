// Codes template file
// all codes are const unsigned int

// NAMING CONVENTIONS

// _STATE for state machine states (entry)
// _ON _OFF are for events that have a start and a stop (spans)
// _EVENT are for actual events (time stamps)

// FSM STATES
const unsigned int INI_STATE = 0;
const unsigned int TRIAL_AVAILABLE_STATE = 1;
const unsigned int TRIAL_ENTRY_STATE = 2;
const unsigned int PRESENT_INTERVAL_STATE = 3;
const unsigned int CHOICE_STATE = 4;
const unsigned int REWARD_STATE = 5;
const unsigned int ITI_STATE = 6;

// REACHES
// unsigned int REACH_LEFT_ON = 10;
// unsigned int REACH_LEFT_OFF = 11;
// unsigned int REACH_RIGHT_ON = 12;
// unsigned int REACH_RIGHT_OFF = 13;

// GRASPS
unsigned int GRASP_LEFT_ON = 100;
unsigned int GRASP_LEFT_OFF = 110;
unsigned int GRASP_RIGHT_ON = 120;
unsigned int GRASP_RIGHT_OFF = 130;

// TOUCHES
unsigned int TOUCH_LEFT_ON = 101;
unsigned int TOUCH_LEFT_OFF = 111;
unsigned int TOUCH_RIGHT_ON = 121;
unsigned int TOUCH_RIGHT_OFF = 131;

// VALVES
unsigned int REWARD_LEFT_VALVE_ON = 14;
unsigned int REWARD_LEFT_VALVE_OFF = 15;
unsigned int REWARD_RIGHT_VALVE_ON = 16;
unsigned int REWARD_RIGHT_VALVE_OFF = 17;

// EVENTS

// trials and their possible outcomes
unsigned int TRIAL_AVAILABLE_EVENT = 20;
unsigned int TRIAL_ENTRY_EVENT = 21;
unsigned int CHOICE_MISSED_EVENT = 22;
unsigned int CHOICE_INCORRECT_EVENT = 23;
unsigned int CHOICE_CORRECT_EVENT = 24;

// reward related
unsigned int REWARD_EVENT = 30;
unsigned int REWARD_LEFT_EVENT = 31;
unsigned int REWARD_RIGHT_EVENT = 32;
unsigned int REWARD_SHORT_EVENT = 33;
unsigned int REWARD_LONG_EVENT = 34;
unsigned int REWARD_AUTODELIVERED_EVENT = 35;

unsigned int REWARD_COLLECTED_EVENT = 36;
unsigned int REWARD_LEFT_COLLECTED_EVENT = 37;
unsigned int REWARD_RIGHT_COLLECTED_EVENT = 38;

// choice related
unsigned int CHOICE_EVENT = 40;
unsigned int PREMATURE_CHOICE_EVENT = 41;
unsigned int CHOICE_LEFT_EVENT = 42;
unsigned int CHOICE_RIGHT_EVENT = 43;
unsigned int CHOICE_LONG_EVENT = 44;
unsigned int CHOICE_SHORT_EVENT = 45;

unsigned int ANTICIPATORY_REACH_EVENT = 46;
unsigned int ANTICIPATORY_REACH_LEFT_EVENT = 47;
unsigned int ANTICIPATORY_REACH_RIGHT_EVENT = 48;


// stim and cue stuff
// unsigned int FIRST_TIMING_CUE_EVENT = 50;
// unsigned int SECOND_TIMING_CUE_EVENT = 51;
unsigned int LED_ON = 52;
unsigned int LED_OFF = 53;
unsigned int GO_CUE_LEFT_EVENT = 54;
unsigned int GO_CUE_RIGHT_EVENT = 55;
unsigned int GO_CUE_SHORT_EVENT = 56;
unsigned int GO_CUE_LONG_EVENT = 57;




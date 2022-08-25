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
const unsigned int PRESENT_STIMULUS_STATE = 3;
const unsigned int REWARD_AVAILABLE_STATE = 4;
const unsigned int REWARD_STATE = 5;
const unsigned int ITI_STATE = 6;

// EVENTS
unsigned int LICK_ON = 10;
unsigned int LICK_OFF = 11;

unsigned int REWARD_VALVE_ON = 12;
unsigned int REWARD_VALVE_OFF = 13;

// trials and their possible outcomes
unsigned int TRIAL_AVAILABLE_EVENT = 20;
unsigned int TRIAL_ENTRY_EVENT = 21;
unsigned int CONTEXT_SWITCH_EVENT = 22;

// reward related
unsigned int REWARD_AVAILABLE_EVENT = 30;
unsigned int REWARD_COLLECTED_EVENT = 31;
unsigned int REWARD_EVENT = 32;
unsigned int REWARD_MISSED_EVENT = 33;

// stim and cue stuff
unsigned int ODOR_ON = 41;
unsigned int ODOR_OFF = 42;

unsigned int FRAME_EVENT = 99;
// unsigned int FIRST_TIMING_CUE_EVENT = 50;
// unsigned int SECOND_TIMING_CUE_EVENT = 51;



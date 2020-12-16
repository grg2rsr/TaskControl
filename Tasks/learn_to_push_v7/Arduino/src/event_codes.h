// Codes template file
// all codes are const unsigned int

// NAMING CONVENTIONS

// _STATE for state machine states (entry)
// _ON _OFF are for events that have a start and a stop (spans)
// _EVENT are for actual events (time stamps)

// STATES
const unsigned int INI_STATE = 0;
// const unsigned int TRIAL_AVAILABLE_STATE = 1;
const unsigned int TRIAL_ENTRY_STATE = 2;
// const unsigned int PRESENT_INTERVAL_STATE = 3;
const unsigned int CHOICE_STATE = 4;
const unsigned int REWARD_AVAILABLE_STATE = 5;
const unsigned int ITI_STATE = 6;
// const unsigned int TIMEOUT_STATE = 7;

// SPANS
unsigned int LICK_ON = 10;
unsigned int LICK_OFF = 11;
unsigned int REWARD_VALVE_ON = 12;
unsigned int REWARD_VALVE_OFF = 13;

// EVENTS

// trials and their possible outcomes
// unsigned int TRIAL_AVAILABLE_EVENT = 20;
unsigned int TRIAL_ENTRY_EVENT = 21;
unsigned int TRIAL_ABORTED_EVENT = 22;
unsigned int TRIAL_SUCCESSFUL_EVENT = 23;
unsigned int TRIAL_UNSUCCESSFUL_EVENT = 24;

unsigned int CHOICE_MISSED_EVENT = 25;
unsigned int CHOICE_INCORRECT_EVENT = 26;
unsigned int CHOICE_CORRECT_EVENT = 27;

// reward related
unsigned int REWARD_AVAILABLE_EVENT = 30;
unsigned int REWARD_COLLECTED_EVENT = 31;
unsigned int REWARD_MISSED_EVENT = 33;
unsigned int REWARD_OMITTED_EVENT = 34;

// choice related
unsigned int CHOICE_EVENT = 40;
unsigned int PREMATURE_CHOICE_EVENT = 41;
unsigned int CHOICE_LEFT_EVENT = 42;
unsigned int CHOICE_RIGHT_EVENT = 43;
// unsigned int CHOICE_LONG_EVENT = 44;
// unsigned int CHOICE_SHORT_EVENT = 45;

// stim and cue stuff
// unsigned int FIRST_TIMING_CUE_EVENT = 50;
// unsigned int SECOND_TIMING_CUE_EVENT = 51;
unsigned int CUE_LED_ON = 52;
unsigned int CUE_LED_OFF = 53;
unsigned int GO_CUE_EVENT = 54;


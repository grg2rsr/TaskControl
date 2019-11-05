// Codes template file
// all codes are const unsigned int

// NAMING CONVENTIONS

// _STATE for state machine states (entry)
// _ON _OFF are for events that have a start and a stop (spans)
// _EVENT are for actual events (time stamps)

// EVENTS
const unsigned int INI_STATE = 0;
const unsigned int TRIAL_AVAILABLE_STATE = 1;
const unsigned int HOLD_STATE = 2;
const unsigned int REWARD_AVAILABLE_STATE = 3;
const unsigned int TIMEOUT_STATE = 4;
const unsigned int ITI_STATE = 5;

const unsigned int LICK_ON = 10;
const unsigned int LICK_OFF = 11;

const unsigned int REWARD_AVAILABLE_ON = 20;
const unsigned int REWARD_AVAILABLE_OFF = 21;
const unsigned int REWARD_COLLECTED_EVENT = 23;

const unsigned int ON_TARGET_ON = 30;
const unsigned int ON_TARGET_OFF = 31;
const unsigned int BROKEN_FIXATION = 32;

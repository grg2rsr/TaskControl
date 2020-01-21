// Codes template file
// all codes are const unsigned int

// NAMING CONVENTIONS

// _STATE for state machine states (entry)
// _ON _OFF are for events that have a start and a stop (spans)
// _EVENT are for actual events (time stamps)

// EVENTS
const unsigned int INI_STATE = 0;
const unsigned int REWARD_AVAILABLE_STATE = 1;
const unsigned int ITI_STATE = 2;

const unsigned int LICK_ON = 10;
const unsigned int LICK_OFF = 11;

const unsigned int REWARD_COLLECTED_EVENT = 12;



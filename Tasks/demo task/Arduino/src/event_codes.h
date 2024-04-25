// Codes template file
// all codes are const unsigned int

// NAMING CONVENTIONS

// _STATE for state machine states (entry)
// _ON _OFF are for events that have a start and a stop (spans)
// _EVENT are for actual events (time stamps)

// FSM STATES
const unsigned int INI_STATE = 0;
const unsigned int ITI_STATE = 1;
const unsigned int TRIAL_AVAILABLE_STATE = 2;
const unsigned int DELAY_STATE = 3;
const unsigned int TIMEOUT_STATE = 4;

// EVENTS
const unsigned int POKE_IN = 20;
const unsigned int POKE_OUT = 21;

const unsigned int REWARD_VALVE_ON = 30;
const unsigned int REWARD_VALVE_OFF = 31;

// reward related
const unsigned int REWARD_EVENT = 40;
const unsigned int BROKEN_FIXATION_EVENT = 41;


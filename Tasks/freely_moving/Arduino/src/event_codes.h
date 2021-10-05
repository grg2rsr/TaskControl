// Codes template file
// all codes are const unsigned int

// NAMING CONVENTIONS

// _STATE for state machine states (entry)
// _ON _OFF are for events that have a start and a stop (spans)
// _EVENT are for actual events (time stamps)

// FSM STATES
const unsigned int INI_STATE = 0;
const unsigned int REWARD_STATE = 1;
const unsigned int REWARD_AVAIL_STATE = 2;
const unsigned int DONE_STATE = 3;

// REACHES
unsigned int REACH_ON = 10;
unsigned int REACH_OFF = 11;

// SPANS
const unsigned int REWARD_VALVE_ON = 12;
const unsigned int REWARD_VALVE_OFF = 13;

// REWARD
unsigned int REWARD_COLLECTED_EVENT = 36;



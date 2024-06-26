// Codes template file
// all codes are const unsigned int

// NAMING CONVENTIONS

// _STATE for state machine states (entry)
// _ON _OFF are for events that have a start and a stop (spans)
// _EVENT are for actual events (time stamps)

// FSM STATES
const unsigned int INI_STATE = 0;
const unsigned int LED_ON_STATE = 1;
const unsigned int LED_OFF_STATE = 2;
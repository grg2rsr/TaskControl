// Codes template file
// all codes are const unsigned int

// NAMING CONVENTIONS

// _STATE for state machine states (entry)
// _ON _OFF are for events that have a start and a stop (spans)
// _EVENT are for actual events (time stamps)

// FSM STATES
const unsigned int INI_STATE = 0;
const unsigned int ITI_STATE = 1;
const unsigned int REWARD_AVAILABLE_STATE = 2;

// REACHES
unsigned int REACH_ON = 10;
unsigned int REACH_OFF = 11;

// VALVES
unsigned int REWARD_VALVE_ON = 20;
unsigned int REWARD_VALVE_OFF = 21;

// EVENTS
unsigned int REWARD_COLLECTED_EVENT = 30;


// stim and cue stuff
unsigned int LED_ON = 40;
unsigned int LED_OFF = 41;




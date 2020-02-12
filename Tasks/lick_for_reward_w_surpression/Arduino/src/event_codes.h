// Codes template file
// all codes are const unsigned int

// NAMING CONVENTIONS

// _STATE for state machine states (entry)
// _ON _OFF are for events that have a start and a stop (spans)
// _EVENT are for actual events (time stamps)

// STATES
const unsigned int INI_STATE = 0;
const unsigned int TRIAL_AVAILABLE_STATE = 1;
const unsigned int FIXATE_STATE = 2;
const unsigned int REWARD_AVAILABLE_STATE = 3;
const unsigned int TIMEOUT_STATE = 4;
const unsigned int ITI_STATE = 5;

// SPANS
const unsigned int LICK_ON = 10;
const unsigned int LICK_OFF = 11;
const unsigned int REWARD_VALVE_ON = 12;
const unsigned int REWARD_VALVE_OFF = 13;

// EVENTS
const unsigned int TRIAL_ENTRY_EVENT = 20;
const unsigned int TRIAL_COMPLETED_EVENT = 21;
const unsigned int TRIAL_ABORTED_EVENT = 22;

const unsigned int REWARD_AVAILABLE_EVENT = 30;
const unsigned int REWARD_COLLECTED_EVENT = 31;
const unsigned int REWARD_MISSED_EVENT = 33;

const unsigned int SUCCESSFUL_FIXATION_EVENT = 34;
const unsigned int BROKEN_FIXATION_EVENT = 35;




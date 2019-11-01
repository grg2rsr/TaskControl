# task layout
goal: select task in taskControl and fire it up the regular way

components

# ArduinoController
runs the main statemachine
inputs:
lickTTL
[ ] Cursor position

outputs:
all logged data via serial to TaskControl Computer
PWM to L and R speakers
digitla to ValveBoard

at each loop: sensor read: lick
at the beginning of trial, send target coordinates

[ ] how to distribute data after "serial_data_available"?
https://stackoverflow.com/questions/30676599/emitting-signals-from-a-python-thread-using-qobject

signals across threads are threadsafe
-> possible solution to try out: serial port reading thread 

# BonsaiController
## camera
Camera for paws
Camera for lickdetection (could be the same)
LickDetection and Firmata based LickToDigital conversion
those are sent to task running arduino that deciedes what to do with these guys

required parameters:
crop area, threshold, com port for Arduino (firmata), path to save vid/s

## loadcell (harp)
read from loadcell
[ ] same or different Bonsai instance? Could make sense to decouple these
[ ] find out if there are performance problems
[ ] find out required parameters for this

downsample to x Hz? (simple average last 10 samples would give 100 Hz)
write to udp

required parameters
- saving paths
- udp port
- downsample factor

# LoadCellController
connects to upd, processes the data, emits signal with data package
[ ] check: this leads to a very high rate of emitted signals, is this feasible?
https://stackoverflow.com/questions/52721377/qt-eventloop-delay-with-high-frequency-signal-slot-connections

[ ] alternatively: make the DisplayController directly connect to the udp
also: https://doc.qt.io/qt-5/qudpsocket.html

data processing:
mode: force -> position or force -> velocity coupling
physical cursor: mass/friction?
(J) [ ] other modes?

load cell force data -> conversion to actual force?
F/m = dv/dt
F is measured "F_meas"
friction as a force acting in the opposite direction of F and proportional to v
F_f = mu * v
F_ges = F_f + F_meas

possibl solution: after processing, write to another upd port
so: receive F_x,F_y,t and output X_x, X_y
X_x and X_y need to be both sent to DisplayController and back to the arduino!
[ ] how to get values back to arduino
try:
1 use serial line at x Hz, see when it clogs
2 use other dedicated line (I2C)
3 ethernet shield of arduino and write directly to upd (gets via SPI)
4 alternative to 3 - direct SPI?

in this case: all computations on the arduino, no offloading
alternatively: arduino just receives "in target" when it's hit
problem: no auditory feedback possible

(J) [ ] what kind of computations could be interesting here
-> influences teensy vs arduino vs computations on PC

# DisplayController
(purely receiving, only controlling display)

gets an udp connection where the x,y data comes in
not t!
on receive, update screen

connect to ArduinoController serial_data_available signal in order to 
be put into state (idle/run/hold/listen)
and receive target coordinates

get data either directly from upd or from signal and change the display accordingly
x,y pos of circle

the states to think about:
idle: black screen, wait for being put to listen
listen: wait for coordinates the draw target and go to running
running
also others, depending on task: hold (gray ... )

(J)[ ] states of the display

# visualization!
load cell plot:
past trials force trajectory (button to include n last trials?)
current and past

# latency checks
with photodiode in corner of screen that is recorded by harp direcly
at trial start flash screen 
-> arduino sends TTL to harp
-> arduino says blink screen to display controller
-> measure delay between timestamps of photodiode and arduino trial init TTL

with load cell in the loop
same game, but send trial available TTL and not trial start
trial start depends on LC above whatever value
manually push loadcell above value
-> arduino sends TTL to harp
-> load cell controller sends pos to arduino
-> arduino say good to go and does trial init TTL
-> arduino send blink screen to displaycontroller
-> displaycontroller blinks, photodiode records, harp records TTL
3 timestamps that give all the info



# task / training ideas
## visuomotor reaching primate style
target task:
cursor in center, show target, go cue, go to target, get reward
considerations on optical aspects: visual acuity of mice
2 target version kind of like IBL task



## timing task
target task: combination of delayed movement and interval discrimination task
trial ini, hold, hear tones, hold, go cue, go.

signal trial availability (screen, stripes?)
push/pull forward or backward
(J)[ ] active or passive trial initiation? passive=moving pattern that starts hold period
active=push and then hold

play tones w interval (while gray screen?)
(J)[ ] hold period is dark
(J)[ ] (auditory cursor at target freq during hold?)

show targets is go cue
go left or go right
correct: deliver reward tone and reward


## both: train them to get a cursor in the target
initial help: distance to target modulates auditory "cursor" pitch/amplitude


cue: visual left and right targets, cursor auditory (pitch / amplitude as function of distance)






then left or right targets


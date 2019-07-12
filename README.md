# A unified task control program
## the problem:
A task has a range of different hardware that needs to communicate with each other and each task has a range of different visualizers.

To make things more complicated:
+ animals can be run in different tasks
+ different people can run the same animal
+ a task has specific hardware and visualizers
+ tasks need to be interactive and can change quickly in the design phase

A unified system has to:
+ interactive
+ be able to interface different hardware (=extensible)
+ be portable

things that need to be set in `.ini` files:

## the concept
TaskControl is a top level python program that interacts with a series of Widgets

`profiles.ini` is a computer specific file.
contains the specification of 
+ paths to all system executables needed to launch the task (pio, bonsai ... )
+ a list of users
+ for each user: task folder and animals folder (can of course be shared across users)

The main settings widget - select animal and task, worry not, hit run.
upon run:

the task has a `task_config.ini`
which contains:
a section for each hardwareWidget
[Arudino]
[Bonsai]
etc ... 
each section contains hardware relevant info (like com port, workflow path etc)

Future: a section for each visualizer?
[Visualization]
paths to python scripts that visualize incoming data? need to be able to listen to the ports ... 

## Detailed description of HardwareWidgets
### ArduinoController
task_config.ini section contains obvious stuff
+ baud rate
+ com port

but also: since arduino runs state machine
+ event_codes_fname.h
contains the mapping of codes to events
+ var_fname.h
contains the (non-derived) variables that change interactively/training/testing stuff
+ pio_ini_path
the path to the platformio.ini file
+ pin_map.h # check name

#### ArduinoVariablesWidget
UI to set live variables in the Arduino
for this to work, the arduino code must contain (-> interface.cpp)
and setup
loop must extend:

#### system must platformIO
Task folder must contain Fulder called Arduino (Folder for each hardware, Bonsai etc)
Arduino is a platformIO project folder with `platformio.ini` that specifies board, port etc.

TODO -> this is doubly complicated? maybe this could be solved more elegantly that not the platformio.ini needs to be specced again ...


VisualizationWidget
HardwareWidget

## task_config.ini
each task needs one

which has sections for each hardware
each section has com port 

arduino modifyable variables
need to be registered (?)

## visualizers
definitely break generability
VisWidgets.py to be placed in task folder?
QtWidgets that implement whatever

# animal metadata
weight at training start
current weight
age
date of training start
think about const var column


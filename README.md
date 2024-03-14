# A unified task control program
Software to manage running "tasks" for in behavioral boxes for rodent/animal training with different tasks, boxes, animals, users, hardware etc., all offering a unified interface that allows to flexibly select the different components of the experiment and simply hitting the run button. Takes care of all the communication, data logging and storage. Allows for online visualization of the behavior, and bi-directional online communication with the state-machine and its variables that controls the task. 

## the problems
+ animals can be run in different tasks
+ different tasks can have different hardware
+ different experimentors can run the same animal
+ a task can require different visualizers
+ tasks are automatic, but need to be interactively controllable

A unified system has to:
+ support bi-directional communication with the hardware to allow for interactivity
+ be able to interface different hardware (=extensible)
+ lightweight/portable to easily set up new training boxes

## concepts
TaskControl in itself is a top level python program that interacts with a series of Widgets
### TaskControl components
+ Controllers - implement the hardware control and communication
+ OnlineAnalyzer - implements the analysis of the data stream
+ Monitors - visualize output from the controllers

A TaskControl instance selects Animal, Task, Box, (User)
+ Box - contains all general hardware connection based information (ports, etc.) (each computer is connected to several boxes)
+ Task - contains all task related hardware connections (e.g. pins for the arduino) (each box can run different tasks)
+ Animal - contains all animal history related information (training variables, for the future: pyrat interface)

## user specifications
### `profiles.ini`
system related information
+ paths to executables
+ folders of data storage (animals, tasks ... )

### `task_config.ini`
For each task - contains a section for each hardware element
-> controllers are instantiated based on this file

### Boxes
all hardware connections and ports are specified here

2do: explain with templates

# 2do

[ ] think about last variables when training different animals


[ ] multiple parameter passing to bonsai
make it possible to pass com port to bonsai sketch

## decisions:
tmp folder or not?
pro: cleaner
contra: temporary arduino_vars file also needed

distribute interface generator or not?
pro: makes codebase for tasks cleaner
contra: removes flexibility as interface needs to be freezed
solution: interface generator could have diff versions, could be specified in task config. Could actually be something in task config that defines if raw, where serial etc.

huge pro is though that it will greatly remove clutter

remember that there was a problem, the settable return type (two diff parsers)

## known hardcodes
raw interface sits fixed on serial1
history of serial monitor is limited



## refactoring
Df -> Arudino_VarsDf / VarsDf

## fix the const/newline/init_variables problem
find a way that interface_generator.py does not need a copy of parse_arduino_vars ... 
-> move it! con: makes it less standalone

## arduino variables
write in header day of training, version of TaskControl, date of generation etc etc

## interface generator
+ template and generator is to be distributed with task control actually
make function with settable return type!

## general
Generalize hardware widgets: com port widget
dict for both animal and task
animal = {ID, path, meta ... }

## clean utils

## new animal

## new user
settings: path selector!

## argparse
for ini files

## shouldn't be possible to click run again

## change logging to log by default (to temp)
and then have two modes of quitting

data stored @ ... 

# 2do
the training varialbes 
[ ] think about last variables when training different animals

## decisions:
tmp folder or not?
pro: cleaner
contra: temporary arduino_vars file also needed
this might have solved itself, think about it


## self terminating sessions
[ ] on water
[ ] on trials
[ ] bonus feature: send email

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

## change logging to log by default (to temp)
and then have two modes of quitting

data stored @ ... 

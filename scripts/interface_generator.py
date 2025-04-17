# python me to generate an interface.cpp based on the variables in `init_variables.h`
import pandas as pd
import scipy as sp
import sys
from pathlib import Path

dtype_map = {
    "int": "i4",
    "unsigned int": "u4",
    "long": "i8",
    "unsigned long": "u8",
    "bool": "?",
    "float": "f4",
    "double": "f8",
}


def parse_arduino_vars(path):
    """a kind of hacky parser for init_variables.h"""
    with open(path, "r") as fH:
        lines = fH.readlines()
        lines = [line.strip() for line in lines]

    # hacky parser:
    dfs = []
    for line in lines:
        line = line.strip()
        # to skip
        if line == "":
            continue
        if "*" in line:  # in block comment
            continue
        if line[:2] == "//":  # full line comment
            continue
        if "//" in line:  # remove everything after comment
            line = line.split("//")[0]
            print(line)

        line = line.strip()
        try:
            elements, value = line.split("=")
            value = value[:-1].strip()
            elements = elements.strip().split(" ")
            elements = [elem.strip() for elem in elements]
            name = elements[-1]
            dtype = " ".join(elements[:-1])
            value = sp.array(value, dtype=dtype_map[dtype])
            # FIXME hardcoded dtype instead of dtypemap[dtype] (as in utils), in essence, same func, different behavior. will confuse ppl
            dfs.append(
                pd.DataFrame([[name, value, dtype]], columns=["name", "value", "dtype"])
            )
        except:
            print("unreadable line: ", line)
            pass
    arduino_vars = pd.concat(dfs, axis=0)
    arduino_vars = arduino_vars.reset_index(drop=True)

    return arduino_vars


bool_getter_template = """
        if (strcmp(varname,"VARNAME")==0){
            log_bool("VARNAME", VARNAME);
        }
"""

int_getter_template = """
        if (strcmp(varname,"VARNAME")==0){
            log_int("VARNAME", VARNAME);
        }
"""

long_getter_template = """
        if (strcmp(varname,"VARNAME")==0){
            log_long("VARNAME", VARNAME);
        }
"""

ulong_getter_template = """
        if (strcmp(varname,"VARNAME")==0){
            log_ulong("VARNAME", VARNAME);
        }
"""

float_getter_template = """
        if (strcmp(varname,"VARNAME")==0){
            log_float("VARNAME", VARNAME);
        }
"""

bool_setter_template = """
        if (strcmp(varname,"VARNAME")==0){
            if (strcmp(varvalue,"false")==0) {
                VARNAME = false;
            }
            else {
                VARNAME = true;
            }
        }
"""

int_setter_template = """
        if (strcmp(varname,"VARNAME")==0){
            VARNAME = atoi(varvalue);
        }
"""

long_setter_template = """
        if (strcmp(varname,"VARNAME")==0){
            VARNAME = atol(varvalue);
        }
"""

ulong_setter_template = """
        if (strcmp(varname,"VARNAME")==0){
            VARNAME = strtoul(varvalue,NULL,10);
        }
"""

float_setter_template = """
        if (strcmp(varname,"VARNAME")==0){
            VARNAME = atof(varvalue);
        }
"""
Getters = {
    "int": int_getter_template,
    "unsigned long": ulong_getter_template,
    "float": float_getter_template,
    "bool": bool_getter_template,
}

Setters = {
    "int": int_setter_template,
    "unsigned long": ulong_setter_template,
    "float": float_setter_template,
    "bool": bool_setter_template,
}


def run(variables_path, template_fname="interface_template.cpp"):
    arduino_vars = parse_arduino_vars(variables_path)

    # generate lines for getters
    all_getters = []
    for i, row in arduino_vars.iterrows():
        template = Getters[row["dtype"]]
        template = template.replace("VARNAME", row["name"])
        all_getters.append(template)

    # generate lines for setters
    all_setters = []
    for i, row in arduino_vars.iterrows():
        template = Setters[row["dtype"]]
        template = template.replace("VARNAME", row["name"])
        all_setters.append(template)

    # read in template
    with open(Path(__file__).with_name(template_fname), "r") as fH:
        lines = fH.readlines()

    # replace in include line
    for i, line in enumerate(lines):
        if line == '#include "interface_variables.h"\n':
            insertion_ind = i
    lines[insertion_ind] = '#include "' + variables_path.name + '"\n'

    # insert getters
    for i, line in enumerate(lines):
        if line == "        // INSERT_GETTERS\n":
            getter_insertion_ind = i
    lines.insert(getter_insertion_ind + 1, "".join(all_getters))

    # insert setters
    for i, line in enumerate(lines):
        if line == "            // INSERT_SETTERS\n":
            setter_insertion_ind = i
    lines.insert(setter_insertion_ind + 1, "".join(all_setters))

    # write all
    with open(variables_path.with_name("interface.cpp"), "w") as fH:
        fH.writelines("".join(lines))


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # for using defaults from the cmd
        run(Path.cwd.joinpath("interface_variables.h"))

    if len(sys.argv) == 2:
        variables_path = Path(sys.argv[1])
        run(variables_path)

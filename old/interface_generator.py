# python me to generate an interface.cpp based on the variables in `init_variables.h`

import pandas as pd
import scipy as sp
import sys,os

dtype_map = {
            'int':'i4',
            'unsigned int':'u4',
            'long':'i8',
            'unsigned long':'u8',
            'bool':'?',
            'float':'f4',
            'double':'f8',
            }

# def parse_arduino_vars(path):
#     """ a hacky parser """  # FIXME this needs a new name as well
#     with open(path, 'r') as fH:
#         lines = fH.readlines()
#         lines = [line.strip() for line in lines]

#     # hacky parser:
#     dfs = []
#     for line in lines:
#         line = line.strip()
#         # to skip
#         if line == '':
#             continue
#         if '*' in line:  # in block comment
#             continue
#         if line[:2] == '//': # full line comment
#             continue
#         if '//' in line: # remove everything after comment
#             line = line.split('//')[0]
#             print(line)
        
#         line = line.strip()
#         try:
#             elements, value = line.split('=')
#             value = value[:-1].strip()
#             elements = elements.strip().split(' ')
#             elements = [elem.strip() for elem in elements]
#             name = elements[-1]
#             if elements[0] == 'const':
#                 const = True
#                 dtype = ' '.join(elements[1:-1])
#             else:
#                 const = False
#                 dtype = ' '.join(elements[:-1])
#             value = sp.array(value, dtype=dtype_map[dtype])
#             dfs.append(pd.DataFrame([[name, value, dtype, const]],columns=['name', 'value', 'dtype', 'const']))
#         except:
#             print('unreadable line: ',line)
#             pass
#     arduino_vars = pd.concat(dfs, axis=0)
#     arduino_vars = arduino_vars.reset_index(drop=True)

#     return arduino_vars

def parse_arduino_vars(path):
    """ a kind of hacky parser for init_variables.h """
    with open(path, 'r') as fH:
        lines = fH.readlines()
        lines = [line.strip() for line in lines]

    # hacky parser:
    dfs = []
    for line in lines:
        line = line.strip()
        # to skip
        if line == '':
            continue
        if '*' in line:  # in block comment
            continue
        if line[:2] == '//': # full line comment
            continue
        if '//' in line: # remove everything after comment
            line = line.split('//')[0]
            print(line)
        
        line = line.strip()
        try:
            elements, value = line.split('=')
            value = value[:-1].strip()
            elements = elements.strip().split(' ')
            elements = [elem.strip() for elem in elements]
            name = elements[-1]
            dtype = ' '.join(elements[:-1])
            value = sp.array(value, dtype=dtype_map[dtype])
            # FIXME hardcoded dtype instead of dtypemap[dtype] (as in utils), in essence, same func, different behavior. will confuse ppl
            dfs.append(pd.DataFrame([[name, value, dtype]],columns=['name', 'value', 'dtype']))
        except:
            print('unreadable line: ',line)
            pass
    arduino_vars = pd.concat(dfs, axis=0)
    arduino_vars = arduino_vars.reset_index(drop=True)

    return arduino_vars


def run(variables_path):
    init_vars = parse_arduino_vars(variables_path)

    getter_template = """
            if (strcmp(varname,"VARNAME")==0){
                Serial.println(String(varname)+String("=")+String(VARNAME));
            }
    """

    bool_setter_template = """
            if (dtype == "bool") {
                if (strcmp(varname,"VARNAME")==0){
                    if (strcmp(varvalue,"false")==0) {
                        VARNAME = false;
                    }
                    else {
                        VARNAME = true;
                    }
                }
            }
    """

    int_setter_template = """
            if (dtype == "int") {
                if (strcmp(varname,"VARNAME")==0){
                    VARNAME = atoi(varvalue);
                }
            }
    """

    float_setter_template = """
            if (dtype == "float") {
                if (strcmp(varname,"VARNAME")==0){
                    VARNAME = atof(varvalue);
                }
            }
    """


    # make getters
    all_getters = []
    all_varnames = []
    for i,row in init_vars.iterrows():
        all_varnames.append(row['name'])

    for i in range(len(all_varnames)):
        all_getters.append(getter_template.replace("VARNAME",all_varnames[i]))

    # make setters
    all_setters = []
    try:
        for i, row in init_vars.groupby('dtype').get_group('bool').iterrows():
            all_setters.append(bool_setter_template.replace("VARNAME",row['name']))
    except KeyError:
        # no bools found
        pass

    try:
        for i, row in init_vars.groupby('dtype').get_group('int').iterrows():
            all_setters.append(int_setter_template.replace("VARNAME",row['name']))
    except KeyError:
        # no ints found
        pass

    try:
        for i, row in init_vars.groupby('dtype').get_group('float').iterrows():
            all_setters.append(float_setter_template.replace("VARNAME",row['name']))
    except KeyError:
        #  no floats ...
        pass

    with open("interface_template.cpp",'r') as fH:
        lines = fH.readlines()

    # replace in include line
    for i, line in enumerate(lines):
        if line == "#include \"interface_variables.h\"\n":
            insertion_ind = i
    lines[insertion_ind] = "#include \""+variables_path+"\"\n"

    # insert getters
    for i,line in enumerate(lines):
        if line == '            // INSERT_GETTERS\n':
            getter_insertion_ind = i
    lines.insert(getter_insertion_ind+1,''.join(all_getters))

    # insert setters
    for i,line in enumerate(lines):
        if line == '            // INSERT_SETTERS\n':
            setter_insertion_ind = i
    lines.insert(setter_insertion_ind+1,''.join(all_setters))

    # write all
    with open('interface.cpp','w') as fH:
        fH.writelines(''.join(lines))

if __name__== "__main__":
    if len(sys.argv)==1:
        # for using defaults from the cmd
        run("interface_variables.h")

    if len(sys.argv) == 2:
        variables_path = sys.argv[1]
        run(variables_path)
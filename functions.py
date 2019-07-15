import scipy as sp
import pandas as pd
import os

# this is the mapping from numpy letter codes to C style arduino compatible
dtype_map = {
            'int':'i4',
            'unsigned int':'u4',
            'long':'i8',
            'unsigned long':'u8',
            'bool':'?',
            'float':'f4',
            'double':'f8',
            }

def parse_code_map(path):
    # FIXME this needs a new name as well - and right now is unused!
    """ a hacky parser """  
    with open(path, 'r') as fH:
        lines = fH.readlines()
        lines = [line.strip() for line in lines]

    # hacky parser:
    dfs = []
    for line in lines:
        try:
            a, b, = line.split(' int ')
            state, code = b.split(' = ')

            dfs.append(pd.DataFrame([[code[:-1], state]], columns=['code', 'name']))
        except:
            pass
    code_map = pd.concat(dfs, axis=0)
    code_map = code_map.reset_index(drop=True)

    return code_map


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
            dfs.append(pd.DataFrame([[name, value, dtype_map[dtype]]],columns=['name', 'value', 'dtype']))
        except:
            print('unreadable line: ',line)
            pass
    arduino_vars = pd.concat(dfs, axis=0)
    arduino_vars = arduino_vars.reset_index(drop=True)

    return arduino_vars

# UI layouting functinos
def tile_Widgets(Widget, RefWidget, where='right', gap=50):
    """ where can be left right above below """
    if where == 'right':
        x = RefWidget.pos().x() + RefWidget.size().width() + gap
        y = RefWidget.pos().y()
    if where == 'below':
        x = RefWidget.pos().x()
        y = RefWidget.pos().y() + RefWidget.size().height() + gap
    Widget.move(x, y)

def scale_Widgets(Widgets, how='vertical'):
    if how == 'vertical':
        widths = [widget.size().width() for widget in Widgets]
        max_width = max(widths)
        [widget.resize(max_width,widget.height()) for widget in Widgets]
        

# if __name__ == '__main__':
#     codes = '/home/georg/Dropbox/Projects/headfixed/data/02_event_codes.h'
#     behav = '/home/georg/Dropbox/Projects/headfixed/data/15_Lollypop_181205_Mauro.txt'

#     code_map = parse_code_map(codes)
#     data_ard = pd.read_csv(behav, delimiter='\t', names=['code', 't', 'values'])

#     code_name = 'TRIAL_NUM_IN_SESSION'
#     code = code_map[code_map['name'] == code_name]['code'].values[0]
#     code = sp.int32(code)
#     times = data_ard.groupby('code').get_group(code)['t']
#     trial_ind = data_ard.groupby('code').get_group(code)['values']

#     import matplotlib.pyplot as plt
#     fig, axes = plt.subplots()
#     axes.plot(times,trial_ind)

#     names = [name for name in code_map.name]
#     for name in names:
#         print(name)

# code_name = 'MISS_REPORT_EVENT'
# code = code_map[code_map['name'] == code_name]['code'].values[0]
# code = sp.int32(code)
# times = data_ard.groupby('code').get_group(code)['t']
# trial_ind = data_ard.groupby('code').get_group(code)['values']

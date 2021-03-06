from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets

import sys

import pandas as pd
import scipy as sp
import utils

class StringChoiceWidget(QtWidgets.QComboBox):
    """ A QComboBox with convenience setter and getter """

    def __init__(self, parent, choices):
        super(StringChoiceWidget, self).__init__(parent=parent)
        self.choices = choices

        for choice in self.choices:
            self.addItem(choice)

    def get_value(self):
        return self.choices[self.currentIndex()]

    def set_value(self, value):
        try:
            self.setCurrentIndex(self.choices.index(value))
        except ValueError:
            self.setCurrentIndex(0)


class ValueEdit(QtWidgets.QLineEdit):
    """ a QLineEdit that keeps track of the numpy dtype and returns accordingly """

    def __init__(self, value, dtype, parent):
        super(ValueEdit, self).__init__(parent=parent)
        self.dtype = dtype
        self.set_value(value)
        self.editingFinished.connect(self.edit_finished)

    def get_value(self):
        self.value = sp.array(self.text(), dtype=self.dtype)
        return self.value

    def set_value(self, value):
        self.value = sp.array(value, dtype=self.dtype)
        self.setText(str(self.value))

    def edit_finished(self):
        self.set_value(self.get_value())

class ValueEditFormLayout(QtWidgets.QFormLayout):
    """ a QFormLayout consisting of ValueEdit rows, to be initialized with a pd.DataFrame 
    with columns name and value, optional dtype (numpy letter codes) """

    def __init__(self, parent, DataFrame):
        super(ValueEditFormLayout,self).__init__(parent=parent)
        self.Df = DataFrame # model

        # if DataFrame does not contain a dtype column, set it to strings
        # TODO figure out when is this actually needed
        # utils.debug_trace()
        if 'dtype' not in self.Df.columns:
            maxlen = max([len(el) for el in self.Df['name']])
            self.Df['dtype'] = 'U'+str(maxlen)

        self.initUI()
    
    def initUI(self):
        self.setVerticalSpacing(10)
        self.setLabelAlignment(QtCore.Qt.AlignRight)

        # init the view
        for i, row in self.Df.iterrows():
            self.addRow(row['name'], ValueEdit(row['value'], row['dtype'], self.parent()))

    def set_entry(self, name, value):
        """ controller function - update both view and model """
        try:
            # get index
            ix = list(self.Df['name']).index(name)
            
            # update model 
            dtype = self.itemAt(ix,1).widget().dtype
            self.Df.loc[ix,'value'] = sp.array(value, dtype=dtype) 
            
            # update view
            self.itemAt(ix,1).widget().set_value(value)

        except ValueError:
            utils.printer("ValueError on attempting to set %s to %s:" % (name, value), 'error')

    def setEnabled(self, value):
         for i in range(self.rowCount()):
            widget = self.itemAt(i, 1).widget()
            widget.setEnabled(value)

    def set_entries(self, Df):
        # test compatibility first
        if not sp.all(Df['name'].sort_values().values == self.Df['name'].sort_values().values):
            utils.printer("can't set entries of variable Df bc they are not equal", 'error')
            utils.debug_trace()
        
        # update the model
        self.Df = Df

        # update the view
        for i, row in Df.iterrows():
            self.set_entry(row['name'], row['value'])

    def get_entry(self, name):
        # controller function - returns a pd.Series
        self.update_model()
        ix = list(self.Df['name']).index(name)
        return self.Df.loc[ix]

    def get_entries(self):
        self.update_model()
        return self.Df

    def update_model(self):
        """ updates model based on UI entries """
        for i in range(self.rowCount()):
            label = self.itemAt(i, 0).widget()
            widget = self.itemAt(i, 1).widget()
            self.set_entry(label.text(), widget.get_value())

class PandasModel(QtCore.QAbstractTableModel):
    """
    Class to populate a table view with a pandas dataframe
    source: https://stackoverflow.com/questions/31475965/fastest-way-to-populate-qtableview-from-pandas-data-frame
    """
    def __init__(self, data, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self._data = data

    def rowCount(self, parent=None):
        return len(self._data.values)

    def columnCount(self, parent=None):
        return self._data.columns.size

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                return str(self._data.values[index.row()][index.column()])
        return None

    def headerData(self, col, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self._data.columns[col]
        return None
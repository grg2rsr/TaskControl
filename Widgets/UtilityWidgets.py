from PyQt5 import QtCore
from PyQt5 import QtWidgets

import numpy as np


import logging

logger = logging.getLogger(__name__)


class StringChoiceWidget(QtWidgets.QComboBox):
    """A QComboBox with convenience setter and getter"""

    def __init__(self, parent, choices, default=None):
        super(StringChoiceWidget, self).__init__(parent=parent)
        self.choices = choices

        for choice in self.choices:
            self.addItem(choice)

        if default is not None:
            self.set_value(default)

    def get_value(self):
        return self.choices[self.currentIndex()]

    def set_value(self, value):
        try:
            self.setCurrentIndex(self.choices.index(value))
        except ValueError:
            self.setCurrentIndex(0)


class ValueEdit(QtWidgets.QLineEdit):
    """a QLineEdit that keeps track of the numpy dtype and returns accordingly"""

    def __init__(self, value, dtype, parent):
        super(ValueEdit, self).__init__(parent=parent)
        self.dtype = dtype
        self.set_value(value)
        self.editingFinished.connect(self.edit_finished)

    def get_value(self):
        try:
            self.value = np.array(self.text(), dtype=self.dtype)
        except:
            logger.warning("invalid entry - discarding")
        return self.value

    def set_value(self, value):
        self.value = np.array(value, dtype=self.dtype)
        self.setText(str(self.value))

    def edit_finished(self):
        self.set_value(self.get_value())


class ValueEditFormLayout(QtWidgets.QWidget):
    """a QFormLayout consisting of ValueEdit rows, to be initialized with a pd.DataFrame
    with columns name and value, optional dtype (numpy letter codes)"""

    def __init__(self, parent, DataFrame=None):
        super(ValueEditFormLayout, self).__init__(parent=parent)
        self.Df = DataFrame  # model

        # if DataFrame does not contain a dtype column, set it to strings
        if "dtype" not in self.Df.columns:
            maxlen = max([len(el) for el in self.Df["name"]])
            self.Df["dtype"] = "U" + str(maxlen)

        self.initUI()

    def initUI(self):
        self.FormLayout = QtWidgets.QFormLayout(self)
        self.FormLayout.setVerticalSpacing(10)
        self.FormLayout.setLabelAlignment(QtCore.Qt.AlignRight)

        # init the view
        for i, row in self.Df.iterrows():
            self.FormLayout.addRow(
                row["name"], ValueEdit(row["value"], row["dtype"], self.parent())
            )

    def set_entry(self, name, value):
        """controller function - update both view and model"""
        if name not in list(self.Df["name"]):
            logger.warning("trying to set variable %s, but is not part of model" % name)
            # self.Df.loc[name,'value'] = value

        else:
            # get index
            ix = list(self.Df["name"]).index(name)

            # update model
            # dtype = self.FormLayout.itemAt(ix,1).widget().dtype
            dtype = self.Df.loc[ix, "dtype"]  # dtype is part of the model
            self.Df.loc[ix, "value"] = np.array(value, dtype=dtype)  # explicit cast

            # update view
            self.FormLayout.itemAt(ix, 1).widget().set_value(value)

    def set_entries(self, Df):
        """make sure elsewhere that this is only called with valid Dfs?"""
        # update the model
        # self.Df = Df

        # update the view
        for i, row in Df.iterrows():
            self.Df[row["name"]] = row["value"]
            self.set_entry(row["name"], row["value"])

    def get_entry(self, name):
        # controller function - returns a pd.Series
        self.update_model()
        ix = list(self.Df["name"]).index(name)
        return self.Df.loc[ix]

    def get_entries(self):
        self.update_model()
        return self.Df

    def update_model(self):
        """updates model based on UI entries"""
        for i in range(self.FormLayout.rowCount()):
            label = self.FormLayout.itemAt(i, 0).widget()
            widget = self.FormLayout.itemAt(i, 1).widget()
            self.set_entry(label.text(), widget.get_value())

    def setEnabled(self, value):
        for i in range(self.FormLayout.rowCount()):
            widget = self.FormLayout.itemAt(i, 1).widget()
            widget.setEnabled(value)


class TerminateEdit(QtWidgets.QWidget):
    def __init__(self, parent, DataFrame=None):
        super(TerminateEdit, self).__init__(parent=parent)
        self.FormLayout = QtWidgets.QFormLayout(self)
        self.FormLayout.setVerticalSpacing(10)
        self.FormLayout.setLabelAlignment(QtCore.Qt.AlignRight)

        # self terminate
        self.selfTerminateCheckBox = QtWidgets.QCheckBox()
        self.selfTerminateCheckBox.setChecked(True)
        self.is_enabled = True
        self.selfTerminateCheckBox.stateChanged.connect(self.TerminateCheckBoxToggle)
        self.FormLayout.addRow("self terminate", self.selfTerminateCheckBox)

        self.selfTerminateEdit = ValueEditFormLayout(self.parent(), DataFrame=DataFrame)
        self.FormLayout.addRow(self.selfTerminateEdit)
        self.selfTerminateEdit.setEnabled(False)

    def TerminateCheckBoxToggle(self, state):
        if state == 0:
            self.selfTerminateEdit.setEnabled(True)
            self.is_enabled = False

        if state == 2:
            self.selfTerminateEdit.setEnabled(False)
            self.is_enabled = True


class PandasModel(QtCore.QAbstractTableModel):
    """
    Class to populate a table view with a pandas dataframe
    source: https://stackoverflow.com/questions/31475965/fastest-way-to-populate-qtableview-from-pandas-data-frame
    """

    def __init__(self, data, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self.setDf(data)

    def setData(self, *args):
        super().setData(*args)
        self.dataChanged.emit(
            self.index(0, 0), self.index(self._data.shape[0], self._data.shape[1])
        )
        return True

    def setDf(self, data):
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


# class PandasModel(QtGui.QStandardItemModel):
#     """ modified from this post https://stackoverflow.com/a/63708391 """

#     def __init__(self, data, parent=None):
#         QtGui.QStandardItemModel.__init__(self, parent)
#         self._data = data

#         for col in data.columns:
#             data_col = [QtGui.QStandardItem("{}".format(x)) for x in data[col].values]
#             self.appendColumn(data_col)
#         return

#     def rowCount(self, parent=None):
#         return len(self._data.values)

#     def columnCount(self, parent=None):
#         return self._data.columns.size

#     def headerData(self, x, orientation, role):
#         if orientation == Qt.Horizontal and role == Qt.DisplayRole:
#             return self._data.columns[x]
#         if orientation == Qt.Vertical and role == Qt.DisplayRole:
#             return self._data.index[x]
#         return None

#     def setDf(self, Df):
#         for i in range(Df.shape[0]):
#             for j in range(Df.shape[1]):
#                 index = QtCore.QModelIndex().sibling(i,j)
#                 val = Df.iloc[i,j]
#                 super().setData(index, val, 2)

#     def setData(self,*args):
#         super().setData(*args)
#         self.dataChanged.emit(self.index(0,0), self.index(self._data.shape[0], self._data.shape[1]))
#         return True

# def set_data(self, Df):
#     self._data = Df
#     self.dataChanged.emit(self.index(0,0), self.index(Df.shape[0],Df.shape[1]))
# for i in range(   Df.shape[0]):
#     for j in range(Df.shape[1]):
#         self.dataChanged.emit(self.index(i,j), self.index(i,j))


class ArrayModel(QtCore.QAbstractTableModel):
    """
    adapted from source
    source: https://stackoverflow.com/questions/31475965/fastest-way-to-populate-qtableview-from-pandas-data-frame

    also check here: https://www.pythonguis.com/faq/editing-pyqt-tableview/
    """

    def __init__(self, array, row_labels, col_labels, parent=None):
        # super(ArrayModel).__init__(self, parent) # this doesn't work
        QtCore.QAbstractTableModel.__init__(self, parent)  # this does. No idea why

        # self.set_data(array, row_labels, col_labels)
        self.array = array
        self.row_labels = row_labels
        self.col_labels = col_labels

    # def set_data(self, array, row_labels, col_labels):

    # def setData(self,*args):
    #     super().setData(*args) # ??
    #     return True

    def update(self):
        self.dataChanged.emit(
            self.index(0, 0), self.index(self.array.shape[0], self.array.shape[1])
        )

    def setData(self, index, value, role):
        if role == QtCore.EditRole:
            # try:
            #     value = int(value)
            # except ValueError:
            #     return False
            self.array[index.row(), index.column()] = value
            self.dataChanged.emit(
                self.index(0, 0), self.index(self.array.shape[0], self.array.shape[1])
            )
            return True
        return False

    def rowCount(self, parent=None):
        return len(self.row_labels)

    def columnCount(self, parent=None):
        return len(self.col_labels)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                return str(self.array[index.row(), index.column()])
        return None

    def headerData(self, col, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.col_labels[col]
        return None

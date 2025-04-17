import sys
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from Widgets.UtilityWidgets import ValueEdit


class RunInfoPopup(QtWidgets.QDialog):
    """collects all that is left required manual input by the user upon run"""

    # TODO Implement this!!
    # idea: also this logs stuff about the session
    # after each run, a session_meta df is created containing
    # animal id, task, date, start, stop, duration, ntrials

    def __init__(self, parent):
        super(RunInfoPopup, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.initUI()

    def initUI(self):
        self.FormLayout = QtWidgets.QFormLayout()
        self.FormLayout.setVerticalSpacing(10)
        self.FormLayout.setLabelAlignment(QtCore.Qt.AlignRight)

        # Fields
        self.WeigthEditWidget = ValueEdit(30, "f4", self)
        self.FormLayout.addRow("Weight (g)", self.WeigthEditWidget)

        FormWidget = QtWidgets.QWidget()
        FormWidget.setLayout(self.FormLayout)

        Btn = QtWidgets.QPushButton()
        Btn.setText("Done")
        Btn.clicked.connect(self.done_btn_clicked)

        Full_Layout = QtWidgets.QVBoxLayout()
        Full_Layout.addWidget(FormWidget)
        Full_Layout.addWidget(Btn)
        self.setLayout(Full_Layout)

        self.setWindowTitle("Run info")
        self.exec()

    def done_btn_clicked(self):
        meta = self.parent().Animal.meta
        weight = self.WeigthEditWidget.get_value()
        if "current_weight" not in meta["name"].values:
            ix = meta.shape[0]
            meta.loc[ix] = ["current_weight", weight]
        else:
            meta.loc[meta["name"] == "current_weight", "value"] = weight
        self.accept()


class ErrorPopup(QtWidgets.QMessageBox):
    # TODO implement me
    def __init__(self, error_msg, parent=None):
        super(ErrorPopup, self).__init__(parent=parent)
        self.setText(error_msg)
        self.setIcon(QtWidgets.QMessageBox.Critical)
        self.setStandardButtons(QtWidgets.QMessageBox.Close)
        self.buttonClicked.connect(self.crash)
        self.show()

    def crash(self):
        # TODO log crash error msg
        sys.exit()

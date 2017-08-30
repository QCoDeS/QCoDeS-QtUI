# QCoDeS
from qcodes.plots.base import BasePlot

# PyQt
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import  QAction, QApplication, QListWidget, QListWidgetItem

class DataArrayListWidget(QListWidget):

    def __init__(self, dataArrayChanged, parent=None):
        self.dataArrayChanged = dataArrayChanged
        QListWidget.__init__(self, parent)
        self.selectionModel().currentChanged.connect(self.onSelectionChange)
        self.dataArrays = dict()

    def onSelectionChange(self, current, previous):
        print('sel')
        # TODO: add some fail check to this
        self.dataArrayChanged.emit(self.dataArrays[current.data()])


    def loadDataSet(self, dataset):
        self._dataset = dataset
        self._populate()
        # set the active view
        # for now just use the first array
        for data_array in self._dataset.arrays.values():
            if not data_array.is_setpoint:
                break
        self.dataArrayChanged.emit(data_array)

    def _populate(self):
        self.clear()
        self.dataArrays.clear()
        iUnnamed=1
        for data_array in self._dataset.arrays.values():
            if not data_array.is_setpoint:
                # for now, store dataarrays in dictionary
                name = data_array.name
                print(name)
                if name == '' or not name:
                    name = 'unamed {}'.format(iUnnamed)
                    iUnnamed += 1
                self.dataArrays[name] = data_array
                item = QListWidgetItem(name, self)
                # 0 display role... cant find include at the moment
                # TODO: replace by proper constant Qt.DisplayRole
                item.setData(0,data_array)
                item.setText(name)
                # data_array.name
                self.addItem(item)

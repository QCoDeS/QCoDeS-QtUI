# PyQt
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import  QAction, QWidget, QLabel, QVBoxLayout, QPushButton, QApplication, QListWidget, QListWidgetItem, QGroupBox
from PyQt5.QtGui import  QListView
import PyQt5.QtGui as QtGui

class FilterListWidget(QListWidget):

    def __init__(self, parent=None):
        QListWidget.__init__(self, parent)
        self.selectionModel().currentChanged.connect(self.onSelectionChange)
        self.setFlow(QListView.LeftToRight)
        for i in range(2):
            name = "name {}".format(i)
            item = QListWidgetItem(name, self)
            item.setText(name)
            widget = item.listWidget()
            widget.setStyleSheet("QListWidget::item {border: 1px solid grey}")
        item = QListWidgetItem(self)
        item_widget = AddFilterWidget()
        item.setSizeHint(item_widget.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, item_widget)

    def onSelectionChange(self, current, previous):
        print('sel')
        # TODO: add some fail check to this


class AddFilterWidget(QGroupBox):
    def __init__(self, parent=None):
        super(AddFilterWidget, self).__init__(parent)
        self.setTitle("addFilter")
        # label = QLabel("add filter")
        button = QPushButton("+")
        button.setMinimumHeight(50)
        button.setMinimumWidth(10)
        layout = QVBoxLayout()
        # layout.addWidget(label)
        layout.addWidget(button)
        layout.addStretch(1)
        self.setLayout(layout)

        self.actionHello = QtGui.QAction(self)
        self.actionHello.setText("Hello")

        self.menu = QtGui.QMenu(self)
        self.menu.addAction(self.actionHello)

        button.setMenu(self.menu)


class BaseFilterWidget(QWidget):
    def __init__(self, parent=None):
        super(AddFilterWidget, self).__init__(parent)
        label = QLabel("add filter")
        button = QPushButton("+")
        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(button)
        self.setLayout(layout)

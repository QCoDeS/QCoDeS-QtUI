import sys
import os

# Matplotlib
import matplotlib
# Make sure that we are using QT5
matplotlib.use('Qt5Agg')
from matplotlib.figure import Figure

# qcodes
from qcodes.data.data_set import load_data
from qcodes.data.data_array import DataArray

# PyQt
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMainWindow, QTextEdit, QAction, QApplication, QListWidget, QDockWidget, QFileDialog
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPainter, QFont
from PyQt5.QtCore import QSize, QRect, Qt, pyqtSignal

from .widgets.xsection import CrossSectionWidget
from .widgets.DataArrayListWidget import DataArrayListWidget

def getImageResourcePath(resource):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), '../data/', resource)

def getIconFromLetter(letter, color):
    pixmap = QPixmap(256,256)
    pixmap.fill(QColor('#00000000'))
    painter = QPainter(pixmap)
    painter.setPen(QColor(color));
    font = QFont()
    font.setPixelSize(256)
    # painter.setFont(QFont("Decorative", 10));
    painter.setFont(font);
    painter.drawText(QRect(0,0, 256,256), Qt.AlignCenter, letter);
    painter.end()
    icon = QIcon(pixmap)
    return icon


class ApplicationWindow(QMainWindow):
    # http://pyqt.sourceforge.net/Docs/PyQt5/signals_slots.html
    dataArrayChanged = pyqtSignal(DataArray, name='OnDataSetChanged')

    def __init__(self, dataset):
        QtWidgets.QMainWindow.__init__(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        # Main Window
        self.setWindowTitle("QCoDeS Qt Ui")
        # self.setIcon(QIcon(getImageResourcePath('qcodes.png')))
        self.setWindowIcon(QIcon(getImageResourcePath('qcodes.png')))
        # Actions

        quit_action = QAction(QIcon(getImageResourcePath('quit.png')), 'Quit' , self)
        quit_action.setShortcut('Ctrl+q')
        quit_action.triggered.connect(self.onQuit)

        file_open_action = QAction(QIcon(getImageResourcePath('fileopen.png')), 'Open' , self)
        file_open_action.setShortcut('Ctrl+o')
        file_open_action.triggered.connect(self.onOpenFile)

        about_action = QAction(QIcon(getImageResourcePath('about.png')), 'About' , self)
        about_action.triggered.connect(self.onAbout)

        # Menus
        # File
        self.file_menu = QtWidgets.QMenu('&File', self)
        self.menuBar().addMenu(self.file_menu)
        self.file_menu.addAction(file_open_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(quit_action)
        # Tools
        tool_menu = QtWidgets.QMenu('&Tools', self)
        self.menuBar().addMenu(tool_menu)

        # help
        self.help_menu = QtWidgets.QMenu('&Help', self)
        self.menuBar().addSeparator()
        self.menuBar().addMenu(self.help_menu)
        self.help_menu.addAction(about_action)

        # toolbars
        toolbar = self.addToolBar('Tools')
        toolbar2 = self.addToolBar('mplTools')

        # Tools
        tools = dict()
        def addTool(id,  name, shortcut, tip, **kwargs):
            if 'icon' in kwargs.keys():
                tools[id] =  QAction(kwargs['icon'], name, self)
            else:
                tools[id] =  QAction(name, self)
            tools[id].setShortcut(shortcut)
            tools[id].setStatusTip(tip)
            toolbar.addAction(tools[id])
            tool_menu.addAction(tools[id])

        addTool('OrthoXSection', 'Orthorgonal cross section', 'Ctrl+o',
                'The orthorgonal cross section tool creates a profile of the data'+
                'at a given point',
                icon=QIcon(getImageResourcePath('crosshair.png')))
        addTool('CustomXSection', 'Custom cross section', 'Ctrl+u',
                'The custom cross section tool creates a profile of the data between'+
                'two given points',
                icon=QIcon(getImageResourcePath('customXSection.png')))
        addTool('sumXSection', 'sum cross section', 'Ctrl+u',
                'The sum cross section tool creates a profile of the data between'+
                'by summing all datapoints',
                icon=getIconFromLetter('Σ','#5f8cba'))
        addTool('planeFit', 'Plane fit', 'Ctrl+f',
                'Substract any linear background by fitting a plane to the data'+
                'and substracting it',
                icon=QIcon(getImageResourcePath('planeFit.png')))
        # Widgets

        # Data array dock
        self.data_array_widget = DataArrayListWidget(self.dataArrayChanged)
        data_array_dock = QDockWidget("Data arrays", self)
        data_array_dock.setWidget(self.data_array_widget)
        data_array_dock.setFloating(False)

        # Main Widget
        self.main_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.main_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, data_array_dock)

        l = QtWidgets.QHBoxLayout(self.main_widget)


        # toolbar2.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
        #                        QtWidgets.QSizePolicy.Expanding)
        toolbar2.setFixedWidth(500)
        cw = CrossSectionWidget(self.dataArrayChanged, toolbar2, tools=tools)
        l.addWidget(cw)

        self.main_widget.setFocus()

        self.statusBar().showMessage("Starting", 2000)
        self.data_array_widget.loadDataSet(dataset)

        # # Cross Section Widget
        # # find first meassured dataset
        # for data_array in dataset.arrays.values():
        #     if not data_array.is_setpoint:
        #         first_data_array = data_array
        #         break

    # events
    def onOpenFile(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","All Files (*);;Python Files (*.py)", options=options)
        if fileName:
            dataset = load_data(location=fileName)
            self.data_array_widget.loadDataSet(dataset)


    def onQuit(self):
        self.close()

    def closeEvent(self, ce):
        self.fileQuit()

    def onAbout(self):
        QtWidgets.QMessageBox.about(self, "About", "QCoDeS Qt Ui v0.1" )


# QCoDeS
from qcodes.plots.base import BasePlot

# matplotlib
import matplotlib
matplotlib.use("QT5Agg")
from matplotlib.widgets import Cursor
from matplotlib.ticker import FormatStrFormatter
from matplotlib.widgets import RectangleSelector
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import mplcursors

# scipy and numpy
from scipy.interpolate import interp2d
import numpy as np

# PyQt
from PyQt5 import QtWidgets


class CrossSectionWidget(BasePlot):

    def __init__(self, dataset):
        super().__init__()
        data = {}
        self.expand_trace(args=[dataset], kwargs=data)
        self.traces = []

        data['xlabel'] = self.get_label(data['x'])
        data['ylabel'] = self.get_label(data['y'])
        data['zlabel'] = self.get_label(data['z'])
        data['xaxis'] = data['x'].ndarray[0, :]
        data['yaxis'] = data['y'].ndarray
        self.traces.append({
            'config': data,
        })
        self.fig = plt.figure()

        self._lines = []
        self._datacursor = []
        self._cid = 0
        self._XSection = (0,0)
        self._creatingCustomXSection = False
        self._drawingLine = False
        # self._customLine = np.array([[ 0.0,0.0 ],[ 0.0,0.0 ]])
        self._customLine = None
        self._customLinePlots = []
        self._customLinePos = np.array([[ 0,0 ],[ 0,0 ]])
        self._customLineExists = False
        self._customXPoints = None
        self._customYPoints = None
        self._crossSections = []
        self._followCursor = False
        self._cursors = []

        hbox = QtWidgets.QHBoxLayout()
        self.fig.canvas.setLayout(hbox)
        hspace = QtWidgets.QSpacerItem(0,
                                       0,
                                       QtWidgets.QSizePolicy.Expanding,
                                       QtWidgets.QSizePolicy.Expanding)
        vspace = QtWidgets.QSpacerItem(0,
                                       0,
                                       QtWidgets.QSizePolicy.Minimum,
                                       QtWidgets.QSizePolicy.Expanding)
        hbox.addItem(hspace)

        vbox = QtWidgets.QVBoxLayout()
        self.crossbtn = QtWidgets.QCheckBox('Cross section')
        self.crossbtn.setToolTip("Display extra subplots with selectable cross sections "
                                 "or sums along axis.")
        self.customSectionBtn = QtWidgets.QCheckBox('custom cross section')
        # self.customSectionBtn.setToolTip("Display extra subplots with selectable cross sections "
                                 # "or sums along axis.")
        self.sumbtn = QtWidgets.QCheckBox('Sum')
        self.sumbtn.setToolTip("Display sums or cross sections.")

        self.savehmbtn = QtWidgets.QPushButton('Save Heatmap')
        self.savehmbtn.setToolTip("Save heatmap as a file (PDF)")
        self.savexbtn = QtWidgets.QPushButton('Save Vert')
        self.savexbtn.setToolTip("Save vertical cross section or sum as a file (PDF)")
        self.saveybtn = QtWidgets.QPushButton('Save Horz')
        self.savexbtn.setToolTip("Save horizontal cross section or sum as a file (PDF)")

        self.crossbtn.toggled.connect(self.toggle_cross)
        self.customSectionBtn.toggled.connect(self.toggle_customSection)
        self.sumbtn.toggled.connect(self.toggle_sum)

        self.savehmbtn.pressed.connect(self.save_heatmap)
        self.savexbtn.pressed.connect(self.save_subplot_x)
        self.saveybtn.pressed.connect(self.save_subplot_y)
        # Save custom cross section button
        self.customCrossSectionBtn = QtWidgets.QPushButton('save custom x-section')
        self.customCrossSectionBtn.pressed.connect(self.save_custom_x_section)
        vbox.addWidget(self.customCrossSectionBtn)

        self.toggle_cross()
        self.toggle_sum()

        vbox.addItem(vspace)
        vbox.addWidget(self.crossbtn)
        vbox.addWidget(self.customSectionBtn)
        vbox.addWidget(self.sumbtn)
        vbox.addWidget(self.savehmbtn)
        vbox.addWidget(self.savexbtn)
        vbox.addWidget(self.saveybtn)

        hbox.addLayout(vbox)

    @staticmethod
    def full_extent(ax, pad=0.0):
        """Get the full extent of an axes, including axes labels, tick labels, and
        titles."""
        # for text objects we only include them if they are non empty.
        # empty ticks may be rendered outside the figure
        from matplotlib.transforms import Bbox
        items = []
        items += [ax.xaxis.label, ax.yaxis.label, ax.title]
        items = [item for item in items if item.get_text()]
        items.append(ax)
        bbox = Bbox.union([item.get_window_extent() for item in items])
        return bbox.expanded(1.0 + pad, 1.0 + pad)

    def save_custom_x_section(self): 
        fig2 = plt.figure()
        ax1 = fig2.add_subplot(121)
        ax2 = fig2.add_subplot(122)
        self.draw3DData(ax1)
        self.drawCustomXSectionOn3DData(ax1)
        self.drawCustomXSection(ax2)
        fig2.show()



    def save_subplot(self, axnumber, savename, saveformat='pdf'):
        extent = self.full_extent(self.ax[axnumber]).transformed(self.fig.dpi_scale_trans.inverted())
        full_title = "{}.{}".format(savename, saveformat)
        self.fig.savefig(full_title, bbox_inches=extent)

    def save_subplot_x(self):
        title = self.get_default_title()
        label, unit = self._get_label_and_unit(self.traces[0]['config']['xlabel'])
        if self.sumbtn.isChecked():
            title += " sum over {}".format(label)
        else:
            title += " cross section {} = {} {}".format(label,
                                                        self.traces[0]['config']['xpos'],
                                                        unit)
        self.save_subplot(axnumber=(0, 1), savename=title)

    def save_subplot_y(self):
        title = self.get_default_title()
        label, unit = self._get_label_and_unit(self.traces[0]['config']['ylabel'])
        if self.sumbtn.isChecked():
            title += " sum over {}".format(label)
        else:
            title += " cross section {} = {} {}".format(label,
                                                        self.traces[0]['config']['xpos'],
                                                        unit)
        self.save_subplot(axnumber=(1, 0), savename=title)

    def save_heatmap(self):
        title = self.get_default_title() + " heatmap"
        self.save_subplot(axnumber=(0, 0), savename=title)

    def _update_label(self, ax, axletter, label, extra=None):

        if type(label) == tuple and len(label) == 2:
            label, unit = label
        else:
            unit = ""
        axsetter = getattr(ax, "set_{}label".format(axletter))
        if extra:
            axsetter(extra + "{} ({})".format(label, unit))
        else:
            axsetter("{} ({})".format(label, unit))

    @staticmethod
    def _get_label_and_unit(config):
        if type(config) == tuple and len(config) == 2:
            label, unit = config
        else:
            unit = ""
            label = config
        return label, unit

    # def _create_subplots(self):


    def toggle_cross(self):
        self.remove_plots()
        self.fig.clear()
        if self._cid:
            self.fig.canvas.mpl_disconnect(self._cid)
        if self.crossbtn.isChecked():
            self.sumbtn.setEnabled(True)
            self.savexbtn.setEnabled(True)
            self.saveybtn.setEnabled(True)
            self.ax = np.empty((2, 2), dtype='O')
            self.ax[0, 0] = self.fig.add_subplot(2, 2, 1)
            self.ax[0, 1] = self.fig.add_subplot(2, 2, 2)
            self.ax[1, 0] = self.fig.add_subplot(2, 2, 3)
            self.ax[1, 1] = self.fig.add_subplot(2, 2, 4)
            self._cid = self.fig.canvas.mpl_connect('motion_notify_event', self._onMouseMove)
            self._cid = self.fig.canvas.mpl_connect('button_press_event', self._onMouseDown)
            self.fig.canvas.mpl_connect('key_press_event', self._onKeyPress)
            # self._cid = self.fig.canvas.mpl_connect('button_press_event', self._onMouseUp)
            self._cursor = Cursor(self.ax[0, 0], useblit=True, color='black')
            self._followCursor = True
            self.toggle_sum()
            figure_rect = (0, 0.0, 0.75, 1)
        else:
            self.sumbtn.setEnabled(False)
            self.savexbtn.setEnabled(False)
            self.saveybtn.setEnabled(False)
            self.ax = np.empty((1, 1), dtype='O')
            self.ax[0, 0] = self.fig.add_subplot(1, 1, 1)
            figure_rect = (0, 0.0, 0.75, 1)
        self.draw3DData(self.ax[0,0])
        self.fig.tight_layout(rect=figure_rect)
        self.fig.canvas.draw_idle()

    def draw3DData(self, ax):
        ax.pcolormesh(self.traces[0]['config']['x'],
                      self.traces[0]['config']['y'],
                      self.traces[0]['config']['z'],
                      edgecolor='face')
        self._update_label(ax, 'x', self.traces[0]['config']['xlabel'])
        self._update_label(ax, 'y', self.traces[0]['config']['ylabel'])
        ax.yaxis.get_major_formatter().set_powerlimits((0,0))


    def toggle_customSection(self):
        if self.customSectionBtn.isChecked():
            self._creatingCustomXSection = True
        else:
            self._creatingCustomXSection = False

    def toggle_sum(self):
        self.remove_plots()
        if not self.crossbtn.isChecked():
            return
        self.ax[1, 0].clear()
        self.ax[0, 1].clear()
        if self.sumbtn.isChecked():
            self._cursor.set_active(False)
            self.ax[1, 0].set_ylim(0, self.traces[0]['config']['z'].sum(axis=0).max() * 1.05)
            self.ax[0, 1].set_xlim(0, self.traces[0]['config']['z'].sum(axis=1).max() * 1.05)
            self._update_label(self.ax[1, 0], 'x', self.traces[0]['config']['xlabel'])
            self._update_label(self.ax[1, 0], 'y', self.traces[0]['config']['zlabel'], extra='sum of ')

            self._update_label(self.ax[0, 1], 'x', self.traces[0]['config']['zlabel'], extra='sum of ')
            self._update_label(self.ax[0, 1], 'y', self.traces[0]['config']['ylabel'])

            self._lines.append(self.ax[0, 1].plot(self.traces[0]['config']['z'].sum(axis=1),
                                                  self.traces[0]['config']['yaxis'],
                                                  color='C0',
                                                  marker='.')[0])
            self.ax[0, 1].set_title("")
            self._lines.append(self.ax[1, 0].plot(self.traces[0]['config']['xaxis'],
                                                  self.traces[0]['config']['z'].sum(axis=0),
                                                  color='C0',
                                                  marker='.')[0])
            self.ax[1, 0].set_title("")
            self._datacursor = mplcursors.cursor(self._lines, multiple=False)
        else:
            self._cursor.set_active(True)
            self._update_label(self.ax[1, 0], 'x', self.traces[0]['config']['xlabel'])
            self._update_label(self.ax[1, 0], 'y', self.traces[0]['config']['zlabel'])

            self._update_label(self.ax[0, 1], 'x', self.traces[0]['config']['zlabel'])
            self._update_label(self.ax[0, 1], 'y', self.traces[0]['config']['ylabel'])

            self.ax[1, 0].set_ylim(self.traces[0]['config']['z'].min() * 1.05,
                                   self.traces[0]['config']['z'].max() * 1.05)
            self.ax[0, 1].set_xlim(self.traces[0]['config']['z'].min() * 1.05,
                                   self.traces[0]['config']['z'].max() * 1.05)
        self.fig.canvas.draw_idle()

    def remove_plots(self):
        for line in self._lines:
            line.remove()
        self._lines = []
        if self._datacursor:
            self._datacursor.remove()

    def _addXSectionPlots(self):
        self.remove_plots()
        self._lines.append(self.ax[0, 1].plot(self.traces[0]['config']['z'][:,self._XSection[0]],
                                                self.traces[0]['config']['yaxis'],
                                                color='C0',
                                                marker='.')[0])
        xlabel, xunit = self._get_label_and_unit(self.traces[0]['config']['xlabel'])
        self.ax[0, 1].set_title("{} = {:.2n} {} ".format(xlabel, self.traces[0]['config']['xaxis'][self._XSection[0]], xunit),
                                fontsize='small')
        self.traces[0]['config']['xpos'] = self.traces[0]['config']['xaxis'][self._XSection[0]]
        self._lines.append(self.ax[1, 0].plot(self.traces[0]['config']['xaxis'],
                                                self.traces[0]['config']['z'][self._XSection[1], :],
                                                color='C0',
                                                marker='.')[0])
        ylabel, yunit = self._get_label_and_unit(self.traces[0]['config']['ylabel'])
        self.ax[1, 0].set_title("{} = {:.2n} {}".format(ylabel, self.traces[0]['config']['yaxis'][self._XSection[1]], yunit),
                                fontsize='small')
        self.traces[0]['config']['ypos'] = self.traces[0]['config']['yaxis'][self._XSection[1]]
        self.ax[1,0].yaxis.get_major_formatter().set_powerlimits((0,0))
        self.ax[0,1].yaxis.get_major_formatter().set_powerlimits((0,0))

    def _getAxisCoordinatesFromEvent(self, event):
        xpos = (abs(self.traces[0]['config']['xaxis'] - event.xdata)).argmin()
        ypos = (abs(self.traces[0]['config']['yaxis'] - event.ydata)).argmin()
        return [xpos, ypos]

    def _updateXSections(self):
        if not self._lines:
            self._addXSectionPlots()
        else:
            self._lines[0].set_xdata(self.traces[0]['config']['z'][:, self._XSection[0]])
            self._lines[1].set_ydata(self.traces[0]['config']['z'][self._XSection[1], :])
        self.ax[0,1].relim()
        self.ax[0,1].autoscale_view()
        self.ax[1,0].relim()
        self.ax[1,0].autoscale_view()
        xlabel, xunit = self._get_label_and_unit(self.traces[0]['config']['xlabel'])
        ylabel, yunit = self._get_label_and_unit(self.traces[0]['config']['ylabel'])
        self.ax[0,1].set_title("{} = {:.2n} {} ".format(xlabel, self.traces[0]['config']['xaxis'][self._XSection[0]], xunit),
                                fontsize='small')
        self.ax[1,0].set_title("{} = {:.2n} {}".format(ylabel, self.traces[0]['config']['yaxis'][self._XSection[1]], yunit),
                                fontsize='small')
        self._datacursor = mplcursors.cursor(self._lines, multiple=False)
        self.fig.canvas.draw_idle()

    def _index2data(self, index):
        x = self.traces[0]['config']['xaxis'][index[0]]
        y = self.traces[0]['config']['yaxis'][index[1]]
        return (x,y)

    def _updateCursor(self):
        x,y  = self._index2data(self._XSection)
        # print(x)
        # print(y)
        if self._cursors:
            self._cursors[0].remove()
            self._cursors[1].remove()
            self._cursors = []
        self._cursors.append(self.ax[0,0].axhline(y=y, zorder=20))
        self._cursors.append(self.ax[0,0].axvline(x=x, zorder=20))
        self.fig.canvas.draw_idle()

    def _onMouseMove(self, event):
        if event.inaxes == self.ax[0, 0] and not self.sumbtn.isChecked():
            pos = self._getAxisCoordinatesFromEvent(event)
            if self._followCursor:
                self._XSection = pos
                self._updateXSections()

    def _interpolate(self ):
        f = interp2d(self.traces[0]['config']['xaxis'],
                     self.traces[0]['config']['yaxis'],
                     self.traces[0]['config']['z'])
        start = self._customLine[0,:]
        end = self._customLine[1,:]
        maxV = np.hypot(end[0]-start[0],end[1]-start[1])
        r2 = np.expand_dims(end-start,1)
        s2 = np.expand_dims(start,1)
        lp = self._customLinePos
        numPoints = np.hypot(lp[0,0]-lp[1,0],lp[0,1]-lp[1,1])
        xPoints = np.linspace(0,maxV, numPoints)
        p = np.linspace(0,1,numPoints)
        points = s2 + np.kron(r2,p)
        # ok this is dirty but it should work
        return xPoints, np.transpose(np.diag(f(points[0,:],points[1,:])))

    def _onMouseDown(self, event):
        if event.inaxes == self.ax[0, 0] and not self.sumbtn.isChecked():
            # get psoition and data for click event
            pos = self._getAxisCoordinatesFromEvent(event)
            x,y = self._index2data(pos)
            x,y = event.xdata, event.ydata
            # events for left mouse button click
            if event.button ==1:
                # for the custom cross section tool
                if self._creatingCustomXSection:
                    # are in the middle of drawing a line?
                    if not self._drawingLine:
                        # creating a new line
                        # is there already a line that has been drawn earlier
                        if self._customLineExists:
                            # if so delete it
                            for l in self.ax[1,1].lines:
                                l.remove()
                            self.ax[1,1].lines = []
                            for l in self._customLinePlots:
                                l.remove()
                            self._customLinePlots = []
                            self._customLineExists = False

                        # create a new cross section
                        self._customLine = np.array([[ 0.0,0.0 ],[ 0.0,0.0 ]])
                        self._customLinePlots.append(self.ax[0,0].plot(x,y, 'r+')[0])
                        self._customLine[0] = [x,y]
                        self._customLinePos[0] = pos
                        self._drawingLine = True
                        self.fig.canvas.draw_idle()
                    else:
                        # we have already set the first point
                        self._customLine[1] = [x,y]
                        self._customLinePos[1] = pos
                        self._customLinePlots.append(self.drawCustomXSectionOn3DData(self.ax[0,0]))
                        self._drawingLine = False
                        self._customLineExists = True
                        self.fig.canvas.draw_idle()
                        self._customXPoints, self._customYPoints = self._interpolate()
                        self.drawCustomXSection(self.ax[1,1])

                else:
                    # using the parallel cross section tool
                    self._XSection = pos
                    self._updateCursor()
                    self._updateXSections()
                    self._followCursor = False

    def drawCustomXSection(self, ax):
        ax.set_xlim((min(self._customXPoints),max(self._customXPoints)))
        ax.plot(self._customXPoints,self._customYPoints, color='C0')
        ax.set_title('Multiparameter Crossection', fontsize='small')

    def drawCustomXSectionOn3DData(self, ax):
        return ax.plot(self._customLine[:,0],self._customLine[:,1], 'r+-')[0]

    def _onKeyPress(self, event):
        if self._creatingCustomXSection:
            pass
        else:
            if event.key == 'left':
                self._XSection[0] = self._XSection[0]-1
            elif event.key == 'right':
                self._XSection[0] = self._XSection[0]+1
            if event.key == 'up':
                self._XSection[1] = self._XSection[1]+1
            elif event.key == 'down':
                self._XSection[1] = self._XSection[1]-1
            self._updateCursor()
            self._updateXSections()

    def _onCustomSection(self, eclick, erelease):
        pass

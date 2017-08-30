# QCoDeS
from qcodes.plots.base import BasePlot

# matplotlib
import matplotlib
matplotlib.use("QT5Agg")
from matplotlib.widgets import Cursor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from matplotlib.ticker import FormatStrFormatter
from matplotlib.widgets import RectangleSelector
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.figure import Figure
import mplcursors

# scipy and numpy
from scipy.interpolate import interp2d
import numpy as np

# PyQt
from PyQt5 import QtWidgets, QtCore


class CrossSectionWidget(FigureCanvas, BasePlot):
    rotateCrossSection = True

    def __init__(self, dataArrayChanged, parent, tools=None):
        #
        self.dataArrayChanged = dataArrayChanged
        self.parent = parent

        BasePlot.__init__(self)

        # create plot
        self.fig = Figure()

        FigureCanvas.__init__(self, self.fig)
        FigureCanvas.setSizePolicy(self,
                                   QtWidgets.QSizePolicy.Expanding,
                                   QtWidgets.QSizePolicy.Expanding)
        # for receiving key events this focus has to be set
        self.setFocusPolicy( QtCore.Qt.ClickFocus )
        self.setFocus()
        FigureCanvas.updateGeometry(self)

        # connect events for data array update
        dataArrayChanged.connect(self.onDataArrayChange)

        # connect events for tools
        if tools is not None:
        # this function does not do anything. It is however necessary to create a new scope for id
        # wihtout it id would always be the last value of the for loop
            def createHandler(id):
                return lambda: self.onToolChange(id)
            for id in tools.keys():
                tools[id].triggered.connect(createHandler(id))

        # add toolbar
        self.mpl_toolbar = NavigationToolbar(self, parent)

    def onDataArrayChange(self, dataArray):
        print('on data array change in xsection widget')
        self.showDataArray(dataArray)

    def showDataArray(self, dataArray):
        # handle data
        data = {}
        self.expand_trace(args=[dataArray], kwargs=data)
        self.traces = []

        data['xlabel'] = self.get_label(data['x'])
        data['ylabel'] = self.get_label(data['y'])
        data['zlabel'] = self.get_label(data['z'])
        data['xaxis'] = data['x'].ndarray[0, :]
        data['yaxis'] = data['y'].ndarray
        self.traces.append({
            'config': data,
        })

        # clear figure first
        self.fig.clear()
        self.axes = dict()
        self.axes['main'] = self.fig.add_subplot(111)
        self.draw3DData(self.axes['main'])
        self.fig.canvas.draw_idle()

        # init members

        # widget relevant

        # dictionary of the active event handlers
        self.eventIDs = dict()

        # orthogonal cross sections

        # plot object reference to the presisten lines drawn on the main axes
        # representing the cuts where the cross sections are taken at
        self.staticOrthoCursors = []
        # position where the two cursors meet in index coordinates
        self.orhtoXSectionPos = (0,0)
        # plot object reference to the plots in the two axis of the cross sections
        self._lines = []
        # Indicates wheter the cross section should be updated on cursor movement
        self.orthoXSectionlive = True

        # custom cross section:

        # reflecting state of having set one point and awaiting selection of the second
        self._drawingLine = False
        # the points of the custom cross section in data coordinates
        self._customLine = None
        # Custom cross section defining points in index coordinates
        self._customLinePos = np.array([[ 0,0 ],[ 0,0 ]])
        # reference to the plot of the dot and the line as
        # drawn on the main figure when creating a custom cross section
        self._customLinePlots = []
        # reflects state of a custom cross section has been drawn.
        # -> remove and use coordinates
        self._customLineExists = False
        # inter polated data representing the data points along the cross section
        self._customXPoints = None
        self._customYPoints = None


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

    def save_subplot(self, axes, savename, saveformat='pdf'):
        extent = self.full_extent(axes).transformed(
            self.fig.dpi_scale_trans.inverted())
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

    # plotting
    def remove_plots(self):
        for line in self._lines:
            line.remove()
        for key,ax in self.axes.items():
            ax.clear()
        self.axes = dict()
        self._customLinePlots = []
        self.staticOrthoCursors = []
        self._lines = []

    def _addXSectionPlots(self):
        # self.remove_plots()
        # x means cut parrallel to x axes at a given y value, lower plot
        # y is first index in traces
        ax = self.axes['x'] 
        ax.yaxis.get_major_formatter().set_powerlimits((0,0))
        self._lines.append(ax.plot(self.traces[0]['config']['xaxis'],
                                   self.traces[0]['config']['z'][self.orhtoXSectionPos[1], :],
                                   color='C0',
                                   marker='.')[0])
        self._update_label(ax, 'x', self.traces[0]['config']['xlabel'])
        self._update_label(ax, 'y', self.traces[0]['config']['zlabel'])
        self.traces[0]['config']['ypos'] = self.traces[0]['config']['yaxis'][self.orhtoXSectionPos[1]]
        theMax = self.traces[0]['config']['z'].ravel().max() * 1.05
        theMin = self.traces[0]['config']['z'].ravel().min() * 1.05
        ax.set_ylim(theMin, theMax)

        # y means cut parrallel to y axes at a given x value, right plot
        # x is second index in traces
        ax = self.axes['y'] # y means cut parrallel to y axes, as 
        if self.rotateCrossSection:
            ax.xaxis.get_major_formatter().set_powerlimits((0,0))
            self._lines.append(ax.plot(self.traces[0]['config']['yaxis'],
                                       self.traces[0]['config']['z'][:,self.orhtoXSectionPos[0]],
                                       color='C0',
                                       marker='.')[0])
            self._update_label(ax, 'x', self.traces[0]['config']['ylabel'])
            self._update_label(ax, 'y', self.traces[0]['config']['zlabel'])
            self.traces[0]['config']['xpos'] = self.traces[0]['config']['yaxis'][self.orhtoXSectionPos[0]]
            sum = self.traces[0]['config']['z'].sum(axis=0) * 1.05
            ax.set_ylim(theMin, theMax)
        else:
            ax.yaxis.get_major_formatter().set_powerlimits((0,0))
            self._lines.append(ax.plot(self.traces[0]['config']['z'][:,self.orhtoXSectionPos[0]],
                                       self.traces[0]['config']['yaxis'],
                                       color='C0',
                                       marker='.')[0])
            self._update_label(ax, 'y', self.traces[0]['config']['ylabel'])
            self._update_label(ax, 'x', self.traces[0]['config']['zlabel'])
            self.traces[0]['config']['xpos'] = self.traces[0]['config']['yaxis'][self.orhtoXSectionPos[0]]
            sum = self.traces[0]['config']['z'].sum(axis=0) * 1.05
            ax.set_xlim(theMin, theMax)

        self._updateXSections()


    def _updateXSections(self):
        # updating data points
        if not self._lines:
            self._addXSectionPlots()
        else:
            # lines[0] is parallel x axes, so y values change for a given ypos
            self._lines[0].set_ydata(self.traces[0]['config']['z'][self.orhtoXSectionPos[1], :])
            if self.rotateCrossSection:
                self._lines[1].set_ydata(self.traces[0]['config']['z'][:, self.orhtoXSectionPos[0]])
            else:
                self._lines[1].set_xdata(self.traces[0]['config']['z'][:, self.orhtoXSectionPos[0]])

        # updateing title and label
        for i,d in enumerate(['x', 'y']):
            # self.axes[d].relim()
            # self.axes[d].autoscale_view()
            label, unit = self._get_label_and_unit(self.traces[0]['config'][d+'label'])
            self.axes[d].set_title("{} = {:.2n} {} ".format(
                label, self.traces[0]['config'][d+'axis'][self.orhtoXSectionPos[i]], unit),
                                   fontsize='small')
        # self._datacursor = mplcursor.cursor(self._lines, multiple=False)
        self.fig.canvas.draw_idle()

    def draw3DData(self, ax):
        ax.pcolormesh(self.traces[0]['config']['x'],
                      self.traces[0]['config']['y'],
                      self.traces[0]['config']['z'],
                      edgecolor='face')
        self._update_label(ax, 'x', self.traces[0]['config']['xlabel'])
        self._update_label(ax, 'y', self.traces[0]['config']['ylabel'])
        ax.yaxis.get_major_formatter().set_powerlimits((0,0))

    def drawCustomXSection(self, ax):
        ax.set_xlim((min(self._customXPoints),max(self._customXPoints)))
        ax.plot(self._customXPoints,self._customYPoints, color='C0')
        ax.set_title('Multiparameter Crossection', fontsize='small')

    def drawCustomXSectionOn3DData(self, ax):
        return ax.plot(self._customLine[:,0],self._customLine[:,1], 'r+-')[0]

    # Coordinate transformations
    def _getAxisCoordinatesFromEvent(self, event):
        xpos = (abs(self.traces[0]['config']['xaxis'] - event.xdata)).argmin()
        ypos = (abs(self.traces[0]['config']['yaxis'] - event.ydata)).argmin()
        return [xpos, ypos]

    def _index2data(self, index):
        x = self.traces[0]['config']['xaxis'][index[0]]
        y = self.traces[0]['config']['yaxis'][index[1]]
        return (x,y)

    # events
    def removeStaticCursor(self):
        if self.staticOrthoCursors:
            self.staticOrthoCursors[0].remove()
            self.staticOrthoCursors[1].remove()
            self.staticOrthoCursors = []
        self.fig.canvas.draw_idle()

    def _updateStaticCursor(self):
        self.removeStaticCursor()
        x,y  = self._index2data(self.orhtoXSectionPos)
        self.staticOrthoCursors.append(self.axes['main'].axhline(y=y, zorder=20))
        self.staticOrthoCursors.append(self.axes['main'].axvline(x=x, zorder=20))
        self.fig.canvas.draw_idle()

    def _onKey(self, event):
        print('onKey')

    def onToolChange(self, id):
        self.tool = id
        print(id)
        if id == 'OrthoXSection' or id=='CustomXSection' or id=='sumXSection':
            self.remove_plots()
            self.fig.clear()

            self.axes['main'] = self.fig.add_subplot(2, 2, 1)
            self.axes['x']= self.fig.add_subplot(2, 2, 3)
            self.axes['y'] = self.fig.add_subplot(2, 2, 2)
            self._addXSectionPlots()

            self.draw3DData(self.axes['main'])
            self.fig.tight_layout()
            self.fig.canvas.draw_idle()

        if id == 'OrthoXSection' or id=='CustomXSection':
            self._cursor = Cursor(self.axes['main'], useblit=True, color='black')
            # rewire events
            for eventName, callback in [('motion_notify_event', self._onMouseMove),
                                        ('button_press_event', self._onMouseDown),
                                        ('key_press_event', self._onKeyPress)]:
                if self.eventIDs.get(eventName) is not None:
                    self.fig.canvas.mpl_disconnect(self.eventIDs[eventName])
                self.eventIDs[eventName] = self.fig.canvas.mpl_connect(eventName, callback)

        if id == 'CustomXSection':
            self.axes['custom'] = self.fig.add_subplot(2, 2, 4)

        if id == 'sumXSection':
            # lines[0] is parallel x axes, so y values change for a given ypos
            self.axes['x'].set_ylim(0, self.traces[0]['config']['z'].sum(axis=0).max() * 1.05)
            self._lines[0].set_ydata(self.traces[0]['config']['z'].sum(axis=0))
            if self.rotateCrossSection:
                self.axes['y'].set_ylim(0, self.traces[0]['config']['z'].sum(axis=1).max() * 1.05)
                self._lines[1].set_ydata(self.traces[0]['config']['z'].sum(axis=1))
            else:
                self.axes['y'].set_xlim(0, self.traces[0]['config']['z'].sum(axis=1).max() * 1.05)
                self._lines[1].set_xdata(self.traces[0]['config']['z'].sum(axis=1))

            self.fig.canvas.draw_idle()
        if id == 'planeFit':
            x = self.traces[0]['config']['xaxis']
            y = self.traces[0]['config']['yaxis']
            xv, yv = np.meshgrid(x,y)
            z = self.traces[0]['config']['z']
            A = np.column_stack((np.ones(xv.size), xv.flatten(), yv.flatten()))
            zus,resid,rank,sigma = np.linalg.lstsq(A,z.flatten())
            z = z-zus[0]-xv*zus[1]-yv*zus[2]
            self.traces[0]['config']['z'] = z
            self.draw3DData(self.axes['main'])
            self.fig.tight_layout()
            self.fig.canvas.draw_idle()



    def _onMouseMove(self, event):
        if event.inaxes == self.axes['main']:
            pos = self._getAxisCoordinatesFromEvent(event)
            if self.tool == 'OrthoXSection':
                if self.orthoXSectionlive == True:
                    self.orhtoXSectionPos = pos
                    self._updateXSections()


    def _onMouseDown(self, event):
        # only capture click events for the main figure
        if event.inaxes == self.axes['main']:
            # get psoition and data for click event
            pos = self._getAxisCoordinatesFromEvent(event)
            # x,y = self._index2data(pos)
            x,y = event.xdata, event.ydata
            # events for left mouse button click
            if event.button ==1:
                # for the custom cross section tool
                if self.tool == 'CustomXSection':
                    # are in the middle of drawing a line?
                    if not self._drawingLine:
                        # creating a new line
                        # is there already a line that has been drawn earlier
                        if self._customLineExists:
                            # if so delete it
                            for l in self.axes['custom'].lines:
                                l.remove()
                            self.axes['custom'].lines = []
                            for l in self._customLinePlots:
                                l.remove()
                            self._customLinePlots = []
                            self._customLineExists = False

                        # create a new cross section
                        self._customLine = np.array([[ 0.0,0.0 ],[ 0.0,0.0 ]])
                        self._customLinePlots.append(self.axes['main'].plot(x,y, 'r+')[0])
                        self._customLine[0] = [x,y]
                        self._customLinePos[0] = pos
                        self._drawingLine = True
                        self.fig.canvas.draw_idle()
                    else:
                        # we have already set the first point
                        self._customLine[1] = [x,y]
                        self._customLinePos[1] = pos
                        self._customLinePlots.append(self.drawCustomXSectionOn3DData(self.axes['main']))
                        self._drawingLine = False
                        self._customLineExists = True
                        self.fig.canvas.draw_idle()
                        self._customXPoints, self._customYPoints = self._interpolate()
                        self.drawCustomXSection(self.axes['custom'])

                elif self.tool == 'OrthoXSection':
                    # using the parallel cross section tool
                    self.orthoXSectionlive = False
                    self.orhtoXSectionPos = pos
                    self._updateStaticCursor()
                    self._updateXSections()
            if event.button ==3:
                if self.tool == 'OrthoXSection':
                    self.removeStaticCursor()
                    self.orthoXSectionlive = True


    def _onKeyPress(self, event):
        if self.tool == 'CustomXSection':
            pass
        elif self.tool == 'OrthoXSection':
            if event.key == 'left':
                self.orhtoXSectionPos[0] = self.orhtoXSectionPos[0]-1
            elif event.key == 'right':
                self.orhtoXSectionPos[0] = self.orhtoXSectionPos[0]+1
            if event.key == 'up':
                self.orhtoXSectionPos[1] = self.orhtoXSectionPos[1]+1
            elif event.key == 'down':
                self.orhtoXSectionPos[1] = self.orhtoXSectionPos[1]-1
            self._updateStaticCursor()
            self._updateXSections()

    # calculation
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

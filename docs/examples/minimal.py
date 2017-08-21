import numpy as np
import matplotlib
matplotlib.use("QT5Agg")
import qcodes as qc
from qcodes.instrument.parameter import ArrayParameter, MultiParameter
from qcodes.tests.instrument_mocks import DummyInstrument
from qcodes.utils.wrappers import do1d, do2d, do1dDiagonal, init
from qcodes.plots.qcmatplotlib_viewer_widget import *
from qcodes.data.data_array import DataArray

# ugly way of importing QCoDeS-QtUI module
import sys
import os
sys.path.append(os.path.join('../..',''))
from qcqtui.widgets.xsection import CrossSectionWidget

dac = DummyInstrument(name="dac", gates=['ch1', 'ch2'])  # The DAC voltage source
dmm = DummyInstrument(name="dmm", gates=['voltage', 'current'])  # The DMM reader

import random
dmm.voltage.get =  lambda: random.randint(0, 100)
dmm.current.get = lambda: 1e-3*np.random.randn()
dmm.current.unit = 'A'
station = qc.Station(dac, dmm)
init(mainfolder='PlotTesting',
     sample_name='plottestsample',
     station=station,
     annotate_image=False)

plot, data = do2d(dac.ch1, 0, 10e-7, 50, 0.00,
                  dac.ch2, 0, 10, 55, 0.00, dmm.voltage, do_plots=False)
dac.close()
dmm.close()


# generate test data
y, x = np.meshgrid(np.linspace(-3, 3,55), np.linspace(-3,3, 50))
z = (1 - x / 2. + x ** 5 + y ** 3) * np.exp(-x ** 2 - y ** 2)

# set the test data to the sample dataset
data.dmm_voltage.ndarray = z

# create widget
cw = CrossSectionWidget(data.dmm_voltage)
cw.fig.show()

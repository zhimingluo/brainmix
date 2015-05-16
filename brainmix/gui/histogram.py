'''
Widget to edit the pixel-intensity histogram of images.

Currently this class is intended to do it all:
calculate histogram, show it, edit it.

Please see the AUTHORS file for credits.
'''

from PySide import QtGui
from PySide import QtCore
import numpy as np

class HistogramView(QtGui.QWidget):
    def __init__(self,parent=None):
        '''
        Intended to show intensity histogram of images.
        It will also show boundaries (to be edited with a slider)
        '''
        super(HistogramView, self).__init__(parent)
        self.setMinimumWidth(200)
        self.setMinimumHeight(100)
        self.setMaximumWidth(300)
        self.setMaximumHeight(200)
        ###self.boundPos = [0,300] ### FIXME

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+W"), self, self.close,
                        context=QtCore.Qt.WidgetShortcut)

    def set_data(self,image,nbins):
        '''Calculate histogram and show it, given image data'''
        if self.isVisible():
             #FIXME: calculating bins every time may be slow
            if image.dtype==np.float:
                bins = np.linspace(0,1,nbins+1)
            else:
                bins = np.arange(nbins)
            (histValues, binEdges) = np.histogram(image,bins=bins)
            self.hist = histValues
            self.bins = binEdges[:-1]
            self.update()

    def transform_coords(self,xval,yval):
        '''Transform plotting values to window pixel values'''
        width = self.width()
        height = self.height()
        xvalrange = float(xval[-1]-xval[0])
        yvalrange = float(max(yval))
        hval = (width * (xval-xval[0])/xvalrange).astype(int)
        vval = height-(height * (yval-yval[0])/yvalrange).astype(int)
        return (hval,vval)

    def paintEvent(self, e):
        qp = QtGui.QPainter()
        qp.begin(self)
        if len(self.bins):
            self.draw_hist(qp)
            ###self.draw_bound(qp,1) # FIXME
        qp.end()

    def draw_bound(self,qp,ind):
        '''Draw darkest and brightest level boundaries'''
        boundColor = QtGui.QColor(200,200,220,128)
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(boundColor)
        nBins = len(self.bins)
        width = self.width() * self.boundPos[ind]/nBins
        height = self.height()
        if ind==0:
            qp.drawRect(0,0,width,height)
        elif ind==1:
            qp.drawRect(width,0,self.width(),height)

    def draw_hist(self, qp):
        '''Draw histogram'''
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(QtCore.Qt.gray)
        xval = np.r_[self.bins[0],self.bins,self.bins[-1]]
        yval = np.r_[0,self.hist,0]
        hval,vval = self.transform_coords(xval,yval)
        histPoints = QtGui.QPolygonF()
        for oneHval,oneVval in zip(hval,vval):
            histPoints.append(QtCore.QPointF(oneHval,oneVval))
        qp.drawPolygon(histPoints)

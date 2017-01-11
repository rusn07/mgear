# MGEAR is under the terms of the MIT License

# Copyright (c) 2016 Jeremie Passerin, Miquel Campos

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Author:     Jeremie Passerin      geerem@hotmail.com  www.jeremiepasserin.com
# Author:     Miquel Campos         hello@miquel-campos.com  www.miquel-campos.com
# Date:       2016 / 10 / 10


##################################################
# GLOBAL
##################################################
import traceback

import pymel.core as pm
import maya.OpenMayaUI as OpenMayaUI
import mgear.maya.pyqt as gqt

import mgear
import mgear.maya.synoptic.utils as syn_uti
import mgear.maya.synoptic.widgets as mwi

# import functools

QtGui, QtCore, QtWidgets, wrapInstance, shiboken = gqt.qt_import(True)


##################################################
# SYNOPTIC TAB WIDGET
##################################################
class MainSynopticTab(QtWidgets.QDialog):
    """
    Base class of synoptic tab widget

    """

    description = "base calss of synoptic tab"
    name = ""
    bgPath = None

    buttons = []
    default_buttons = [
        {"name": "selAll", "mouseTracking": True},
        {"name": "keyAll"},
        {"name": "keySel"},
        {"name": "resetAll"},
        {"name": "resetSel"}
    ]

    # ============================================
    # INIT
    def __init__(self, klass, parent=None):
        # type: (MainSynopticTab, QtWidgets.QWidget) -> None

        print("Loading synoptic tab of {0}".format(self.name))

        super(MainSynopticTab, self).__init__(parent)

        klass.setupUi(self)
        klass.setBackground()
        klass.connectSignals()
        klass.connectMaya()

        # This is necessary for not to be zombie job on close.
        # Qt does not actually destroy the object by just pressing
        # close button by default.
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

    def setBackground(self):
        # type: () -> None

        # Retarget background Image to absolute path
        if self.bgPath is not None:
            self.img_background.setPixmap(QtGui.QPixmap(self.bgPath))

    def connectSignals(self):
        # type: () -> None

        def _conn(entry):
            name = entry.get("name")
            buttonName = "b_{0}".format(name)
            button = getattr(self, buttonName, None)

            clickEventName = "{0}_clicked".format(name)
            clickEvent = getattr(self, clickEventName, None)

            if not button or not clickEvent:
                return  # TODO

            button.clicked.connect(clickEvent)
            if entry.get("mouseTracking", False):
                button.setMouseTracking(True)

        # this is equivalent to below code commented out
        for entry in self.default_buttons + self.buttons:
            _conn(entry)

        # self.b_selAll.clicked.connect(self.selAll_clicked)
        # self.b_selAll.setMouseTracking(True)
        # self.b_keyAll.clicked.connect(self.keyAll_clicked)
        # self.b_keySel.clicked.connect(self.keySel_clicked)

        self.rubberband = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Rectangle, self)

    def connectMaya(self):
        # type: () -> None
        # script job callback
        ptr = long(shiboken.getCppPointer(self)[0])
        gui = OpenMayaUI.MQtUtil.fullName(ptr)
        self.selJob = pm.scriptJob(e=("SelectionChanged", self.selectChanged), parent=gui)

    def selectChanged(self, *args):
        """

        :param args:
        """

        # wrap to catch exception guaranteeing maya does not stop at this
        try:
            self.__selectChanged(*args)

        except Exception as e:
            mes = traceback.format_exc()
            mes = "error has occur in scriptJob SelectionChanged\n{0}".format(mes)
            mes = "{0}\n{1}".format(mes, e)
            mgear.log(mes, mgear.sev_error)

    def __selectChanged(self, *args):

        sels = []
        [sels.append(x.name()) for x in pm.ls(sl=True)]

        oModel = syn_uti.getModel(self)
        if not oModel:
            mes = "model not found for synoptic"
            mgear.log(mes, mgear.sev_info)

            self.close()

            syn_widget = syn_uti.getSynopticWidget(self)
            syn_widget.updateModelList()

            return

        nameSpace = syn_uti.getNamespace(oModel.name())

        selButtons = self.findChildren(mwi.SelectButton)
        for selB in selButtons:
            obj = str(selB.property("object")).split(",")
            if len(obj) == 1:
                if nameSpace:
                    checkName = ":".join([nameSpace, obj[0]])
                else:
                    checkName = obj[0]

                if checkName in sels:
                    selB.paintSelected(True)
                else:
                    selB.paintSelected(False)

    def mousePressEvent(self, event):
        self.origin = event.pos()
        self.rubberband.setGeometry(QtCore.QRect(self.origin, QtCore.QSize()))
        self.rubberband.show()
        QtWidgets.QWidget.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self.rubberband.isVisible():
            self.rubberband.setGeometry(QtCore.QRect(self.origin, event.pos()).normalized())
        QtWidgets.QWidget.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self.rubberband.isVisible():
            self.rubberband.hide()
            selected = []
            rect = self.rubberband.geometry()

            for child in self.findChildren(mwi.SelectButton):
                if rect.intersects(child.geometry()):
                    selected.append(child)

            if selected:
                firstLoop = True
                with pm.UndoChunk():
                    for wi in selected:
                        wi.rectangleSelection(event, firstLoop)
                        firstLoop = False

            else:
                if event.modifiers() == QtCore.Qt.NoModifier:
                    pm.select(cl=True)
                    pm.displayInfo("Clear selection")

        QtWidgets.QWidget.mouseReleaseEvent(self, event)

    # ============================================
    # BUTTONS
    def selAll_clicked(self):
        model = syn_uti.getModel(self)
        syn_uti.selAll(model)

    def resetAll_clicked(self):
        print "resetAll"

    def resetSel_clicked(self):
        print "resetSel"

    def keyAll_clicked(self):
        model = syn_uti.getModel(self)
        syn_uti.keyAll(model)

    def keySel_clicked(self):
        syn_uti.keySel()

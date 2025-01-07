# Standard imports
import sys, time, pickle
# Library imports
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
# Custom imports
from BlenderState import BlenderState, BlenderStateManager
from ConvertedMat import ConvertedMat
from TextureConverter import TextureConverterTab
from VRAMPacker import VRAMPackerTab
from ModelExporter import ModelExporterTab

class MainWindow(QMainWindow):
    def __init__(self):
        # Setup window
        super().__init__()
        self.setWindowTitle("PSXport")
        self.setGeometry(0, 0, 1280, 1024)
        # Program state vars
        self.blender = BlenderStateManager(BlenderState())
        self.convertedMats = {}
        # Setup main tabbed section
        self.mainTabs = QTabWidget(self)
        self.textureConverter = TextureConverterTab(self.blender, self.convertedMats)
        self.VRAMPacker = VRAMPackerTab(self.blender, self.convertedMats)
        self.modelExporter = ModelExporterTab(self.blender, self.convertedMats)
        self.mainTabs.addTab(self.textureConverter, 'Texture Converter')
        self.mainTabs.addTab(self.VRAMPacker, 'VRAM Packer')
        self.mainTabs.addTab(self.modelExporter, 'Model Exporter')
        self.mainTabs.currentChanged.connect(self.updatePages)
        # Setup actions for managing Blender connection
        self.connectAction = QAction(QIcon('./icons/connect.png'), 'Connect', self)
        self.connectAction.setStatusTip('Connect to Blender')
        self.connectAction.triggered.connect(self.blender.connect)
        self.disconnectAction = QAction(QIcon('./icons/disconnect.png'), 'Disconnect', self)
        self.disconnectAction.setStatusTip('Disconnect from Blender')
        self.disconnectAction.triggered.connect(self.blender.disconnect)
        self.syncAction = QAction(QIcon('./icons/refresh.png'), 'Sync', self)
        self.syncAction.setStatusTip('Sync with Blender')
        self.syncAction.triggered.connect(self.syncBlender)
        # Setup actions for saving and loading state
        self.saveAction = QAction(QIcon('./icons/save.png'), 'Save', self)
        self.saveAction.setStatusTip('Save')
        self.saveAction.triggered.connect(self.save)
        self.loadAction = QAction(QIcon('./icons/load.png'), 'Load', self)
        self.loadAction.setStatusTip('Load')
        self.loadAction.triggered.connect(self.load)
        # Add everything to the main window
        self.setCentralWidget(self.mainTabs)
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.addAction(self.connectAction)
        self.toolbar.addAction(self.disconnectAction)
        self.toolbar.addAction(self.syncAction)
        spacer = QLabel('')
        spacer.setFixedWidth(50)
        self.toolbar.addWidget(spacer)
        self.toolbar.addAction(self.saveAction)
        self.toolbar.addAction(self.loadAction)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.addToolBar(self.toolbar)
        self.statusBar()
    def save(self):
        saveFile = open("./saveFile.pkl", "wb")
        pickle.dump(self.convertedMats, saveFile)
        saveFile.close()
    def load(self):
        loadFile = open("./saveFile.pkl", "rb")
        self.convertedMats.clear()
        self.convertedMats.update(pickle.load(loadFile))
        loadFile.close()
        self.updatePages()
    # Called everytime you sync with blender
    def syncBlender(self):
        self.blender.sync()
        # TODO Invalidate converted mats which have changed originals
        self.updatePages()
    def updatePages(self):
        self.textureConverter.updatePage()
        self.VRAMPacker.updatePage()
        self.modelExporter.updatePage()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec())

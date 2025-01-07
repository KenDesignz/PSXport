# Standard imports
import math, struct
# Library imports
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QImage, QPainter, QPen, QColor, QMouseEvent
# Custom imports
from BlenderState import BlenderStateManager
from ConvertedMat import ConvertedMat
# Generated imports
from VRAMPackerGen import Ui_VRAMPacker

class VRAMPackerTab(QWidget, Ui_VRAMPacker):
    def __init__(self, sharedBlender, sharedConvertedMats):
        # Shared program state
        self.blender = sharedBlender
        self.convertedMats = sharedConvertedMats
        # Tab state
        self.selectedItemID = None
        self.selectedItemType = None
        # Setup tab
        super().__init__()
        self.setupUi(self)
        self.VRAMViewer = VRAMWidget(self)
        self.VRAMScrollArea.setWidget(self.VRAMViewer)
        self.itemList.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.itemList.sortItems(3, Qt.AscendingOrder)
        # Setup custom signals
        self.exportBinButton.clicked.connect(self.exportBin)
        self.exportHeaderButton.clicked.connect(self.exportHeader)
        self.packSelectedButton.clicked.connect(lambda: self.packSelected(True))
        self.unpackSelectedButton.clicked.connect(lambda: self.packSelected(False))
        self.itemList.itemSelectionChanged.connect(self.selectItemList)
        self.autopackSelectedButton.clicked.connect(self.autoPackSelected)
        self.autopackAllButton.clicked.connect(self.autoPackAll)
        self.selectedXSpin.valueChanged.connect(self.updateItemSpin)
        self.selectedYSpin.valueChanged.connect(self.updateItemSpin)
        self.bufferWidthSelector.currentTextChanged.connect(self.VRAMViewer.repaint)
        self.bufferHeightSelector.currentTextChanged.connect(self.VRAMViewer.repaint)
        self.buffer1XPosSelector.valueChanged.connect(self.VRAMViewer.repaint)
        self.buffer1YPosSelector.valueChanged.connect(self.VRAMViewer.repaint)
        self.buffer2XPosSelector.valueChanged.connect(self.VRAMViewer.repaint)
        self.buffer2YPosSelector.valueChanged.connect(self.VRAMViewer.repaint)
    def selectItemList(self):
        if len(self.itemList.selectedItems()) == 0: return
        self.selectedItemID = self.itemList.selectedItems()[0].text(3)
        self.selectedItemType = self.itemList.selectedItems()[0].text(2)
        mat = self.convertedMats[self.selectedItemID]
        xPos = 0
        yPos = 0
        enableFlag = False
        if self.selectedItemType == 'Texture':
            if mat.packed:
                xPos = mat.xPos
                yPos = mat.yPos
                enableFlag = True
        elif self.selectedItemType == 'CLUT':
            if mat.packedCLUT:
                xPos = mat.xPosCLUT
                yPos = mat.yPosCLUT
                enableFlag = True
        self.selectedXSpin.setEnabled(enableFlag)
        self.selectedYSpin.setEnabled(enableFlag)
        self.selectedXLabel.setEnabled(enableFlag)
        self.selectedYLabel.setEnabled(enableFlag)
        self.selectedXSpin.setValue(xPos)
        self.selectedYSpin.setValue(yPos)
    def packSelected(self, packState):
        if self.selectedItemID == None: return
        mat = self.convertedMats[self.selectedItemID]
        if self.selectedItemType == 'Texture':
            mat.packed = packState
        elif self.selectedItemType == 'CLUT':
            mat.packedCLUT = packState
        self.selectItemList()
        self.updatePage()
    def boxInside(self, xBox, yBox, wBox, hBox, xBin, yBin, wBin, hBin):
        return (
            xBox >= xBin and
            yBox >= yBin and
            (xBox + wBox) <= (xBin + wBin) and
            (yBox + hBox) <= (yBin + hBin)
        )
    def boxCollision(self, xBox, yBox, wBox, hBox, xBin, yBin, wBin, hBin):
        # Check if one box is to the left of the other
        if xBox + wBox <= xBin or xBin + wBin <= xBox:
            return False

        # Check if one box is above the other
        if yBox + hBox <= yBin or yBin + hBin <= yBox:
            return False

        # If none of the conditions for being separated are met, the boxes collide
        return True
    def anyCollisions(self, x, y, w, h):
        # TODO Check collisions with framebuffer(s)
        bufWidth = int(self.bufferWidthSelector.currentText())
        bufHeight = int(self.bufferHeightSelector.currentText())
        bufX1 = self.buffer1XPosSelector.value()
        bufY1 = self.buffer1YPosSelector.value()
        if self.boxCollision(x, y, w, h, bufX1, bufY1, bufWidth, bufHeight):
            return True, bufX1+bufWidth
        if self.doubleBufferCheck.isChecked():
            bufX2 = self.buffer2XPosSelector.value()
            bufY2 = self.buffer2YPosSelector.value()
            if self.boxCollision(x, y, w, h, bufX2, bufY2, bufWidth, bufHeight):
                return True, bufX2+bufWidth
        for matKey in self.convertedMats:
            mat = self.convertedMats[matKey]
            if mat.packed:
                if self.boxCollision(x, y, w, h, mat.xPos, mat.yPos, mat.tpXSize, mat.ySize):
                    return True, mat.xPos+mat.tpXSize
            if mat.packedCLUT:
                colorCount = {4: 16, 8: 256}[mat.colorMode]
                if self.boxCollision(x, y, w, h, mat.xPosCLUT, mat.yPosCLUT, colorCount, 1):
                    return True, mat.xPosCLUT+colorCount
        return False, 0
    def findTexturePackCoords(self, width, height, tpWidth):
        for y in range(0, 512, 8):
            tpY = math.floor(y/256)*256
            if not self.boxInside(0, y, width, height, 0, tpY, tpWidth, 256):
                y = tpY + 256 - 8
                continue
            for x in range(0, 1024, 8):
                tpX = math.floor(x/64)*64
                if not self.boxInside(x, y, width, height, tpX, tpY, tpWidth, 256):
                    x = tpX + tpWidth - 8
                    continue
                collisions, nextXPos = self.anyCollisions(x, y, width, height)
                if not collisions:
                    return (True, x, y)
                else:
                    x = nextXPos-8
        return False, None, None
    def findCLUTPackCoords(self, colorCount):
        for y in range(0, 512, 1):
            for x in range(0, 1024, 16):
                if not self.boxInside(x, y, colorCount, 1, 0, 0, 1024, 512):
                    continue
                collisions, nextXPos = self.anyCollisions(x, y, colorCount, 1)
                if not collisions:
                    return True, x, y
                else:
                    x = nextXPos-16
        return False, None, None
    def autoPackSingle(self, itemID, itemType):
        if itemID == None: return
        mat = self.convertedMats[itemID]
        if itemType == 'Texture':
            tpWidth = {4: 64, 8: 128, 15: 256}[mat.colorMode]
            status, xFound, yFound = self.findTexturePackCoords(mat.tpXSize, mat.ySize, tpWidth)
            if status:
                mat.packed = True
                mat.xPos = xFound
                mat.yPos = yFound
        elif itemType == 'CLUT':
            status, xFound, yFound = self.findCLUTPackCoords({4: 16, 8: 256}[mat.colorMode])
            if status:
                mat.packedCLUT = True
                mat.xPosCLUT = xFound
                mat.yPosCLUT = yFound
        self.selectItemList()
        self.updatePage()
    def autoPackSelected(self):
        self.autoPackSingle(self.selectedItemID, self.selectedItemType)
    def autoPackAll(self):
        for matKey in self.convertedMats:
            mat = self.convertedMats[matKey]
            if mat.textureImg != None:
                self.autoPackSingle(matKey, 'Texture')
        for matKey in self.convertedMats:
            mat = self.convertedMats[matKey]
            if mat.textureCLUT != None:
                self.autoPackSingle(matKey, 'CLUT')
    def unPackAll(self):
        pass
    def updateItemSpin(self):
        if self.selectedItemID == None: return
        xPos = self.selectedXSpin.value()
        yPos = self.selectedYSpin.value()
        mat = self.convertedMats[self.selectedItemID]
        if self.selectedItemType == 'Texture':
            mat.xPos = xPos
            mat.yPos = yPos
        elif self.selectedItemType == 'CLUT':
            mat.xPosCLUT = xPos
            mat.yPosCLUT = yPos
        self.selectItemList()
        self.updatePage()
    def redrawList(self):
        self.itemList.itemSelectionChanged.disconnect()
        self.itemList.clear()
        for matName in self.convertedMats:
            mat = self.convertedMats[matName]
            if mat.type != 'T': continue
            # Texture
            valid = '🚫'
            packed = '➖'
            if mat.valid:
                valid = '✅'
                if mat.packed:
                    packed = '✅'
                else:
                    packed = '🚫'
            item = QTreeWidgetItem([valid, packed, "Texture", matName])
            if valid == '🚫':
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.itemList.addTopLevelItem(item)
            # CLUT
            if mat.textureCLUT == None: continue
            if mat.packedCLUT:
                packed = '✅'
            else:
                packed = '🚫'
            item = QTreeWidgetItem([valid, packed, "CLUT", matName])
            if valid == '🚫':
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.itemList.addTopLevelItem(item)
        self.itemList.sortItems(self.itemList.header().sortIndicatorSection(), self.itemList.header().sortIndicatorOrder())
        self.itemList.itemSelectionChanged.connect(self.selectItemList)
    def exportBin(self):
        outputName = "MATS1"
        outputPath = "./DummyPath/"
        outputFile = open(f'{outputPath}/{outputName}.BIN', 'wb')
        for matName in self.convertedMats:
            mat = self.convertedMats[matName]
            if mat.type != 'T': continue
            if not mat.packed: continue
            outputFile.write(struct.pack('<HHHH', mat.tpXSize, mat.ySize, mat.xPos, mat.yPos))
            if mat.colorMode == 15:
                for y in range(mat.ySize):
                    for x in range(mat.xSize):
                        pixRGB = mat.textureImg.getpixel((x, y))
                        pixR = pixRGB[0] >> 3
                        pixG = pixRGB[1] >> 3
                        pixB = pixRGB[2] >> 3
                        pixTotal = (pixB << 10) + (pixG << 5) + (pixR)
                        outputFile.write(struct.pack('<H', pixTotal))
            elif mat.colorMode == 8:
                for y in range(mat.ySize):
                    for x in range(mat.tpXSize):
                        pix0 = mat.textureImg.getpixel((x*2, y))
                        pix1 = mat.textureImg.getpixel((x*2+1, y))
                        pixTotal = (pix1 << 8) + pix0
                        outputFile.write(struct.pack('<H', pixTotal))
            elif mat.colorMode == 4:
                for y in range(mat.ySize):
                    for x in range(mat.tpXSize):
                        pix0 = mat.textureImg.getpixel((x*4, y))
                        pix1 = mat.textureImg.getpixel((x*4+1, y))
                        pix2 = mat.textureImg.getpixel((x*4+2, y))
                        pix3 = mat.textureImg.getpixel((x*4+3, y))
                        pixTotal = (pix3 << 12) + (pix2 << 8) + (pix1 << 4) + pix0
                        outputFile.write(struct.pack('<H', pixTotal))
            if not mat.packedCLUT: continue
            colorCount = {8: 256, 4: 16}[mat.colorMode]
            outputFile.write(struct.pack('<HHHH', colorCount, 1, mat.xPosCLUT, mat.yPosCLUT))
            for x in range(colorCount):
                pixRGB = mat.textureCLUT.getpixel((x, 0))
                pixR = pixRGB[0] >> 3
                pixG = pixRGB[1] >> 3
                pixB = pixRGB[2] >> 3
                pixTotal = (pixB << 10) + (pixG << 5) + (pixR)
                outputFile.write(struct.pack('<H', pixTotal))
        outputFile.close()
    def exportHeader(self):
        outputName = "level"
        outputPath = "./DummyPath/"
        textureFile = open(f'{outputPath}/data_textures_{outputName}.h', 'w')
        textureFile.write(f"#ifndef texture_{outputName}_h\n#define texture_{outputName}_h\n")
        textureFile.write('#include "types_gfx.h"\n\n')
        # Textures
        for matName in self.convertedMats:
            mat = self.convertedMats[matName]
            if mat.type != 'T': continue
            if not mat.packed: continue
            safeName = ''.join([char for char in matName if char.isalnum()])
            if not safeName[0].isalpha(): safeName = "m" + safeName
            # Texture Data
            textureFile.write(f'unsigned short {safeName}_texture[] = {{\n\t')
            if mat.colorMode == 15:
                for y in range(mat.ySize):
                    for x in range(mat.xSize):
                        pixRGB = mat.textureImg.getpixel((x, y))
                        pixR = pixRGB[0] >> 3
                        pixG = pixRGB[1] >> 3
                        pixB = pixRGB[2] >> 3
                        pixTotal = (pixB << 10) + (pixG << 5) + (pixR)
                        textureFile.write(f'{pixTotal}, ')
            elif mat.colorMode == 8:
                for y in range(mat.ySize):
                    for x in range(mat.tpXSize):
                        pix0 = mat.textureImg.getpixel((x*2, y))
                        pix1 = mat.textureImg.getpixel((x*2+1, y))
                        pixTotal = (pix1 << 8) + pix0
                        textureFile.write(f'{pixTotal}, ')
            elif mat.colorMode == 4:
                for y in range(mat.ySize):
                    for x in range(mat.tpXSize):
                        pix0 = mat.textureImg.getpixel((x*4, y))
                        pix1 = mat.textureImg.getpixel((x*4+1, y))
                        pix2 = mat.textureImg.getpixel((x*4+2, y))
                        pix3 = mat.textureImg.getpixel((x*4+3, y))
                        pixTotal = (pix3 << 12) + (pix2 << 8) + (pix1 << 4) + pix0
                        textureFile.write(f'{pixTotal}, ')
            textureFile.write('\n};\n')
            # CLUT Data
            if not mat.packedCLUT: continue
            textureFile.write(f'unsigned short {safeName}_CLUT[] = {{\n\t')
            colorCount = {8: 256, 4: 16}[mat.colorMode]
            for x in range(colorCount):
                pixRGB = mat.textureCLUT.getpixel((x, 0))
                pixR = pixRGB[0] >> 3
                pixG = pixRGB[1] >> 3
                pixB = pixRGB[2] >> 3
                pixTotal = (pixB << 10) + (pixG << 5) + (pixR)
                textureFile.write(f'{pixTotal}, ')
            textureFile.write('\n};\n')
        # Table Data
        textureFile.write(f'\nstruct Texture DAT_TEXTURES_{outputName}[] = {{\n')
        textureCount = 0
        for matName in self.convertedMats:
            mat = self.convertedMats[matName]
            if mat.type != 'T': continue
            if not mat.packed: continue
            safeName = ''.join([char for char in matName if char.isalnum()])
            if not safeName[0].isalpha(): safeName = "m" + safeName
            textureFile.write('\t{' + f'{mat.tpXSize}, {mat.ySize}, ')
            textureFile.write(f'{mat.xPos}, {mat.yPos}, ')
            textureFile.write(f'{safeName}_texture' + '},\n')
            textureCount += 1
            if not mat.packedCLUT: continue
            colorCount = {8: 256, 4: 16}[mat.colorMode]
            textureFile.write('\t{' + f'{colorCount}, {1}, ')
            textureFile.write(f'{mat.xPosCLUT}, {mat.yPosCLUT}, ')
            textureFile.write(f'{safeName}_CLUT' + '},\n')
            textureCount += 1
        textureFile.write('};\n\n')
        textureFile.write(f'#define TEXTURE_LEN_{outputName} {textureCount}\n')
        textureFile.write('#endif\n')
        textureFile.close()
    def updatePage(self):
        self.redrawList()
        self.VRAMViewer.repaint()

class VRAMWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.ui = parent
        self.viewZoomScale = 1
        self.VRAMQSize = QSize(1024, 512)
        self.setFixedSize(self.VRAMQSize)
    def setZoomScale(self, zoomScale):
        self.viewZoomScale = zoomScale
        self.setFixedSize(self.VRAMQSize * zoomScale)
    def mousePressEvent(self, event: QMouseEvent):
        pos = event.pos()
        xPos = pos.x()/self.viewZoomScale
        yPos = pos.y()/self.viewZoomScale
        print(f"Mouse clicked at: {pos.x()}, {pos.y()} relative to the widget")
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.scale(self.viewZoomScale, self.viewZoomScale)
        # Draw Background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(128, 128, 128))
        painter.drawRect(0, 0, 1024, 512)
        # Draw Framebuffer(s)
        bufWidth = int(self.ui.bufferWidthSelector.currentText())
        bufHeight = int(self.ui.bufferHeightSelector.currentText())
        bufX1 = self.ui.buffer1XPosSelector.value()
        bufY1 = self.ui.buffer1YPosSelector.value()
        painter.setBrush(QColor(200, 100, 0))
        painter.setPen(Qt.NoPen)
        painter.drawRect(bufX1, bufY1, bufWidth, bufHeight)
        painter.setPen(QPen(QColor(0, 100, 200), 3))
        painter.drawText(bufX1+10, bufY1+20, "Frame Buffer 1")
        if (self.ui.doubleBufferCheck.isChecked()):
            bufX2 = self.ui.buffer2XPosSelector.value()
            bufY2 = self.ui.buffer2YPosSelector.value()
            painter.setBrush(QColor(0, 100, 200))
            painter.setPen(Qt.NoPen)
            painter.drawRect(bufX2, bufY2, bufWidth, bufHeight)
            painter.setPen(QPen(QColor(200, 100, 0), 3))
            painter.drawText(bufX2+10, bufY2+20, "Frame Buffer 2")
        # Draw Textures and CLUTs
        for matKey in self.ui.convertedMats:
            mat = self.ui.convertedMats[matKey]
            if not mat.valid: continue
            if mat.packed:
                rgbTexture = mat.textureImg.convert("RGBA")
                qTexture = QImage(rgbTexture.tobytes("raw", "RGBA"), rgbTexture.width, rgbTexture.height, QImage.Format_RGBA8888)
                qTexturePreview = qTexture.scaled(mat.tpXSize, mat.ySize)
                painter.drawImage(mat.xPos, mat.yPos, qTexturePreview)
            if mat.packedCLUT and mat.textureCLUT != None:
                rgbCLUT = mat.textureCLUT.convert("RGBA")
                qCLUTPreview = QImage(rgbCLUT.tobytes("raw", "RGBA"), rgbCLUT.width, rgbCLUT.height, QImage.Format_RGBA8888)
                painter.drawImage(mat.xPosCLUT, mat.yPosCLUT, qCLUTPreview)

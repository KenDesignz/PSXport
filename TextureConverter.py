# Standard imports
import os, math
# Library imports
from PIL import Image
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage
# Custom imports
from BlenderState import BlenderStateManager
from ConvertedMat import ConvertedMat
# Generated imports
from TextureConverterGen import Ui_TextureConverter

class TextureConverterTab(QWidget, Ui_TextureConverter):
    def __init__(self, sharedBlender, sharedConvertedMats):
        # Shared program state
        self.blender = sharedBlender
        self.convertedMats = sharedConvertedMats
        # Tab state
        self.selectedMatID = None
        self.dummyImg = QPixmap('./icons/placeholder.jpg')
        # Setup tab
        super().__init__()
        self.setupUi(self)
        self.redrawPreviews()
        self.conversionToolBox.setEnabled(False)
        self.matList.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.matList.sortItems(2, Qt.AscendingOrder)
        # Setup custom signals
        self.matList.itemSelectionChanged.connect(self.selectMat)
        self.originalZoomSelector.currentIndexChanged.connect(self.redrawPreviews)
        self.convertedZoomSelector.currentIndexChanged.connect(self.redrawPreviews)
        self.convertButton.clicked.connect(self.convertSelected)
        self.unconvertButton.clicked.connect(self.unconvertSelected)
    def redrawPreviews(self):
        originalViewZoom = int(self.originalZoomSelector.currentText().strip('%'))/100
        convertedViewZoom = int(self.convertedZoomSelector.currentText().strip('%'))/100
        # Get texture path if currently selected material has one
        if self.selectedMatID == None:
            texturePath = ""
        else:
            texturePath = self.blender.data.mats[self.selectedMatID].texturePath
            if not os.path.exists(texturePath): texturePath = ""
        # If it has a path draw the original texture
        if texturePath != "":
            originalTextureQPix = QPixmap(texturePath)
            # Draw the converted textures if they exist
            if self.selectedMatID in self.convertedMats and self.convertedMats[self.selectedMatID].type == 'T':
                convertedImg = self.convertedMats[self.selectedMatID].textureImg
                convertedImgData = convertedImg.convert("RGBA").tobytes("raw", "RGBA")
                convertedQImg = QImage(convertedImgData, convertedImg.width, convertedImg.height, QImage.Format_RGBA8888)
                convertedTextureQPix = QPixmap.fromImage(convertedQImg)
            # If converted textures dont exist, draw a placeholder
            else:
                convertedTextureQPix = self.dummyImg
        # If it doesnt have a path draw placeholders
        else:
            originalTextureQPix = self.dummyImg
            convertedTextureQPix = self.dummyImg
        newX = int(originalTextureQPix.width() * originalViewZoom)
        newY = int(originalTextureQPix.height() * originalViewZoom)
        self.originalTexture.setPixmap(originalTextureQPix.scaled(newX, newY, Qt.KeepAspectRatio))
        newX = int(convertedTextureQPix.width() * convertedViewZoom)
        newY = int(convertedTextureQPix.height() * convertedViewZoom)
        self.convertedTexture.setPixmap(convertedTextureQPix.scaled(newX, newY, Qt.KeepAspectRatio))
    def selectMat(self):
        if len(self.matList.selectedItems()) != 0:
            self.selectedMatID = self.matList.selectedItems()[-1].text(2)
            self.conversionToolBox.setEnabled(True)
        else:
            self.selectedMatID = None
            self.conversionToolBox.setEnabled(False)
        self.originalZoomSelector.setCurrentText("100%")
        self.convertedZoomSelector.setCurrentText("100%")
        self.redrawPreviews()
    def convertImg15BPP(self, image):
        # Reduce the image to 5 bits per channel (15-bit color)
        for x in range(image.width):
            for y in range(image.height):
                oldVal = image.getpixel((x,y))
                newVal = ((oldVal[0]>>3)<<3, (oldVal[1]>>3)<<3, (oldVal[2]>>3)<<3)
                image.putpixel((x, y), newVal)
        return image
    def convertPallet15BPP(self, image, colorCount):
        pallet = image.getpalette()
        palletImgPixels = []
        for i in range(0, len(pallet), 3):
            r = (pallet[i] >> 3) << 3
            g = (pallet[i+1] >> 3) << 3
            b = (pallet[i+2] >> 3) << 3
            pallet[i] = r
            pallet[i+1] = g
            pallet[i+2] = b
            palletImgPixels.append((r, g, b))
        image.putpalette(pallet)
        palletImg = Image.new('RGB', (colorCount, 1))
        palletImg.putdata(palletImgPixels)
        return palletImg
    def convertSingle(self, selectedID):
        if not selectedID: return
        baseType = self.typeRadioGroup.checkedButton().text()[0]
        if baseType == "F" or baseType == "G":
            converted = ConvertedMat()
            converted.id = selectedID
            converted.valid = True
            converted.type = baseType
            self.convertedMats[selectedID] = converted
            return
        texturePath = self.blender.data.mats[selectedID].texturePath
        # TODO If no texture but a texture type is specified, show an error message
        if texturePath == '': return
        # TODO Check if path is valid, if not show an error message
        # if not os.path.exists(self.blender.data.mats[self.selectedMatID].texturePath):
        textureImg = Image.open(texturePath).convert("RGB")
        ###################
        # Size Adjustment #
        ###################
        if self.adjustSizeCheck.isChecked():
            xSize = self.adjustWidthSpin.value()
            ySize = self.adjustHeightSpin.value()
            scaleType = {'N': Image.NEAREST, 'B': Image.BILINEAR}[self.scaleRadioGroup.checkedButton().text()[0]]
            textureImg = textureImg.resize((xSize, ySize), scaleType)
        else:
            xSize, ySize = textureImg.size
            # TODO Warning message the image is to big and had to be resized
            if xSize > 256: xSize = 256
            if ySize > 256: ySize = 256
            scaleType = {'N': Image.NEAREST, 'B': Image.BILINEAR}[self.scaleRadioGroup.checkedButton().text()[0]]
            textureImg = textureImg.resize((xSize, ySize), scaleType)
        ####################
        # Color Adjustment #
        ####################
        if self.removeBlackCheck.isChecked():
            textureImgPixels = list(textureImg.getdata())
            textureImgPixels = [((0b1000, 0b1000, 0b1000) if pixel == (0, 0, 0) else pixel) for pixel in textureImgPixels]
            textureImg.putdata(textureImgPixels)
        colorMode = {'1': 15, '4': 4, '8': 8}[self.colorRadioGroup.checkedButton().text()[0]]
        textureCLUT = None
        if colorMode == 15:
            textureImg = self.convertImg15BPP(textureImg)
            tpXSize = xSize
        else:
            colorCount = {4: 16, 8: 256}[colorMode]
            tpWidthScale = {4: 4, 8: 2}[colorMode]
            texturePal = textureImg.quantize(colorCount)
            texturePalImg = self.convertPallet15BPP(texturePal, colorCount)
            if self.generateCLUTCheck.isChecked():
                textureCLUT = texturePalImg
            tpXSize = math.ceil(xSize/tpWidthScale)
            if xSize%tpWidthScale:
                xSize = tpXSize*tpWidthScale
                blackImg = Image.new('RGB', (xSize, ySize), (0, 0, 0))
                blackImg.paste(textureImg, (0, 0))
                textureImg = blackImg
            ditherMode = {True: Image.FLOYDSTEINBERG, False: Image.NONE}[self.ditheringCheck.isChecked()]
            textureImg = textureImg.quantize(colorCount, palette=texturePal, dither=ditherMode)
        ##################################
        # Creating Converted Texture Mat #
        ##################################
        converted = ConvertedMat()
        # General Attributes
        converted.id = selectedID
        converted.valid = True
        converted.type = baseType
        # Texture Attributes
        converted.origTexturePath = texturePath
        converted.textureImg = textureImg
        converted.xSize = xSize
        converted.ySize = ySize
        converted.tiled = self.enableTilingCheck.isChecked()
        converted.tileX = int(self.tileXSelector.currentText())
        converted.tileY = int(self.tileYSelector.currentText())
        converted.forceSemiTrans = self.makeSemiTransCheck.isChecked()
        converted.colorMode = colorMode
        converted.tpXSize = tpXSize
        # CLUT Attributes
        converted.textureCLUT = textureCLUT
        # Save converted mat
        self.convertedMats[selectedID] = converted
    def convertSelected(self):
        # TODO Make this convert selected
        for mat in self.matList.selectedItems():
            self.convertSingle(mat.text(2))
        self.redrawPreviews()
        self.redrawList()
    def unconvertSelected(self):
        for mat in self.matList.selectedItems():
            if mat.text(2) not in self.convertedMats: continue
            del self.convertedMats[mat.text(2)]
        self.redrawPreviews()
        self.redrawList()
    def redrawList(self):
        self.matList.itemSelectionChanged.disconnect()
        self.matList.clear()
        for mat in self.blender.data.matIDs:
            status = '🚫'
            valid = '➖'
            if mat in self.convertedMats:
                status = '✅'
                if self.convertedMats[mat].valid:
                    valid = '✅'
                else:
                    valid = '🚫'
            self.matList.addTopLevelItem(QTreeWidgetItem([valid, status, mat]))
        self.matList.sortItems(self.matList.header().sortIndicatorSection(), self.matList.header().sortIndicatorOrder())
        self.matList.itemSelectionChanged.connect(self.selectMat)
    def updatePage(self):
        self.selectedMatID = None
        self.originalZoomSelector.setCurrentText("100%")
        self.convertedZoomSelector.setCurrentText("100%")
        self.redrawList()
        self.redrawPreviews()

# Standard imports
import math, struct
# Library imports
from PyQt5.QtWidgets import *
# Custom imports
from BlenderState import BlenderStateManager
from ConvertedMat import ConvertedMat
# Generated imports
from ModelExporterGen import Ui_ModelExporter

class ModelExporterTab(QWidget, Ui_ModelExporter):
    def __init__(self, sharedBlender, sharedConvertedMats):
        # Shared program state
        self.blender = sharedBlender
        self.convertedMats = sharedConvertedMats
        # Tab state
        self.selectedScene = None
        self.selectedModel = None
        # Setup tab
        super().__init__()
        self.setupUi(self)
        # Setup signals
        self.sceneList.currentIndexChanged.connect(self.selectScene)
        self.objectList.itemSelectionChanged.connect(self.selectModel)
        self.exportHeaderButton.clicked.connect(self.exportHeader)
    def redrawSceneList(self):
        self.sceneList.clear()
        self.sceneList.addItems(self.blender.data.sceneIDs)
    def selectScene(self):
        self.selectedScene = self.sceneList.currentText()
        self.redrawModelList()
    def redrawModelList(self):
        if self.selectedScene == None or self.selectedScene == '': return
        self.objectList.itemSelectionChanged.disconnect()
        self.objectList.clear()
        for obj in self.blender.data.sceneObjIDs[self.selectedScene]:
            self.objectList.addTopLevelItem(QTreeWidgetItem([obj]))
        self.objectList.itemSelectionChanged.connect(self.selectModel)
    def selectModel(self):
        self.selectedModel = self.objectList.selectedItems()[0].text(0)
    def exportBin(self):
        outputName = "MODS1"
        outputPath = "./DummyPath/"
        outputFile = open(f'{outputPath}/{outputName}.BIN', 'wb')
        verts = self.blender.data.sceneObjs[self.selectedScene][self.selectedModel].verts
        polys = self.blender.data.sceneObjs[self.selectedScene][self.selectedModel].polys
        norms = self.blender.data.sceneObjs[self.selectedScene][self.selectedModel].norms
        mats = self.blender.data.sceneObjs[self.selectedScene][self.selectedModel].mats
        uvs = self.blender.data.sceneObjs[self.selectedScene][self.selectedModel].uvs
        colors = self.blender.data.sceneObjs[self.selectedScene][self.selectedModel].colors
        scale = 32768/100
        for i, poly in enumerate(polys):
            matName = mats[i]
            if matName not in self.convertedMats: continue
            mat = self.convertedMats[matName]
            if not mat.packed: continue
            if mat.colorMode != 15 and not mat.packedCLUT: continue
        outputFile.close()
    def exportHeader(self):
        outputName = 'cube'
        outputPath = "./DummyPath/"
        verts = self.blender.data.sceneObjs[self.selectedScene][self.selectedModel].verts
        polys = self.blender.data.sceneObjs[self.selectedScene][self.selectedModel].polys
        norms = self.blender.data.sceneObjs[self.selectedScene][self.selectedModel].norms
        mats = self.blender.data.sceneObjs[self.selectedScene][self.selectedModel].mats
        uvs = self.blender.data.sceneObjs[self.selectedScene][self.selectedModel].uvs
        colors = self.blender.data.sceneObjs[self.selectedScene][self.selectedModel].colors
        scale = 32768/100
        modelFile = open(f'{outputPath}/data_model_{outputName}.h', "w")
        modelFile.write(f"#ifndef prims_{outputName}_h\n#define prims_{outputName}_h\n")
        modelFile.write('#include "types_gfx.h"\n\n')
        modelFile.write(f'struct TriVertPack DAT_VERTNORMS_{outputName}[] = {{\n')
        for i, poly in enumerate(polys):
            # Hack to prevent unconverted/packed mats from crashing everything, just skip them
            matName = mats[i]
            if matName not in self.convertedMats: continue
            mat = self.convertedMats[matName]
            if not mat.packed: continue
            if mat.colorMode != 15 and not mat.packedCLUT: continue
            modelFile.write(f"\t/* Tri {i} */ {{")
            for vertIndex in poly:
                vertX = int(verts[vertIndex][0]*scale)
                vertY = int(verts[vertIndex][1]*scale)
                modelFile.write(f"{vertX}, {vertY}, ")
            for vertIndex in poly:
                vertZ = int(verts[vertIndex][2]*scale)
                modelFile.write(f"{vertZ}, ")
            modelFile.write(f"0, ")
            for norm in norms[i]:
                normX = int(norm[0]*4096)
                normY = int(norm[1]*4096)
                normZ = int(norm[2]*4096)
                # modelFile.write(f"{normX}, {normY}, {normZ}, 0, ")
            modelFile.write("},\n")
        modelFile.write("};\n\n")
        primDataBody = ""
        realPolyCount = 0
        for i, poly in enumerate(polys):
            matName = mats[i]
            # Hack to prevent unconverted/packed mats from crashing everything, just skip them
            if matName not in self.convertedMats: continue
            mat = self.convertedMats[matName]
            if not mat.packed: continue
            if mat.colorMode != 15 and not mat.packedCLUT: continue
            uv = uvs[i]
            # Make tile prim
            if mat.tiled:
                #tilePrimX = 0b11111 - (((mat.tileX-1)&0xFF)>>3)
                #tilePrimY = 0b11111 - (((mat.tileY-1)&0xFF)>>3)
                tilePrimX = {8: 0b11111, 16: 0b11110, 32: 0b11100, 64: 0b11000, 128: 0b10000, 256: 0b00000}[mat.tileX]
                tilePrimY = {8: 0b11111, 16: 0b11110, 32: 0b11100, 64: 0b11000, 128: 0b10000, 256: 0b00000}[mat.tileY]
                tpOffsetX = mat.xPos & 0b111111
                tpOffsetX = tpOffsetX << {15: 0, 8: 1, 4: 2}[mat.colorMode]
                tpOffsetY = mat.yPos & 0xFF
                tilePrimOffsetX = tpOffsetX>>3
                tilePrimOffsetY = tpOffsetY>>3
                tilePrim = (0xE20<<20) + (tilePrimOffsetY<<15) + (tilePrimOffsetX<<10) + (tilePrimY<<5) + (tilePrimX) #3791651740
            else:
                tilePrim = 0
            # Get poly params
            tag = 0x0A000000
            code = 0b110100
            if colors != []:
                rgb0 = [int(channel*255) for channel in colors[i][0]]
                rgb1 = [int(channel*255) for channel in colors[i][1]]
                rgb2 = [int(channel*255) for channel in colors[i][2]]
            else:
                rgb0 = [127, 127, 127]
                rgb1 = [127, 127, 127]
                rgb2 = [127, 127, 127]
            clutID = 0
            if mat.packedCLUT:
                clutX = mat.xPosCLUT >> 4
                clutY = mat.yPosCLUT
                clutID = (clutY << 6) + clutX
            tpX = (mat.xPos & 0b1111000000) >> 6
            tpY = (mat.yPos & 0b100000000) >> 8
            tpC = {15: 0b10, 8: 0b01, 4: 0b00}[mat.colorMode]
            semiTrans = 0b00
            tPageID = (tpC << 7) + (semiTrans << 5) + (tpY << 4) + (tpX)
            # Unfuck UVs
            u0, v0 = uv[0]
            u1, v1 = uv[1]
            u2, v2 = uv[2]
            if math.isnan(u0): u0 = 0
            if math.isnan(u1): u1 = 0
            if math.isnan(u2): u2 = 0
            if math.isnan(v0): v0 = 0
            if math.isnan(v1): v1 = 0
            if math.isnan(v2): v2 = 0
            # First remove negative UVs
            if u0 < 0 or u1 < 0 or u2 < 0:
                minU = min(u0, u1, u2)
                shift = math.ceil(abs(minU))
                u0 += shift
                u1 += shift
                u2 += shift
            if v0 < 0 or v1 < 0 or v2 < 0:
                minV = min(v0, v1, v2)
                shift = math.ceil(abs(minV))
                v0 += shift
                v1 += shift
                v2 += shift
            # Next, remove UVs that are offset outside the 0, 1 range
            if u0 >= 1 and u1 >= 1 and u2 >= 1:
                minU = min(u0, u1, u2)
                shift = math.floor(abs(minU))
                u0 -= shift
                u1 -= shift
                u2 -= shift
            if v0 >= 1 and v1 >= 1 and v2 >= 1:
                minV = min(v0, v1, v2)
                shift = math.floor(abs(minV))
                v0 -= shift
                v1 -= shift
                v2 -= shift
            uvScaleX = mat.xSize-1
            uvScaleY = mat.ySize-1
            if mat.tiled:
                uv0 = [int(u0*uvScaleX)&0xFF,  int(255-(v0*uvScaleY))&0xFF]
                uv1 = [int(u1*uvScaleX)&0xFF,  int(255-(v1*uvScaleY))&0xFF]
                uv2 = [int(u2*uvScaleX)&0xFF,  int(255-(v2*uvScaleY))&0xFF]
            else:
                tpOffsetX = mat.xPos & 0b111111
                tpOffsetX = tpOffsetX << {15: 0, 8: 1, 4: 2}[mat.colorMode]
                tpOffsetY = mat.yPos & 0xFF
                uv0 = [int(u0*uvScaleX) + tpOffsetX &0xFF,  int(uvScaleY-(v0*uvScaleY)) + tpOffsetY &0xFF]
                uv1 = [int(u1*uvScaleX) + tpOffsetX &0xFF,  int(uvScaleY-(v1*uvScaleY)) + tpOffsetY &0xFF]
                uv2 = [int(u2*uvScaleX) + tpOffsetX &0xFF,  int(uvScaleY-(v2*uvScaleY)) + tpOffsetY &0xFF]
            primDataBody += f"    /* Prim {i} */ {{"
            primDataBody += f"(u32*){tag}, {tilePrim}, "
            primDataBody += f"{rgb0[0]}, {rgb0[1]}, {rgb0[2]}, "
            primDataBody += f"{code}, {0}, {0}, "
            primDataBody += f"{uv0[0]}, {uv0[1]}, {clutID}, "
            primDataBody += f"{rgb1[0]}, {rgb1[1]}, {rgb1[2]}, "
            primDataBody += f"{0}, {0}, {0}, "
            primDataBody += f"{uv1[0]}, {uv1[1]}, {tPageID}, "
            primDataBody += f"{rgb2[0]}, {rgb2[1]}, {rgb2[2]}, "
            primDataBody += f"{0}, {0}, {0}, "
            primDataBody += f"{uv2[0]}, {uv2[1]}, {0}"
            primDataBody += f"}}, \n"
            realPolyCount += 1
        modelFile.write(f"struct PolyGT3Tiled DAT_PRIMS_{outputName}_0[] = {{\n")
        modelFile.write(primDataBody)
        modelFile.write(f"}};\n")
        modelFile.write(f"struct PolyGT3Tiled DAT_PRIMS_{outputName}_1[] = {{\n")
        modelFile.write(primDataBody)
        modelFile.write(f"}};\n")
        modelFile.write(f'\n#define PRIMS_LEN_{outputName} {realPolyCount}\n')
        modelFile.write(f'#endif')
        modelFile.close()
    def updatePage(self):
        self.redrawSceneList()
        self.redrawModelList()

class ConvertedMat:
    def __init__(self):
        # General Attributes
        self.id = ""                    # Blender Mat Name
        self.valid = False              # Flag if material is still in sync with Blender
        self.type = None                # Flag to set the prim type (flat, gourad or textured)
        # Texture Map Attributes
        self.origTexturePath = ""       # File path to original texture image
        self.textureImg = None          # Pillow image object of the converted texture
        self.xSize = None               # Width of converted texture
        self.ySize = None               # Height of converted texture
        self.tiled = False              # Flag to allow tiling during export
        self.tileX = None               # Tiling width (MUST BE POWER OF 2!!!)
        self.tileY = None               # Tiling height (MUST BE POWER OF 2!!!)
        self.forceSemiTrans = False     # Flag to force semitrans during export
        self.colorMode = None           # Texture pixel color format (options are 15, 8, 4)
        self.tpXSize = None             # Width of converted texture in VRAM
        self.packed = False             # Flag if texture has been packed into VRAM
        self.xPos = 640                 # X position of texture in VRAM
        self.yPos = 0                   # Y position of texture in VRAM
        # CLUT Attributes
        self.textureCLUT = None         # Pillow image object of the CLUT
        self.packedCLUT = False         # Flag if the CLUT has been packed into VRAM
        self.xPosCLUT = 0               # X position of the CLUT in VRAM
        self.yPosCLUT = 0               # Y position of the CLUT in VRAM
        # Normal Map Attributes
        self.origNormalPath = ""        # File path to original normal map image
        self.normalImg = None           # Pillow image object of the converted normal map
        self.tpXSizeNorm = None         # Width of converted normal map in VRAM
        self.packedNorm = False         # Flag if normal map has been packed into VRAM
        self.xPosNorm = 0               # X position of normal map in VRAM
        self.yPosNorm = 0               # X position of normal map in VRAM

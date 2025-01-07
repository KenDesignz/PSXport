import os, pickle
from multiprocessing import shared_memory
from Connection import Connection

class Object:
    def __init__(self, pos = (0, 0, 0), rot = (0, 0, 0), verts = [], polys = [], mats = [], norms = [], colors = [], uvs = [], tans = []):
        # Per obj attributes
        self.pos = pos
        self.rot = rot
        self.verts = verts
        self.polys = polys
        # Per poly attributes
        self.mats = mats
        # Per vert attributes
        self.norms = norms
        self.colors = colors
        self.uvs = uvs
        self.tans = tans
class Material:
    def __init__(self, texturePath = '', normalPath = ''):
        self.texturePath = texturePath
        self.normalPath = normalPath
class BlenderState:
    def __init__(self):
        self.sceneIDs = []
        self.sceneObjIDs = {}
        self.sceneObjs = {}
        self.matIDs = []
        self.mats = {}
    def clear(self):
        self.sceneIDs.clear()
        self.sceneObjIDs.clear()
        self.sceneObjs.clear()
        self.matIDs.clear()
        self.mats.clear()
class BlenderStateManager:
    def __init__(self, stateToManage):
        inPipePath = "/tmp/B2P"
        outPipePath = "/tmp/P2B"
        self.connection = Connection(inPipePath, outPipePath)
        self.data = stateToManage
    def connect(self):
        print("Attemping connection...")
        self.connection.init()
        print("Connected!")
    def disconnect(self):
        if not self.connection.connected:
            print("You must first connect to blender!")
            return
        print("Closing connection...")
        self.request('quit')
        self.connection.deinit()
        print("Closed!")
    def request(self, command, args = [], isPickled = False):
        sendMsg = (command + ':' + ':'.join(args)).encode()
        self.connection.blockingSend(sendMsg)
        response = self.connection.blockingRecive()
        responseStatus = response.split(b':', 1)[0]
        responseData = response.split(b':', 1)[1]
        if responseStatus == b'True' and isPickled:
            return pickle.loads(responseData), True
        elif responseStatus == b'True' and not isPickled:
            return responseData, True
        else:
            return responseData, False
    def sync(self):
        response, status = self.request('sync_state', [], False)
        if status:
            print("State has been generated and pickled!")
        else:
            print("Failed to generated and pickle state!")
            print(response)
            return
        pickleLen = int(response.decode())
        sharedMemoryManager = shared_memory.SharedMemory(name='BlenderPSXPlusStudio')
        pickled = bytes(sharedMemoryManager.buf[:pickleLen])
        self.data = pickle.loads(pickled)
        sharedMemoryManager.close()
        response, status = self.request('sync_close', [], False)

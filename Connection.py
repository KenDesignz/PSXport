import os, time

# TODO add timeouts

class Connection:
    def __init__(self, inPath, outPath, autoInit = False):
        self.inPipePath = inPath
        self.outPipePath = outPath
        self.connected = False
        if autoInit: self.init()
    def init(self):
        self.initRecive()
        self.initSend()
        self.connected = True
    def initRecive(self):
        self.inPipeFD = os.open(self.inPipePath, os.O_RDONLY | os.O_NONBLOCK)
    def initSend(self):
        while 1:
            try:
                print("Attemping connection...")
                self.outPipeFD = os.open(self.outPipePath, os.O_WRONLY)
            except:
                time.sleep(1)
            else:
                print("Connected!")
                break
    def deinit(self):
        try: os.close(self.inPipeFD)
        except: pass
        try: os.close(self.outPipeFD)
        except: pass
        self.connected = False
    def blockingSend(self, data):
        os.write(self.outPipeFD, data)
    def pollingRecive(self):
        msg = bytearray()
        while 1:
            try:
                readBuffer = os.read(self.inPipeFD, 1024)
                if readBuffer == b'': break
                msg.extend(readBuffer)
            except BlockingIOError: break
        return bytes(msg)
    def blockingRecive(self):
        msg = bytearray()
        retryCount = 0
        while 1:
            try:
                readBuffer = os.read(self.inPipeFD, 1024)
                if readBuffer == b'': break
                msg.extend(readBuffer)
                retryCount = 0
            except BlockingIOError:
                if msg == b'': continue
                retryCount += 1
                if retryCount >= 20000:
                    print(retryCount)
                    break
        return bytes(msg)

#动捕 DLL 调用测试（验证 CMVrpn.dll 能取到刚体位姿）
import os
import sys
import time
from ctypes import *
# Load dynamic Library
def LoadDll(dllPath):
    if(os.path.exists(dllPath)):
        return CDLL(dllPath)
    else:
        print("Chingmu's dynamic Library  does not exist \n")
        sys.exit()
# get body(id:0) component 0:x,1:y,2:z,3:rx,4:ry,5:rz,6:rw with time predict
# warning : When using this function, the 'frameCount' must increase with the number of calls
def CMTrackerExtern(host,bodyID,frameCount):
    bodyPos = (c_double * 3)()
    bodyRot = (c_double * 4)()
    trackerExtern = cmVrpn.CMTrackerExtern
    trackerExtern.restype = c_double
    bodyPos[0] = cmVrpn.CMTrackerExtern(host, bodyID, 0, frameCount)
    bodyPos[1] = cmVrpn.CMTrackerExtern(host, bodyID, 1, frameCount)
    bodyPos[2] = cmVrpn.CMTrackerExtern(host, bodyID, 2, frameCount)
    bodyRot[0] = cmVrpn.CMTrackerExtern(host, bodyID, 3, frameCount)
    bodyRot[1] = cmVrpn.CMTrackerExtern(host, bodyID, 4, frameCount)
    bodyRot[2] = cmVrpn.CMTrackerExtern(host, bodyID, 5, frameCount)
    bodyRot[3] = cmVrpn.CMTrackerExtern(host, bodyID, 6, frameCount)
    # check body detected, must call after CMTrackerExtern
    isBodyDetected = cmVrpn.CMTrackerExternIsDetected(host, bodyID, frameCount)
    if (isBodyDetected):
        print("pos: X:%f Y:%f Z:%f"%(bodyPos[0], bodyPos[1], bodyPos[2]))
        print("quaternion: rx:%f ry:%f rz:%f rw:%f"%(bodyRot[0], bodyRot[1], bodyRot[2], bodyRot[3]))
    else:
        print("Rigid body %d not detected"%(bodyID))
    return isBodyDetected
if __name__ == '__main__':
    # Set dynamic Library path
    dllPath = "ChingmuDLL\\CMVrpn.dll"
    # Load dynamic Library
    cmVrpn = LoadDll(dllPath)
    # set server address
    host = bytes("MCServer@192.168.0.100", "gbk")
    # start vrpn thread
    cmVrpn.CMVrpnStartExtern()
    # enable write trace_log.txt
    cmVrpn.CMVrpnEnableLog(True)
    # Person ID displayed on the server
    bodyID = 0
    frameCount = 0
    getfailed = 0
    loopState = True
    while(loopState):
        if(frameCount > 1000):
            loopState = False
        # Control acquisition frequency.parameters can be customized.
        time.sleep(0.2)
        
        isDataDetected = CMTrackerExtern(host, bodyID, frameCount)
        if(isDataDetected):
            getfailed = 0
        else:
            getfailed += 1
        if(getfailed > 10):
            print("Continuous acquisition failed, exit the program.")
            loopState = False
        frameCount += 1
    # quit vrpn thread
    cmVrpn.CMVrpnQuitExtern()

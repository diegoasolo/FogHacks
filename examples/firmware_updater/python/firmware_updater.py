import ajiledriver as aj
import sys
import os
import struct

# Python 2.x - 3.x workaround
try:
    input = raw_input
except NameError:
    pass

def printUsage():
    print ("Usage: " + sys.argv[0] + " <firmwareFile.ajb> [-i <IP address>] [--usb3] [-d <deviceNumber>]")

def updateDeviceSoftware(system, filename):      
    if not os.path.isfile(filename):
        print("Software Update Error: The selected device software file does not exist. Please select a valid device software image file for upgrade.")
        sys.exit(-1)

    # read the file header and make sure that it is valid
    newFile = open(filename, "rb")
    newFileData = newFile.read(8)
    (headerChar0, headerChar1, programDeviceType, programType, programSize) = struct.unpack('!BBBBL', newFileData)
    newFile.close()

    foundComponent = -1
    errorString = ""
    if headerChar0 != ord('A') or headerChar1 != ord('J'):
        errorString = "Invalid program file header detected. Please select a valid device software image file for upgrade."
    else:
        for componentIndex, component in enumerate(system.GetProject().Components()):
            if component.DeviceType().HardwareType() == programDeviceType:
                foundComponent = componentIndex
                reply = input("Valid device found at index " + str(componentIndex) + " with device type " + str(programDeviceType) + ".\n" + \
                              "This will erase the device software (including the device firmware and FPGA software)\n" + \
                              "and replace it with the selected device software image. Are you sure you want to do this? (y/n): ")
                if reply == "y" or reply == "Y":
                    print ("Programming device firmware, this will take some time. Do not power off the device while this is in progress.")
                    err = system.GetDriver().ProgramDeviceFromFile(filename, componentIndex, False, 0)
                    if err != aj.ERROR_NONE:
                        errorString = "Error while attempting to program device. Error type is " + str(err) + "."
                        break  
                    lastProgress = 0
                    currProgress = 0
                    while currProgress < 100:
                        currProgress = system.GetDriver().GetProgrammingProgress()
                        if currProgress != lastProgress:
                            print ("Progress: %d" % (currProgress))
                            lastProgress = currProgress
                else:
                    errorString = "Device software update cancelled."

        if foundComponent < 0:
            errorString = "No component was found in the system which matches the file device type, " + str(programDeviceType) + "."

    if errorString != "":
        print("Software Update Error: " + errorString)
        return False
    else:
        print("Device software update complete.\nPlease power the device off then on to load the new software.\n" + \
              "When complete, restart the GUI and reconnect to the device.")
        return True

    
if __name__ == "__main__":
    # default connection settings
    ipAddress = "192.168.200.1"
    netmask = "255.255.255.0"
    gateway = "0.0.0.0"
    port = 5005
    commInterface = aj.USB2_INTERFACE_TYPE
    deviceNumber = 0

    if len(sys.argv) < 2:
        printUsage()
        sys.exit(-1)

    firmwareFilename = sys.argv[1]
        
    # read command line arguments
    i=2
    while i < len(sys.argv):
        if sys.argv[i] == "-i":
            ipAddress = sys.argv[i+1]
            i += 1
        elif sys.argv[i] == "--usb3":
            commInterface = aj.USB3_INTERFACE_TYPE
        else:
            printUsage()
            sys.exit(2)
        i += 1    
        
    # connect to the device
    ajileSystem = aj.HostSystem()    
    ajileSystem.SetConnectionSettingsStr(ipAddress, netmask, gateway, port)
    ajileSystem.SetCommunicationInterface(commInterface)
    if ajileSystem.StartSystem() != aj.ERROR_NONE:
        print ("Error starting AjileSystem.")
        sys.exit(-1)

    updateDeviceSoftware(ajileSystem, firmwareFilename)

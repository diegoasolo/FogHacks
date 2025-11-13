#ifndef _EXAMPLE_HELPER_H_
#define _EXAMPLE_HELPER_H_

#include <ajile/AJObjects.h>
#include <ajile/HostSystem.h>

#include <vector>

int RunExample(aj::Project (*createFunction)(unsigned short, unsigned int, float, std::vector<aj::Component>), int argc, char *argv[]);

int RunCameraExample(aj::Project (*createFunction)(unsigned short, unsigned int, float,
                                                   unsigned int, unsigned int, unsigned int, unsigned int,
                                                   std::vector<aj::Component>),
                     int argc, char *argv[]);

int RunCameraDmdExample(aj::Project (*createFunction)(unsigned short, unsigned int, float,
                                                   unsigned int, unsigned int, unsigned int, unsigned int,
                                                   std::vector<aj::Component>),
                     int argc, char *argv[]);

class Parameters {
  public:
    Parameters();
    
    // default connection settings
    char ipAddress[32];
    char netmask[32];
    char gateway[32];
    unsigned short port;
    CommunicationInterfaceType_e commInterface;
    int deviceNumber;

    // default sequence settings
    unsigned int repeatCount;
    float frameTime_ms;
    unsigned short sequenceID;

    // camera settings
    unsigned int bitDepth;
    unsigned int roiFirstRow;
    unsigned int roiNumRows;
    unsigned int subsampleRowSkip;
};

void PrintUsage(int argc, char *argv[]);
void ParseCommandArguments(Parameters& parameters, int argc, char *argv[]);
void ConnectToDevice(aj::HostSystem& ajileSystem, Parameters& parameters);

#endif

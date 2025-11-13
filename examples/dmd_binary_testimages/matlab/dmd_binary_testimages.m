function dmd_binary_testimages(repeatCount, frameTime_ms, usbType)

    RunExample(repeatCount, frameTime_ms, usbType)
  
end

function [project] = CreateProject(sequenceID, sequenceRepeatCount, frameTime_ms, components)

    projectName = 'dmd_binary_testimages_example';
    filenameBase = '../../images/cat_';
    if frameTime_ms < 0
        frameTime_ms = 100;
    end
    numImages = 14;
    
    % create a new project
    project = py.ajiledriver.Project(projectName);
    project.SetComponents(components)
    
    % create the images
    for i = 1 : numImages
        filename = strcat(filenameBase, num2str(i), '.png');
        testImage = py.ajiledriver.Image(uint16(i));
        testImage.ReadFromFile(filename, py.ajiledriver.DMD_4500_DEVICE_TYPE);
        project.AddImage(testImage);
    end
    
    % create the sequence
    project.AddSequence(py.ajiledriver.Sequence(uint16(sequenceID), projectName, py.ajiledriver.DMD_4500_DEVICE_TYPE, py.ajiledriver.SEQ_TYPE_PRELOAD, uint16(sequenceRepeatCount)));

    % create a single sequence item, which all the frames will be added to
    project.AddSequenceItem(py.ajiledriver.SequenceItem(uint16(sequenceID), uint32(1)));

    for i = 1 : numImages
        frame = py.ajiledriver.Frame();
        frame.SetSequenceID(uint16(sequenceID));
        frame.SetImageID(uint16(i));
        frame.SetFrameTimeMSec(frameTime_ms);
        project.AddFrame(frame);
    end

end

function RunExample(repeatCount, frameTime_ms, usbType)

    % default connection settings
    ipAddress = '192.168.200.1';
    netmask = '255.255.255.0';
    gateway = '0.0.0.0';
    port = uint16(5005);
    if usbType == 2
        commInterface = py.ajiledriver.USB2_INTERFACE_TYPE;
    else
        commInterface = py.ajiledriver.USB3_INTERFACE_TYPE;
    end

    sequenceID = uint16(1);

    % connect to the device
    ajileSystem = py.ajiledriver.HostSystem();
    ajileSystem.SetConnectionSettingsStr(ipAddress, netmask, gateway, port);
    ajileSystem.SetCommunicationInterface(commInterface);
    if ajileSystem.StartSystem() ~= py.ajiledriver.ERROR_NONE
        'Error starting AjileSystem.'
        return;
    end
        
    % create the project
    project = CreateProject(sequenceID, repeatCount, frameTime_ms, ajileSystem.GetProject().Components());

    % get the first valid component index which will run the sequence
    result = cell(project.FindSequence(sequenceID));
    sequence = result{1};
    wasFound = result{2};
    if false(wasFound)
        'Sequence not found.'
        return;
    end
    componentIndex = ajileSystem.GetProject().GetComponentIndexWithDeviceType(sequence.HardwareType());

    % stop any existing project from running on the device
    ajileSystem.GetDriver().StopSequence(componentIndex);

    % load the project to the device
    ajileSystem.GetDriver().LoadProject(project);
    ajileSystem.GetDriver().WaitForLoadComplete(int32(-1));
            
    % run the project
    if frameTime_ms > 0
        sprintf('Starting sequence %d with frame rate %f and repeat count %d', sequence.ID(), frameTime_ms, repeatCount)
    end

    ajileSystem.GetDriver().StartSequence(sequence.ID(), componentIndex);

    % wait for the sequence to start
    sprintf('Waiting for sequence %d to start', sequence.ID())
    while ajileSystem.GetDeviceState(uint8(componentIndex)).RunState() ~= py.ajiledriver.RUN_STATE_RUNNING
        continue;
    end

    if repeatCount == 0
        'Sequence repeating forever. Press a key or click to stop the sequence'
        waitforbuttonpress;
        ajileSystem.GetDriver().StopSequence(uint8(componentIndex));
    end

    'Waiting for the sequence to stop.'
    while ajileSystem.GetDeviceState(uint8(componentIndex)).RunState() == py.ajiledriver.RUN_STATE_RUNNING
        continue;
    end

end

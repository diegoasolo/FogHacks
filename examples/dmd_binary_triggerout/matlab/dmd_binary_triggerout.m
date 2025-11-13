function dmd_binary_triggerout(repeatCount, frameTime_ms, usbType)

    RunExample(repeatCount, frameTime_ms, usbType)
  
end

% helper function which creates a checkerboard pattern and its inverse
function [boardImages] = GenerateCheckerboards(width, height)

    % width and height of each checkerboard square
    squareWidth = 100;

    % use Matlab checkerboard function to create a checkerboard pattern and its inverse, sized to the passed in width and height
    boardImage0 = checkerboard(squareWidth, uint16(height/squareWidth/2)+1, uint16(width/squareWidth)+1);
    boardImage0 = imresize(boardImage0, [height, width]);
    boardImage0 = boardImage0 * 255;
    boardImage1 = ~boardImage0;
    
    boardImages{1} = boardImage0;
    boardImages{2} = boardImage1;

end
        
function [project] = CreateProject(sequenceID, sequenceRepeatCount, frameTime_ms, components)

    projectName = 'dmd_binary_triggerout_example';
    if frameTime_ms < 0
        frameTime_ms = 100;
    end
    
    % create a new project
    project = py.ajiledriver.Project(projectName);
    project.SetComponents(components);

    % get the component indices
    componentIterator = project.Components().begin();
    for index = 1 : int64(size(project.Components()))
        deviceType = componentIterator.value().DeviceType().HardwareType();        
        if deviceType == py.ajiledriver.AJILE_CONTROLLER_DEVICE_TYPE || deviceType == py.ajiledriver.AJILE_2PORT_CONTROLLER_DEVICE_TYPE || deviceType == py.ajiledriver.AJILE_3PORT_CONTROLLER_DEVICE_TYPE
            controllerIndex = index;
            controllerComponent = componentIterator.value();
        end
        componentIterator.incr();
    end
    controllerIndex = project.GetComponentIndexWithDeviceType(py.ajiledriver.AJILE_CONTROLLER_DEVICE_TYPE);
    dmdIndex = project.GetComponentIndexWithDeviceType(py.ajiledriver.DMD_4500_DEVICE_TYPE);
    
    % configure the external output triggers of the Ajile controller component to be rising edge, with a hold time of half the frame time
    % (Note that the default trigger hold time is defined by TRIGGER_DEFAULT_HOLD_TIME. 
    %  This step can be skipped if the default hold time and rising edge is sufficient.)
    outputTriggerSettings = controllerComponent.OutputTriggerSettings();
    outputTriggerSettingsIterator = outputTriggerSettings.begin();
    for i = 1 : int64(size(outputTriggerSettings))
        project.SetOutputTriggerSetting(controllerIndex, i-1, py.ajiledriver.ExternalTriggerSetting(py.ajiledriver.RISING_EDGE, py.ajiledriver.FromMSec(frameTime_ms/2)));
    end

    % create a trigger rule to connect the DMD frame started to the external output trigger 0
    dmdFrameStartedToExtTrigOut = py.ajiledriver.TriggerRule();
    dmdFrameStartedToExtTrigOut.AddTriggerFromDevice(py.ajiledriver.TriggerRulePair(dmdIndex, py.ajiledriver.FRAME_STARTED));
    dmdFrameStartedToExtTrigOut.SetTriggerToDevice(py.ajiledriver.TriggerRulePair(controllerIndex, py.ajiledriver.EXT_TRIGGER_OUTPUT_1));
    % add the trigger rule to the project
    project.AddTriggerRule(dmdFrameStartedToExtTrigOut);
    
    % generate a list of gray code images (which are numpy arrays)
    boardImages = GenerateCheckerboards(py.ajiledriver.DMD_IMAGE_WIDTH_MAX, py.ajiledriver.DMD_IMAGE_HEIGHT_MAX);
    
    % create the images from the numpy gray code images and add them to our project
    imageCount = 1;
    [x, numImages] = size(boardImages);
    for i = 1 : numImages
        tempImageFilename = 'boardImage.png';
        imwrite(boardImages{i}, tempImageFilename);
        image = py.ajiledriver.Image(uint16(imageCount));
        image.ReadFromFile(tempImageFilename, py.ajiledriver.DMD_4500_DEVICE_TYPE);
        imageCount = imageCount + 1;
        project.AddImage(image);
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

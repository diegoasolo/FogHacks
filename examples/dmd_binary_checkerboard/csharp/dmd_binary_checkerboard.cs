using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;


namespace dmd_binary_checkerboard_namespace
{
    class dmd_binary_checkerboard
    {

        static List<ucharArray> GenerateCheckerboards(int width, int height)
        {

            // width and height of each checkerboard square
            int squareWidth = 50;
            int squareHeight = 100;
            
            // Allocate checkerboard pattern images
            List<ucharArray> boardImages = new List<ucharArray>();
            for (int i=0; i<2; i++)
                boardImages.Add(new ucharArray((uint)(width * height)));
            
            // draw the checkerboard pattern
            byte value = 0;
            byte firstValue = 0;
            for (int r=0; r<height; r++) {
                if (r % squareHeight == 0) firstValue = (byte)(firstValue == 0 ? 255 : 0);
                value = firstValue;
                for (int c=0; c<width; c++) {
                    if (c % squareWidth == 0) value = (byte)(value == 0 ? 255 : 0);
                    boardImages[0].setitem((uint)(r*width+c), value);
                    boardImages[1].setitem((uint)(r *width+c), (byte)(255 - value));                    
                }                
            }

            return boardImages;
            
        }
        
        static Project CreateProject(ushort sequenceID = 1, uint sequenceRepeatCount = 0, float frameTime_ms = -1, ComponentList components = null)
        {

            string projectName = "dmd_binary_testimages_example";
            if (frameTime_ms < 0)
                frameTime_ms = 100;

            // create a new project
            Project project = new Project(projectName);
            if (components != null && components.Count > 0)
                project.SetComponents(components);

            List<ucharArray> boardImages = GenerateCheckerboards(ajiledriver.DMD_IMAGE_WIDTH_MAX, ajiledriver.DMD_IMAGE_HEIGHT_MAX);

            ushort imageCount = 1;
            for (int i=0; i<boardImages.Count(); i++) {
                Image image = new Image(imageCount);
                imageCount += 1;
                image.ReadFromMemory(boardImages[i].cast(), ajiledriver.DMD_IMAGE_HEIGHT_MAX, ajiledriver.DMD_IMAGE_WIDTH_MAX, 1, 8, ImageMajorOrder_e.ROW_MAJOR_ORDER, DeviceType_e.DMD_4500_DEVICE_TYPE);
                project.AddImage(image);
            }

            int numImages = boardImages.Count();

            // create the sequence
            project.AddSequence(new Sequence(sequenceID, projectName, DeviceType_e.DMD_4500_DEVICE_TYPE, SequenceType_e.SEQ_TYPE_PRELOAD, sequenceRepeatCount));

            // create a single sequence item, which all the frames will be added to
            project.AddSequenceItem(new SequenceItem(sequenceID, 1));

            // create the frames and add them to the project, which adds them to the last sequence item
            for (int i=0; i<numImages; i++) {
                Frame frame = new Frame();
                frame.SetSequenceID(sequenceID);
                frame.SetImageID((ushort)(i+1));
                frame.SetFrameTimeMSec(frameTime_ms);
                project.AddFrame(frame);
            }
            
            return project;
        }

        static int RunExample(string[] args)
        {

            // default connection settings
            string ipAddress = "192.168.200.1";
            string netmask = "255.255.255.0";
            string gateway = "0.0.0.0";
            ushort port = 5005;
            CommunicationInterfaceType_e commInterface = CommunicationInterfaceType_e.USB2_INTERFACE_TYPE;

            // default sequence settings
            uint repeatCount = 0; // repeat forever
            float frameTime_ms = -1.0f; // frame time in milliseconds
            ushort sequenceID = 1;

            // read command line arguments
            for (int i = 1; i < args.Length; i++)
            {
                if (args[i] == "-i")
                {
                    ipAddress = args[++i];
                }
                else if (args[i] == "-r")
                {
                    repeatCount = ushort.Parse(args[++i]);
                }
                else if (args[i] == "-f")
                {
                    frameTime_ms = float.Parse(args[++i]);
                }
                else if (args[i] == "--usb3")
                {
                    commInterface = CommunicationInterfaceType_e.USB3_INTERFACE_TYPE;
                }
                else
                {
                    Console.WriteLine("Usage: " + args[0] + " [-i <IP address>] [-r <repeat count>] [-f <frame rate in ms>] [--usb3]\n");
                    return -1;
                }
            }

            // connect to the device
            HostSystem ajileSystem = new HostSystem();
            ajileSystem.SetConnectionSettingsStr(ipAddress, netmask, gateway, port);
            ajileSystem.SetCommunicationInterface(commInterface);
            if (ajileSystem.StartSystem() != ErrorType_e.ERROR_NONE)
            {
                Console.WriteLine("Error starting AjileSystem.");
                return -1;
            }

            // create the project
            //Project project = CreateProject(sequenceID, repeatCount, frameTime_ms, ajileSystem.GetProject().Components());
            Project project = CreateProject(sequenceID, repeatCount, frameTime_ms, ajileSystem.GetProject().Components());

            // get the first valid component index which will run the sequence
            bool wasFound = false;
            Sequence sequence = project.FindSequence(sequenceID, out wasFound);
            if (!wasFound) return -1;
            int componentIndex = ajileSystem.GetProject().GetComponentIndexWithDeviceType(sequence.HardwareType());

            // stop any existing project from running on the device
            ajileSystem.GetDriver().StopSequence(componentIndex);

            // load the project to the device
            ajileSystem.GetDriver().LoadProject(project);
            ajileSystem.GetDriver().WaitForLoadComplete(-1);

            // run the project
            if (frameTime_ms >= 0)
                Console.WriteLine("Starting sequence " + sequence.ID().ToString() + " with frame rate " + frameTime_ms.ToString() + " and repeat count " + repeatCount.ToString());

            ajileSystem.GetDriver().StartSequence(sequenceID, componentIndex);

            // wait for the sequence to start
            Console.WriteLine("Waiting for sequence " + sequence.ID().ToString() + " to start");
            while (ajileSystem.GetDeviceState((byte)componentIndex).RunState() != RunState_e.RUN_STATE_RUNNING) ;

            if (repeatCount == 0)
            {
                Console.WriteLine("Sequence repeating forever. Press a key to stop the sequence");
                Console.ReadKey();
                ajileSystem.GetDriver().StopSequence(componentIndex);
            }

            Console.WriteLine("Waiting for the sequence to stop.");
            while (ajileSystem.GetDeviceState((byte)componentIndex).RunState() == RunState_e.RUN_STATE_RUNNING) ;

            return 0;
        }

        static void Main(string[] args)
        {
            RunExample(args);
        }
    }
}

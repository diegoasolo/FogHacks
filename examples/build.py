import os
import sys
import glob
import subprocess
import shutil
import datetime

C_BIN_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'bin')
BUILD_TYPE = 'Release'
HOME_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
SW_DIRECTORY = os.path.join(HOME_DIRECTORY, "..", "..")
IS_WINDOWS = (os.name == 'nt')

if not IS_WINDOWS:
    NUM_CORES = int(subprocess.check_output(['nproc']).decode(sys.stdout.encoding).strip())
else:
    NUM_CORES = 8

arguments = []


def run_command(command, validate=True):
    # turn string command into a list
    if isinstance(command, str):
        command = command.split(' ')
    
    # add visual studio environment script to the command
    process = subprocess.Popen(command)
    rc = process.wait()
    
    if rc != 0:
        print(f'Command appeared to fail, return code {rc}.')
        commandStr = ' '.join(command)
        print(f'Failed command was: {commandStr}')
        if validate:
            sys.exit(2)
        return False
    return True

def read_arguments():

    global BUILD_TYPE
    global BUILD_CPP_ONLY
    global BUILD_DEVELOPMENT_PYTHON_ONLY
    global arguments

    if "--debug" in sys.argv:
        BUILD_TYPE = "RelWithDebInfo" if IS_WINDOWS else "Debug"
    if "--cpp" in sys.argv:
        BUILD_CPP_ONLY = True
    if "--fast" in sys.argv:
        BUILD_DEVELOPMENT_PYTHON_ONLY = True
    for arg in sys.argv:
        if arg.startswith("-D"):
            arguments.append(arg)
            
def build_cpp():
    os.chdir(C_BIN_DIR)
    exampleDirs = [os.path.dirname(cmake_file) for cmake_file in glob.glob(os.path.join(HOME_DIRECTORY, "**", "cpp", "CMakeLists.txt"), recursive=True)]
    
    for e in exampleDirs:
        print(e)

    for projectDir in exampleDirs:
        project_name = os.path.basename(os.path.dirname(projectDir))  # Get the example project name
        build_dir = os.path.join(C_BIN_DIR, project_name)  # Create a dedicated bin directory for each example

        print(f"\nBuilding C++ project: {project_name} in {build_dir}")

        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        os.makedirs(build_dir, exist_ok=True)

        os.chdir(build_dir)

        # Run CMake to configure the project
        if IS_WINDOWS:
            cmakeCommand = [
                "cmake", projectDir, 
                f"-DCMAKE_BUILD_TYPE={BUILD_TYPE}", 
                f"-DPTHREAD_HOME={os.environ['PTHREAD_HOME']}", 
                f"-DAJILEDRIVER_HOME={os.path.join(SW_DIRECTORY, 'AJController')}"
            ]
        else:
            cmakeCommand = [
                "cmake", projectDir, 
                f"-DCMAKE_BUILD_TYPE={BUILD_TYPE}", 
                f"-DAJILEDRIVER_HOME={os.path.join(SW_DIRECTORY, 'AJController')}"
            ]
        run_command(cmakeCommand)

        # Compile the project
        if IS_WINDOWS:
            sln_files = glob.glob(os.path.join(build_dir, "*.sln"))
            if sln_files:
                sln_file = sln_files[0]
                sln_filename = os.path.basename(sln_file)
                buildCommand = f"msbuild {sln_filename} /t:Clean,Build /p:Configuration={BUILD_TYPE} -maxcpucount:{NUM_CORES}"
                run_command(buildCommand)
        else:
            buildCommand = f'make -j {NUM_CORES}'
            run_command(buildCommand)

        os.chdir(HOME_DIRECTORY)

    print("\nAll C++ example projects have been built successfully.")


def build_csharp():
    if not IS_WINDOWS:
        return True

    os.chdir(C_BIN_DIR)
    exampleDirs = glob.glob(os.path.join(HOME_DIRECTORY, "**", "csharp"), recursive=True)

    for projectDir in exampleDirs:
        print(f"Processing project directory: {projectDir}")

        project_name = os.path.basename(os.path.dirname(projectDir))
        build_dir = os.path.join(C_BIN_DIR, project_name)
        build_dir_csharp = os.path.join(C_BIN_DIR, f"{project_name}_csharp")

        print(f"\nBuilding C# project: {project_name} in {build_dir_csharp}")

        # Remove old build directories if they exist
        for folder in [build_dir_csharp]:
            if os.path.exists(folder):
                shutil.rmtree(folder)
            os.makedirs(folder, exist_ok=True)

        # Copy all files from the original project directory to the new build directory
        def copy_files(src, dest):
            if os.path.exists(src):
                shutil.copytree(src, dest, dirs_exist_ok=True)
                print(f"Copied files from {src} to {dest}")
            else:
                print(f"Warning: Source directory {src} does not exist, skipping copy.")

        # Copy C# project files into the bin directory
        copy_files(projectDir, build_dir_csharp)

        # Compile the project
        sln_files = glob.glob(os.path.join(build_dir_csharp, "*.sln"))
        if sln_files:
            sln_file = sln_files[0]
            run_command([
                "msbuild", 
                f"{sln_file}", 
                "/t:Clean,Build", 
                "/p:Configuration=Release", 
                "/p:Platform=Any CPU",
                f"-maxcpucount:{NUM_CORES}"        
            ])

        os.chdir(HOME_DIRECTORY)

    print("\nAll C# example projects have been built successfully.")

def copyImages():
    source_images_folder = os.path.join(HOME_DIRECTORY, "images")
    destination_images_folder = os.path.join(C_BIN_DIR, "images")

    if os.path.exists(source_images_folder):
        print(f"\nCopying Images folder from {source_images_folder} to {destination_images_folder}...")

        if os.path.exists(destination_images_folder):
            shutil.rmtree(destination_images_folder)  # Remove existing folder to ensure fresh copy

        shutil.copytree(source_images_folder, destination_images_folder, dirs_exist_ok=True)
        print("Images folder copied successfully.")
    else:
        print(f"Warning: Source Images folder '{source_images_folder}' does not exist. Skipping copy.")

##########################################################################
# main
##########################################################################
if __name__ == '__main__':
    if os.path.isdir(C_BIN_DIR):
        shutil.rmtree(C_BIN_DIR)
    os.makedirs(C_BIN_DIR, exist_ok=True)
    read_arguments()
    copyImages()
    build_cpp()
    build_csharp()

#!/bin/bash

home=`pwd`

for exampleDir in dmd_*; do
    cd $home/$exampleDir/cpp
    cmake . -DCMAKE_BUILD_TYPE=Debug -G"Eclipse CDT4 - Unix Makefiles"
    make
done

cd $home

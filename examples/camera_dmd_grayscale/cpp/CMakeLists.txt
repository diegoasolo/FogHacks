CMAKE_MINIMUM_REQUIRED(VERSION 2.8)

PROJECT(camera_dmd_grayscale_example)

find_package( OpenCV REQUIRED )
ADD_DEFINITIONS(-DEXAMPLE_OPENCV_REQUIRED)

IF(WIN32)
  SET(AJILEDRIVER_HOME "C:/Program Files/Ajile/AjileDriver/" CACHE STRING "Location of Ajile Driver include and lib")
  ADD_DEFINITIONS(-DWIN32_LEAN_AND_MEAN)
ELSE(WIN32)
  SET(AJILEDRIVER_HOME "/opt/ajile/AjileDriver/" CACHE STRING "Location of Ajile Driver include and lib")
ENDIF(WIN32)

SET(SOURCE
  camera_dmd_grayscale_example.cpp
  ../../common/cpp/example_helper.cxx
)

INCLUDE_DIRECTORIES(
  ${CMAKE_CURRENT_BINARY_DIR}
  ${CMAKE_CURRENT_SOURCE_DIR}
  ${OpenCV_INCLUDE_DIRS}
  ../../common/cpp/
)

LINK_DIRECTORIES(${LINK_DIRECTORIES} ${AJILEDRIVER_HOME}/lib ${AJILEDRIVER_HOME}/lib_thirdparty)
INCLUDE_DIRECTORIES(
  ${INCLUDE_DIRECTORIES} 
  ${AJILEDRIVER_HOME}/include
  )

ADD_EXECUTABLE(camera_dmd_grayscale_example ${SOURCE})

IF(UNIX)
  TARGET_LINK_LIBRARIES( camera_dmd_grayscale_example
    -lajiledriver
    ${OpenCV_LIBS}
    )
ELSE(UNIX)
  IF(WIN32)
    TARGET_LINK_LIBRARIES( camera_dmd_grayscale_example
      ajiledriver.lib
      ${OpenCV_LIBS}
    )
  ENDIF(WIN32)
ENDIF(UNIX)

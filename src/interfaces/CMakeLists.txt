cmake_minimum_required(VERSION 3.8)
project(interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(action_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}

  "action/MoveX.action"

  "action/MoveYaw.action"
 DEPENDENCIES action_msgs
)

ament_export_dependencies(rosidl_default_runtime)

<<<<<<< HEAD
ament_package()
=======
ament_package()
>>>>>>> 6d37652e64e5392a2ea48398d3cc72d18eabfac0

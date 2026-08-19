#Maze Escape Solution
This is our form of solving the maze as the task was for a turtle to escape a maze using either the normal long way or a shortcut by calling a hidden service that
controls walls

#Solution consists of
##A ros2 package which consists of
  - ### Movement-x Client & Movement-x Server : which are responsible for the movement of the turtle
  - ### Yaw-movement Client & Server : which are responsible for the rotation of the turtle
  - ### Action Client Node : This node houses 3 clients and a method `solve_maze` that initiates them to solve the maze:
              - A Move Action Client that moves the robot one step forward.
              - A Yaw Action Client that rotates the robot 90 degrees.
              - A Wall Service Client that opens walls in the maze



# Requirements to operate the solution:
   - Ubuntu version 24.04
   - install Ros2 jazzy
   - install gazebo & turtlebot3

# Challenges faced during the task :
   - Finding the hidden wall service
   - merging the 3 clients into one node (Action client node)
   - merging all the codes together 
     



























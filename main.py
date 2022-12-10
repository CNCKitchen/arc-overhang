import shapely
from shapely.geometry import Point, Polygon, LineString, GeometryCollection
import geopandas as gpd
import matplotlib.pyplot as plt
import moviepy.editor as mp
import numpy as np
import os
import util
import imageio
import os

# 3D printing parameters
LINE_WIDTH = 0.4  # AKA the increase in radius as arcs grow from a central point.
OVERLAP = 10 # Overlap in %
LAYER_HEIGHT = 0.3  # Thicker seems to be more stable due to physics.
ARC_E_MULTIPLIER = 1.25  # Amount of overextrusion to do while doing the overhangs. This somewhat compensates for the unconstrained filament
FEEDRATE = 2  # Speed while printing the overhangs. In mm/s. Slower helps make it look cleaner.
BASE_FEEDRATE = 20
TOWER_FEEDRATE = 30
FILAMENT_DIAMETER = 1.75 
BRIM_WIDTH = 0  #

print_settings = {
    "layer_height": LAYER_HEIGHT,
    "line_width": LINE_WIDTH,
    "e_multiplier": ARC_E_MULTIPLIER,
    "feedrate": FEEDRATE,
    "filament_diam": FILAMENT_DIAMETER,
    "brim_width": BRIM_WIDTH
}

# Shape generation parameters
OVERHANG_HEIGHT = 20  # How high the test print is above the build plate
BASE_HEIGHT = 0.3 # thickness of circular base

# Hard-coded recursion information
THRESHOLD = LINE_WIDTH / 2  # How much of a 'buffer' the arcs leave around the base polygon. Don't set it negative or bad things happen.
OUTPUT_FILE_NAME = "output/output.gcode"
R_MAX = 30  # maximum radius for a circle
N = 40      # number of points per circle

# Create a figure that we can plot stuff onto
fig, ax = plt.subplots(1, 2)
ax[0].set_aspect('equal')
ax[1].set_aspect('equal')
ax[0].title.set_text('Gcode Preview')
ax[1].title.set_text('Rainbow Visualization')

# Create a list of image names
image_name_list = []

recursion_info = {
    "threshold": THRESHOLD,
    "gcode_file": OUTPUT_FILE_NAME,
    "fig": fig,
    "ax": ax,
    "image_name_list": image_name_list,
    "r_max": R_MAX,
    "n": N
}

# Delete all previous images
current_directory = "./"
files_in_directory = os.listdir(current_directory)
for item in files_in_directory:
    if item.endswith(".png"):
        os.remove(os.path.join(current_directory, item))

# Create a new gcode file
os.makedirs(os.path.dirname(OUTPUT_FILE_NAME), exist_ok=True)
with open(OUTPUT_FILE_NAME, 'w') as gcode_file:
    gcode_file.write(""";gcode for ArcOverhang. Created by Steven McCulloch\n""")

# Add start gcode
with open('input/start.gcode','r') as start_gcode, open(OUTPUT_FILE_NAME,'a') as gcode_file:
    for line in start_gcode:
        gcode_file.write(line)

# Create base polygon. The base polygon is the shape that will be filled by arcs
#base_poly = create_rect(RECT_X, RECT_Y, RECT_LENGTH, RECT_WIDTH, True)

# Make the base polygon a randomly generated shape
base_poly = Polygon(util.generate_polygon(center=(120, 30),
                                          avg_radius=20,
                                          irregularity=0.9,
                                          spikiness=0.4,
                                          num_vertices=10))

#base_poly = Polygon([[140,10],[140,50],[180,50],[180,10]])
#base_poly = Polygon([[50,100],[70,100],[70,30],[66,30],[38,58],[38,68],[50,80]])
#base_poly = Polygon([[95,75],[95,105],[105,105],[105,75]])  #ridge_01
#base_poly = Polygon([[149.5,35],[135,35],[135,20],[178,20],[178,30.673],[157.41,42.561],[157.374,39.572],[149.5,35]])  #rotbot_01
#base_poly = Polygon([[135,65],[149.5,65],[141.75,69.5],[135,69.5]])  #rotbot_02
#base_poly = Polygon([[178,28],[170.75,28],[170.75,23],[178,23]])  #rotbot_03
#base_poly = Polygon([[178,23],[138,23],[138,69.5],[135,69.5],[135,20],[178,20]])  #rotbot_04
#base_poly = Polygon([[138,23],[138,69.5],[135,69.5],[135,20]])  #rotbot_05

# Find starting edge (in this implementation, it just finds the largest edge to start from.
# TODO Allow multiple starting points
# TODO Come up with some way to determine starting edges based on geometry of previous layer
 
p1, p2 = util.longest_edge(base_poly)
starting_line = LineString([p1, p2])

#starting_line = LineString([Point(140,10), Point(140,50)])
#starting_line = LineString([Point(50,80), Point(50,100)])
#starting_line = LineString([Point(95,75), Point(95,105)]) # ridge
#starting_line = LineString([Point(149.5,35), Point(135,35)]) #rotbot_01
#starting_line = LineString([Point(135,65), Point(149.5,65)]) #rotbot_02
#starting_line = LineString([Point(178,28), Point(170.75,28)]) #rotbot_03
#starting_line = LineString([Point(178,23), Point(138,23)]) #rotbot_04
#starting_line = LineString([Point(138,23), Point(138,69.5)]) #rotbot_05

# Copy the base polygon, but exclude the starting (longest) line, turning it from a closed Polygon to an open LineString
boundary_line = LineString(util.get_boundary_line(base_poly, p1))
#boundary_line = LineString(util.get_boundary_line(base_poly, Point(140,10)))
#boundary_line = LineString(util.get_boundary_line(base_poly, Point(50,80)))
#boundary_line = LineString(util.get_boundary_line(base_poly, Point(149.5,35))) #rotbot_01
#boundary_line = LineString(util.get_boundary_line(base_poly, Point(135,65))) #rotbot_02
#boundary_line = LineString(util.get_boundary_line(base_poly, Point(178,28))) #rotbot_03
#boundary_line = LineString(util.get_boundary_line(base_poly, Point(178,23))) #rotbot_04
#boundary_line = LineString(util.get_boundary_line(base_poly, Point(138,23))) #rotbot_05

# Create the first arc
starting_point, r_start, r_farthest = util.get_farthest_point(starting_line, boundary_line, base_poly)
starting_circle = util.create_circle(starting_point.x, starting_point.y, r_start, N)
starting_arc = starting_circle.intersection(base_poly)

# plot base poly
base_poly_geoseries = gpd.GeoSeries(base_poly)
base_poly_geoseries.plot(ax=ax[0], color='white', edgecolor='black', linewidth=1)
base_poly_geoseries.plot(ax=ax[1], color='white', edgecolor='black', linewidth=1)

# plot starting line
starting_line_geoseries = gpd.GeoSeries(starting_line)
starting_line_geoseries.plot(ax=ax[0], color='red', linewidth=2)

# Generate 3d printed starting tower
curr_z = LAYER_HEIGHT  # Height of first layer
with open(OUTPUT_FILE_NAME, 'a') as gcode_file:
    gcode_file.write(f"G1 Z{curr_z} F500\n")
    gcode_file.write(";Generating first layer\n")
    #gcode_file.write("G1 E4.25\n")  # Unretract
    
# Fill in circles from outside to inside
while curr_z <= BASE_HEIGHT:
    starting_tower_r = r_start + BRIM_WIDTH  
    while starting_tower_r > LINE_WIDTH*2:
        first_layer_circle = util.create_circle(starting_point.x, starting_point.y, starting_tower_r, N)
        util.write_gcode(OUTPUT_FILE_NAME, first_layer_circle, LINE_WIDTH, LAYER_HEIGHT, FILAMENT_DIAMETER, 2, BASE_FEEDRATE, close_loop=True)
        starting_tower_r -= LINE_WIDTH*2
    
    curr_z += LAYER_HEIGHT
    with open(OUTPUT_FILE_NAME, 'a') as gcode_file:
        gcode_file.write(f"G1 Z{'{0:.3f}'.format(curr_z)} F500\n")

with open(OUTPUT_FILE_NAME, 'a') as gcode_file:
    gcode_file.write(f"G1 Z{'{0:.3f}'.format(curr_z)} F500\n")
    gcode_file.write(";Generating tower\n") 
    gcode_file.write("M106 S255\n") 
    
while curr_z < OVERHANG_HEIGHT:
    util.write_gcode(OUTPUT_FILE_NAME, starting_line.buffer(LINE_WIDTH *4), LINE_WIDTH, LAYER_HEIGHT, FILAMENT_DIAMETER, 2, TOWER_FEEDRATE, close_loop=True)
    with open(OUTPUT_FILE_NAME, 'a') as gcode_file:
        gcode_file.write(f"G1 Z{'{0:.3f}'.format(curr_z)} F500\n")
    curr_z += LAYER_HEIGHT

LINE_WIDTH = LINE_WIDTH * (1 - OVERLAP / 100)

with open(OUTPUT_FILE_NAME, 'a') as gcode_file:
    gcode_file.write("; Start of ARC OVERHANG\n")

# Create multiple layers
r = LINE_WIDTH
curr_arc = starting_arc
while r < r_start-THRESHOLD:
    # Create a circle based on point location, radius, n
    next_circle = Polygon(util.create_circle(starting_point.x, starting_point.y, r, N))
    # Plot arc
    next_arc = util.create_arc(next_circle, base_poly, ax, depth=0)
    curr_arc = Polygon(next_arc)
    r += LINE_WIDTH
    
    # Write gcode to file
    util.write_gcode(OUTPUT_FILE_NAME, next_arc, LINE_WIDTH, LAYER_HEIGHT, FILAMENT_DIAMETER, ARC_E_MULTIPLIER * (OVERLAP/100 + 1), FEEDRATE, close_loop=False)
    
    # Create image  ~~~~~~~~~~~~~~~~~~~~
    #file_name = util.image_number(image_name_list)   
    #plt.savefig(file_name, dpi=300)
    #image_name_list.append(file_name + ".png")

remaining_empty_space = base_poly.difference(curr_arc)
next_point, longest_distance, _ = util.get_farthest_point(curr_arc, boundary_line, base_poly)

while longest_distance > THRESHOLD + LINE_WIDTH:
    next_arc, remaining_empty_space, image_name_list = util.arc_overhang(curr_arc, boundary_line, N, 
                                                                        remaining_empty_space, next_circle, 
                                                                        THRESHOLD, ax, fig, 1, image_name_list, 
                                                                        R_MAX, LINE_WIDTH, OUTPUT_FILE_NAME,
                                                                        LAYER_HEIGHT, FILAMENT_DIAMETER, ARC_E_MULTIPLIER * (OVERLAP/100 + 1),
                                                                        FEEDRATE)
    next_point, longest_distance, _ = util.get_farthest_point(curr_arc, boundary_line, remaining_empty_space)
"""
# Turn images into gif + MP4
print("Making gif")
with imageio.get_writer('mygif.gif', mode='I', fps=20) as writer:
    for file_name in image_name_list:
        image = imageio.imread(file_name)
        writer.append_data(image)

print("Making movie")
clip = mp.VideoFileClip("output/output_gif.gif")
clip.write_videofile("output/output_video.mp4")"""

# Build a few layers on top of the overhanging area

for i in range(10): #was 10
    util.write_gcode(OUTPUT_FILE_NAME, Polygon(boundary_line).buffer(-THRESHOLD/2), LINE_WIDTH, LAYER_HEIGHT, FILAMENT_DIAMETER, ARC_E_MULTIPLIER, FEEDRATE*10, close_loop=True)
    with open(OUTPUT_FILE_NAME, 'a') as gcode_file:
        gcode_file.write(f"G1 Z{'{0:.3f}'.format(curr_z+LAYER_HEIGHT*i)} F500\n")
        
# Write end gcode
with open('input/end.gcode','r') as end_gcode, open(OUTPUT_FILE_NAME,'a') as gcode_file:
    for line in end_gcode:
        gcode_file.write(line)
        
plt.show()
"""Builds the simulator files for an incident from Nav2's stock files.

- the world: the stock sandbox plus the incident's walls
- the robot: the stock TurtleBot 3 Waffle plus a pose publisher, so the true position is known
- the map: the stock sandbox map with the same walls drawn in, as a site map would have them

Walls are axis-aligned boxes {"cx", "cy", "sx", "sy"} in metres: centre and size on the floor, 1 m tall.
"""
WALL_HEIGHT_M = 1.0
OCCUPIED = 0

POSE_PUBLISHER = """
    <plugin filename="gz-sim-pose-publisher-system" name="gz::sim::systems::PosePublisher">
      <publish_model_pose>true</publish_model_pose>
      <publish_link_pose>false</publish_link_pose>
      <publish_visual_pose>false</publish_visual_pose>
      <publish_collision_pose>false</publish_collision_pose>
      <publish_sensor_pose>false</publish_sensor_pose>
      <publish_nested_model_pose>false</publish_nested_model_pose>
      <use_pose_vector_msg>true</use_pose_vector_msg>
      <update_frequency>20</update_frequency>
    </plugin>
"""


def wall_model(name, wall):
    size = f"{wall['sx']} {wall['sy']} {WALL_HEIGHT_M}"
    geometry = f"<geometry><box><size>{size}</size></box></geometry>"
    return (
        f"<model name='{name}'><static>true</static>"
        f"<pose>{wall['cx']} {wall['cy']} {WALL_HEIGHT_M / 2} 0 0 0</pose>"
        f"<link name='link'><collision name='c'>{geometry}</collision>"
        f"<visual name='v'>{geometry}</visual></link></model>\n"
    )


def world_with_walls(world_sdf, walls):
    models = "".join(wall_model(f"wall_{k}", w) for k, w in enumerate(walls))
    at = world_sdf.rindex("</world>")
    return world_sdf[:at] + models + world_sdf[at:]


def robot_with_pose_publisher(robot_sdf):
    at = robot_sdf.rindex("</model>")
    return robot_sdf[:at] + POSE_PUBLISHER + robot_sdf[at:]


def draw_walls(pixels, width, height, resolution, origin, walls):
    """Marks every map cell whose centre lies inside a wall as occupied. Row 0 is the top of the map."""
    out = bytearray(pixels)
    for row in range(height):
        y = origin[1] + (height - 1 - row + 0.5) * resolution
        for col in range(width):
            x = origin[0] + (col + 0.5) * resolution
            for w in walls:
                if abs(x - w["cx"]) <= w["sx"] / 2 and abs(y - w["cy"]) <= w["sy"] / 2:
                    out[row * width + col] = OCCUPIED
                    break
    return out


def parse_pgm(data):
    """Binary PGM (P5, 8 bit) to (pixels, width, height)."""
    fields, i = [], 0
    while len(fields) < 4:
        while data[i:i + 1].isspace():
            i += 1
        if data[i:i + 1] == b"#":
            while data[i:i + 1] != b"\n":
                i += 1
            continue
        j = i
        while not data[j:j + 1].isspace():
            j += 1
        fields.append(data[i:j])
        i = j
    if fields[0] != b"P5" or int(fields[3]) != 255:
        raise ValueError("expected an 8-bit binary PGM (P5, maxval 255)")
    width, height = int(fields[1]), int(fields[2])
    return bytearray(data[i + 1:i + 1 + width * height]), width, height


def write_pgm(pixels, width, height):
    return b"P5\n%d %d\n255\n" % (width, height) + bytes(pixels)

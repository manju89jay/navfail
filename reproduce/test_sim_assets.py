"""Tests for sim_assets: walls drawn into the map, walls added to the world, pose publisher added to the robot."""
from sim_assets import draw_walls, parse_pgm, robot_with_pose_publisher, world_with_walls, write_pgm

FREE, OCC = 254, 0


def blank_map(w=40, h=40):
    return bytearray([FREE] * (w * h)), w, h


def cell(px, w, h, res, origin, x, y):
    col = int((x - origin[0]) / res)
    row = h - 1 - int((y - origin[1]) / res)
    return px[row * w + col]


def test_draw_walls_marks_inside_and_leaves_outside():
    px, w, h = blank_map()
    res, origin = 0.05, (-1.0, -1.0)
    wall = {"cx": 0.0, "cy": 0.0, "sx": 0.1, "sy": 0.5}
    out = draw_walls(px, w, h, res, origin, [wall])
    assert cell(out, w, h, res, origin, 0.01, 0.2) == OCC
    assert cell(out, w, h, res, origin, 0.01, -0.2) == OCC
    assert cell(out, w, h, res, origin, 0.2, 0.0) == FREE
    assert cell(out, w, h, res, origin, 0.01, 0.4) == FREE


def test_draw_walls_row_zero_is_the_top_of_the_map():
    px, w, h = blank_map()
    res, origin = 0.05, (-1.0, -1.0)
    out = draw_walls(px, w, h, res, origin, [{"cx": -0.975, "cy": 0.975, "sx": 0.05, "sy": 0.05}])
    assert out[0] == OCC
    assert out[(h - 1) * w] == FREE


def test_pgm_round_trip():
    px, w, h = blank_map(5, 3)
    px[7] = OCC
    data = write_pgm(px, w, h)
    px2, w2, h2 = parse_pgm(data)
    assert (w2, h2) == (5, 3)
    assert px2 == px


def test_world_with_walls_adds_static_models_inside_the_world():
    world = "<sdf><world name='default'><model name='a'/></world></sdf>"
    walls = [{"cx": 1.0, "cy": 2.0, "sx": 0.1, "sy": 1.0}, {"cx": 1.0, "cy": -2.0, "sx": 0.1, "sy": 1.0}]
    out = world_with_walls(world, walls)
    assert out.count("<model name='wall_") == 2
    assert out.count("<static>true</static>") == 2
    assert out.index("wall_1") < out.index("</world>")
    assert "<pose>1.0 2.0 0.5 0 0 0</pose>" in out
    assert "<size>0.1 1.0 1.0</size>" in out


def test_robot_gets_one_pose_publisher_inside_the_last_model():
    robot = "<sdf><model name='r'><link name='l'/></model></sdf>"
    out = robot_with_pose_publisher(robot)
    assert out.count("gz-sim-pose-publisher-system") == 1
    assert out.index("gz-sim-pose-publisher-system") < out.rindex("</model>")

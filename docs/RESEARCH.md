# Research behind navfail

A summary of research done from 24 to 27 October 2026 for navfail, a debugger for robot navigation failures on ROS 2 and Nav2 (see the README). The full working notes (scoring, how each fix was traced, the raw search data) are kept in a private repository; this page holds what a reader needs to check the claims in the README. It assumes some familiarity with Nav2; names such as MPPI, DWB and RPP (controllers), Smac, Theta* and NavFn (planners), AMCL (localisation) and costmap (Nav2's grid of where the robot may go) are Nav2 components.

## 1. How the failures were collected

- **Nav2 issue tracker** (github.com/ros-navigation/navigation2): 22 searches through GitHub's search interface (for example "stuck", "oscillate", "collision", "inflation", "recovery", "no valid path", "failed to make progress", and the bug label) returned 1,323 different issues. A screen by title kept 176; reading those and their discussions gave 40 entries (IDs starting with N).
- **Papers and documentation:** papers on Nav2 and robot navigation testing, and the official Nav2 Jazzy documentation (IDs starting with P).
- **Question-and-answer sites and robot trackers:** Robotics Stack Exchange (questions with an accepted answer, including posts moved there from ROS Answers) and the TurtleBot 3 and TurtleBot 4 issue trackers (IDs starting with Q).
- **The ID prefix names the search batch that found an entry, not its source type:** P05 is a Nav2 tracker issue found through a paper; Q12 is a Stack Exchange post backed by a Nav2 tracker issue.
- **From 70 to 50:** the three batches gave 70 entries. Three duplicates were merged and 17 entries dropped after reading, which left 50; that is why the IDs have gaps.
- **Not all are Nav2 defects:** Q01 is a TurtleBot 4 package misconfiguration, and Q13 and Q14 are ROS 1 posts (the older navigation stack), kept because the same mechanism exists in Nav2.
- **Links:** every source link was checked to open; Stack Exchange questions were checked through its public interface, because its pages refuse automated reads.

What each column of the table means:

- **Category:** the eight categories of section 3.
- **Seen as:** the nearest of nine outcome classes: collision, stall (the robot stops), oscillation (back and forth), abort (Nav2 gives up), no path, path through obstacle (the plan crosses an obstacle), deadline (takes too long), recovery loop, localisation loss. A `*` marks rows where the report does not say this outright and the class is inferred or the nearest fit.
- **Credibility:** a = a Nav2 maintainer's comment, a bug label, or a linked fix; b = a paper accepted at IROS 2020 (one paper, entries P06 and P07; the date is that of its arXiv version 2); c = accepted answer on Stack Exchange; d = official Nav2 documentation. Counts: a 31, b 2, c 11, d 6.
- **Fixed in 1.3.13:** checked against the history of Nav2 1.3.13, the version navfail runs on, on 26 October 2026. yes = a fix commit was found in that history (19); no = a fix was merged upstream and was not found in that history (7); open = no fix merged (2); n/a = no Nav2 code fix: configuration advice, behaviour by design, no fix stated, an accepted limitation, or fixed outside Nav2 (22). A `†` marks the least certain: N03's fix only adds warnings, so the failure can still be configured; N17 had a second change that was not identified; for N23 and N36 a different change in the release was not ruled out.

## 2. The 50 failures, by category

| ID | Date | Category | What was reported | Seen as | Credibility | Fixed in 1.3.13 | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| N03 | 2023-05-19 | C1 | Smac Hybrid-A* path collides with the footprint when the inflation radius is too small | path through obstacle | a | yes† | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/3580) |
| N04 | 2022-08-04 | C1 | Planner ignores keepout-filter zones for a rectangular robot (filter not inflated) | path through obstacle | a | n/a | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/3102) |
| N17 | 2025-03-06 | C1 | navigate_to_pose aborts with "Path is empty" after the global costmap is cleared in a narrow passage | abort | a | yes† | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/4964) |
| N24 | 2024-12-19 | C1 | Smac Hybrid path runs through inscribed cells in a narrow corridor | path through obstacle | a | yes | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/4808) |
| N29 | 2024-05-22 | C1 | MPPI footprint distance never drops below the inscribed radius | collision* | a | yes | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/4361) |
| N32 | 2021-07-17 | C1 | Smac Hybrid treats a footprint touching inscribed cells as a collision, so navigation fails | abort | a | yes | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/2457) |
| P10 | not stated | C1 | Docs: thin inflation around walls and wide zero-cost areas give poor clearance to moving obstacles | collision* | d | n/a | [Nav2 docs](https://docs.nav2.org/jazzy/configuration_and_development/tuning_guide/) |
| P11 | not stated | C1 | Docs: circular radius for a non-circular robot causes "stuck robot" situations | no path | d | n/a | [Nav2 docs](https://docs.nav2.org/jazzy/configuration_and_development/tuning_guide/) |
| Q04 | 2024-02-20 | C1 | Inflation layer listed before the obstacle layer, so detected obstacles get no inflation | collision | c | n/a | [Stack Exchange](https://robotics.stackexchange.com/questions/108412/obstacle-layer-in-global-costmap-not-set) |
| Q06 | 2023-04-12 | C1 | Differential-drive robot stalls and rocks at doorways | oscillation | c | n/a | [Stack Exchange](https://robotics.stackexchange.com/questions/103181/helping-diff-drive-robot-get-through-doorways) |
| Q11 | 2024-03-05 | C1 | MPPI with Smac Hybrid ignores a long rectangular footprint and collides | collision | c | n/a | [Stack Exchange](https://robotics.stackexchange.com/questions/109722/mppismacplannerhybrid-navigation-with-a-large-base-footprint-problem) |
| Q14 | 2011-08-29 | C1 | ROS 1: robot scrapes obstacles while turning away from them | collision | c | n/a | [Stack Exchange](https://robotics.stackexchange.com/questions/33963/move-base-scrapes-obstacles-instead-of-staying-clear) |
| N11 | 2020-09-27 | C2 | Planner routes through walls and the robot drives into them after the global costmap is cleared | path through obstacle | a | yes | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/1999) |
| N21 | 2025-08-22 | C2 | Obstacle erased from the costmap when the robot reverses away from it | path through obstacle* | a | yes | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/5476) |
| N23 | 2024-10-29 | C2 | Clear-costmap call leaves a short window in which obstacles in front of the robot are ignored | path through obstacle* | a | no† | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/4734) |
| N33 | 2019-01-29 | C2 | Ghost cost stays in the global costmap after a dropped box is removed | no path* | a | n/a | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/545) |
| N36 | 2025-01-04 | C2 | Cells cleared under the footprint in the static layer never come back | path through obstacle* | a | no† | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/4825) |
| Q03 | 2024-07-30 | C2 | Removed obstacle stays in the local costmap when nothing behind it returns a lidar hit | no path | c | n/a | [Stack Exchange](https://robotics.stackexchange.com/questions/112451/removed-object-is-not-cleared-from-local-costmap) |
| Q09 | 2020-06-17 | C2 | Obstacle is dropped from the costmap inside the sensor's blind zone, planner drives into it | collision | c | yes | [Stack Exchange](https://robotics.stackexchange.com/questions/96259/obstacles-in-sensor-deadzone) |
| Q13 | 2011-10-06 | C2 | ROS 1: obstacles never clear with outdoor lidar that returns max range | no path* | c | n/a | [Stack Exchange](https://robotics.stackexchange.com/questions/34737/costmaps-obstacle-does-not-clear-properly-under-sparse-environment) |
| N39 | 2025-10-28 | C3 | MPPI hesitates and goes back and forth beside a lethal obstacle | oscillation | a | n/a | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/5661) |
| P12 | not stated | C3 | Docs: whipping, stuttering rotation when the path heading differs a lot from the robot heading | oscillation | d | n/a | [Nav2 docs](https://docs.nav2.org/jazzy/configuration_and_development/tuning_guide/) |
| P13 | not stated | C3 | Docs: MPPI obstacle critic mismatched with inflation causes wobble, free-space refusal and corridor jitter | stall | d | n/a | [Nav2 docs](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/controller_plugins/mppi_controller/configuring_mppic/) |
| P14 | not stated | C3 | Docs: MPPI prediction horizon larger than the local costmap, and extreme path-align offsets | stall | d | n/a | [Nav2 docs](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/controller_plugins/mppi_controller/configuring_mppic/) |
| Q02 | 2024-03-09 | C3 | DWB reports "No valid trajectories" next to an obstacle because it only samples forward motion | stall | c | n/a | [Stack Exchange](https://robotics.stackexchange.com/questions/109841/ros2-navigation2-local-plan-does-not-avoid-obstacle) |
| Q07 | 2019-12-20 | C3 | DWB stops about 0.5 m short of the goal and recovery starts (goal tolerance 0.2 instead of 0.25) | stall | c | n/a | [Stack Exchange](https://robotics.stackexchange.com/questions/94190/local-planner-stops-shortly-before-arriving-at-goal) |
| Q08 | 2025-03-31 | C3 | DWB cannot rotate in place at the goal because minimum linear velocity is non-zero | stall | c | n/a | [Stack Exchange](https://robotics.stackexchange.com/questions/115215/robot-failing-to-rotate-to-goal) |
| N12 | 2019-10-26 | C4 | Obstacle dropped on the path: global costmap shows it, path is not replanned | stall | a | yes | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/1307) |
| N13 | 2019-10-07 | C4 | Robot drives into an object that is not in the static map | collision | a | yes | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/1208) |
| N34 | 2023-11-10 | C4 | Replanning not triggered when an obstacle appears next to the path (IsPathValid checks points only) | collision | a | yes | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/3954) |
| P07 | 2020-07-14 | C4 | No route to goal in crowded space leads to costmap clearing, then waiting | no path | b | n/a | [arXiv paper](https://arxiv.org/abs/2003.00368) |
| P15 | not stated | C4 | Docs: cached obstacle heuristic in Smac planners slows search when a corridor becomes blocked | deadline | d | n/a | [Nav2 docs](https://docs.nav2.org/jazzy/configuration_and_development/tuning_guide/) |
| Q01 | 2023-08-15 | C4 | TurtleBot 4 costmap layers subscribe to the wrong scan topic, obstacles never reach the costmap | collision | a | n/a | [TurtleBot 4 tracker](https://github.com/turtlebot/turtlebot4/issues/247) |
| N05 | 2022-09-05 | C5 | Collision monitor does not detect an obstacle while the robot rotates in place | collision | a | yes | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/3171) |
| N07 | 2021-07-16 | C5 | BackUp recovery never terminates when the robot is blocked behind | stall | a | yes | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/2453) |
| N08 | 2021-02-17 | C5 | BackUp refuses to start: its collision look-ahead reaches far-away obstacles | recovery loop | a | yes | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/2189) |
| N10 | 2019-12-04 | C5 | Spin recovery hits a nearby obstacle before the collision check stops it | collision | a | yes | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/1404) |
| N15 | 2024-10-31 | C5 | RoundRobin recovery is not reset after the main branch succeeds | recovery loop | a | yes | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/4737) |
| N19 | 2026-06-30 | C5 | MPPI FollowPath aborts again and again with "Resulting plan has 0 poses" when the same path is resent | recovery loop | a | no | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/6235) |
| N01 | 2026-01-13 | C6 | Theta* path intersects lethal obstacles (line-of-sight check) | path through obstacle | a | no | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/5863) |
| N02 | 2025-07-03 | C6 | SMAC smoother returns a colliding path for a non-circular robot in a confined space | path through obstacle* | a | no | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/5330) |
| N18 | 2026-08-25 | C6 | Theta* reports "no path" although a collision-free path exists | no path | a | no | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/6398) |
| N26 | 2026-03-03 | C6 | Smac Hybrid returns paths that is_path_valid calls colliding | path through obstacle | a | open | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/5996) |
| N30 | 2021-11-02 | C6 | Smac Hybrid analytic expansion ignores costs along the last stretch | path through obstacle | a | yes | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/2659) |
| Q05 | 2022-06-14 | C6 | Global planner flips between two symmetric routes, robot stuck at the fork | oscillation | c | n/a | [Stack Exchange](https://robotics.stackexchange.com/questions/101950/how-to-avoid-planner-jumping-between-2-possible-path) |
| N28 | 2026-10-03 | C7 | Smac Hybrid checks the goal pose at the snapped angle bin, not the real yaw | no path* | a | open | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/6604) |
| N38 | 2025-09-30 | C7 | Smac plans to a goal deep in a lethal zone when the goal tolerance is non-zero | deadline* | a | no | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/5566) |
| P05 | 2021-11-11 | C7 | RPP collision warnings and stops when approaching a goal near an obstacle or taking a tight turn | stall | a | yes | [Nav2 tracker](https://github.com/ros-navigation/navigation2/issues/2670) |
| Q12 | 2024-10-22 | C7 | Behaviour tree does not pause near a goal obstacle on Humble (back-port missing) | abort* | a | yes | [Stack Exchange](https://robotics.stackexchange.com/questions/113421/navigate-to-pose-and-pause-near-goal-obstacle-doesnt-work) |
| P06 | 2020-07-14 | C8 | AMCL confidence drops in long repetitive corridors with many people | localisation loss | b | n/a | [arXiv paper](https://arxiv.org/abs/2003.00368) |

"not stated" in the Date column: the Nav2 documentation pages carry no date.

## 3. The eight categories

| # | Category | What goes wrong | Entries | Fix not in 1.3.13, or none merged |
| --- | --- | --- | ---: | ---: |
| C1 | Footprint, inflation and tight gaps | the robot's size or safety margin is wrong for the space, so it gets too close or refuses to pass | 12 | 0 |
| C2 | Costmap not clearing or clearing wrongly | Nav2 keeps an obstacle that is gone, or loses one that is there | 8 | 2 |
| C3 | Controller tuning | controller settings make the robot stop, hesitate or wobble near an obstacle or the goal | 7 | 0 |
| C4 | Late, dynamic or unseen obstacle | an obstacle appears after the start, or is never registered | 6 | 0 |
| C5 | Recovery loop or recovery collision | a recovery (turn on the spot, back up, pause) hits something or repeats without end | 6 | 1 |
| C6 | Planner path validity | the planner returns a path through an obstacle, says "no path" when one exists, or flips between two paths | 6 | 4 |
| C7 | Goal in or near an obstacle | the goal is inside or beside an obstacle and Nav2 handles it badly | 4 | 2 |
| C8 | Localisation near obstacles | the robot loses track of where it is when what it sees differs from the map | 1 | 0 |

The other entries either have their fix in 1.3.13, or have no Nav2 code fix (n/a); for the n/a entries the behaviour is still possible in 1.3.13.

## 4. What existing tools cover

Tools and sources reviewed (the first six read in detail, the last three at summary level):

| Tool | What it is |
| --- | --- |
| RoboVAST | a framework for large scenario campaigns on ROS 2, Nav2 and Gazebo (Karlsruhe and Bremen, 2026) |
| Scenario Execution for Robotics | runs scenarios written in the OpenSCENARIO language as behaviour trees, with Gazebo and Nav2 actions |
| Nav2 system tests | the Nav2 project's own integration tests, on the same TurtleBot 3 sandbox navfail uses |
| DDEnv | removes parts of a Gazebo world while a robot failure still happens (von Stein and Elbaum, ICRA 2021; ROS 1, no licence) |
| Valle et al. | shrinks failing tests that are flaky, by repeating each run 30 times (2026; its robot case study is on ROS 1) |
| Zeller's ddmin | the general method for shrinking a failing input (2002) |
| Robot fuzzers | random or search-guided test generators (PGFuzz, RoboFuzz, AmbieGen, PHYS-FUZZ and others); they stop at "found a failure" |
| LLM scenario generators | language models that write test scenarios (ChatScene, SocRATES and others); none explains a failure |
| Industry | car-industry tools and practice (Applied Intuition, Foretellix, Waymo, Tier IV's scenario_simulator_v2 for Autoware); mostly closed; scenario_simulator_v2 is open source but targets Autoware |

Who covers each step of an investigation, for Nav2 failures:

| Step | Coverage today |
| --- | --- |
| Detect the failure | partial: collisions, aborts and timeouts are seen; a plan through an obstacle or a wrong costmap cell is not, because none of the listed tools is described as checking the plan or the costmap |
| Confirm by repeated runs | RoboVAST (10 or 20 runs), DDEnv (3 runs), Valle (30 runs), only for what each one detects |
| Shrink the scene to what matters | partial: DDEnv removes obstacles, but on ROS 1 and without a licence; Valle shrinks time windows on ROS 1; none is described as shrinking the time an obstacle appears, or a parameter file |
| Explain the failure | not covered: RoboVAST lets an attached model query logs, but no tool produces an explanation |
| Compare two configurations | partial: RoboVAST varies parameters and queries the results, but gives no verdict from repeated runs, and has no control (running the same configuration against itself to see how much results vary by chance) |
| Package the failure for replay | partial: RoboVAST archives whole campaigns, Scenario Execution saves a scenario file |
| Point to the configuration or source line (a step navfail adds) | our reading: none of the listed tools is described as doing this |

**The gap is per step, not per failure type:** shrinking, explaining, comparing and packaging are not fully covered for any of the eight categories. How much detection covers differs by category, because what goes wrong is visible in different places: a collision or a stop is seen by every tool, a plan through an obstacle only by reading the plan. Where the existing tools are stronger, navfail does not compete: scale (RoboVAST reports 100,000 runs on 1,920 CPUs), many environments, sensor-noise variation and cluster infrastructure. navfail runs on one laptop, with one robot and one simulated world.

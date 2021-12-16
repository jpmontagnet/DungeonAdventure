from typing import Any
# import random

from Compass import North, South, East, West
from Room import RoomStyle
from Grid import Grid


class Maze(Grid):

    def __init__(self,
                 width: int = 4, height: int = 4,
                 map_str: str = None,
                 debug: bool = False) -> None:
        if map_str is not None:
            width, height = Maze.parse_map(map_str=map_str, debug=debug)
        super().__init__(width=width, height=height)
        if map_str is not None:
            self.load_map(map_str=map_str, debug=debug)
        # Initialization of other fields deferred to separate methods.
        self.__path: list[Any] = []

    def load_map(self, **kwargs):
        Maze.parse_map(grid=self, **kwargs)

    @staticmethod
    def parse_map(map_str: str = None, grid=None, style=RoomStyle, debug=False):
        """ Parse string containing specification for map.
        Operates in one of two modes, depending upon whether grid is provided:

        - grid is None - measure-only mode:
          Returns dimensions necessary for a grid that can contain the map.
          This is a quick estimate that assumes properly formatted input.

        - grid present - full-load mode:
          Fully parses map, populating the grid as specified in the map.
          Non-static method load_map() is a thin wrapper for this mode,
          since Maze is a Grid subclass.

        Map format is identical to output format, except mixed-item 'M'
        marker is replaced with multi-character list of markers for items,
        with repetition where there are multiple of same item type,
        e.g. "HHV" represents 2 health potions + 1 vision potion.

        For measure-only mode, there is no validation of walls, doors, or
        room contents, other than having expected width.

        :param map_str: String containing specification for map.
        :param grid: Grid of rooms of sufficient size to hold map.
            If None, function instead operates in measure-only mode.
        :param style: Map rendering style in which map is formatted.
        :param debug: Whether to print debug info while parsing.
            For troubleshooting mistakes in str_map (and/or bugs in parsing)
        :return: In measure-only mode, returns a pair of ints representing
            width and height, respectively, of necessary grid dimensions.
            In full-load mode, returns None.
        :exception ValueError, if map appears improperly formatted.
        """
        wall_len: int = len(style.wall_n)
        line_len: int = 0

        in_grid: bool = False
        south_edge: bool = False

        num_rows: int = 0
        # num_cols: int = 0
        grid_row: int = 0
        want_lat: bool = True

        line_num: int = 0  # 1-indexed, unlike everything else
        char_num = 0

        def dbg_parse(*args, **kwargs):
            if debug:
                print(f"L{line_num}C{char_num}: ", *args, **kwargs)

        lines = map_str.splitlines()
        for line in lines:
            line_num += 1
            line = line.rstrip()
            dbg_parse(f"line '{line}'")

            # skip header comment/whitespace lines
            if not in_grid and (len(line) == 0 or line.startswith('#')):
                continue

            # one-time work upon first entering grid
            if not in_grid:
                in_grid = True

                # Initial dimensions assessment, before grid has been created.
                # Do quick math sanity-check, conversion to grid dimensions.
                # Parses only first line of grid, then returns result.
                if grid is None:
                    if len(line) % (wall_len+1) != 1:
                        raise ValueError(f"L{line_num}: expected line len of form {wall_len+1}*N+1, got {len(line)}")
                    num_cols = (len(line)-1)//(wall_len+1)
                    if (len(lines)-line_num) % 2 != 0:
                        raise ValueError(f"expected line count 2*N+1, got {len(lines)-line_num}")
                    num_rows = (len(lines)-line_num)//2
                    dbg_parse(f"estimated grid dims={num_cols}x{num_rows}")
                    return num_cols, num_rows
                    # All done! Only estimating dimensions.
                    # TODO could optionally do fuller validation that grid looks legit

                else:
                    num_cols = grid.width
                    num_rows = grid.height
                    line_len = num_cols * (wall_len + 1) + 1
                    dbg_parse(f"grid dims={num_cols}x{num_rows} line_len={line_len}")

            dbg_parse(f"line len {len(line)}")
            # sanity check, for errant line unexpectedly longer than first line
            if len(line) != line_len:
                raise ValueError(f"L{line_num}: does not match expected len_len {line_len}")
            dbg_parse(f"want_lat={want_lat}")

            # walk the line
            char_num = 0
            grid_col: int = 0
            east_edge: bool = False
            r = None  # current room
            while char_num < len(line):
                dbg_parse(f"room ({grid_col},{grid_row})")

                # last char in line
                if char_num + 1 >= len(line):
                    dbg_parse(f"last char in line")
                    east_edge = True

                # on or aligned with a vertical wall, which is either:
                # west side of room contents that follows
                # OR east side of room contents just parsed
                dbg_parse(f"grid col {grid_col}")
                c = line[char_num]
                if want_lat:
                    if c != style.corner:
                        raise ValueError(f"L{line_num}C{char_num}: expected corner '{style.corner}', got '{c}'")
                    dbg_parse(f"corner")
                else:
                    if c != style.wall_w and c != style.door_w:
                        raise ValueError(f"L{line_num}C{char_num}: expected wall '{style.wall_w}'" +
                                         f" or door '{style.door_w}', got '{c}'")
                    dbg_parse(f"East-West room side")
                if east_edge:
                    if not want_lat and r:
                        # completing room from previous round
                        if c == style.door_e:
                            r.add_door(East)
                    break  # from "walk the line" loop

                dbg_parse(f"get room...")
                r = grid.room(grid_col, grid_row)

                if not want_lat:
                    if r and c == style.door_w:
                        r.add_door(West)

                char_num += 1

                # between vertical walls
                if want_lat:
                    # horizontal wall/door
                    wall = line[char_num:char_num+wall_len]
                    if wall != style.wall_n and wall != style.door_n:
                        raise ValueError(f"L{line_num}C{char_num}: expected north wall '{style.wall_n}'" +
                                         f" or door '{style.door_n}', but got '{wall}'")
                    dbg_parse(f"North-South room side")
                    if r:
                        if south_edge:
                            if wall == style.door_s:
                                r.add_door(South)
                        elif wall == style.door_n:
                            r.add_door(North)
                else:
                    contents = line[char_num:char_num+wall_len].strip()
                    dbg_parse(f"contents: {contents}")
                    for c in contents:
                        if c == 'i':
                            r.is_entrance = True
                        elif c == 'O':
                            r.is_exit = True
                        elif c == 'X':
                            r.has_pit = True
                        elif c == 'H':
                            r.healing_potions += 1
                        elif c == 'V':
                            r.vision_potions += 1
                        elif c in ('A', 'E', 'I', 'P'):
                            r.pillar = c
                        else:
                            raise ValueError(f"{c} in room {r.coords} not recognized")
                char_num += wall_len

                if not east_edge:
                    grid_col += 1
                    dbg_parse(f"next up: grid_col {grid_col} west edge")
                else:
                    dbg_parse(f"next up: grid_row {grid_row} east edge")

            dbg_parse(f"prep for next line...")

            # if last line, then completing room on bottom row
            if line_num == len(lines):
                dbg_parse(f"final wall completed")
                break

            # prep for next line
            # if got content line, increment in row_num for next row...
            # unless on last row, in which case next line is final line,
            # handled as south wall of final row and south edge of grid.
            if not want_lat:
                if grid_row + 1 < num_rows:
                    grid_row += 1
                else:
                    south_edge = True
                    dbg_parse(f"next up: row {grid_row} south edge")
            want_lat = not want_lat
            dbg_parse(f"next up: row {grid_row} want_lat={want_lat}")

    def generate(self):
        # TODO
        pass


if __name__ == '__main__':
    print("Greetings from Maze!\n")

    # Default 4x4 grid, no doors yet
    m = Maze()
    print(f"default maze is {m.width}x{m.height}:")
    print(m)

    # Measure canned
    print(f"canned dungeon:")
    g_map_str = """
# This is my dungeon
+-----+-----+-----+
| i   |     =     |
+--H--+--H--+--H--+
|     =     | O   |
+-----+-----+-----+
""".lstrip()
    print(g_map_str)
    g_width, g_height = Maze.parse_map(map_str=g_map_str)
    print(f"measure-only estimates as {g_width}x{g_height}\n")

    # Full init from canned maze
    print(f"another canned dungeon:")
    g_map_str = """
# This is my other dungeon
+-----+-----+-----+
| i   |     = O   |
+--H--+--H--+-----+
| P   = XV  = HH  |
+-----+-----+-----+
""".lstrip()
    print(g_map_str)
    print(f"...now do full load...")
    m = Maze(map_str=g_map_str)
    print(f"...reports dimensions {m.width}x{m.height}")
    print(f"...and re-render:")
    print(f"{m}")

# END

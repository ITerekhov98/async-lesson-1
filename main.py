import os
import argparse
import asyncio
import time
import curses
import random

from itertools import cycle

from physics import update_speed
from curses_tools import get_frame_size, draw_frame

EXPLOSION_FRAMES = [
    """\
           (_)
       (  (   (  (
      () (  (  )
        ( )  ()
    """,
    """\
           (_)
       (  (   (
         (  (  )
          )  (
    """,
    """\
            (
          (   (
         (     (
          )  (
    """,
    """\
            (
              (
            (
    """,
]

TIC_TIMEOUT = 0.1
SPACE_KEY_CODE = 32
LEFT_KEY_CODE = 260
RIGHT_KEY_CODE = 261
UP_KEY_CODE = 259
DOWN_KEY_CODE = 258
CANVAS_FRAME_THICKNESS = 2


class Obstacle:
    
    def __init__(self, row, column, rows_size=1, columns_size=1, uid=None):
        self.row = row
        self.column = column
        self.rows_size = rows_size
        self.columns_size = columns_size
        self.uid = uid
    
    def get_bounding_box_frame(self):
        # increment box size to compensate obstacle movement
        rows, columns = self.rows_size + 1, self.columns_size + 1
        return '\n'.join(_get_bounding_box_lines(rows, columns))
   
    def get_bounding_box_corner_pos(self):
        return self.row - 1, self.column - 1
   
    def dump_bounding_box(self):
        row, column = self.get_bounding_box_corner_pos()
        return row, column, self.get_bounding_box_frame()
        
    def has_collision(self, obj_corner_row, obj_corner_column, obj_size_rows=1, obj_size_columns=1):
        '''Determine if collision has occured. Return True or False.'''
        return has_collision(
            (self.row, self.column),
            (self.rows_size, self.columns_size),
            (obj_corner_row, obj_corner_column),
            (obj_size_rows, obj_size_columns),
        )


def _get_bounding_box_lines(rows, columns):

    yield ' ' + '-' * columns + ' '
    for _ in range(rows):
        yield '|' + ' ' * columns + '|'
    yield ' ' + '-' * columns + ' '


async def show_obstacles(canvas, obstacles):
    """Display bounding boxes of every obstacle in a list"""
    
    while True:
        boxes = []

        for obstacle in obstacles:
            boxes.append(obstacle.dump_bounding_box())
        
        for row, column, frame in boxes:
            draw_frame(canvas, (row, column), frame)

        await asyncio.sleep(0)

        for row, column, frame in boxes:
            draw_frame(canvas, (row, column), frame, negative=True)


def _is_point_inside(corner_row, corner_column, size_rows, size_columns, point_row, point_row_column):
    rows_flag = corner_row <= point_row < corner_row + size_rows
    columns_flag = corner_column <= point_row_column < corner_column + size_columns

    return rows_flag and columns_flag


def has_collision(obstacle_corner, obstacle_size, obj_corner, obj_size=(1, 1)):
    '''Determine if collision has occured. Return True or False.'''

    opposite_obstacle_corner = (
        obstacle_corner[0] + obstacle_size[0] - 1,
        obstacle_corner[1] + obstacle_size[1] - 1,
    )

    opposite_obj_corner = (
        obj_corner[0] + obj_size[0] - 1,
        obj_corner[1] + obj_size[1] - 1,
    )

    return any([
        _is_point_inside(*obstacle_corner, *obstacle_size, *obj_corner),
        _is_point_inside(*obstacle_corner, *obstacle_size, *opposite_obj_corner),

        _is_point_inside(*obj_corner, *obj_size, *obstacle_corner),
        _is_point_inside(*obj_corner, *obj_size, *opposite_obstacle_corner),
    ])

def read_controls(canvas, rocket_speed):
    """Read keys pressed and returns tuple witl controls state."""

    rows_direction = columns_direction = 0
    space_pressed = False

    while True:
        pressed_key_code = canvas.getch()

        if pressed_key_code == -1:
            # https://docs.python.org/3/library/curses.html#curses.window.getch
            break

        if pressed_key_code == UP_KEY_CODE:
            rows_direction = -1

        if pressed_key_code == DOWN_KEY_CODE:
            rows_direction = 1

        if pressed_key_code == RIGHT_KEY_CODE:
            columns_direction = 1

        if pressed_key_code == LEFT_KEY_CODE:
            columns_direction = -1

        if pressed_key_code == SPACE_KEY_CODE:
            space_pressed = True

    return rows_direction, columns_direction, space_pressed


async def fire(canvas, fire_position, rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot, direction and speed can be specified."""

    row, column = fire_position

    canvas.addstr(round(row), round(column), '*')
    await sleep(1)

    canvas.addstr(round(row), round(column), 'O')
    await sleep(1)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await sleep(1)
        canvas.addstr(round(row), round(column), ' ')
        for obstacle in obstacles:
            if obstacle.has_collision(row, column):
                obstacles_in_last_collisions.append(obstacle)
                return
        row += rows_speed
        column += columns_speed


async def explode(canvas, center_row, center_column):
    rows, columns = get_frame_size(EXPLOSION_FRAMES[0])
    corner_row = center_row - rows / 2
    corner_column = center_column - columns / 2

    curses.beep()
    for frame in EXPLOSION_FRAMES:

        draw_frame(canvas, (corner_row, corner_column), frame)

        await asyncio.sleep(0)
        draw_frame(canvas, (corner_row, corner_column), frame, negative=True)
        await asyncio.sleep(0)


async def blink(canvas, offset_tics, row, column, symbol='*'):
    await sleep(offset_tics)

    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        await sleep(20)

        canvas.addstr(row, column, symbol)
        await sleep(3)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await sleep(5)

        canvas.addstr(row, column, symbol)
        await sleep(3)


def get_star_params(canvas_size):
    rows_number, columns_number = canvas_size
    x = random.randint(
        CANVAS_FRAME_THICKNESS,
        columns_number-CANVAS_FRAME_THICKNESS
    )
    y = random.randint(
        CANVAS_FRAME_THICKNESS,
        rows_number-CANVAS_FRAME_THICKNESS
    )
    symbol = random.choice(['*', '.', ':', '+'])
    return y, x, symbol


def clip_rocket_position(position, min_position, max_position):
    '''does not allow the rocket to take off outside the canvas'''
    return max(min(max_position, position), min_position)

def calculate_rocket_move(
        rocket_position,
        rocket_size,
        canvas_size,
        row_speed,
        column_speed,
        rows_direction,
        columns_direction):

    rocket_rows_position, rocket_columns_position = rocket_position
    rocket_row_size, rocket_column_size = rocket_size
    rows_number, columns_number = canvas_size
    

    row_speed, column_speed = update_speed(row_speed, column_speed, rows_direction, columns_direction)
    rocket_rows_position += row_speed
    rocket_columns_position += column_speed

    rocket_columns_position = clip_rocket_position(rocket_columns_position, 0, (columns_number - rocket_column_size))
    rocket_rows_position = clip_rocket_position(rocket_rows_position, 0, (rows_number - rocket_row_size))

    return (rocket_rows_position, rocket_columns_position), row_speed, column_speed


def get_rocket_frames():
    rocket_frames = []
    for rocket in os.listdir('rocket'):
        with open(f'rocket/{rocket}', 'r') as f:
            rocket = f.read()
            rocket_frames.extend((rocket, rocket))
    return rocket_frames


def get_garbage_frames():
    garbage_frames = []
    for garbage in os.listdir('garbage'):
        with open(f'garbage/{garbage}', 'r') as f:
            frame = f.read()
            garbage_frames.append(frame)
    return garbage_frames


def get_game_over_tag():
    with open('gameover.txt', 'r') as f:
        tag = f.read()
    return tag

async def sleep(ticks=1):
    for _ in range(ticks):
        await asyncio.sleep(0)


async def animate_spaceship(
        canvas,
        rocket_frames,
        rocket_position,
        rocket_size,
        canvas_size,
        rocket_speed):

    row_speed = column_speed = 0
    for rocket in cycle(rocket_frames):
        rows_direction, columns_direction, space_pressed = read_controls(canvas, rocket_speed)
        rocket_position, row_speed, column_speed = calculate_rocket_move(
            rocket_position,
            rocket_size,
            canvas_size,
            row_speed,
            column_speed,
            rows_direction,
            columns_direction
        )
        draw_frame(canvas, rocket_position, rocket)
        gun_position = (rocket_position[0], rocket_position[1] + (rocket_size[1] // 2))
        
        if space_pressed:
            coroutines.append(fire(canvas, gun_position))
        await sleep(1)
        draw_frame(canvas, rocket_position, rocket, negative=True)
        for obstacle in obstacles:
            if obstacle.has_collision(*rocket_position):
                coroutines.append(show_gameover(canvas, canvas_size))
                return

async def show_gameover(canvas, canvas_size):
    row_center, column_center = (dim//2 for dim in canvas_size)
    row_size, column_size = get_frame_size(game_over_tag)
    row = row_center - row_size // 2
    column = column_center - column_size // 2
    while True:
        draw_frame(canvas, (row, column), game_over_tag)
        await sleep(1)


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0
    row_size, column_size = get_frame_size(garbage_frame)
    while row < rows_number:
        obstacle = Obstacle(row, column, row_size, column_size)
        obstacles.append(obstacle)

        draw_frame(canvas, (row, column), garbage_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, (row, column), garbage_frame, negative=True)
        obstacles.remove(obstacle)
        if obstacle in obstacles_in_last_collisions:
            center_row = (row * 2 + row_size) // 2
            center_column = (column * 2 + column_size) // 2
            coroutines.append(explode(canvas, center_row, center_column))
            return
        
        row += speed



async def fill_orbit_with_garbage(canvas, canvas_row_size, garbage_frames):
    for garbage in cycle(garbage_frames):
        delay = get_garbage_delay_tics(year)
        if not delay:
            await sleep(1)
            continue

        frame_rows = garbage.split('\n')
        row_limit = canvas_row_size - max(len(row) for row in frame_rows)
        column = random.randint(1, row_limit)
        coroutines.append(fly_garbage(canvas, column, garbage))
        await sleep(delay)



def get_garbage_delay_tics(year):
    if year < 1961:
        return None
    elif year < 1969:
        return 20
    elif year < 1981:
        return 14
    elif year < 1995:
        return 10
    elif year < 2010:
        return 8
    elif year < 2020:
        return 6
    else:
        return 2


async def change_year():
    global year
    while True:
        await sleep(15)
        year += 1

PHRASES = {
    # Только на английском, Repl.it ломается на кириллице
    1957: "First Sputnik",
    1961: "Gagarin flew!",
    1969: "Armstrong got on the moon!",
    1971: "First orbital space station Salute-1",
    1981: "Flight of the Shuttle Columbia",
    1998: 'ISS start building',
    2011: 'Messenger launch to Mercury',
    2020: "Take the plasma gun! Shoot the garbage!",
}


async def draw_info_panel(canvas):
    current_year_info = ''
    year_area_position = (1,2)
    year_area_size = (4,6)
    year_info_position = (2,9) 
    while True:
        year_area = canvas.derwin(
            *year_area_size,
            *year_area_position
        )
        year_area.border()
        year_area.addstr(1, 1, f'YEAR')
        year_area.addstr(2, 1, str(year))
        if year in PHRASES.keys():
            current_year_info = PHRASES[year]
        year_info_area = canvas.derwin(
            *year_info_position
        )
        year_info_area.addstr(current_year_info)
        await sleep(1)


def draw(canvas, args):
    rocket_frames = get_rocket_frames()
    garbage_frames = get_garbage_frames()
    rocket_size = get_frame_size(rocket_frames[0])
    canvas_size = canvas.getmaxyx()
    canvas.border()
    canvas.nodelay(True)
    curses.curs_set(False)

    rocket_position = list(dimension//2 for dimension in canvas_size)
    global year
    year = 1957

    global game_over_tag
    game_over_tag = get_game_over_tag()
    
    global obstacles 
    obstacles = []
    
    global obstacles_in_last_collisions
    obstacles_in_last_collisions = []
    
    global coroutines
    coroutines = [fire(canvas, rocket_position, rows_speed=-1)]
    
    for star in range(args.stars_count):
        offset_ticks = random.randint(1, 10)
        coroutines.append(
            blink(canvas, offset_ticks, *get_star_params(canvas_size))
        )
    coroutines.append(fill_orbit_with_garbage(canvas, canvas_size[1], garbage_frames))
    coroutines.append(
        animate_spaceship(
            canvas,
            rocket_frames,
            rocket_position,
            rocket_size,
            canvas_size,
            args.rocket_speed)
    )
    coroutines.append(show_obstacles(canvas, obstacles))
    coroutines.append(change_year())
    coroutines.append(draw_info_panel(canvas))
    while True:
        canvas.border()
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)
        canvas.refresh()
        time.sleep(TIC_TIMEOUT)
            

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Полетели!'
    )
    parser.add_argument(
        '--rocket_speed',
        help='Начальная страница',
        type=int,
        default=2,
    )
    parser.add_argument(
        '--stars_count',
        help='Начальная страница',
        type=int,
        default=100,
    )
    args = parser.parse_args()
    curses.update_lines_cols()
    curses.wrapper(draw, args)

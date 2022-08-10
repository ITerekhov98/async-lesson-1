import argparse
import asyncio
import time
import curses
import random

from itertools import cycle

from curses_tools import get_frame_size, draw_frame
from additional_functions import (
    read_controls,
    calculate_rocket_move,
    get_star_params,
    get_garbage_delay_tics,
    get_frames,
    TIC_TIMEOUT,
    PHRASES

)


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


def _is_point_inside(
        corner_row,
        corner_column,
        size_rows,
        size_columns,
        point_row,
        point_row_column):
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


async def explode(canvas, center_row, center_column, explosion_frames):
    rows, columns = get_frame_size(explosion_frames[0])
    corner_row = center_row - rows / 2
    corner_column = center_column - columns / 2

    curses.beep()
    for frame in explosion_frames:

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


async def sleep(ticks=1):
    for _ in range(ticks):
        await asyncio.sleep(0)


async def animate_spaceship(
        canvas,
        rocket_frames,
        rocket_position,
        rocket_size,
        canvas_size,
        rocket_speed,
        game_over_tag):

    row_speed = column_speed = 0
    for rocket in cycle(rocket_frames):
        rows_direction, columns_direction, space_pressed = read_controls(canvas)
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
        gun_position = (
            rocket_position[0],
            rocket_position[1] + (rocket_size[1] // 2)
        )

        if space_pressed:
            coroutines.append(fire(canvas, gun_position))
        await sleep(1)
        draw_frame(canvas, rocket_position, rocket, negative=True)
        for obstacle in obstacles:
            if obstacle.has_collision(*rocket_position):
                coroutines.append(
                    show_gameover(canvas, canvas_size, game_over_tag)
                )
                return


async def show_gameover(canvas, canvas_size, game_over_tag):
    row_center, column_center = (dim//2 for dim in canvas_size)
    row_size, column_size = get_frame_size(game_over_tag)
    row = row_center - row_size // 2
    column = column_center - column_size // 2
    while True:
        draw_frame(canvas, (row, column), game_over_tag)
        await sleep(1)


async def fly_garbage(canvas, column, garbage_frame, explosion_frames, speed=0.5):
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
            coroutines.append(explode(canvas, center_row, center_column, explosion_frames))
            return

        row += speed


async def fill_orbit_with_garbage(canvas, canvas_row_size, garbage_frames, explosion_frames):
    for garbage in cycle(garbage_frames):
        delay = get_garbage_delay_tics(year)
        if not delay:
            await sleep(1)
            continue

        frame_rows = garbage.split('\n')
        row_limit = canvas_row_size - max(len(row) for row in frame_rows)
        column = random.randint(1, row_limit)
        coroutines.append(fly_garbage(canvas, column, garbage, explosion_frames))
        await sleep(delay)


async def change_year():
    global year
    while True:
        await sleep(15)
        year += 1


async def draw_info_panel(canvas):
    current_year_info = ''
    year_area_position = (1, 2)
    year_area_size = (4, 6)
    year_info_position = (2, 9)
    while True:
        year_area = canvas.derwin(
            *year_area_size,
            *year_area_position
        )
        year_area.border()
        year_area.addstr(1, 1, 'YEAR')
        year_area.addstr(2, 1, str(year))
        if year in PHRASES.keys():
            current_year_info = PHRASES[year]
        year_info_area = canvas.derwin(
            *year_info_position
        )
        year_info_area.addstr(current_year_info)
        await sleep(1)


def draw(canvas, args):
    rocket_frames = get_frames('rocket')
    garbage_frames = get_frames('garbage')
    game_over_tag = get_frames('gameover')
    explosion_frames = get_frames('explosion')
    rocket_size = get_frame_size(rocket_frames[0])
    canvas_size = canvas.getmaxyx()
    canvas.border()
    canvas.nodelay(True)
    curses.curs_set(False)

    rocket_position = list(dimension//2 for dimension in canvas_size)
    global year
    year = 1957

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
    coroutines.append(
        fill_orbit_with_garbage(canvas, canvas_size[1], garbage_frames, explosion_frames)
    )
    coroutines.append(
        animate_spaceship(
            canvas,
            rocket_frames,
            rocket_position,
            rocket_size,
            canvas_size,
            args.rocket_speed,
            game_over_tag)
    )
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

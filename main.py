import os
import argparse
import asyncio
import time
import curses
import random

from itertools import cycle

from physics import update_speed


TIC_TIMEOUT = 0.1
SPACE_KEY_CODE = 32
LEFT_KEY_CODE = 260
RIGHT_KEY_CODE = 261
UP_KEY_CODE = 259
DOWN_KEY_CODE = 258
CANVAS_FRAME_THICKNESS = 2


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

    return rows_direction, columns_direction


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
        row += rows_speed
        column += columns_speed


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


def draw_frame(canvas, start_position, text, negative=False):
    """Draw multiline text fragment on canvas,
    erase text instead of drawing if negative=True is specified."""

    rows_number, columns_number = canvas.getmaxyx()
    start_row, start_column = start_position

    for row, line in enumerate(text.splitlines(), round(start_row)):
        if row < 0:
            continue

        if row >= rows_number:
            break

        for column, symbol in enumerate(line, round(start_column)):
            if column < 0:
                continue

            if column >= columns_number:
                break

            if symbol == ' ':
                continue

            # Check that current position it is not in a lower right corner of the window
            # Curses will raise exception in that case. Don`t ask why…
            # https://docs.python.org/3/library/curses.html#curses.window.addch
            if row == rows_number - 1 and column == columns_number - 1:
                continue

            symbol = symbol if not negative else ' '
            canvas.addch(row, column, symbol)


def get_frame_size(text):
    """Calculate size of multiline text fragment,
    return pair — number of rows and colums."""

    lines = text.splitlines()
    rows = len(lines)
    columns = max([len(line) for line in lines])
    return rows, columns


def clip_rocket_position(position, min_position, max_position):
    '''does not allow the rocket to take off outside the canvas'''
    return max(min(max_position, position), min_position)

def calculate_rocket_move(
        canvas,
        rocket_position,
        rocket_size,
        canvas_size,
        rocket_speed,
        row_speed,
        column_speed):

    rocket_rows_position, rocket_columns_position = rocket_position
    rocket_row_size, rocket_column_size = rocket_size
    rows_number, columns_number = canvas_size
    rows_direction, columns_direction = read_controls(canvas, rocket_speed)

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
        rocket_position, row_speed, column_speed = calculate_rocket_move(
            canvas,
            rocket_position,
            rocket_size,
            canvas_size,
            rocket_speed,
            row_speed,
            column_speed
        )
        draw_frame(canvas, rocket_position, rocket)
        await sleep(1)
        draw_frame(canvas, rocket_position, rocket, negative=True)


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0

    while row < rows_number:
        draw_frame(canvas, (row, column), garbage_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, (row, column), garbage_frame, negative=True)
        row += speed


async def fill_orbit_with_garbage(canvas, canvas_row_size):
    garbage_frames = get_garbage_frames()
    for garbage in cycle(garbage_frames):
        frame_rows = garbage.split('\n')
        row_limit = canvas_row_size - max(len(row) for row in frame_rows)
        column = random.randint(1, row_limit)
        coroutines.append(fly_garbage(canvas, column, garbage))
        await sleep(15)


def draw(canvas, args):
    rocket_frames = get_rocket_frames()
    
    rocket_size = get_frame_size(rocket_frames[0])
    canvas_size = canvas.getmaxyx()
    canvas.border()
    canvas.nodelay(True)
    curses.curs_set(False)

    rocket_position = list(dimension//2 for dimension in canvas_size)
    global coroutines
    coroutines = [fire(canvas, rocket_position, rows_speed=-1)]
    for star in range(args.stars_count):
        offset_ticks = random.randint(1, 10)
        coroutines.append(
            blink(canvas, offset_ticks, *get_star_params(canvas_size))
        )
    coroutines.append(fill_orbit_with_garbage(canvas, canvas_size[1]))
    coroutines.append(
        animate_spaceship(
            canvas,
            rocket_frames,
            rocket_position,
            rocket_size,
            canvas_size,
            args.rocket_speed)
    )
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

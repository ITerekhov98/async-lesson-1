import os
import argparse
import asyncio
import time
import curses
import random

from itertools import cycle


TIC_TIMEOUT = 0.1
SPACE_KEY_CODE = 32
LEFT_KEY_CODE = 260
RIGHT_KEY_CODE = 261
UP_KEY_CODE = 259
DOWN_KEY_CODE = 258
CANVAS_FRAME_THICKNESS = 1

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
            rows_direction = -rocket_speed

        if pressed_key_code == DOWN_KEY_CODE:
            rows_direction = rocket_speed

        if pressed_key_code == RIGHT_KEY_CODE:
            columns_direction = rocket_speed

        if pressed_key_code == LEFT_KEY_CODE:
            columns_direction = -rocket_speed

        if pressed_key_code == SPACE_KEY_CODE:
            space_pressed = True

    return rows_direction, columns_direction


async def fire(canvas, fire_position, rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot, direction and speed can be specified."""

    row, column = fire_position

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def blink(canvas, offset_tics, row, column, symbol='*'):
    for _ in range(offset_tics):
        await asyncio.sleep(0)
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        for _ in range(20):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for _ in range(3):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        for _ in range(5):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for _ in range(3):
            await asyncio.sleep(0)


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
    """Draw multiline text fragment on canvas, erase text instead of drawing if negative=True is specified."""

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
    """Calculate size of multiline text fragment, return pair — number of rows and colums."""

    lines = text.splitlines()
    rows = len(lines)
    columns = max([len(line) for line in lines])
    return rows, columns


def calculate_rocket_move(canvas, rocket_position, rocket_size, canvas_size, rocket_speed):
    rocket_rows_position, rocket_columns_position = rocket_position
    rocket_row_size, rocket_column_size = rocket_size
    rows_number, columns_number = canvas_size
    rows_direction, columns_direction = read_controls(canvas, rocket_speed)

    if columns_direction < 0:
        rocket_columns_position = max(
            0,
            rocket_columns_position + columns_direction
        )
    elif columns_direction > 0:
        rocket_columns_position = min(
            columns_number - rocket_column_size,
            rocket_columns_position + columns_direction
        )

    if rows_direction < 0:
        rocket_rows_position = max(
            0,
            rocket_rows_position + rows_direction
        )
    elif rows_direction > 0:
        rocket_rows_position = min(
            rows_number - rocket_row_size,
            rocket_rows_position + rows_direction
        )

    return rocket_rows_position, rocket_columns_position


def draw(canvas, args):
    rocket_frames = []
    for rocket in os.listdir('rocket'):
        with open(f'rocket/{rocket}', 'r') as f:
            rocket_frames.append(f.read())

    rocket_size = get_frame_size(rocket_frames[0])
    canvas_size = canvas.getmaxyx()
    canvas.border()
    canvas.nodelay(True)
    curses.curs_set(False)

    rocket_position = list(dimension//2 for dimension in canvas_size)
    offset_ticks = random.randint(1, 10)
    stars_coroutines = [
        blink(canvas, offset_ticks, *get_star_params(canvas_size)) for star in range(args.stars_count)
    ]
    fire_coroutine = fire(canvas, rocket_position, rows_speed=-1)
    while True:
        try:
            fire_coroutine.send(None)
            canvas.refresh()
            time.sleep(TIC_TIMEOUT)
        except StopIteration:
            break

    for rocket in cycle(rocket_frames):
        canvas.border()
        for coroutine in stars_coroutines.copy():
            coroutine.send(None)
            canvas.refresh()

        rocket_position = calculate_rocket_move(
            canvas,
            rocket_position,
            rocket_size,
            canvas_size,
            args.rocket_speed
        )
        draw_frame(canvas, rocket_position, rocket)
        canvas.refresh()
        time.sleep(TIC_TIMEOUT)
        draw_frame(canvas, rocket_position, rocket, negative=True)


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

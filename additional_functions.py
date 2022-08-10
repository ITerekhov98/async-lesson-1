import os
import math
import random

TIC_TIMEOUT = 0.1
SPACE_KEY_CODE = 32
LEFT_KEY_CODE = 260
RIGHT_KEY_CODE = 261
UP_KEY_CODE = 259
DOWN_KEY_CODE = 258
CANVAS_FRAME_THICKNESS = 2
PHRASES = {
    1957: "First Sputnik",
    1961: "Gagarin flew!",
    1969: "Armstrong got on the moon!",
    1971: "First orbital space station Salute-1",
    1981: "Flight of the Shuttle Columbia",
    1998: 'ISS start building',
    2011: 'Messenger launch to Mercury',
    2020: "Take the plasma gun! Shoot the garbage!",
}


def _limit(value, min_value, max_value):
    """Limit value by min_value and max_value."""

    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value


def _apply_acceleration(speed, speed_limit, forward=True):
    """Change speed — accelerate or brake — according to force direction."""

    speed_limit = abs(speed_limit)

    speed_fraction = speed / speed_limit

    # если корабль стоит на месте, дергаем резко
    # если корабль уже летит быстро, прибавляем медленно
    delta = math.cos(speed_fraction) * 0.75

    if forward:
        result_speed = speed + delta
    else:
        result_speed = speed - delta

    result_speed = _limit(result_speed, -speed_limit, speed_limit)

    # если скорость близка к нулю, то останавливаем корабль
    if abs(result_speed) < 0.1:
        result_speed = 0

    return result_speed


def update_speed(
        row_speed,
        column_speed,
        rows_direction,
        columns_direction,
        row_speed_limit=2,
        column_speed_limit=2,
        fading=0.8):
    """Update speed smootly to make control handy for player. Return new speed value (row_speed, column_speed)

    rows_direction — is a force direction by rows axis. Possible values:
       -1 — if force pulls up
       0  — if force has no effect
       1  — if force pulls down
    columns_direction — is a force direction by colums axis. Possible values:
       -1 — if force pulls left
       0  — if force has no effect
       1  — if force pulls right
    """

    if rows_direction not in (-1, 0, 1):
        raise ValueError(
            f'Wrong rows_direction value {rows_direction}. Expects -1, 0 or 1.'
        )

    if columns_direction not in (-1, 0, 1):
        raise ValueError(
            f'Wrong columns_direction value {columns_direction}. Expects -1, 0 or 1.'
        )

    if fading < 0 or fading > 1:
        raise ValueError(
            f'Wrong columns_direction value {fading}. Expects float between 0 and 1.'
        )

    # гасим скорость, чтобы корабль останавливался со временем
    row_speed *= fading
    column_speed *= fading

    row_speed_limit = abs(row_speed_limit)
    column_speed_limit = abs(column_speed_limit)

    if rows_direction != 0:
        row_speed = _apply_acceleration(
            row_speed,
            row_speed_limit,
            rows_direction > 0
        )

    if columns_direction != 0:
        column_speed = _apply_acceleration(
            column_speed,
            column_speed_limit,
            columns_direction > 0
        )
    return row_speed, column_speed


def get_frames(frame_type):
    if frame_type == 'gameover':
        with open('frames/gameover.txt', 'r') as f:
            tag = f.read()
        return tag

    frames = []
    for frame_name in os.listdir(f'frames/{frame_type}'):
        with open(f'frames/{frame_type}/{frame_name}', 'r') as f:
            frame = f.read()
            if frame_type == 'rocket':
                frames.extend((frame, frame))
            else:
                frames.append(frame)
    return frames


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

    row_speed, column_speed = update_speed(
        row_speed,
        column_speed,
        rows_direction,
        columns_direction
    )
    rocket_rows_position += row_speed
    rocket_columns_position += column_speed

    rocket_columns_position = clip_rocket_position(
        rocket_columns_position,
        0,
        (columns_number - rocket_column_size)
    )
    rocket_rows_position = clip_rocket_position(
        rocket_rows_position,
        0,
        (rows_number - rocket_row_size)
    )
    return (rocket_rows_position, rocket_columns_position), row_speed, column_speed


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


def read_controls(canvas):
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

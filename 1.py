import os

def get_rocket_frames():
    rocket_frames = []
    for rocket in os.listdir('rocket'):
        with open(f'rocket/{rocket}', 'r') as f:
            rocket = f.read()
            rocket_frames.extend((rocket, rocket))
    return rocket_frames

for i in get_rocket_frames():
    print(i)
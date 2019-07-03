import geojson
import geopy
import geopy.distance
import json
import numpy as np
import pandas as pd
import requests
import time
from tqdm import tqdm


secrets = json.load(open('secrets.json'))
CLIENT_ID = secrets['CLIENT_ID']
CLIENT_SECRET = secrets['CLIENT_SECRET']
VERSION = secrets['VERSION']

START = [55.755825, 37.617298]
# Box height and width in kilometers
HEIGHT = 5
WIDTH = 4
STEP = 1
RADIUS = 1500

GEOJSON_FILE = 'geojson.json'
DATA_FILE = 'data.csv'

IGNORED_CATEGORIES = ['Event']


def get_polygons(start, height, width, step):
    """Create list of square polygons from center covering height and width with step"""
    polygons = []
    polygons_start = start

    # start creating polygon points from northwest to southeast
    for i in np.arange(-height/2, height/2, step):
        # STEP south
        polygon_north = geopy.distance.distance(kilometers = i).destination(point=polygons_start, bearing=180)[0]
        polygon_south = geopy.distance.distance(kilometers = i + step).destination(point=polygons_start, bearing=180)[0]
        for k in np.arange(-width/2, width/2, step):
            # STEP east
            polygon_west = geopy.distance.distance(kilometers = k).destination(point=polygons_start, bearing=90)[1]
            polygon_east = geopy.distance.distance(kilometers = k + step).destination(point=polygons_start, bearing=90)[1]

            polygons.append([[polygon_north, polygon_west],
                             [polygon_north, polygon_east],
                             [polygon_south, polygon_east],
                             [polygon_south, polygon_west]])
    return polygons


def get_square_center(square):
    return [(square[0][0]+square[2][0])/2,(square[0][1] + square[2][1])/2]


def polygon_to_feature(idx, polygon):
    """Create geojson Feature from polygon"""
    return {
        'type': 'Feature',
        'geometry': {
            'type': 'Polygon',
            'coordinates': [[[lon,lat] for [lat, lon] in polygon]]
        },
        'properties': {
            'name': f'Square {str(idx)}'
        }
    }


def get_venues_count(ll, radius, categoryId = ''):
    explore_url = 'https://api.foursquare.com/v2/venues/explore?' \
                  'client_id={}&client_secret={}&v={}&ll={}&radius={}&categoryId={}'\
        .format(
            CLIENT_ID,
            CLIENT_SECRET,
            VERSION,
            '{},{}'.format(ll[0],ll[1]),
            radius,
            categoryId)

    success = False
    while not success:
        # make the GET request
        res = requests.get(explore_url)

        # request status code can sometimes be 403, then wait and retry
        if res.status_code != 200:
            time.sleep(10)
        else:
            success = True
            # Foursquare limits requests to 5000 per hour and returns remaining count in X-RateLimit-Remaining header
            remaining = int(res.headers['X-RateLimit-Remaining'])
            # sometimes X-RateLimit-Remaining is 0 and X-RateLimit-Reset is not returned, just retry
            if remaining == 0:
                time.sleep(10)
                continue
            # X-RateLimit-Reset is the time when the limit will be reset
            reset_time = int(res.headers['X-RateLimit-Reset'])
            # If too few requests remaining, wait to refresh limit
            if remaining < 10:
                while time.time() < reset_time:
                    time.sleep(10)

    return res.json()['response']['totalResults']


# Create list of polygons
polygons = get_polygons(START, HEIGHT, WIDTH, STEP)

# Create geojson
squares_geojson = geojson.FeatureCollection([polygon_to_feature(i, poly) for i, poly in enumerate(polygons)])

# Save geojson to output file
with open(GEOJSON_FILE, 'w') as outfile:
    json.dump(squares_geojson, outfile, indent=4)

# Create dataframe of squares
squares_df = pd.DataFrame(columns=['Name','Polygon','Center'])
# Fill dataframe
for i, polygon in enumerate(polygons):
    squares_df = squares_df.append({
        'Name': f'Square {i}',
        'Polygon': polygon,
        'Center': get_square_center(polygon)
    }, ignore_index=True)

# Get list of categories
categories_url = 'https://api.foursquare.com/v2/venues/categories?client_id={}&client_secret={}&v={}'\
    .format(
        CLIENT_ID,
        CLIENT_SECRET,
        VERSION)

categories = requests.get(categories_url).json()['response']['categories']
# drop ignored categories
for category in IGNORED_CATEGORIES:
    categories = list(filter(lambda x: x['name'] != category, categories))
# add dummy category with blank ID to get all venue categories
dummy_category = {
    'name': 'Venues',
    'id': ''
}
categories.insert(0, dummy_category)


for category in categories:
    category_name = category['name']
    category_id = category['id']
    print(f'Category {category_name} ({category_id})')

    # Initialize column for category
    squares_df[category_name] = 0

    # Request number of venues, store result as CSV
    for i, row in tqdm(squares_df.iterrows(), total=squares_df.shape[0]):
        count = get_venues_count(squares_df.Center.iloc[i], radius=RADIUS, categoryId=category_id)
        squares_df.loc[i, category_name] = count

    squares_df.to_csv(DATA_FILE)
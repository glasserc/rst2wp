import os.path
from xdg import BaseDirectory

def posts_location():
    return os.path.join(BaseDirectory.save_config_path('rst2wp', 'published'),
                        'posts')

def images_location():
    return os.path.join(BaseDirectory.save_config_path('rst2wp', 'published'),
                        'images')

POSTS_LOCATION = posts_location
IMAGES_LOCATION = images_location

TEMP_DIRECTORY = '/tmp'
TEMP_FILES = []

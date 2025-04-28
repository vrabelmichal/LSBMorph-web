import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# class Config:
#     SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key')  # Change for production!
#     SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'lsbmorph.db')
#     SQLALCHEMY_TRACK_MODIFICATIONS = False


import os
from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Secret key - Replace with a real secret key in production
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-for-development')

# Database configuration
SQLALCHEMY_DATABASE_URI = os.environ.get(
    'DATABASE_URL', 
    f'sqlite:///{os.path.join(BASE_DIR, "lsbmorph.db")}'
)
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Directory settings
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static/uploads')
GALAXY_IMAGES_FOLDER = os.path.join(BASE_DIR, 'static/galaxy_images')
HELP_IMAGES_FOLDER = os.path.join(BASE_DIR, 'static/images/tips')
CONNECTION_IMAGES_FOLDER = os.path.join(BASE_DIR, 'static/images/connection')
EXAMPLES_IMAGES_FOLDER = os.path.join(BASE_DIR, 'static/images/examples')

# Ensure all required directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GALAXY_IMAGES_FOLDER, exist_ok=True)
os.makedirs(HELP_IMAGES_FOLDER, exist_ok=True)
os.makedirs(CONNECTION_IMAGES_FOLDER, exist_ok=True)
os.makedirs(EXAMPLES_IMAGES_FOLDER, exist_ok=True)

# Image processing settings
FITS_PERCENTILE_LIMITS = {
    'lower': 0,
    'upper': 99.5,
}

# Classification settings
LSB_CLASS_OPTIONS = {
    -1: 'Failed fitting',
    0: 'Non-LSB',
    1: 'LSB'
}

MORPHOLOGY_OPTIONS = {
    -1: 'Featureless',
    0: 'Not sure (Irr/other)',
    1: 'LTG (Sp)',
    2: 'ETG (Ell)'
}

# Base directory for galaxy data 
DATA_BASE_DIR = os.environ.get('LSBMORPH_DATA_DIR', '/media/vrabel/DATA_KIN4TB/lsb-kids')

# Ensure these subdirectories match your data structure
DATA_SUBDIRS = {
    'aplpy_images': 'color_images/aplpy',
    'lupton_images': 'color_images/Lupton_RGB_Images',
    'masks': 'masks_r',
    'cutouts': 'Cutouts_r',
    'imgblocks': 'r_imgblocks'
}

# Default display settings
DEFAULT_COLORS = ['viridis', 'red', 'black']  # [cmap, ellipse_color, redshift_marker]

VMAX_PERCENTILE = 99.0
VMAX_PERCENTILE_RAW = 99.7

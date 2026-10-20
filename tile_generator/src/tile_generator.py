"""
Tile generator for creating tile sets for OSRS maps to be used with map viewers such as leaflet.
"""

import glob
import json
import logging
import math
import os
import re
import shutil
import subprocess
import zipfile
from datetime import datetime
from enum import Enum
from multiprocessing import Pool
from pathlib import Path

from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed, thread
import concurrent.futures
import numpy as np
import pyvips
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw
from skimage.metrics import structural_similarity

CACHES_BASE_URL = "https://archive.openrs2.org"
CACHE_ID = 2746
CACHE_URL = f"{CACHES_BASE_URL}/caches/runescape/{CACHE_ID}/disk.zip"
XTEA_URL = f"{CACHES_BASE_URL}/caches/runescape/{CACHE_ID}/keys.json"

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

Image.MAX_IMAGE_PIXELS = 1000000000000000

TILE_SIZE_PX = 256

MIN_ZOOM = 3
MAX_ZOOM = 11

MIN_Z = 0
MAX_Z = 3

REPO_DIR = '/repo' # Name of the directory mounted on the local machine
ROOT_CACHE_DIR = os.path.join(REPO_DIR, 'cache/')
GENERATED_FULL_IMAGES = os.path.join(REPO_DIR, 'generated_images/')
TILE_DIR = REPO_DIR

image_prefix = "full_image_"

logging.basicConfig(
    format='%(asctime)s %(levelname)-4s %(message)s',
    level=logging.WARNING,
    datefmt='%Y-%m-%d %H:%M:%S'
)

DEFAULT_TILE_IMAGE = (
    pyvips.Image.black(TILE_SIZE_PX, TILE_SIZE_PX, bands=4)
    .draw_rect([0, 0, 0, 0], 0, 0, TILE_SIZE_PX, TILE_SIZE_PX, fill=True)
)

class Side(Enum):
    TOP_LEFT = 1
    TOP_RIGHT = 2
    BOTTOM_LEFT = 3
    BOTTOM_RIGHT = 4


def main():
    LOG.info("Downloading cache & XTEAs")
    [cache_dir, xtea_file] = download_cache_with_xteas()

    LOG.info("Building map base images")
    build_full_map_images(cache_dir, xtea_file)

    LOG.info("Generating tiles")
    for plane in range(MAX_Z + 1):
        generate_tiles_for_plane(plane)

    for plane in range(MIN_Z, MAX_Z + 1):
        previous_map_image_name = os.path.join(GENERATED_FULL_IMAGES, f"previous-map-image-{plane}.png")
        current_map_image_name = os.path.join(GENERATED_FULL_IMAGES, f"current-map-image-{plane}.png")
        generated_file_name = os.path.join(GENERATED_FULL_IMAGES, f"new-map-image-{plane}.png")

        if os.path.isfile(current_map_image_name):
            os.replace(current_map_image_name, previous_map_image_name)
        os.replace(generated_file_name, current_map_image_name)
       

def download_cache_with_xteas():
    """Download the fixed OpenRS2 cache and its XTEA keys."""
    cache_dir = os.path.join(ROOT_CACHE_DIR, str(CACHE_ID))
    xtea_file = os.path.join(cache_dir, "xteas.json")

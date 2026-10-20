    is_bottom = original_y % 2 == 0

    if is_left:
        side = Side.BOTTOM_LEFT if is_bottom else Side.TOP_LEFT
    else:
        side = Side.BOTTOM_RIGHT if is_bottom else Side.TOP_RIGHT

    if side == Side.TOP_LEFT:
        tiles = [
            load_generated_tile(plane, current_zoom, original_x, original_y),
            load_generated_tile(plane, current_zoom, original_x + 1, original_y),
            load_generated_tile(plane, current_zoom, original_x, original_y - 1),
            load_generated_tile(plane, current_zoom, original_x + 1, original_y - 1)
        ]
    elif side == Side.TOP_RIGHT:
        tiles = [
            load_generated_tile(plane, current_zoom, original_x - 1, original_y),
            load_generated_tile(plane, current_zoom, original_x, original_y),
            load_generated_tile(plane, current_zoom, original_x - 1, original_y - 1),
            load_generated_tile(plane, current_zoom, original_x, original_y - 1)
        ]
    elif side == Side.BOTTOM_LEFT:
        tiles = [
            load_generated_tile(plane, current_zoom, original_x, original_y + 1),
            load_generated_tile(plane, current_zoom, original_x + 1, original_y + 1),
            load_generated_tile(plane, current_zoom, original_x, original_y),
            load_generated_tile(plane, current_zoom, original_x + 1, original_y)
        ]
    else:
        tiles = [
            load_generated_tile(plane, current_zoom, original_x - 1, original_y + 1),
            load_generated_tile(plane, current_zoom, original_x, original_y + 1),
            load_generated_tile(plane, current_zoom, original_x - 1, original_y),
            load_generated_tile(plane, current_zoom, original_x, original_y)
        ]

    new_tile_image = pyvips.Image.arrayjoin(tiles, across=2)

    new_tile_image_resized = new_tile_image.resize(0.5, kernel='lanczos3')

    new_x = math.floor(original_x / 2)
    new_y = math.floor(original_y / 2)

    save_tile(new_tile_image_resized, plane, new_zoom, new_x, new_y)

    return {
        "x": new_x,
        "y": new_y,
        "image": new_tile_image_resized
    }

def save_tile(tile_image, plane, zoom, x, y):
    file_dir = Path(TILE_DIR, str(plane), str(zoom), str(x))

    file_dir.mkdir(parents=True, exist_ok=True)

    file_path = Path(file_dir, str(y) + ".png")

    tile_image.pngsave(str(file_path), compression=9)


def load_generated_tile(plane, zoom, x, y):
    """
        Loads a tile image from the tile set stored in the repo
    """
    if not generated_tile_exists(plane, zoom, x, y):
        return DEFAULT_TILE_IMAGE

    file_path = generated_tile_path(plane, zoom, x, y)

    image = pyvips.Image.new_from_file(str(file_path), access="sequential")

    if not image.hasalpha():
        image = image.addalpha()

    return image


def generated_tile_exists(plane, zoom, x, y):
    return os.path.isfile(generated_tile_path(plane, zoom, x, y))


def generated_tile_path(plane, zoom, x, y):
    return Path(TILE_DIR, str(plane), str(zoom), str(x), str(y) + ".png")


def output_tile_diff_image(changed_tiles, new_image_location, output_file_name):
    diff_image = im = Image.open(new_image_location)

    draw = ImageDraw.Draw(im)

    for tile in changed_tiles:
        shape = [(tile["pixel_x"], tile["pixel_y"]), (tile["pixel_x"] + TILE_SIZE_PX, tile["pixel_y"] + TILE_SIZE_PX)]
        draw.rectangle(shape, fill=None, outline="red", width=3)

    diff_image.save(output_file_name)


@contextmanager
def thread_pool_executor():
    with ThreadPoolExecutor() as executor:
        try:
            yield executor
        except KeyboardInterrupt:
            LOG.warning("Performing non-graceful shutdown of threads")
            executor._threads.clear()
            concurrent.futures.thread._threads_queues.clear()


if __name__ == '__main__':
    main()

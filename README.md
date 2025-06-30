# Drastic View

Drastic View is a small Python application that showcases your Plex media library.
It cycles through recently added items or whatever is currently being played and 
shows their posters and details in a Pygame window. Optionally a clock can be
shown between rotations.

## Requirements

Install the dependencies from `requirements.txt` using pip:

```bash
pip install -r requirements.txt
```

The application uses Pygame and the Plex API, so it needs access to a running Plex
server.

## Configuration

1. Copy `config - Sample.json` to `config.json`.
2. Edit `config.json` and fill in your Plex server URL and token.
3. Adjust the other settings:
   - `DISPLAY_TIME` – seconds to display each item
   - `NUM_RECENT_ITEMS` – how many recently added shows or movies to rotate
   - `TIME_FORMAT` – strftime format for the clock
   - `SHOW_CLOCK` – set to `1` to show the clock, `0` to disable

## Usage

Run the application from the command line:

```bash
python Drastic_Display_Final.py
```

When running on Windows, the script attempts to bring its window to the front
using the Windows API.

## License

This project is provided as‑is under the MIT license.

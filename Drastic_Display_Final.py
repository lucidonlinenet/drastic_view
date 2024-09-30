import pygame
import requests
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer
import time
import io
import json
from PIL import Image
from datetime import datetime, timedelta
import pygetwindow as gw
import os
import ctypes

# Load Windows API functions from user32.dll
user32 = ctypes.WinDLL('user32', use_last_error=True)

# Load config from config.json
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

config = load_config()

# Plex API Configuration from config.json
PLEX_URL = config['PLEX_URL']
PLEX_TOKEN = config['PLEX_TOKEN']

# Plex API Setup
plex = PlexServer(PLEX_URL, PLEX_TOKEN)

# Pygame Setup
pygame.init()
screen = pygame.display.set_mode((800, 480))
pygame.display.set_caption("Plex Now Playing")
clock = pygame.time.Clock()

# Font setup
font = pygame.font.SysFont('Arial', 25)
title_font = pygame.font.SysFont('Arial', 30, bold=True)

# Time to display each screen in seconds
DISPLAY_TIME = config['DISPLAY_TIME']  # Load from config

def get_currently_playing():
    """
    Fetches currently playing media on Plex.
    Returns a list of currently playing items, with relevant metadata, including fanart, direct play/transcoding status, and estimated end time.
    """
    now_playing = []
    for session in plex.sessions():
        # Initialize poster and fanart URLs based on whether it's a movie or TV show
        if session.type == 'episode':
            fanart_url = session.grandparentArt or session.parentArt or session.artUrl
            poster_url = session.grandparentThumb or session.thumb
            description = session.grandparentTitle + ": " + session.summary
        else:
            fanart_url = session.artUrl or session.thumbUrl
            poster_url = session.thumbUrl
            description = session.summary

        # Calculate estimated end time
        current_position = session.viewOffset / 1000  # Convert milliseconds to seconds
        duration = session.duration / 1000  # Convert milliseconds to seconds
        time_remaining = duration - current_position
        estimated_end_time = datetime.now() + timedelta(seconds=time_remaining)
        estimated_end_time_str = estimated_end_time.strftime('%H:%M:%S')

        # Fetch user data
        if hasattr(session, 'usernames') and session.usernames:
            user = session.usernames[0]  # Get the first username from the list
        else:
            user = 'Unknown User'  # Fallback in case no username is available

        # Determine if the session is transcoding or direct play
        play_status = 'Transcoding' if session.transcodeSessions else 'Direct Play'

        # Transcode the fanart and poster images
        transcode_fanart_url = plex.transcodeImage(fanart_url, height=480, width=800)
        transcode_poster_url = plex.transcodeImage(poster_url, height=300, width=200)

        now_playing.append({
            'title': session.title,
            'user': user,  # User who is playing the media
            'transcode': play_status,  # Play status: Transcoding or Direct Play
            'poster_url': transcode_poster_url,
            'fanart_url': transcode_fanart_url,
            'description': description,
            'end_time': estimated_end_time_str
        })

    print(f"Currently playing items with users and play status: {now_playing}")  # Debug log
    return now_playing


def get_last_added():
    """
    Fetches the last X movies or TV shows added to Plex, where X is from the config.
    Returns relevant metadata, ensuring we get the show or movie description, and background fanart. 
    """
    recently_added = []
    num_items = config['NUM_RECENT_ITEMS']  # Load number of items to display from config

    for item in plex.library.recentlyAdded()[:num_items]:
        # Print diagnostic information about the item
        print(f"Item Type: {item.type}")
        print(f"Title: {item.title}")

        # Fetch the poster and background fanart URL
        poster_url = item.thumbUrl
        fanart_url = item.artUrl  # For movies, we'll use this by default

        # Initialize title and description
        if item.type == 'season' or item.type == 'show':
            try:
                # Fetch the parent show metadata using parentRatingKey for the season or show
                show = plex.fetchItem(item.parentRatingKey if item.type == 'season' else item.ratingKey)
                title = show.title  # The show title
                description = show.summary  # The show description
                fanart_url = show.artUrl  # Fetch the show's fanart

                # Fetch the number of seasons and episodes
                num_seasons = len(show.seasons())
                num_episodes = sum(len(season.episodes()) for season in show.seasons())

                print(f"Fetched Show Title: {title}")
                print(f"Fetched Show Summary: {description}")
                print(f"Fetched Show Fanart URL: {fanart_url}")
                print(f"Seasons: {num_seasons}, Episodes: {num_episodes}")

            except Exception as e:
                print(f"Error fetching show metadata: {e}")
                title = item.title  # Fallback to the season title if show data cannot be fetched
                description = "Description not available"  # Fallback description
                num_seasons = 0
                num_episodes = 0

            # Include the seasons and episodes in the media item
            recently_added.append({
                'title': title,
                'poster_url': poster_url,
                'fanart_url': fanart_url,
                'description': description,
                'seasons': num_seasons,
                'episodes': num_episodes,
                'type': 'show',  # Mark this as a show for display_info
            })

        elif item.type == 'movie':
            # For movies, use the normal title and description
            title = item.title  # Movie title
            description = item.summary  # Movie description
            num_seasons = None  # No seasons for movies
            num_episodes = None  # No episodes for movies
            # Fanart URL for movies will be used as is (from artUrl)

            # Append the movie item
            recently_added.append({
                'title': title,
                'poster_url': poster_url,
                'fanart_url': fanart_url,
                'description': description,
                'type': 'movie'  # Mark this as a movie for display_info
            })

    return recently_added



def fetch_poster(url):
    """
    Fetches the poster image from a given URL.
    Returns a Pygame image surface.
    """
    response = requests.get(url, headers={'X-Plex-Token': PLEX_TOKEN})
    if response.status_code == 200:
        image_data = response.content
        image = Image.open(io.BytesIO(image_data))
        return pygame.image.fromstring(image.tobytes(), image.size, image.mode)
    return None


def display_info(media_item):
    """
    Display information about a media item on the screen, including fanart as the background.
    If the item is currently playing, display user and play status (Transcoding or Direct Play).
    Also, display season and episode count for TV shows.
    """
    screen.fill((0, 0, 0))  # Clear screen

    # Fetch fanart image for background
    fanart = fetch_poster(media_item['fanart_url'])  # Reuse fetch_poster to load fanart
    if fanart:
        fanart = pygame.transform.scale(fanart, (800, 480))  # Scale fanart to fill the screen
        screen.blit(fanart, (0, 0))  # Display the fanart as the background
    else:
        screen.fill((0, 0, 0))  # Fill the screen with a black background if fanart cannot be loaded

    # Draw a semi-transparent black rectangle overlay for readability
    overlay = pygame.Surface((800, 480))  # Create an overlay surface
    overlay.set_alpha(128)  # Set transparency (0 = fully transparent, 255 = fully opaque)
    overlay.fill((0, 0, 0))  # Fill overlay with black color
    screen.blit(overlay, (0, 0))  # Draw overlay on top of the fanart or fallback background

    # Fetch poster image
    poster = fetch_poster(media_item['poster_url'])
    if poster:
        poster = pygame.transform.scale(poster, (200, 300))  # Scale the poster
        screen.blit(poster, (50, 90))  # Position the poster on the screen

    # Display title text with shadow for better readability
    shadow_offset = 2  # Offset for shadow effect

    title_text = title_font.render(media_item['title'], True, (255, 255, 255))
    title_shadow = title_font.render(media_item['title'], True, (0, 0, 0))  # Black shadow
    screen.blit(title_shadow, (300 + shadow_offset, 90 + shadow_offset))  # Position shadow
    screen.blit(title_text, (300, 90))  # Position the title text

    # Ensure the description is not None
    description = media_item.get('description', "No description available") or "No description available"

    # Wrap and display description text
    description_lines = wrap_text(description, font, 500)
    description_lines = description_lines[:5]  # Limit to first 5 lines

    y_position = 140
    for line in description_lines:
        description_text = font.render(line, True, (255, 255, 255))
        screen.blit(description_text, (300, y_position))
        y_position += 30

    # Display season and episode count if it's a TV show or season
    if media_item.get('type') in ['show', 'season']:
        # Display the number of Seasons and Episodes
        seasons_text = font.render(f"Seasons: {media_item.get('seasons', 'Unknown')}", True, (255, 255, 255))
        episodes_text = font.render(f"Episodes: {media_item.get('episodes', 'Unknown')}", True, (255, 255, 255))

        screen.blit(seasons_text, (300, y_position + 20))  # Position the seasons text
        screen.blit(episodes_text, (300, y_position + 50))  # Position the episodes text

        y_position += 80  # Adjust the position for the next elements

    # Check if this media item is from the currently playing list
    if 'user' in media_item and 'transcode' in media_item:
        # Display user and play status (Transcoding or Direct Play) only if currently playing
        user_text = font.render(f"User: {media_item.get('user', 'Unknown User')}", True, (255, 255, 255))
        transcode_text = font.render(f"Status: {media_item.get('transcode', 'Error')}", True, (255, 255, 255))

        screen.blit(user_text, (300, y_position + 20))  # Position the user text
        screen.blit(transcode_text, (300, y_position + 50))  # Position the play status text

    pygame.display.update()




def wrap_text(text, font, max_width):
    """
    A helper function to wrap text into multiple lines to fit within the specified max_width.
    """
    if not text:
        return []  # Return empty list if text is None or empty
    
    words = text.split(' ')
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + word + " "
        if font.size(test_line)[0] < max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word + " "

    if current_line:
        lines.append(current_line)

    return lines


def display_time_and_info():
    """
    Displays the current time centered in large font and additional smaller information
    (number of movies, TV shows, and currently playing items) at the bottom.
    """
    # Get the current time using the format from config.json
    current_time = datetime.now().strftime(config['TIME_FORMAT'])
    
    # Use a larger font for the time
    large_font = pygame.font.SysFont('Arial', 80)
    time_text = large_font.render(current_time, True, (255, 255, 255))
    
    # Calculate the centered position for the time
    text_rect = time_text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
    
    # Get the total number of movies and TV shows
    movies_section = plex.library.section('Movies')
    tv_shows_section = plex.library.section('TV Shows')
    
    num_movies = len(movies_section.all())
    num_tv_shows = len(tv_shows_section.all())
    
    # Get the number of currently playing items
    num_currently_playing = len(get_currently_playing())
    
    # Log the information being displayed
    print(f"Current time: {current_time}")
    print(f"Total Movies: {num_movies}, Total TV Shows: {num_tv_shows}, Currently Playing: {num_currently_playing}")
    
    # Render the smaller info text
    movies_text = font.render(f"Total Movies: {num_movies}", True, (255, 255, 255))
    tv_shows_text = font.render(f"Total TV Shows: {num_tv_shows}", True, (255, 255, 255))
    currently_playing_text = font.render(f"Currently Playing: {num_currently_playing}", True, (255, 255, 255))
    
    # Clear the screen before displaying
    screen.fill((0, 0, 0))

    # Display the centered time
    screen.blit(time_text, text_rect)

    # Positioning for the smaller texts at the bottom of the screen
    screen.blit(movies_text, (50, 400))
    screen.blit(tv_shows_text, (300, 400))
    screen.blit(currently_playing_text, (550, 400))
    
    # Update the Pygame display
    pygame.display.update()

# Function to bring window to the front using Windows API
def bring_window_to_front():
    """
    Bring the Pygame window to the front using the Windows API.
    """
    # Get all windows with the title 'Plex Now Playing'
    windows = gw.getWindowsWithTitle('Plex Now Playing')
    
    if windows:
        win = windows[0]  # Get the first matching window

        if win.isMinimized:
            win.restore()  # Restore the window if minimized

        # Get the window handle (HWND)
        hwnd = user32.FindWindowW(None, "Plex Now Playing")
        
        if hwnd:
            # Bring the window to the front using SetForegroundWindow
            user32.SetForegroundWindow(hwnd)
            print("Window brought to the front using Windows API.")
        else:
            print("Failed to find window handle (HWND).")
    else:
        print("No window found with the title 'Plex Now Playing'.")

def main_loop():
    """
    Main application loop. Fetches current playing or last added media and rotates through them.
    Allows exiting the full-screen mode with a key press (e.g., Esc key).
    """
    running = True
    while running:
        bring_window_to_front()  # Bring the window to the front if minimized or in the background

        now_playing = get_currently_playing()
        media_to_display = now_playing if now_playing else get_last_added()

        # Iterate through media items (either currently playing or recently added)
        for media_item in media_to_display:
            display_info(media_item)
            time.sleep(DISPLAY_TIME)

            # Check for events (including key presses)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False  # Exit loop on window close
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False  # Exit loop on Esc key press

        # After displaying all media items, show the centered time and smaller additional info together
        display_time_and_info()  # Display large centered time and smaller additional info simultaneously
        time.sleep(DISPLAY_TIME)  # Keep this info on screen for the defined time

    pygame.quit()  # Clean up and close the window when exiting


if __name__ == "__main__":
    main_loop()

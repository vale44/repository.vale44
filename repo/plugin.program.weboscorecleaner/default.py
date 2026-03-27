import os
import xbmc
import xbmcaddon
import xbmcvfs
import shutil
import threading
import time
import xbmcgui
import sys
import re
from collections import deque

ADDON = xbmcaddon.Addon(id='plugin.program.weboscorecleanar')
ADDON_PATH = ADDON.getAddonInfo('path')
sys.path.append(ADDON_PATH)

# WebOS Kodi core files path
WEBOS_CORE_PATH = "/media/developer/apps/usr/palm/applications/org.xbmc.kodi"

LOG_HISTORY = deque(maxlen=10)  # Keep track of the last 10 messages

def log_message(message):
    xbmc.log(f"[COLOR orange]WebOS Core Cleaner[/COLOR]: {message}", xbmc.LOGINFO)
    LOG_HISTORY.append(message)

def path_exists(path):
    """Check if a path exists."""
    try:
        return os.path.exists(path)
    except Exception as e:
        log_message(f"Error checking path: {path} - {str(e)}")
        return False

def get_core_files(path):
    """
    Get all core.NUMBERS files in the specified path (not in subfolders).
    Returns a list of tuples (filename, full_path).
    Pattern: core.1234, core.5678, etc.
    """
    core_files = []
    
    if not path_exists(path):
        log_message(f"[COLOR red]WebOS Kodi path does not exist: {path}[/COLOR]")
        return core_files
    
    try:
        items = os.listdir(path)
        for item in items:
            # Check if file matches pattern: core.NUMBERS (core followed by dot and digits)
            if re.match(r'^core\.\d+$', item):
                full_path = os.path.join(path, item)
                # Make sure it's a file, not a directory
                if os.path.isfile(full_path):
                    core_files.append((item, full_path))
    except Exception as e:
        log_message(f"Error listing files in {path}: {str(e)}")
    
    return core_files

def get_file_size(path):
    """Get size of a single file in bytes."""
    try:
        return os.path.getsize(path)
    except Exception as e:
        log_message(f"Failed to get size of file: {path} - {str(e)}")
        return 0

def convert_size(size_bytes):
    """Convert size in bytes to MB."""
    return size_bytes / (1024 * 1024)

def get_total_core_size(core_files):
    """Calculate total size of all core files."""
    total_size = 0
    for filename, filepath in core_files:
        total_size += get_file_size(filepath)
    return total_size

def delete_core_files(core_files):
    """Delete all core files and return count and size."""
    deleted_count = 0
    deleted_size = 0
    
    for filename, filepath in core_files:
        try:
            file_size = get_file_size(filepath)
            os.remove(filepath)
            deleted_count += 1
            deleted_size += file_size
            log_message(f"[COLOR orange]Deleted:[/COLOR] {filename} ({convert_size(file_size):.2f} MB)")
        except Exception as e:
            log_message(f"[COLOR red]Failed to delete file:[/COLOR] {filename} - {str(e)}")
    
    return deleted_count, deleted_size

def check_and_clean():
    log_message("Starting WebOS core files check")
    
    # Check if the feature is enabled
    if not ADDON.getSettingBool('enable_core_cleaning'):
        log_message("[COLOR yellow]WebOS Core Cleaner is disabled[/COLOR]")
        return
    
    # Check if the WebOS Kodi path exists
    if not path_exists(WEBOS_CORE_PATH):
        log_message(f"[COLOR yellow]WebOS Kodi path not found: {WEBOS_CORE_PATH}[/COLOR]")
        log_message("[COLOR yellow]This addon is designed for WebOS Kodi installations[/COLOR]")
        return
    
    # Get all core files
    core_files = get_core_files(WEBOS_CORE_PATH)
    
    if not core_files:
        log_message("[COLOR green]No core files found - system is clean![/COLOR]")
        interval = int(ADDON.getSetting('check_interval'))
        log_message(f"[COLOR orange]Next check in {interval} minutes[/COLOR]")
        return
    
    # Calculate total size of core files
    total_size = get_total_core_size(core_files)
    
    log_message(f"[COLOR orange]Found {len(core_files)} core file(s)[/COLOR]")
    log_message(f"[COLOR orange]Total size:[/COLOR] {convert_size(total_size):.2f} MB")
    
    # Delete the core files
    deleted_count, deleted_size = delete_core_files(core_files)
    
    if deleted_count > 0:
        file_word = "file" if deleted_count == 1 else "files"
        message = f"Cleaned {deleted_count} {file_word} ({convert_size(deleted_size):.2f} MB)"
        log_message(f"[COLOR green]SUCCESS:[/COLOR] {message}")
        send_notification("Core Files Cleaned", message)
    
    # Log next check time
    interval = int(ADDON.getSetting('check_interval'))
    log_message(f"[COLOR orange]Next check in {interval} minutes[/COLOR]")

def periodic_check():
    interval = int(ADDON.getSetting('check_interval')) * 60
    while not xbmc.Monitor().abortRequested():
        check_and_clean()
        xbmc.sleep(interval * 1000)

def get_notification_sound():
    return ", special://xbmc/media/sounds/success.wav" if ADDON.getSettingBool('notification_sound') else ""

def send_notification(title, message):
    if ADDON.getSettingBool('show_notifications'):
        notification_sound = get_notification_sound()
        xbmc.executebuiltin(f'Notification(WebOS Core Cleaner - {title}, {message}, 6000{notification_sound})')

if __name__ == '__main__':
    log_message("WebOS Core Cleaner script started")
    if ADDON.getSetting('run_on_startup') == 'true':
        log_message("Running check_and_clean on startup")
        check_and_clean()
    if ADDON.getSetting('run_periodically') == 'true':
        if not threading.active_count() > 1:
            log_message("Starting periodic check thread")
            threading.Thread(target=periodic_check).start()
        else:
            log_message("[COLOR orange]Periodic check thread already running[/COLOR]")
    else:
        log_message("Running check_and_clean once as periodic checks are disabled")
        check_and_clean()
    interval = int(ADDON.getSetting('check_interval'))
    log_message(f"[COLOR orange]Service setup completed. Next check in {interval} minutes[/COLOR]")
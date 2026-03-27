import os
import xbmc
import xbmcaddon
import xbmcvfs
import shutil
import threading
import time
import xbmcgui
import sys
from collections import deque

ADDON = xbmcaddon.Addon(id='plugin.program.autocleaner')
ADDON_PATH = ADDON.getAddonInfo('path')
sys.path.append(ADDON_PATH)

THUMBNAILS_PATH = xbmcvfs.translatePath("special://userdata/Thumbnails")
CACHE_PATHS = [xbmcvfs.translatePath("special://home/cache")]
PACKAGES_PATH = xbmcvfs.translatePath("special://home/addons/packages")
DATABASE_PATH = xbmcvfs.translatePath("special://userdata/Database/Textures13.db")
ADDON_DATA_PATH = xbmcvfs.translatePath("special://userdata/addon_data")

CACHE_SUBFOLDERS = ['cache', 'htmlcache', 'temp']
LOG_HISTORY = deque(maxlen=10)  # Keep track of the last 10 messages

def log_message(message):
    xbmc.log(f"[COLOR lightgreen]Auto Cleaner[/COLOR]: {message}", xbmc.LOGINFO)
    LOG_HISTORY.append(message)

def get_size(path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)
    return total_size

def convert_size(size_bytes):
    """Convert size in bytes to MB."""
    return size_bytes / (1024 * 1024)

def get_total_cache_size(paths):
    total_size = 0
    for path in paths:
        if os.path.exists(path):
            total_size += get_size(path)
    return total_size

def get_addon_cache_size():
    total_size = 0
    for root, dirs, files in os.walk(ADDON_DATA_PATH):
        for dir_name in CACHE_SUBFOLDERS:
            dir_path = os.path.join(root, dir_name)
            if os.path.exists(dir_path):
                total_size += get_size(dir_path)
    return total_size

def delete_folder_contents(path):
    item_count = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            if os.path.exists(fp):
                try:
                    os.remove(fp)
                    item_count += 1
                except Exception as e:
                    log_message(f"Failed to delete file: {fp} - {str(e)}")
        for d in dirs:
            dp = os.path.join(root, d)
            if os.path.exists(dp):
                try:
                    shutil.rmtree(dp)
                    item_count += 1
                except Exception as e:
                    log_message(f"Failed to delete directory: {dp} - {str(e)}")
    return item_count

def delete_addon_cache_folders():
    cleared_paths = []
    for root, dirs, files in os.walk(ADDON_DATA_PATH):
        for dir_name in CACHE_SUBFOLDERS:
            dir_path = os.path.join(root, dir_name)
            if os.path.exists(dir_path):
                delete_folder_contents(dir_path)
                cleared_paths.append(dir_path)
    return cleared_paths

def delete_folder(path, folder_name):
    if os.path.exists(path):
        item_count = delete_folder_contents(path)  # Clear the contents instead of deleting the folder
        if folder_name == "Thumbnails":
            delete_textures_db()  # Delete the Textures13.db file
        return item_count
    return 0

def delete_textures_db():
    if os.path.exists(DATABASE_PATH):
        os.remove(DATABASE_PATH)

def ask_for_shutdown():
    dialog = xbmcgui.Dialog()
    if dialog.yesno('Shutdown Required', 'Kodi needs to shut down to complete the cleanup. Do you want to shut down now?'):
        xbmc.executebuiltin('Quit()')  # Quit Kodi completely

def check_and_clean():
    thumb_size_limit = float(ADDON.getSetting('thumb_size_limit')) * 1024 * 1024
    cache_size_limit = float(ADDON.getSetting('cache_size_limit')) * 1024 * 1024
    packages_size_limit = float(ADDON.getSetting('packages_size_limit')) * 1024 * 1024

    thumb_size = get_size(THUMBNAILS_PATH)
    cache_size = get_total_cache_size(CACHE_PATHS) + get_addon_cache_size()
    packages_size = get_size(PACKAGES_PATH)

    log_message(f"[COLOR blue]Thumbnails size:[/COLOR] {convert_size(thumb_size):.2f} MB, limit: {convert_size(thumb_size_limit):.2f} MB")
    log_message(f"[COLOR yellow]Cache size:[/COLOR] {convert_size(cache_size):.2f} MB, limit: {convert_size(cache_size_limit):.2f} MB")
    log_message(f"[COLOR orange]Packages size:[/COLOR] {convert_size(packages_size):.2f} MB, limit: {convert_size(packages_size_limit):.2f} MB")

    packages_cleared = False
    cache_cleared = False
    thumbnails_cleared = False

    if packages_size > packages_size_limit:
        package_count = delete_folder_contents(PACKAGES_PATH)
        package_message = f"Deleted {package_count} package" if package_count == 1 else f"Deleted {package_count} packages"
        log_message(f"[COLOR orange]Packages:[/COLOR] {package_message}")
        send_notification("Packages", package_message)
        packages_cleared = True

    if cache_size > cache_size_limit:
        cleared_cache_paths = delete_addon_cache_folders()
        log_message(f"[COLOR yellow]Cache:[/COLOR] Cleared {len(cleared_cache_paths)} paths")
        for path in cleared_cache_paths:
            log_message(f"[COLOR yellow]Cleared path:[/COLOR] {path}")
        send_notification("Cache", f"Cleared {len(cleared_cache_paths)} paths")
        cache_cleared = True

    if thumb_size > thumb_size_limit:
        thumb_count = delete_folder(THUMBNAILS_PATH, "Thumbnails")
        log_message(f"[COLOR blue]Thumbnails:[/COLOR] Deleted {thumb_count} files totaling {convert_size(thumb_size):.2f} MB")
        send_notification("Thumbnails", f"Deleted {thumb_count} files totaling {convert_size(thumb_size):.2f} MB")
        thumbnails_cleared = True

    if thumbnails_cleared:
        time.sleep(6)  # Delay before asking for shutdown
        ask_for_shutdown()  # Request shutdown after notification

    # Log next check time
    interval = int(ADDON.getSetting('check_interval'))  # Get interval in minutes
    log_message(f"[COLOR blue]Next check in {interval} minutes[/COLOR]")

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
        xbmc.executebuiltin(f'Notification(Auto Cleaner - {title}, {message}, 6000{notification_sound})')

if __name__ == '__main__':
    log_message("Auto Cleaner script started")
    if ADDON.getSetting('run_on_startup') == 'true':
        log_message("Running check_and_clean on startup")
        check_and_clean()
    if ADDON.getSetting('run_periodically') == 'true':
        if not threading.active_count() > 1:
            log_message("Starting periodic check thread")
            threading.Thread(target=periodic_check).start()
        else:
            log_message("[COLOR lightgreen]Periodic check thread already running[/COLOR]")
    else:
        log_message("Running check_and_clean once as periodic checks are disabled")
        check_and_clean()
    interval = int(ADDON.getSetting('check_interval'))
    log_message(f"[COLOR lightgreen]Service setup completed. Next check in {interval} minutes[/COLOR]")
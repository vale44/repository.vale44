import xbmc
import xbmcaddon
import sys
import default  # Import the default module to call its functions

# Ensure the add-on context is properly set
ADDON = xbmcaddon.Addon(id='plugin.program.autocleaner')
ADDON_PATH = ADDON.getAddonInfo('path')
sys.path.append(ADDON_PATH)

# Your existing service logic here
def log_message(message):
    xbmc.log(f"[COLOR lightgreen]Auto Cleaner[/COLOR]: {message}", xbmc.LOGINFO)

log_message("Service starting")

# Example service functionality
def run_service():
    while not xbmc.Monitor().abortRequested():
        log_message("Service running")
        default.check_and_clean()  # Call the check_and_clean function from default.py
        xbmc.sleep(60000)  # Sleep for 1 minute

if __name__ == '__main__':
    log_message("Service.py started")
    run_service()
    log_message("Service.py finished")
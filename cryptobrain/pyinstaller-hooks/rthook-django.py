import os
import sys

# This hook ensures that the DJANGO_SETTINGS_MODULE is set correctly
# when the application is running as a frozen executable.
os.environ['DJANGO_SETTINGS_MODULE'] = 'cryptobrain.settings'

# Add the bundled directory to the path to help with module resolution.
# sys._MEIPASS is the temporary folder where PyInstaller unpacks the app.
if getattr(sys, 'frozen', False):
    sys.path.append(sys._MEIPASS)

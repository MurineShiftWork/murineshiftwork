import logging

SETTINGS_PRIORITY = 0

APP_LOG_FILENAME = "/tmp/pybpod_gui.log"
PYBPOD_API_LOG_FILE = "/tmp/pybpod_api.log"
# Setting log levels here, but msw.__init__ log overwrite takes precedence
APP_LOG_HANDLER_CONSOLE_LEVEL = logging.WARNING
APP_LOG_HANDLER_FILE_LEVEL = logging.WARNING
PYBPOD_API_LOG_LEVEL = logging.WARNING

# timer for thread look for events (seconds)
PYBOARD_COMMUNICATION_THREAD_REFRESH_TIME = 1
# timer for process look for events (seconds)
PYBOARD_COMMUNICATION_PROCESS_REFRESH_TIME = 1
# wait before killing process (seconds)
PYBOARD_COMMUNICATION_PROCESS_TIME_2_LIVE = 0

USE_MULTIPROCESSING = True
PYBPOD_API_STREAM2STDOUT = False  # REMOVES stdout messages

_TEST_KEY_TO_CONFIRM_USER_SETTINGS_WERE_READ = 47474

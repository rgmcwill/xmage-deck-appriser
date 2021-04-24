#! /usr/bin/python3

import logging
import sys
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, '/home/svfserver/XDA/')
from main import app as application
application.secret_key = '12345'

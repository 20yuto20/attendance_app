from slack_bolt import App 
from slack_bolt.adapter.socket_mode import SocketModeHandler
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import pandas as pd
import re
from slack import WebClient
import warnings
import os
import json

#settings.pyの内容
import settings

# Google Sheetsへのアクセスを認証する関数
def auth():
    global gc
    SP_CREDENTIAL_FILE = '/Users/yutokohata/attendanceManagement/secretKey.json'
    SP_SCOPE = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(SP_CREDENTIAL_FILE, SP_SCOPE)
    gc = gspread.authorize(credentials)
    return gc.open_by_key(settings.database_url).worksheet(settings.SP_SHEET)
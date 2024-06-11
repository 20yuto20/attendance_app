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
import db_connection

# Google Sheetsへのアクセスを認証する関数
def auth(user_id, workspace_id):
    connection = db_connection.get_db_connection()
    cursor = connection.cursor()

    query = "SELECT database_url FROM user_settings WHERE user_id = %s AND workspace_id = %s"
    values = (user_id, workspace_id)
    cursor.execute(query, values)
    result = cursor.fetchone()

    if result:
        database_url = result[0]
        current_dir = os.path.dirname(os.path.abspath(__file__))
        SP_CREDENTIAL_FILE = os.path.join(current_dir, 'secretKey.json')
        SP_SCOPE = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(SP_CREDENTIAL_FILE, SP_SCOPE)
        gc = gspread.authorize(credentials)
        return gc.open_by_key(database_url), gc
    else:
        print(f"ワークスペースID: {workspace_id}内のユーザーID: {user_id}の設定値が見つかりませんでした。")
        return None, None

    cursor.close()
    connection.close()
import auth
from slack_bolt import App 
from slack_bolt.adapter.socket_mode import SocketModeHandler
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import pandas as pd
import re
from slack import WebClient
import db_connection

def update_month_sheet(user_id, workspace_id, timestamp_data):
    try:
        # 日付、時間、分、業務内容を取得
        date = timestamp_data["punch_date"]
        operation_time = timestamp_data["work_time"]
        operation_content = timestamp_data["work_contents"]

        if not all([date, operation_time, operation_content]):
            print("必要な情報が提供されていません。更新をスキップします。")
            return

        # 正規表現を使用して稼働時間を解析
        match = re.match(r'(\d+)時間(\d+)分', operation_time)
        if not match:
            raise ValueError("稼働時間の形式が正しくありません。")

        hours, minutes = map(int, match.groups())

        # 日付から年と月を取得
        year, month, _ = date.split('年')[0], date.split('月')[0].split('年')[1], date.split('月')[1]
        month_sheet_name = f'{year}年{month}月'

        # user_idを元にしてsettings.pyからdatabase_urlを取得
        connection = db_connection.get_db_connection()
        cursor = connection.cursor()
        query = "SELECT database_url FROM user_settings WHERE user_id = %s AND workspace_id = %s"
        cursor.execute(query, (user_id, workspace_id))
        result = cursor.fetchone()
        cursor.close()
        connection.close()

        if result:
            # 対応する月のシートを取得
            spreadsheet, gc = auth.auth(user_id, workspace_id)
            if spreadsheet is None:
                raise Exception(f"ユーザーID: {user_id}、ワークスペースID: {workspace_id}の設定が見つかりませんでした。")
            try:
                month_sheet = spreadsheet.worksheet(month_sheet_name)
            except gspread.exceptions.WorksheetNotFound:
                raise Exception(f"シート {month_sheet_name} が見つかりません。")

            # 日付に一致する行を探す
            dates = month_sheet.col_values(1)  # 日付カラムは1列目
            row_index = dates.index(date) + 1  # gspreadは1からインデックスを始める

            # 現在の時間と分を取得して更新
            current_hours = int(month_sheet.cell(row_index, 2).value or 0)  # 時間カラムは2列目
            current_minutes = int(month_sheet.cell(row_index, 3).value or 0)  # 分カラムは3列目
            new_hours = current_hours + hours
            new_minutes = current_minutes + minutes

            # 分が60以上の場合、時間に1を足し、分を60で割った余りにする
            if new_minutes >= 60:
                new_hours += new_minutes // 60  # 新しい分から追加される時間を計算
                new_minutes = new_minutes % 60  # 分を60で割った余りを新しい分とする

            # 業務内容を取得して更新
            current_content = month_sheet.cell(row_index, 4).value  # 業務内容カラムは4列目
            new_content = (current_content + ', ' if current_content else '') + operation_content

            month_sheet.update(f'B{row_index}', new_hours)
            month_sheet.update(f'C{row_index}', new_minutes)
            month_sheet.update(f'D{row_index}', new_content)

            print('更新が完了しました。')
        else:
            print(f"ユーザーID: {user_id}、ワークスペースID: {workspace_id}の設定が見つかりませんでした。")

    except (ValueError, gspread.exceptions.APIError, Exception) as e:
        print(f"エラーが発生しました: {e}")

def on_timestamp_update(body):
    user_id = body["user"]["id"]
    workspace_id = body["user"]["team_id"]

    try:
        connection = db_connection.get_db_connection()
        cursor = connection.cursor()

        # user_idとworkspace_idを元にしてp_keyの最大値を持つレコードを取得
        query = "SELECT * FROM punch_time WHERE punch_user_id = %s AND punch_workspace_id = %s ORDER BY p_key DESC LIMIT 1"
        cursor.execute(query, (user_id, workspace_id))
        result = cursor.fetchone()
        cursor.close()
        connection.close()

        if result:
            timestamp_data = {
                "punch_date": result[3],
                "work_time": result[6],
                "work_contents": result[7]
            }
            print('更新されたデータを取得します。')
            print('update_month_sheet関数を呼び出します。')
            update_month_sheet(user_id, workspace_id, timestamp_data)
        else:
            print(f"ユーザーID: {user_id}、ワークスペースID: {workspace_id}の打刻データが見つかりませんでした。")

    except Exception as e:
        print(f"エラーが発生しました: {e}")
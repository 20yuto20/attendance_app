from slack_bolt import App 
from slack_bolt.adapter.socket_mode import SocketModeHandler
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import gspread
import pandas as pd
import re
from slack import WebClient
import warnings
import os
import json

import db_connection

# .envファイルから環境変数を読み込む
load_dotenv()

app = App(
    token=os.getenv("BOT_TOKEN"),
    signing_secret=os.getenv("APP_TOKEN")
)

def get_user_status(user_id, cursor):
    query = "SELECT status FROM user_status WHERE user_id = %s"
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()
    return result[0] if result else "業務外"

def update_user_status(user_id, status, cursor, connection):
    query = "INSERT INTO user_status (user_id, status) VALUES (%s, %s) ON DUPLICATE KEY UPDATE status = VALUES(status)"
    cursor.execute(query, (user_id, status))
    connection.commit()

@app.event("app_home_opened")
def update_hometab(client, event, logger):
    try:
        user_id = event["user"]
        
        if isinstance(user_id, str):
            connection = db_connection.get_db_connection()
            cursor = connection.cursor()

            # ユーザーの現在の状態を取得
            status = get_user_status(user_id, cursor)

            # 現在の状態に基づいて画面を更新
            if status == "業務中":
                client.views_publish(
                    user_id=user_id,
                    view={
                        "type": "home",
                        "blocks": [
                            {
                                "type": "header",
                                "text": {
                                    "type": "plain_text",
                                    "text": "🕒 Kotonaru勤怠管理",
                                    "emoji": True
                                }
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "勤怠管理アプリへようこそ！こちらでは、日々の業務開始・終了時間、休憩時間の記録が簡単にできます。\n\n*主な機能：*\n- 業務開始・終了の記録\n- 休憩開始・終了の記録\n- 設定のカスタマイズ\n- 勤務時間の統計閲覧"
                                }
                            },
                            {
                                "type": "divider"
                            },
                            {
                                "type": "header",
                                "text": {
                                    "type": "plain_text",
                                    "text": "⏱ 勤怠記録",
                                    "emoji": True
                                }
                            },
                            {
                                "type": "actions",
                                "elements": [
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "業務終了",
                                            "emoji": True
                                        },
                                        "style": "danger",
                                        "value": "end_work",
                                        "action_id": "click_work_end"
                                    },
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "休憩開始",
                                            "emoji": True
                                        },
                                        "style": "primary",
                                        "value": "start_break",
                                        "action_id": "click_break_begin"
                                    }
                                ]
                            },
                            {
                                "type": "divider"
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": ":clock1: *現在のステータス*\n- ステータス: 業務中\n"
                                }
                            },
                            {
                                "type": "divider"
                            },
                            {
                                "type": "header",
                                "text": {
                                    "type": "plain_text",
                                    "text": "🔧 設定 & 📊 統計",
                                    "emoji": True
                                }
                            },
                            {
                                "type": "actions",
                                "elements": [
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "設定",
                                            "emoji": True
                                        },
                                        "value": "open_settings",
                                        "action_id": "open_settings"
                                    },
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "統計",
                                            "emoji": True
                                        },
                                        "value": "view_statistics",
                                        "action_id": "view_statistics"
                                    }
                                ]
                            }
                        ]
                    }
                )
            elif status == "休憩中":
                client.views_publish(
                    user_id=user_id,
                    view={
                        "type": "home",
                        "blocks": [
                            {
                                "type": "header",
                                "text": {
                                    "type": "plain_text",
                                    "text": "🕒 Kotonaru勤怠管理",
                                    "emoji": True
                                }
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "勤怠管理アプリへようこそ！こちらでは、日々の業務開始・終了時間、休憩時間の記録が簡単にできます。\n\n*主な機能：*\n- 業務開始・終了の記録\n- 休憩開始・終了の記録\n- 設定のカスタマイズ\n- 勤務時間の統計閲覧"
                                }
                            },
                            {
                                "type": "divider"
                            },
                            {
                                "type": "header",
                                "text": {
                                    "type": "plain_text",
                                    "text": "⏱ 勤怠記録",
                                    "emoji": True
                                }
                            },
                            {
                                "type": "actions",
                                "elements": [
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "休憩終了",
                                            "emoji": True
                                        },
                                        "style": "danger",
                                        "value": "end_break",
                                        "action_id": "click_break_end"
                                    }
                                ]
                            },
                            {
                                "type": "divider"
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": ":clock1: *現在のステータス*\n- ステータス: 休憩中\n"
                                }
                            },
                            {
                                "type": "divider"
                            },
                            {
                                "type": "header",
                                "text": {
                                    "type": "plain_text",
                                    "text": "🔧 設定 & 📊 統計",
                                    "emoji": True
                                }
                            },
                            {
                                "type": "actions",
                                "elements": [
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "設定",
                                            "emoji": True
                                        },
                                        "value": "open_settings",
                                        "action_id": "open_settings"
                                    },
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "統計",
                                            "emoji": True
                                        },
                                        "value": "view_statistics",
                                        "action_id": "view_statistics"
                                    }
                                ]
                            }
                        ]
                    }
                )
            else:
                client.views_publish(
                    user_id=user_id,
                    view={
                        "type": "home",
                        "blocks": [
                            {
                                "type": "header",
                                "text": {
                                    "type": "plain_text",
                                    "text": "🕒 Kotonaru勤怠管理",
                                    "emoji": True
                                }
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "勤怠管理アプリへようこそ！こちらでは、日々の業務開始・終了時間、休憩時間の記録が簡単にできます。\n\n*主な機能：*\n- 業務開始・終了の記録\n- 休憩開始・終了の記録\n- 設定のカスタマイズ\n- 勤務時間の統計閲覧"
                                }
                            },
                            {
                                "type": "divider"
                            },
                            {
                                "type": "header",
                                "text": {
                                    "type": "plain_text",
                                    "text": "⏱ 勤怠記録",
                                    "emoji": True
                                }
                            },
                            {
                                "type": "actions",
                                "elements": [
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "業務開始",
                                            "emoji": True
                                        },
                                        "style": "primary",
                                        "value": "start_work",
                                        "action_id": "click_work_begin"
                                    }
                                ]
                            },
                            {
                                "type": "divider"
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": ":clock1: *現在のステータス*\n- ステータス: 業務外\n"
                                }
                            },
                            {
                                "type": "divider"
                            },
                            {
                                "type": "header",
                                "text": {
                                    "type": "plain_text",
                                    "text": "🔧 設定 & 📊 統計",
                                    "emoji": True
                                }
                            },
                            {
                                "type": "actions",
                                "elements": [
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "設定",
                                            "emoji": True
                                        },
                                        "value": "open_settings",
                                        "action_id": "open_settings"
                                    },
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "統計",
                                            "emoji": True
                                        },
                                        "value": "view_statistics",
                                        "action_id": "view_statistics"
                                    }
                                ]
                            }
                        ]
                    }
                )

            cursor.close()
            connection.close()

    except Exception as e:
        logger.error(f"Error updating home view: {str(e)}")

# 業務開始時の処理
@app.action("click_work_begin")
def handle_work_begin(ack, body, client):
    ack()
    user_id = body["user"]["id"]

    connection = db_connection.get_db_connection()
    cursor = connection.cursor()

    # punch_timeテーブルに打刻データを保存
    record_work_start(ack, body, client)

    # ユーザーのステータスを更新
    update_user_status(user_id, "業務中", cursor, connection)

    cursor.close()
    connection.close()

# 業務終了時の処理
@app.action("click_work_end")
def handle_work_end(ack, body, client):
    ack()
    user_id = body["user"]["id"]

    connection = db_connection.get_db_connection()
    cursor = connection.cursor()

    # punch_timeテーブルの打刻データを更新
    work_done(body, client)

    # ユーザーのステータスを更新
    update_user_status(user_id, "業務外", cursor, connection)

    cursor.close()
    connection.close()

# 休憩開始時の処理
@app.action("click_break_begin")
def handle_break_begin(ack, body, client):
    ack()
    user_id = body["user"]["id"]

    connection = db_connection.get_db_connection()
    cursor = connection.cursor()

    update_user_status(user_id, "休憩中", cursor, connection)

    cursor.close()
    connection.close()

# 休憩終了時の処理
@app.action("click_break_end")
def handle_break_end(ack, body, client):
    ack()
    user_id = body["user"]["id"]

    connection = db_connection.get_db_connection()
    cursor = connection.cursor()

    update_user_status(user_id, "業務中", cursor, connection)

    cursor.close()
    connection.close()

#----------------
#settings.pyの処理
#----------------
from settings import open_settings_modal
from settings import language_select_action, report_channel_select_action, invoice_channel_select_action, database_url_input_action, sheet_name_input_action, supervisor_user_select_action, view_submission

@app.action("open_settings")
def handle_open_settings_modal(ack, body, client):
    # open_settings_modal関数を呼び出す
    ack()
    open_settings_modal(ack, body, client)

# 言語設定に関するアクションの処理を設定
@app.action("static_select-action")
def handle_language_select_action(ack, body, client):
    language_select_action(ack, body, client)

# 報告用チャンネル設定に関するアクションの処理を設定
@app.action("report_channel_select")
def handle_report_channel_select_action(ack, body, client):
    report_channel_select_action(ack, body, client)

# 請求書用チャンネル設定に関するアクションの処理を設定
@app.action("invoice_channel_select")
def handle_invoice_channel_select_action(ack, body, client):
    invoice_channel_select_action(ack, body, client)

# データベースURL設定に関するアクションの処理を設定
@app.action("url_text_input-action")
def handle_database_url_input_action(ack, body, client):
    database_url_input_action(ack, body, client)

# シート名入力に関するアクションの処理を設定
@app.action("sheet_name_input-action")
def handle_sheet_name_input_action(ack, body, client):
    sheet_name_input_action(ack, body, client)

# 報告者設定に関するアクションの処理を設定
@app.action("user_select_action")
def handle_supervisor_user_select_action(ack, body, client):
    supervisor_user_select_action(ack, body, client)

#設定モーダルのsubmitのイベントリスナー
@app.view("callback_settings_modal")
def handle_view_submission(ack, body, client):
    ack()
    view_submission(ack, body, client)


#------------------
#work_begin.pyの処理
#------------------
from work_begin import record_work_start
@app.action("click_work_begin")
def handle_record_work_start(ack, body, client):
    ack()
    record_work_start(ack, body, client)

#-----------------
#work_done.pyの処理
#-----------------
from work_done import work_done, handle_work_summary_input
import asyncio
@app.action("click_work_end")
def handle_work_done(ack, body, client):
    ack()
    work_done(body, client)

@app.view("callback_id_work_done_modal")
def handle_handle_work_summary_input(ack, body, client):
    ack()
    handle_work_summary_input(ack, body, client)

#----------------------------
#calculate_break_time.pyの処理
#----------------------------
from calculate_break_time import handle_break_begin, handle_break_end
@app.action("click_break_begin")
def handle_handle_break_begin(ack, body, client, logger):
    ack()
    handle_break_begin(ack, body, client, logger)

@app.action("click_break_end")
def handle_handle_break_end(ack, body, client, logger):
    ack()
    handle_break_end(ack, body, client, logger)

#--------------------
#check_status.pyの処理
#--------------------
from check_status import message_events
@app.event("message")
def handle_message_events(event, say, logger):
    message_events(event, say, logger)

#-------------
#stats.pyの処理
#-------------
import threading
import settings
from stats import open_stats_modal, plot_data
import asyncio

@app.action("view_statistics")
async def handle_stats_func(ack, body, client):
    # Matplotlibの処理を非同期に実行する
    output_file, total_working_time, average_working_time = await asyncio.get_running_loop().run_in_executor(None, plot_data)

    # ack()を呼び出してリクエストを受け付けたことを通知する
    await ack()

    # モーダルを開く
    await open_stats_modal(ack, body, client, output_file, total_working_time, average_working_time)

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.getenv("APP_TOKEN"))
    handler.start()
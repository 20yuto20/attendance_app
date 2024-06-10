import os
from datetime import datetime
from slack_bolt import App
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

#必要なファイルのインポート
#settings.pyの内容
import settings #設定を行った際の各種変数が格納されている
import auth #シートの権限
import db_connection # データベースの接続のための関数が格納されている

# Slack Botのトークンを設定
app = App(
    token=os.getenv("BOT_TOKEN"),
    signing_secret=os.getenv("APP_TOKEN")
)


# 業務開始時刻を打刻する処理
def record_work_start(ack, body, client):
    ack()

    # 現在の日時を取得し、JSTに変換
    timestamp1 = datetime.now()

    # 日付と曜日を含む文字列を生成
    date_with_weekday = timestamp1.strftime('%Y年%m月%d日')
    # 時刻を取得
    time1 = timestamp1.strftime('%H:%M')

    # 日本語の曜日に変換する辞書
    weekday_dict = {
        "Monday": "月曜日",
        "Tuesday": "火曜日",
        "Wednesday": "水曜日",
        "Thursday": "木曜日",
        "Friday": "金曜日",
        "Saturday": "土曜日",
        "Sunday": "日曜日"
    }

    # 曜日を日本語に変換
    japanese_weekday = weekday_dict[timestamp1.strftime('%A')]

    # 最終的な日付表記
    final_date_with_weekday = date_with_weekday + japanese_weekday

    # メッセージを送信
    client.chat_postMessage(
        channel=body["user"]["id"],
        text=f'-------------------- \n業務開始時刻：{time1}'
    )

    # 管理者に業務開始の通知
    user_id = body["user"]["id"]
    workspace_id = body["user"]["team_id"]
    user_info = client.users_info(user=user_id)
    username = user_info["user"]["real_name"]

    connection = db_connection.get_db_connection()
    cursor = connection.cursor()

    query = "SELECT report_channel_id, supervisor_user_id FROM user_settings WHERE user_id = %s AND workspace_id = %s"
    values = (user_id, workspace_id)
    cursor.execute(query, values)
    result = cursor.fetchone()

    if result:
        report_channel_id, supervisor_user_id = result    
        # ユーザーをメンションして通知
        try:
            client.chat_postMessage(
                channel=report_channel_id,
                text=f'<@{supervisor_user_id}> {username}さんが業務を開始しました。\n業務開始時刻：{time1}'
            )
        except SlackApiError as e:
            print(f"Error posting message: {e}")
    
    else:
        print(f"ワークスペースID: {workspace_id}内のユーザーID: {user_id}の設定値が見つかりませんでした。")
        # メッセージを送信
        client.chat_postMessage(
            channel=body["user"]["id"],
            text='設定値が見つかりませんでした'
        )

    query = "INSERT INTO punch_time (punch_user_id, punch_workspace_id, punch_date, punch_in) VALUES (%s, %s, %s, %s)"
    values = (user_id, workspace_id, final_date_with_weekday, time1)
    cursor.execute(query, values)
    connection.commit()

    cursor.close()
    connection.close()
    print('業務開始時刻の打刻が完了しました。') 

    # Google Sheetsにデータを更新
    #worksheet = auth.auth(user_id, workspace_id)
    #data1 = pd.DataFrame(worksheet.get_all_records())
    #new_row = pd.DataFrame({'日付': [final_date_with_weekday], '業務開始時刻': [time1], '業務終了時刻': ['xx:xx'], '稼働時間': ['xx:xx'], '業務内容': ['xxxx']})
    #data1 = pd.concat([data1, new_row], ignore_index=True)
    #worksheet.update([data1.columns.values.tolist()] + data1.values.tolist())
    #print('業務開始時刻の打刻が完了しました。')



    # ホームビューを更新してステータスを "業務中" に変更し、開始時刻を表示
    try:
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
                            "text": f":clock1: *現在のステータス*\n- ステータス: 業務中\n- 開始時刻: {time1}"
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
    except Exception as e:
        print(f"Error updating home view: {e}")

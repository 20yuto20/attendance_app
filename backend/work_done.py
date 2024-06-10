import os
from datetime import datetime
from slack_bolt import App
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio
import concurrent.futures


#必要なファイルのインポート
#settings.pyの内容
import settings #設定を行った際の各種変数が格納されている
import auth #シートの権限
import calculate_break_time #休憩時間の計算
import manipulate_sheet #シートの操作
import db_connection # データベースへの接続
from get_total_break_duration import get_total_break_duration # SQLを用いた休憩ロジックの関数

# Slack Botのトークンを設定
app = App(
    token=os.getenv("BOT_TOKEN"),
    signing_secret=os.getenv("APP_TOKEN")
)

#業務終了ボタンが押されたら時刻の打刻とモーダルを開く処理
def work_done(body, client):
    user_id = body["user"]["id"]
    workspace_id = body["user"]["team_id"]

    timestamp2 = datetime.now() 
    global time2
    time2 = timestamp2.strftime('%H:%M')

    # SQLの操作
    try:
        connection = db_connection.get_db_connection()
        cursor = connection.cursor()

        # 該当ユーザーの最新のレコードを取得する
        query = "SELECT p_key FROM punch_time WHERE punch_user_id = %s AND punch_workspace_id = %s ORDER BY p_key DESC LIMIT 1"
        cursor.execute(query, (user_id, workspace_id))
        result = cursor.fetchone()

        if result:
            p_key = result[0]

            # punch_in_valueを取得する
            query = "SELECT punch_in FROM punch_time WHERE p_key = %s"
            cursor.execute(query, (p_key,))
            punch_in_result = cursor.fetchone()

            if punch_in_result:
                punch_in_value = punch_in_result[0]
            else:
                print(f"punch_in値が見つかりませんでした。p_key: {p_key}")
                cursor.close()
                connection.close()
                return

            # レコードの更新
            query = "UPDATE punch_time SET punch_out = %s WHERE p_key = %s"
            cursor.execute(query, (time2, p_key))
            connection.commit()
            print(f"punch_outカラムを更新しました。user_id: {user_id}, workspace_id: {workspace_id}, time2: {time2}")

            # 稼働時間の計算（休憩時間も含む）
            global start_time, end_time
            start_time = datetime.strptime(punch_in_value, "%H:%M")
            end_time = datetime.strptime(time2, "%H:%M")
            time_diff = end_time - start_time
            total_work_seconds = time_diff.total_seconds()

            # 休憩時間を外部の関数から取得し、秒に変換
            global total_break_hours, total_break_minutes
            total_break_hours, total_break_minutes = get_total_break_duration(p_key)
            total_break_hours = int(total_break_hours)
            total_break_minutes = int(total_break_minutes)
            total_break_seconds = total_break_hours * 3600 + total_break_minutes * 60

            # 正味の稼働時間の計算
            true_work_seconds = total_work_seconds - total_break_seconds

            if true_work_seconds < 0:
                true_work_seconds = 0

            global true_work_hours, true_work_minutes
            true_work_hours = int(true_work_seconds // 3600)
            true_work_minutes = int((true_work_seconds % 3600) // 60)

            # 正味の稼働時間をwork_timeカラムに記載する
            total_work_time = f"{true_work_hours}時間{true_work_minutes}分"
            query = "UPDATE punch_time SET work_time = %s WHERE p_key = %s"
            cursor.execute(query, (total_work_time, p_key))
            connection.commit()
            print(f"work_timeカラムを更新しました。user_id: {user_id}, workspace_id: {workspace_id}, total_work_time: {total_work_time}")

            # モーダルを開く
            trigger_id = body["trigger_id"]
            client.views_open(
                trigger_id=trigger_id,
                view={
                    "type": "modal",
                    "callback_id": "callback_id_work_done_modal",
                    "title": {
                        "type": "plain_text",
                        "text": "業務サマリー・業務内容記入",
                        "emoji": True
                    },
                    "submit": {
                        "type": "plain_text",
                        "text": "送信",
                        "emoji": True
                    },
                    "close": {
                        "type": "plain_text",
                        "text": "キャンセル",
                        "emoji": True
                    },
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*今回の業務時間*: {true_work_hours}時間{true_work_minutes}分"
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*休憩時間*: {total_break_hours}時間{total_break_minutes}分"
                            }
                        },
                        {
                            "type": "divider"
                        },
                        {
                            "type": "input",
                            "block_id": "work_summary",
                            "label": {
                                "type": "plain_text",
                                "text": "業務内容サマリー",
                                "emoji": True
                            },
                            "element": {
                                "type": "plain_text_input",
                                "multiline": True,
                                "action_id": "work_summary_input",
                                "placeholder": {
                                    "type": "plain_text",
                                    "text": "本日の業務内容の概要を記入してください",
                                    "emoji": True
                                }
                            }
                        },
                        {
                            "type": "input",
                            "block_id": "detailed_tasks",
                            "label": {
                                "type": "plain_text",
                                "text": "具体的な業務内容",
                                "emoji": True
                            },
                            "element": {
                                "type": "plain_text_input",
                                "multiline": True,
                                "action_id": "detailed_tasks_input",
                                "placeholder": {
                                    "type": "plain_text",
                                    "text": "今日取り組んだ具体的なタスクを記入してください",
                                    "emoji": True
                                }
                            }
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "前回の内容をコピー",
                                        "emoji": True
                                    },
                                    "value": "copy_last_summary",
                                    "action_id": "copy_last_summary_action"
                                }
                            ]
                        }
                    ]
                }
            )
        else:
            print(f"該当のレコードが見つかりませんでした。user_id: {user_id}, workspace_id: {workspace_id}")

        cursor.close()
        connection.close()

    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")

# モーダルから送信された内容を処理する
def handle_work_summary_input(ack, body, client):
    # 業務終了時刻と算出された稼働時間の報告
    client.chat_postMessage(
        channel=body["user"]["id"],
        text=f'業務終了時刻：{time2}'
    )
    client.chat_postMessage(
        channel=body["user"]["id"],
        text=f'稼働時間：{true_work_hours}時間{true_work_minutes}分\n休憩時間：{total_break_hours}時間{total_break_minutes}分'
    )

    # 入力内容を取得
    user_text = body["view"]["state"]["values"]["work_summary"]["work_summary_input"]["value"]
    user_detail = body["view"]["state"]["values"]["detailed_tasks"]["detailed_tasks_input"]["value"]

    # ユーザーに対してのバック
    client.chat_postMessage(
        channel=body["user"]["id"],
        text=f'業務内容：{user_text} \n詳細：{user_detail} \n--------------------'
    )

    # ユーザーの情報を取得
    user_id = body["user"]["id"]
    workspace_id = body["user"]["team_id"]
    user_info = client.users_info(user=user_id)
    username = user_info["user"]["real_name"]

    try:
        connection = db_connection.get_db_connection()
        cursor = connection.cursor()

        # 該当のユーザーIDと最新の作業記録のp_keyを取得
        query = "SELECT p_key FROM punch_time WHERE punch_user_id = %s AND punch_workspace_id = %s ORDER BY p_key DESC LIMIT 1"
        cursor.execute(query, (user_id, workspace_id))
        result = cursor.fetchone()

        if result:
            p_key = result[0]

            # work_contentsカラムにuser_textの値を更新
            query = "UPDATE punch_time SET work_contents = %s WHERE p_key = %s"
            cursor.execute(query, (user_text, p_key))
            connection.commit()
            print(f"work_contentsカラムを更新しました。user_id: {user_id}, workspace_id: {workspace_id}, user_text: {user_text}")
        else:
            print(f"該当のレコードが見つかりませんでした。user_id: {user_id}, workspace_id: {workspace_id}")

        cursor.close()
        connection.close()

    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")

    ack()

    connection = db_connection.get_db_connection()
    cursor = connection.cursor()

    query = "SELECT report_channel_id, supervisor_user_id FROM user_settings WHERE user_id = %s AND workspace_id = %s"
    values = (user_id, workspace_id)
    cursor.execute(query, values)
    result = cursor.fetchone()

    if result:
        report_channel_id, supervisor_user_id = result
        # 管理者に報告
        try:
            client.chat_postMessage(
                channel=report_channel_id,
                text=f'<@{supervisor_user_id}> {username}さんが業務を終了しました。\n{username}さんの業務開始時刻：{start_time} \n{username}さんの業務終了時刻：{end_time} \n{username}さんの正味の業務時間：{true_work_hours}時間{true_work_minutes}分 \n{username}さんの休憩時間：{total_break_hours}時間{total_break_minutes}分 \n業務内容：{user_text} \n詳細：{user_detail}'
            )
        except SlackApiError as e:
            print(f"Error posting message: {e.response['error']}")

    else:
        print(f"ワークスペースID: {workspace_id}内のユーザーID: {user_id}の設定値が見つかりませんでした。")
        # メッセージを送信
        client.chat_postMessage(
            channel=body["user"]["id"],
            text='設定値が見つかりませんでした'
        )

    cursor.close()
    connection.close()

    #シート記入に移る
    print('これよりon_timestamp_update関数を呼び出し、稼動時間報告書を更新します。')
    manipulate_sheet.on_timestamp_update(body)

    # 初期状態のホームタブのUIを再表示
    try:
        client.views_publish(
            user_id=body["user"]["id"],
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
    except Exception as e:
        print(f"Error updating home view: {e}")
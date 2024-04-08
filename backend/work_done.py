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

# Slack Botのトークンを設定
app = App(token=os.environ["SLACK_BOT_TOKEN"])

#業務終了ボタンが押されたら時刻の打刻とモーダルを開く処理
async def work_done(ack, body, client):
    timestamp2 = datetime.now()
    time2 = timestamp2.strftime('%H:%M')

    # ユーザーへのメッセージ送信
    await client.chat_postMessage(
        channel=body["user"]["id"],
        text=f'業務終了時刻：{time2}'
    )

    # ワークシートの操作
    worksheet = auth.auth()
    worksheet.update_cell(worksheet.row_count, 3, time2)
    # print('業務終了時刻の打刻が完了しました。') # ログ出力は必要に応じて

    # 業務開始時刻をシートから取得
    punch_in_value = worksheet.cell(worksheet.row_count, 2).value

    # 稼働時間の計算及び出力
    start_time = datetime.strptime(punch_in_value, "%H:%M")
    end_time = datetime.strptime(time2, "%H:%M")
    time_diff = end_time - start_time
    work_hours = time_diff.seconds // 3600
    global true_work_hours
    global true_work_minutes
    true_work_hours = work_hours - calculate_break_time.total_break_hours
    work_minutes = (time_diff.seconds // 60) % 60
    true_work_minutes = work_minutes - calculate_break_time.total_break_minutes

    await client.chat_postMessage(
        channel=body["user"]["id"],
        text=f'稼働時間：{true_work_hours}時間{true_work_minutes}分\n休憩時間：{calculate_break_time.total_break_hours}時間{calculate_break_time.total_break_minutes}分'
    )

    # 正味の稼働時間を稼働時間カラムに記載する
    total_work_time = f"{true_work_hours}時間{true_work_minutes}分"
    with concurrent.futures.ThreadPoolExecutor() as executor:
        await asyncio.get_event_loop().run_in_executor(executor, worksheet.update_cell, worksheet.row_count, 4, total_work_time)
    # print('稼働時間の打刻が完了しました。') # ログ出力は必要に応じて

    #モーダルを開く
    trigger_id = body["trigger_id"]
    await client.views_open(
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
                        "text": f"*休憩時間*: {calculate_break_time.total_break_hours}時間{calculate_break_time.total_break_minutes}分"
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

# モーダルから送信された内容を処理する
def handle_work_summary_input(ack, body, client):
    global total_break_hours, total_break_minutes

    # 入力内容を取得
    user_text = body["view"]["state"]["values"]["work_summary"]["work_summary_input"]["value"]
    user_detail = body["view"]["state"]["values"]["detailed_tasks"]["detailed_tasks_input"]["value"]

    # ユーザーに対してのバック
    client.chat_postMessage(
        channel = body["user"]["id"],
        text = f'業務内容：{user_text} \n詳細：{user_detail} \n--------------------'
    )

    # スプシの操作
    worksheet = auth.auth()
    data1 = pd.DataFrame(worksheet.get_all_records())
    # 最後の行の4列目を更新（業務内容の列を指定する）
    data1.iloc[-1, 4] = user_text
    worksheet.update([data1.columns.values.tolist()] + data1.values.tolist())
    print('業務内容の記載が完了しました。')

    
    # ユーザーにメッセージを送信
    ack()

    # ユーザーの情報を取得
    user_id = body["user"]["id"]
    user_info = client.users_info(user=user_id)
    username = user_info["user"]["real_name"]

    # 管理者に報告
    try:
        client.chat_postMessage(
            channel=settings.report_channel_id,
            text=f'<@{settings.supervisor_user_id}> {username}さんが業務を終了しました。\n{username}さんの業務時間：{true_work_hours}時間{true_work_minutes}分 \n{username}さんの休憩時間：{calculate_break_time.total_break_hours}時間{calculate_break_time.total_break_minutes}分 \n業務内容：{user_text} \n詳細：{user_detail}'
        )
    except SlackApiError as e:
        print(f"Error posting message: {e.response['error']}")

    # 休憩時間をリセット
    total_break_hours = 0
    total_break_minutes = 0
    print(f'休憩時間をリセットしました。\ntotal_break_hours：{total_break_hours} \ntotal_break_minutes：{total_break_minutes}')

    #シート記入に移る
    print('これよりon_timestamp_update関数を呼び出し、稼動時間報告書を更新します。')
    manipulate_sheet.on_timestamp_update()

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

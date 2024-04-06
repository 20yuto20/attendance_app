from slack_bolt import App
from slack_sdk.errors import SlackApiError
import re
import json
import os

# Slack Botのトークンを設定
app = App(token=os.environ["SLACK_BOT_TOKEN"])

def message_events(event, say, logger):
    try:
        print("message_events 関数が呼び出されました。")
        # ステータス確認のメッセージを処理する
        if re.match(r'<@(\w+)>\_<@(\w+)>\_status', event.get("text", "")):
            print("ステータス確認メッセージを検知しました。")
            status_request(event, say, app.client)
        else:
            print("ステータス確認メッセージではありませんでした。")
    except Exception as e:
        print(f"An error occurred while processing message events: {e}")

def status_request(message, say, client):
    try:
        # メッセージから、ステータスを確認したいユーザーのIDを抽出
        target_user_id = re.search(r'<@(\w+)>\_<@(\w+)>', message.get("text", "")).group(2)

        # ホームビューからユーザーのステータスを取得
        response = client.views_open(
            trigger_id=message.get("trigger_id", ""),
            view={
                "type": "home",
                "user_id": target_user_id
            }
        )

        home_view = response.get("view")
        if home_view:
            # ホームビューのJSON情報から、ステータス関連の情報を抽出
            for block in home_view["blocks"]:
                if block["type"] == "section" and "text" in block and "mrkdwn" in block["text"]:
                    status_text = block["text"]["text"]
                    if ":clock1: _現在のステータス_" in status_text:
                        # ステータスと開始時刻を抽出
                        status_info = re.findall(r"- ステータス: (\w+)\n- 開始時刻: (\d+:\d+)", status_text)
                        if status_info:
                            status, start_time = status_info[0]
                            say(f"@{target_user_id}の現在のステータス: {status}, 開始時刻: {start_time}")
                        else:
                            say(f"@{target_user_id}の現在のステータスを取得できませんでした。")
                        return
            say(f"@{target_user_id}の現在のステータスを取得できませんでした。")
        else:
            say(f"@{target_user_id}の現在のステータスを取得できませんでした。")
    except SlackApiError as e:
        print(f"Error getting user status: {e}")
        say(f"ステータス取得に失敗しました。")
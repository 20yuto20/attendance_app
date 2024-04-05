from slack_bolt import App
from slack_sdk.errors import SlackApiError
import re
import json
import os

# Slack Botのトークンを設定
app = App(token=os.environ.get("BOT_TOKEN"))

def message_events(event, say, logger):
    logger.info(event)

    # ステータス確認のメッセージを処理する
    if re.match(r'@\{bot\}_@\{(\w+)\}_status', event.get("text", "")):
        status_request(event, say, app.client)

def status_request(message, say, client):
    try:
        # メッセージから、ステータスを確認したいユーザーのIDを抽出
        target_user_id = re.search(r'@\{(\w+)\}_status', message.text).group(1)

        # ホームビューからユーザーのステータスを取得
        response = client.views_open(
            trigger_id=message["trigger_id"],
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
                    if ":clock1: *現在のステータス*" in status_text:
                        # ステータスを抽出
                        status = re.search(r"- ステータス: (\w+)", status_text)
                        if status:
                            status = status.group(1)
                            say(f"@{target_user_id}の現在のステータス: {status}")
                        else:
                            say(f"@{target_user_id}の現在のステータスを取得できませんでした。")
                        return
        else:
            say(f"@{target_user_id}の現在のステータスを取得できませんでした。")

    except SlackApiError as e:
        print(f"Error getting user status: {e}")
        say(f"ステータス取得に失敗しました。")
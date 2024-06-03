from slack_bolt import App 
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os

import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

import db_connection # データベースに設定の値を保存

# Slack Botのトークンを設定
app = App(token=os.environ["SLACK_BOT_TOKEN"])

#設定のモーダルを開く処理
def open_settings_modal(ack, body, client):
    try:
        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "callback_settings_modal",
                "title": {
                    "type": "plain_text",
                    "text": ":gear:設定",
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
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": ":globe_with_meridians: 言語設定",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "block_id": "block_id_language",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*主要な言語を選択してください*"
                        },
                        "accessory": {
                            "type": "static_select",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "言語を選択",
                                "emoji": True
                            },
                            "options": [
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "英語",
                                        "emoji": True
                                    },
                                    "value": "english"
                                },
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "日本語",
                                        "emoji": True
                                    },
                                    "value": "japanese"
                                },
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "中国語",
                                        "emoji": True
                                    },
                                    "value": "chinese"
                                },
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "スペイン語",
                                        "emoji": True
                                    },
                                    "value": "spanish"
                                }
                            ],
                            "action_id": "static_select-action"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": ":bell: チャンネル設定",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "block_id": "block_id_announce_channel",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*報告用のチャンネルを選択してください*"
                        },
                        "accessory": {
                            "type": "channels_select",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "チャンネルを選択",
                                "emoji": True
                            },
                            "action_id": "report_channel_select"
                        }
                    },
                    {
                        "type": "section",
                        "block_id": "block_id_invoice_channel",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*請求書用のチャンネルを選択してください*"
                        },
                        "accessory": {
                            "type": "channels_select",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "チャンネルを選択",
                                "emoji": True
                            },
                            "action_id": "invoice_channel_select"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": ":clipboard:データベースURL設定",
                            "emoji": True
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "block_id_database_url_id",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "url_text_input-action"
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "勤怠管理用データベースのURLのIDを入力してください",
                            "emoji": True
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": ":loudspeaker:報告者設定",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "block_id": "block_id_supervisor",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*上長（メンションする人）を選択してください*"
                        },
                        "accessory": {
                            "type": "users_select",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "ユーザーを選択",
                                "emoji": True
                            },
                            "action_id": "user_select_action"
                        }
                    }
                ]
            }
        )
        # ack() を呼び出してアクションを処理したことを Slack に通知
        ack()
    except Exception as e:
        print(f"Error open setting modal: {e}")
        ack()

# モーダルで選択された言語を保存する変数
selected_language = ""

# モーダルで選択された報告用チャンネルのIDを保存する変数
report_channel_id = ""

# モーダルで選択された請求書用チャンネルのIDを保存する変数
invoice_channel_id = ""

# モーダルで入力されたデータベースのURLを保存する変数
database_url = ""

# モーダルで選択された上長（メンションする人）のIDを保存する変数
supervisor_user_id = ""

# 送信ボタンが押されたら呼び出される関数
def view_submission(ack, body, logger):
    try:
        global selected_language, report_channel_id, invoice_channel_id, database_url, SP_SHEET, supervisor_user_id
        user_id = body["user"]["id"]
        workspace_id = body["user"]["team_id"]

        # 言語設定の取得
        if "block_id_language" in body["view"]["state"]["values"]:
            selected_language = body["view"]["state"]["values"]["block_id_language"]["static_select-action"]["selected_option"]["value"]
            print(f"selected_language: {selected_language}")
        
        # 報告用チャンネルの取得
        if "block_id_announce_channel" in body["view"]["state"]["values"]:
            report_channel_id = body["view"]["state"]["values"]["block_id_announce_channel"]["report_channel_select"]["selected_channel"]
            print(f"report_channel_id: {report_channel_id}")
        
        # 請求書用チャンネルの取得
        if "block_id_invoice_channel" in body["view"]["state"]["values"]:
            invoice_channel_id = body["view"]["state"]["values"]["block_id_invoice_channel"]["invoice_channel_select"]["selected_channel"]
            print(f"invoice_channel_id: {invoice_channel_id}")
        
        # データベースURLの取得
        if "block_id_database_url_id" in body["view"]["state"]["values"]:
            database_url = body["view"]["state"]["values"]["block_id_database_url_id"]["url_text_input-action"]["value"]
            print(f"database_url: {database_url}")
        
        # 上長のユーザーIDの取得
        if "block_id_supervisor" in body["view"]["state"]["values"]:
            supervisor_user_id = body["view"]["state"]["values"]["block_id_supervisor"]["user_select_action"]["selected_user"]
            print(f"supervisor_user_id: {supervisor_user_id}")

        connection = db_connection.get_db_connection()
        cursor = connection.cursor()

        # データベースに書く値を保存していく
        query = """
            INSERT INTO user_settings (user_id, workspace_id, selected_language, report_channel_id, invoice_channel_id, database_url, supervisor_user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                selected_language = VALUES(selected_language),
                report_channel_id = VALUES(report_channel_id),
                invoice_channel_id = VALUES(invoice_channel_id),
                database_url = VALUES(database_url),
                supervisor_user_id = VALUES(supervisor_user_id)
        """

        values = (user_id, workspace_id, selected_language, report_channel_id, invoice_channel_id, database_url, supervisor_user_id)
        cursor.execute(query, values)
        connection.commit()

        cursor.close()
        connection.close()
        
        ack()


    except Exception as e:
        ack()
        print(f"Error updating variables: {e}")


# 言語設定に関するアクションの処理
def language_select_action(ack, body, client):
    try:
        user_id = body["user"]["id"]
        workspace_id = body["user"]["team_id"]
        view_state = body.get("view", {}).get("state", {}).get("values", {})
        
        if "static_select-action" in view_state:
            selected_option = view_state["static_select-action"].get("selected_option", {})
            
            if "value" in selected_option:
                selected_language = selected_option["value"]
                
                connection = db_connection.get_db_connection()
                cursor = connection.cursor()

                query = "UPDATE user_settings SET selected_language = %s WHERE user_id = %s AND workspace_id = %s"
                values = (selected_language, user_id, workspace_id)
                cursor.execute(query, values)
                connection.commit()

                cursor.close()
                connection.close()

        ack()
    except Exception as e:
        print(f"Error in language_select_action: {e}")
        ack(text=f"Error in language_select_action: {e}")

# 報告用チャンネル設定に関するアクションの処理
def report_channel_select_action(ack, body, client):
    try:
        user_id = body["user"]["id"]
        workspace_id = body["user"]["team_id"]
        view_state = body.get("view", {}).get("state", {}).get("values", {})
        
        if "report_channel_select" in view_state:
            selected_channel = view_state["report_channel_select"].get("channels_select-action", {}).get("selected_channel", None)
            
            if selected_channel:
                connection = db_connection.get_db_connection()
                cursor = connection.cursor()

                query = "UPDATE user_settings SET report_channel_id = %s WHERE user_id = %s AND workspace_id = %s"
                values = (selected_channel, user_id, workspace_id)
                cursor.execute(query, values)
                connection.commit()

                cursor.close()
                connection.close()

        ack()
    except Exception as e:
        print(f"Error in report_channel_select_action: {e}")
        ack(text=f"Error in report_channel_select_action: {e}")

# 請求書用チャンネル設定に関するアクションの処理
def invoice_channel_select_action(ack, body, client):
    try:
        user_id = body["user"]["id"]
        workspace_id = body["user"]["team_id"]
        view_state = body.get("view", {}).get("state", {}).get("values", {})
        
        if "invoice_channel_select" in view_state:
            selected_channel = view_state["invoice_channel_select"].get("channels_select-action", {}).get("selected_channel", None)
            
            if selected_channel:
                connection = db_connection.get_db_connection()
                cursor = connection.cursor()

                query = "UPDATE user_settings SET invoice_channel_id = %s WHERE user_id = %s AND workspace_id = %s"
                values = (selected_channel, user_id, workspace_id)
                cursor.execute(query, values)
                connection.commit()

                cursor.close()
                connection.close()

        ack()
    except Exception as e:
        print(f"Error in invoice_channel_select_action: {e}")
        ack(text=f"Error in invoice_channel_select_action: {e}")

# データベースURL設定に関するアクションの処理
def database_url_input_action(ack, body, client):
    try:
        user_id = body["user"]["id"]
        workspace_id = body["user"]["team_id"]
        view_state = body.get("view", {}).get("state", {}).get("values", {})
        
        if "url_text_input-action" in view_state:
            url_input = view_state["url_text_input-action"].get("url_text_input", {}).get("value", None)
            
            if url_input:
                connection = db_connection.get_db_connection()
                cursor = connection.cursor()

                query = "UPDATE user_settings SET database_url = %s WHERE user_id = %s AND workspace_id = %s"
                values = (url_input, user_id, workspace_id)
                cursor.execute(query, values)
                connection.commit()

                cursor.close()
                connection.close()

        ack()
    except Exception as e:
        print(f"Error in database_url_input_action: {e}")
        ack(text=f"Error in database_url_input_action: {e}")

# シート名設定に関するアクションの処理
def sheet_name_input_action(ack, body, client):
    try:
        user_id = body["user"]["id"]
        workspace_id = body["user"]["team_id"]
        view_state = body.get("view", {}).get("state", {}).get("values", {})
        
        if "sheet_name_input-action" in view_state:
            sheet_name_input = view_state["sheet_name_input-action"].get("plain_text_input", {}).get("value", None)
            
            if sheet_name_input:
                connection = db_connection.get_db_connection()
                cursor = connection.cursor()

                query = "UPDATE user_settings SET sp_sheet = %s WHERE user_id = %s AND workspace_id = %s"
                values = (sheet_name_input, user_id, workspace_id)
                cursor.execute(query, values)
                connection.commit()

                cursor.close()
                connection.close()

        ack()
    except Exception as e:
        print(f"Error in sheet_name_input_action: {e}")
        ack(text=f"Error in sheet_name_input_action: {e}")

# 報告者設定に関するアクションの処理
def supervisor_user_select_action(ack, body, client):
    try:
        user_id = body["user"]["id"]
        workspace_id = body["user"]["team_id"]
        view_state = body.get("view", {}).get("state", {}).get("values", {})
        
        if "user_select_action" in view_state:
            selected_user = view_state["user_select_action"].get("users_select-action", {}).get("users_select", None)
            
            if selected_user:
                connection = db_connection.get_db_connection()
                cursor = connection.cursor()

                query = "UPDATE user_settings SET supervisor_user_id = %s WHERE user_id = %s AND workspace_id = %s"
                values = (selected_user, user_id, workspace_id)
                cursor.execute(query, values)
                connection.commit()

                cursor.close()
                connection.close()

        ack()
    except Exception as e:
        print(f"Error in supervisor_user_select_action: {e}")
        ack(text=f"Error in supervisor_user_select_action: {e}")

# Slack Bolt アプリの各アクションのリスナーを設定
app.action("static_select-action")(language_select_action)
app.action("report_channel_select")(report_channel_select_action)
app.action("invoice_channel_select")(invoice_channel_select_action)
app.action("url_text_input-action")(database_url_input_action)
app.action("sheet_name_input-action")(sheet_name_input_action)
app.action("user_select_action")(supervisor_user_select_action)


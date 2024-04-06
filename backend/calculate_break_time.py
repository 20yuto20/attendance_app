import os
from slack_bolt import App
from datetime import datetime

# Slackアプリの初期化
app = App(token=os.environ["SLACK_BOT_TOKEN"])

# 休憩開始時刻と終了時刻を保持する変数
break_begin_time = None
break_end_time = None

def handle_break_begin(ack, body, client, logger):
    global break_begin_time
    ack()
    break_begin_time = datetime.now()
    break_begin_time_str = break_begin_time.strftime('%H:%M')
    
    try:
        # ユーザーのホームを更新して休憩中のステータスを表示
        user_id = body['user']['id']
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
                            "text": f":clock1: *現在のステータス*\n- ステータス: 休憩中\n- 開始時刻: {break_begin_time_str}"
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
        logger.error(f"Error publishing view: {e}")

# 休憩時間の蓄積用変数
total_break_hours = 0
total_break_minutes = 0

def handle_break_end(ack, body, client, logger):
    global break_end_time, total_break_hours, total_break_minutes
    ack()
    break_end_time = datetime.now()
    break_end_time_str = break_end_time.strftime('%H:%M')
    break_whole_time = break_end_time - break_begin_time
    break_hours = break_whole_time.seconds // 3600
    break_minutes = (break_whole_time.seconds // 60) % 60
    
    # 休憩時間の蓄積
    total_break_hours += break_hours
    total_break_minutes += break_minutes
    
    try:
        # ユーザーのホームを更新して業務中のステータスを表示
        user_id = body['user']['id']
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
                            "text": f":clock1: *現在のステータス*\n- ステータス: 業務中\n- 開始時刻: {break_end_time_str}\n- 休憩時間: {total_break_hours}時間{total_break_minutes}分"
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
        logger.error(f"Error publishing view: {e}")

    #work_done_modalに休憩時間を渡すために戻り値を設定
    return total_break_hours, total_break_minutes

import os
from slack_bolt import App
from datetime import datetime
from db_connection import get_db_connection
from get_total_break_duration import get_total_break_duration

app = App(
    token=os.getenv("BOT_TOKEN"),
    signing_secret=os.getenv("APP_TOKEN")
)

def handle_break_begin(ack, body, client, logger):
    logger.info(f"handle_break_begin called with body: {body}") # 休憩開始ボタンの作動確認のデバッグ
    ack()
    user_id = body["user"]["id"]
    workspace_id = body["user"]["team_id"]
    break_begin_time = datetime.now()

    try:
        # punch_timeテーブルから、該当のユーザーIDと現在の作業時間に対応するp_keyを取得
        connection = get_db_connection()
        cursor = connection.cursor()

        query = "SELECT p_key FROM punch_time WHERE punch_user_id = %s AND punch_workspace_id = %s ORDER BY p_key DESC LIMIT 1"
        cursor.execute(query, (user_id, workspace_id))
        result = cursor.fetchone()

        if result:
            punch_id = result[0]

            # break_timeテーブルに新しいレコードを挿入
            query = "INSERT INTO break_time (punch_id, break_begin_time) VALUES (%s, %s)"
            cursor.execute(query, (punch_id, break_begin_time))
            connection.commit()
            logger.info(f"Break started at {break_begin_time} for user {user_id} in workspace {workspace_id}")

            # ユーザーのホームを更新して休憩中のステータスを表示
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
                                    "text": f":clock1: *現在のステータス*\n- ステータス: 休憩中\n- 開始時刻: {break_begin_time.strftime('%H:%M')}"
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
        else:
            logger.warning(f"No ongoing work session found for user {user_id} in workspace {workspace_id}")

        cursor.close()
        connection.close()

    except Exception as e:
        logger.error(f"Error in handle_break_begin: {e}")

def handle_break_end(ack, body, client, logger):
    ack()
    user_id = body["user"]["id"]
    workspace_id = body["user"]["team_id"]
    break_end_time = datetime.now()

    try:
        # DB接続の取得
        connection = get_db_connection()
        cursor = connection.cursor()
        logger.info("DB connection established")

        try:
            # punch_timeテーブルから、該当のユーザーIDと現在の作業時間に対応するp_keyを取得
            query = "SELECT p_key FROM punch_time WHERE punch_user_id = %s AND punch_workspace_id = %s ORDER BY p_key DESC LIMIT 1"
            cursor.execute(query, (user_id, workspace_id))
            result = cursor.fetchone()
            logger.info(f"Executed query to fetch punch_time p_key: {query} with parameters: {user_id}, {workspace_id}")
            logger.info(f"Query result: {result}")

            if result:
                punch_id = result[0]

                try:
                    # break_timeテーブルから、punch_idが取得したp_keyの値で、break_end_timeがNULLのレコードを取得
                    query = "SELECT break_id, break_begin_time FROM break_time WHERE punch_id = %s AND break_end_time IS NULL"
                    cursor.execute(query, (punch_id,))
                    result = cursor.fetchone()
                    logger.info(f"Executed query to fetch break_time: {query} with parameters: {punch_id}")
                    logger.info(f"Query result: {result}")

                    if result:
                        break_id = result[0]
                        break_begin_time = result[1]

                        try:
                            # クエリの外部で休憩時間を計算する
                            break_duration = int((break_end_time - break_begin_time).total_seconds() // 60)

                            # 取得したレコードのbreak_end_timeに現在の日時を設定し、break_durationを計算して更新
                            query = "UPDATE break_time SET break_end_time = %s, break_duration = %s WHERE break_id = %s"
                            break_end_time_str = break_end_time.strftime('%Y-%m-%d %H:%M:%S')
                            logger.info(f"Executing update query: {query} with parameters: {break_end_time_str}, {break_duration}, {break_id}")
                            cursor.execute(query, (break_end_time_str, break_duration, break_id))
                            connection.commit()
                            logger.info(f"Break ended at {break_end_time} for user {user_id} in workspace {workspace_id} with duration {break_duration} min")

                        except Exception as e:
                            logger.error(f"Error updating break_time: {e}")
                            raise

                        try:
                            # 休憩時間の合計を計算
                            total_break_hours, total_break_minutes = get_total_break_duration(punch_id)
                            logger.info(f"Total break duration calculated: {total_break_hours} hours and {total_break_minutes} minutes")

                            # ユーザーのホームを更新して業務中のステータスを表示
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
                                                    "text": f":clock1: *現在のステータス*\n- ステータス: 業務中\n- 開始時刻: {break_end_time.strftime('%H:%M')}\n- 休憩時間: {total_break_hours}時間{total_break_minutes}分"
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
                                raise

                        except Exception as e:
                            logger.error(f"Error calculating total break duration: {e}")
                            raise

                    else:
                        logger.warning(f"No ongoing break found for user {user_id} in workspace {workspace_id}")
                        raise ValueError("No ongoing break found")

                except Exception as e:
                    logger.error(f"Error fetching break_time: {e}")
                    raise

            else:
                logger.warning(f"No ongoing work session found for user {user_id} in workspace {workspace_id}")
                raise ValueError("No ongoing work session found")

        except Exception as e:
            logger.error(f"Error fetching punch_time: {e}")
            raise

        finally:
            cursor.close()
            connection.close()
            logger.info("DB connection closed")

    except Exception as e:
        logger.error(f"Error in handle_break_end: {e}")

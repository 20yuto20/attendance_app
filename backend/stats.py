import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from auth import auth  # auth.pyからauth関数をimport
from slack_bolt import App 
from slack_bolt.adapter.socket_mode import SocketModeHandler
from datetime import datetime, timedelta
import re
from slack import WebClient
import warnings
import os
import json

# Slack Botのトークンを設定
app = App(token=os.environ["SLACK_BOT_TOKEN"])

# 統計のモーダルを開く処理
def open_stats_modal(ack, body, client):
    try:
        # 統計情報を取得
        output_file, total_working_time, average_working_time = plot_data()
        
        # モーダルを開く
        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "callback_id_stats_modal",
                "title": {
                    "type": "plain_text",
                    "text": ":bar_chart: 勤怠記録",
                    "emoji": True
                },
                "close": {
                    "type": "plain_text",
                    "text": "閉じる",
                    "emoji": True
                },
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "plain_text",
                            "text": f"勤務時間の合計: {total_working_time}分\n"
                                    f"勤務時間の平均: {average_working_time:.2f}分",
                            "emoji": True
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "plain_text",
                            "text": "勤務時間のグラフ表示",
                            "emoji": True
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "image",
                        "image_url": output_file,
                        "alt_text": "勤務時間のグラフ"
                    }
                ]
            }
        )     
        ack()
    except Exception as e:
        print(f"Error open stats modal: {e}")
        ack()


# 統計情報を取得する処理
def plot_data():
    try:
        # Google Sheets API にアクセスするための認証情報を取得
        sheet = auth()

        # データを取得してDataFrameに変換
        data = sheet.get_all_values()
        df = pd.DataFrame(data[1:], columns=data[0])

        # 日付をdatetime型に変換
        df['日付'] = pd.to_datetime(df['日付'])

        # 指定された月のデータをフィルタリング
        current_month = pd.Timestamp.now().month
        df = df[df['日付'].dt.month == current_month]

        # 日付別の業務時間グラフを作成
        plt.figure(figsize=(12, 6))
        df['稼働時間'] = df['稼働時間'].str.extract(r'(\d+)', expand=False).astype(int)
        df.groupby('日付')['稼働時間'].sum().plot(kind='bar')
        plt.title('日付別の業務時間')
        plt.xlabel('日付')
        plt.ylabel('業務時間(分)')
        
        # グラフをファイルとして保存
        output_file = 'output.png'
        plt.savefig(output_file)
        
        # 勤務時間の平均値・合計値を計算
        total_working_time = df['稼働時間'].sum()
        average_working_time = df['稼働時間'].mean()

        return output_file, total_working_time, average_working_time
        
    except Exception as e:
        print(f"Error plotting data: {e}")
        return None, None, None

# 関数を実行して結果を取得
output_file, total_working_time, average_working_time = plot_data()
print(f"勤務時間の合計: {total_working_time}分")
print(f"勤務時間の平均: {average_working_time:.2f}分")
print(f"グラフ画像の保存先: {output_file}")

import mysql.connector

# このhost~databaseまでの変数は本番環境の際はos.environで環境変数から取得すること
def get_db_connection():
    # 今はローカルの値
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="s692948PFddH8i",
        database="atd_app_db"
    )

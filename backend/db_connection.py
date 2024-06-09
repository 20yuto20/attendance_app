import os
import mysql.connector
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

def get_db_connection():
    connection = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST'),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DB')
    )
    return connection

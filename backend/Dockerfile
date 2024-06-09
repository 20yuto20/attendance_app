# ベースイメージを指定
FROM python:3.9-slim

# 作業ディレクトリを作成
WORKDIR /app

# 依存関係をインストール
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . /app

# ポート番号を指定（適宜変更）
EXPOSE 80

# アプリケーションを起動
CMD ["python", "main.py"]

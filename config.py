import os

# データベースファイル名
DB_NAME = "safety_app.db"

# 画像保存ディレクトリ (app.pyからの相対パスを想定)
IMAGE_DIR = "uploaded_images"

# IMAGE_DIRが存在しない場合は作成
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

import sqlite3
import os
import sys

# --- Adjust Python Path to Find 'config' --- #
# Get the absolute path to the directory containing this file (db/connection.py)
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Go one level up to the project root directory
_PROJECT_ROOT = os.path.dirname(_CURRENT_DIR)
# Add the project root to sys.path if it's not already there
if _PROJECT_ROOT not in sys.path:
    sys.path.append(_PROJECT_ROOT)

# Now we can import from the parent directory
from config import DB_NAME

# --- Calculate Absolute DB Path ---
# _PROJECT_ROOT is already calculated above
_DB_PATH = os.path.join(_PROJECT_ROOT, DB_NAME)

# データベース接続を取得
def get_db_connection():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row # カラム名でアクセスできるようにする
    return conn

# データベース初期化
def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 部署テーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')

    # 現場テーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            department_id INTEGER NOT NULL,
            start_date TEXT NOT NULL,       -- YYYY-MM-DD形式
            end_date TEXT,              -- YYYY-MM-DD形式, NULL許可
            is_suspended INTEGER DEFAULT 0, -- 休工中フラグ (0:稼働中, 1:休工中)
            default_employee_workers INTEGER DEFAULT 0,
            default_partner_workers INTEGER DEFAULT 0,
            FOREIGN KEY (department_id) REFERENCES departments(id)
        )
    ''')

    # 現場と作業番号の中間テーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS site_jobnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER NOT NULL,
            job_no TEXT NOT NULL,
            FOREIGN KEY(site_id) REFERENCES sites(id)
        )
    ''')

    # 日誌入力時の点検項目マスタ
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS action_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL UNIQUE
        )
    ''')

    # 予定入力時のリスク評価マスタ
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS risk_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL UNIQUE
        )
    ''')

    # 安全日誌（実績）テーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS safety_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, -- YYYY-MM-DD
            site_id INTEGER NOT NULL,
            employee_workers INTEGER NOT NULL, -- 社員作業員数
            partner_workers INTEGER NOT NULL, -- 協力会社作業員数
            task TEXT NOT NULL,
            action_check TEXT, -- 点検項目のJSON配列 '["項目1", "項目2"]'
            author TEXT NOT NULL, -- 記録者（現場責任者ユーザー名）
            image_path TEXT, -- 画像ファイルパス
            approved INTEGER DEFAULT 0, -- 承認フラグ (0: 未承認, 1: 承認済, 2: 却下)
            comment TEXT, -- 承認/却下時のコメント
            approver TEXT, -- 承認/却下者（部署責任者ユーザー名）
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (site_id) REFERENCES sites(id)
        )
    ''')

    # 作業予定テーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS safety_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER NOT NULL,
            planned_date TEXT NOT NULL, -- YYYY-MM-DD
            task TEXT NOT NULL,
            employee_workers INTEGER NOT NULL,
            partner_workers INTEGER NOT NULL,
            risk_check TEXT, -- リスク評価項目のJSON '{"level": "高", "items": ["項目A"]}'
            risk_action TEXT, -- リスク対策
            created_by TEXT NOT NULL, -- 作成者（現場責任者ユーザー名）
            approved INTEGER DEFAULT 0, -- 承認フラグ (0: 未承認, 1: 承認済, 2: 却下)
            comment TEXT, -- 承認/却下時のコメント
            approver TEXT, -- 承認/却下者（部署責任者ユーザー名）
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (site_id) REFERENCES sites(id)
        )
    ''')

    # --- 初期データ投入（存在しない場合のみ）---
    try:
        # 部署
        cursor.execute("INSERT INTO departments (name) VALUES ('開発部'), ('営業部')")
        # 現場 (job_numbers を削除)
        cursor.execute("INSERT INTO sites (name, department_id, start_date, default_employee_workers, default_partner_workers, is_suspended, end_date) VALUES ('現場A', 1, '2024-01-01', 5, 10, 0, NULL), ('現場B', 1, '2024-03-01', 3, 5, 0, '2025-12-31'), ('現場C', 2, '2023-10-01', 8, 15, 1, '2024-06-30')")
        # 点検項目マスタ
        cursor.execute("INSERT INTO action_checks (item) VALUES ('整理整頓'), ('安全通路確保'), ('火気管理'), ('開口部養生'), ('ヘルメット着用')")
        # リスク評価マスタ
        cursor.execute("INSERT INTO risk_checks (item) VALUES ('墜落・転落'), ('飛来・落下'), ('感電'), ('熱中症'), ('酸欠')")

        # --- ダミーデータ挿入（毎回挿入、必要に応じて削除・調整） ---
        # 既存のダミーデータを削除 (必要に応じてコメント解除)
        # cursor.execute("DELETE FROM site_jobnos")
        # cursor.execute("DELETE FROM safety_logs")
        # cursor.execute("DELETE FROM safety_plans")

        # 現場と作業番号の紐付け
        cursor.execute("INSERT INTO site_jobnos (site_id, job_no) VALUES (1, 'JOB001'), (1, 'JOB002'), (2, 'JOB003'), (3, 'JOB004')")

        # 安全日誌（実績）ダミーデータ
        cursor.execute("INSERT INTO safety_logs (date, site_id, employee_workers, partner_workers, task, action_check, author, image_path, approved, comment, approver) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       ('2024-07-15', 1, 5, 8, '基礎工事', '["整理整頓", "安全通路確保"]' , '現場担当者A', 'images/sample1.jpg', 1, '問題なし', '部署責任者X'))
        cursor.execute("INSERT INTO safety_logs (date, site_id, employee_workers, partner_workers, task, action_check, author, image_path, approved, comment, approver) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       ('2024-07-15', 2, 3, 4, '内部配線', '["火気管理", "感電注意"]' , '現場担当者B', None, 0, None, None))
        cursor.execute("INSERT INTO safety_logs (date, site_id, employee_workers, partner_workers, task, action_check, author, image_path, approved, comment, approver) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       ('2024-07-16', 1, 6, 9, '鉄骨組立', '["整理整頓", "ヘルメット着用"]' , '現場担当者A', None, 2, '整理整頓不十分', '部署責任者X'))

        # 作業予定ダミーデータ
        cursor.execute("INSERT INTO safety_plans (site_id, planned_date, task, employee_workers, partner_workers, risk_check, risk_action, created_by, approved, comment, approver) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (1, '2024-07-17', '外壁塗装準備', 4, 6, '{"level": "中", "items": ["墜落・転落"]}', '足場点検、安全帯使用徹底', '現場担当者A', 1, '安全対策問題なし', '部署責任者X'))
        cursor.execute("INSERT INTO safety_plans (site_id, planned_date, task, employee_workers, partner_workers, risk_check, risk_action, created_by, approved) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (2, '2024-07-17', '天井ボード貼り', 2, 3, '{"level": "小", "items": []}', '特記事項なし', '現場担当者B', 0))
        cursor.execute("INSERT INTO safety_plans (site_id, planned_date, task, employee_workers, partner_workers, risk_check, risk_action, created_by, approved, comment, approver) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (1, '2024-07-18', '外壁塗装', 5, 7, '{"level": "高", "items": ["墜落・転落", "飛来・落下"]}', '強風時の作業中止基準設定、保護帽着用', '現場担当者A', 0, '安全対策問題なし', '部署責任者X'))

        print("Dummy data inserted successfully.")
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database initialization error: {e}")
        conn.rollback() # Rollback changes on error
    finally:
        conn.close()

    print(f"Database initialization check complete. Using DB at: {_DB_PATH}")


if __name__ == '__main__':
    print(f"Attempting manual initialization of database at: {_DB_PATH}")
    # 既存のDBファイルを削除する場合、以下のコメントを解除
    # if os.path.exists(_DB_PATH):
    #     try:
    #         os.remove(_DB_PATH)
    #         print(f"Removed existing database file: {_DB_PATH}")
    #     except OSError as e:
    #         print(f"Error removing file {_DB_PATH}: {e}")
    #         sys.exit(1) # エラーが発生したら終了

    initialize_database()
    print("Manual initialization finished.")

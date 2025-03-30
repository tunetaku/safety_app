import sqlite3 # sqlite3.Row を使用するためにインポート
from .connection import get_db_connection
import json # site_ids の処理で使う可能性 (今回は使わないが念の為)
import calendar # 月の日数取得のため

# --- 汎用データ取得 ---
def get_sites(): # 全現場取得
    conn = get_db_connection()
    sites = conn.execute('SELECT id, name FROM sites ORDER BY name').fetchall()
    conn.close()
    return sites

def get_sites_by_department(department_id):
    conn = get_db_connection()
    sites = conn.execute('SELECT id, name FROM sites WHERE department_id = ? ORDER BY name', (department_id,)).fetchall()
    conn.close()
    return sites

# site_id のリストから site のリストを取得 (これは元のまま役立つ可能性がある)
def get_sites_by_ids(site_ids):
    if not site_ids:
        return []
    conn = get_db_connection()
    placeholders = ',' .join('?' * len(site_ids))
    query = f'SELECT id, name FROM sites WHERE id IN ({placeholders}) ORDER BY name'
    sites = conn.execute(query, site_ids).fetchall()
    conn.close()
    return sites

# ★追加: site名のリストから site のリストを取得
def get_sites_by_names(site_names):
    if not site_names:
        return []
    conn = get_db_connection()
    placeholders = ',' .join('?' * len(site_names))
    query = f'SELECT id, name FROM sites WHERE name IN ({placeholders}) ORDER BY name'
    sites = conn.execute(query, site_names).fetchall()
    conn.close()
    return sites

# ★追加: site名のリストから site_id のリストを取得
def get_site_ids_by_names(site_names):
    if not site_names:
        return []
    conn = get_db_connection()
    placeholders = ',' .join('?' * len(site_names))
    query = f'SELECT id FROM sites WHERE name IN ({placeholders})'
    # fetchall() はタプルのリスト [(1,), (2,)] を返すので、リスト内包表記でIDのリスト [1, 2] に変換
    ids = [row['id'] for row in conn.execute(query, site_names).fetchall()]
    conn.close()
    return ids

def get_departments(): # 全部署取得 (sqlite3.Row のリストを返す)
    conn = get_db_connection()
    departments = conn.execute('SELECT id, name FROM departments ORDER BY name').fetchall()
    conn.close()
    return departments

# ★追加: 全部署IDと名前を辞書のリストで取得 (新しい関数)
def get_all_departments_with_ids():
    """全ての部署のIDと名前を辞書のリストで取得する"""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row # 結果を辞書ライクにアクセスするため
    departments = conn.execute('SELECT id, name FROM departments ORDER BY name').fetchall()
    conn.close()
    # sqlite3.Row を通常の辞書に変換
    return [{'id': row['id'], 'name': row['name']} for row in departments]

# ★追加: 全現場名を取得 (設定画面用)
def get_all_site_names():
    conn = get_db_connection()
    names = [row['name'] for row in conn.execute('SELECT name FROM sites ORDER BY name').fetchall()]
    conn.close()
    return names

def get_action_checks(): # 点検項目マスタ取得
    conn = get_db_connection()
    checks = conn.execute('SELECT id, item FROM action_checks ORDER BY id').fetchall()
    conn.close()
    return [{'id': row['id'], 'item': row['item']} for row in checks]

def get_risk_checks(): # リスク評価項目マスタ取得
    conn = get_db_connection()
    checks = conn.execute('SELECT id, item FROM risk_checks ORDER BY id').fetchall()
    conn.close()
    return [{'id': row['id'], 'item': row['item']} for row in checks]

# --- 部署責任者向け データ取得 ---
def get_logs_for_approval(department_id):
    conn = get_db_connection()
    logs = conn.execute('''
        SELECT sl.*, s.name as site_name
        FROM safety_logs sl
        JOIN sites s ON sl.site_id = s.id
        WHERE s.department_id = ? AND sl.approved = 0
        ORDER BY sl.date DESC, s.name
    ''', (department_id,)).fetchall()
    conn.close()
    return logs

def get_plans_for_approval(department_id):
    conn = get_db_connection()
    plans = conn.execute('''
        SELECT sp.*, s.name as site_name
        FROM safety_plans sp
        JOIN sites s ON sp.site_id = s.id
        WHERE s.department_id = ? AND sp.approved = 0
        ORDER BY sp.planned_date DESC, s.name
    ''', (department_id,)).fetchall()
    conn.close()
    return plans

# --- 部署責任者向け 承認済みデータ取得 (Optional) ---
def get_approved_logs(department_id):
    # 必要に応じて実装
    pass

def get_approved_plans(department_id):
    # 必要に応じて実装
    pass

# --- 管理部門向け データ取得 ---
def get_all_safety_logs_with_details():
    conn = get_db_connection()
    logs = conn.execute('''
        SELECT
            sl.id, sl.date, s.name as site_name, d.name as department_name,
            sl.employee_workers, sl.partner_workers, sl.task, sl.action_check,
            sl.author, sl.image_path, sl.approved, sl.comment, sl.approver
        FROM safety_logs sl
        JOIN sites s ON sl.site_id = s.id
        JOIN departments d ON s.department_id = d.id
        ORDER BY sl.date DESC, s.name
    ''').fetchall()
    conn.close()
    return logs

def get_all_safety_plans_with_details():
    conn = get_db_connection()
    plans = conn.execute('''
        SELECT
            sp.id, sp.planned_date, s.name as site_name, d.name as department_name,
            sp.employee_workers, sp.partner_workers, sp.task, sp.risk_check,
            sp.risk_action, sp.created_by, sp.approved, sp.comment, sp.approver
        FROM safety_plans sp
        JOIN sites s ON sp.site_id = s.id
        JOIN departments d ON s.department_id = d.id
        ORDER BY sp.planned_date DESC, s.name
    ''').fetchall()
    conn.close()
    return plans

# --- 現場責任者向け データ取得 ---
def get_log_by_site_and_date(site_id, date_str):
    """指定現場・日付の実績ログを取得 (古い、単日用)"""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    log = conn.execute('SELECT * FROM safety_logs WHERE site_id = ? AND date = ?', (site_id, date_str)).fetchone()
    conn.close()
    return log

def get_plan_by_site_and_date(site_id, date_str):
    """指定現場・日付の安全計画を取得 (古い、単日用)"""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    plan = conn.execute('SELECT * FROM safety_plans WHERE site_id = ? AND planned_date = ?', (site_id, date_str)).fetchone()
    conn.close()
    return plan

# --- Check Items ---
def get_action_checks(): # 必須項目
    conn = get_db_connection()
    checks = conn.execute('SELECT id, item FROM action_checks ORDER BY id').fetchall()
    conn.close()
    return [{'id': row['id'], 'item': row['item']} for row in checks]

def get_risk_checks(): # リスク項目
    conn = get_db_connection()
    checks = conn.execute('SELECT id, item FROM risk_checks ORDER BY id').fetchall()
    conn.close()
    return [{'id': row['id'], 'item': row['item']} for row in checks]

# --- Safety Logs and Plans ---
def get_safety_logs_summary_by_site(site_name):
    """
    指定された現場名に関連する安全実績ログの概要を取得する。
    カレンダー表示用に、日付と承認ステータスを返す。
    """
    site_id = get_site_ids_by_names([site_name])[0] # site_id を取得
    if not site_id:
        print(f"Warning: Site ID not found for site name '{site_name}'")
        return []

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    try:
        # WHERE 句を site_id に修正
        summary = conn.execute(
            """
            SELECT date, approved
            FROM safety_logs
            WHERE site_id = ?
            ORDER BY date
            """,
            (site_id,) # site_id を使用
        ).fetchall()
        return [dict(row) for row in summary]
    except Exception as e:
        print(f"Error fetching safety log summary for site '{site_name}' (ID: {site_id}): {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_safety_plans_summary_by_site(site_name):
    """
    指定された現場名に関連する安全作業計画の概要を取得する。
    カレンダー表示用に、予定日と作業内容(task)を返す。
    """
    site_id = get_site_ids_by_names([site_name])[0] # site_id を取得
    if not site_id:
        print(f"Warning: Site ID not found for site name '{site_name}'")
        return []

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    try:
        # SELECT句を task に、WHERE句を site_id に修正
        summary = conn.execute(
            """
            SELECT planned_date, task
            FROM safety_plans
            WHERE site_id = ?
            ORDER BY planned_date
            """,
            (site_id,) # site_id を使用
        ).fetchall()
        return [dict(row) for row in summary]
    except Exception as e:
        print(f"Error fetching safety plan summary for site '{site_name}' (ID: {site_id}): {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_safety_logs_by_site_and_date(site_name, selected_date):
    """
    指定された現場名と日付に一致する安全実績ログの詳細を取得する。
    """
    site_id = get_site_ids_by_names([site_name])[0] # site_id を取得
    if not site_id:
        print(f"Warning: Site ID not found for site name '{site_name}'")
        return []

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    try:
        # WHERE 句を site_id に修正 (日付カラムは 'date')
        logs = conn.execute(
            """
            SELECT * FROM safety_logs
            WHERE site_id = ? AND date = ?
            ORDER BY created_at DESC
            """,
            (site_id, selected_date) # site_id を使用
        ).fetchall()
        return [dict(row) for row in logs]
    except Exception as e:
        print(f"Error fetching safety logs for site '{site_name}' (ID: {site_id}) on {selected_date}: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_safety_plans_by_site_and_date(site_name, selected_date):
    """
    指定された現場名と日付に一致する安全作業計画の詳細を取得する。
    """
    site_id = get_site_ids_by_names([site_name])[0] # site_id を取得
    if not site_id:
        print(f"Warning: Site ID not found for site name '{site_name}'")
        return []

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    try:
        # WHERE 句を site_id と planned_date に修正
        plans = conn.execute(
            """
            SELECT * FROM safety_plans
            WHERE site_id = ? AND planned_date = ?
            ORDER BY id DESC
            """,
            (site_id, selected_date) # site_id と selected_date を使用
        ).fetchall()
        return [dict(row) for row in plans]
    except Exception as e:
        print(f"Error fetching safety plans for site '{site_name}' (ID: {site_id}) on {selected_date}: {e}")
        return []
    finally:
        if conn:
            conn.close()

# --- Helper Functions ---
def _dict_factory(cursor, row):
    """sqlite3.Row を辞書に変換するファクトリ"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# --- Log/Plan Data Getters (Month / ID) --- NEW ---
def get_safety_logs_by_site_and_month(site_id, year, month):
    """指定された現場IDと年月の実績ログデータを日付ごとにまとめて取得"""
    conn = get_db_connection()
    conn.row_factory = _dict_factory # 結果を辞書で取得
    month_str = f"{month:02d}"
    start_date = f"{year}-{month_str}-01"
    last_day = calendar.monthrange(year, month)[1]
    end_date = f"{year}-{month_str}-{last_day:02d}"

    logs_raw = conn.execute(
        'SELECT * FROM safety_logs WHERE site_id = ? AND date BETWEEN ? AND ? ORDER BY date',
        (site_id, start_date, end_date)
    ).fetchall()
    conn.close()

    # 日付をキーとする辞書に変換
    logs_by_date = {}
    for log in logs_raw:
        date_str = log['date']
        if date_str not in logs_by_date:
            logs_by_date[date_str] = []
        logs_by_date[date_str].append(log)
    return logs_by_date

def get_safety_plans_by_site_and_month(site_id, year, month):
    """指定された現場IDと年月の安全計画データを日付ごとにまとめて取得"""
    conn = get_db_connection()
    conn.row_factory = _dict_factory # 結果を辞書で取得
    month_str = f"{month:02d}"
    start_date = f"{year}-{month_str}-01"
    last_day = calendar.monthrange(year, month)[1]
    end_date = f"{year}-{month_str}-{last_day:02d}"

    plans_raw = conn.execute(
        'SELECT * FROM safety_plans WHERE site_id = ? AND planned_date BETWEEN ? AND ? ORDER BY planned_date',
        (site_id, start_date, end_date)
    ).fetchall()
    conn.close()

    # 日付をキーとする辞書に変換
    plans_by_date = {}
    for plan in plans_raw:
        date_str = plan['planned_date']
        if date_str not in plans_by_date:
            plans_by_date[date_str] = []
        plans_by_date[date_str].append(plan)
    return plans_by_date

def get_safety_log_by_id(log_id):
    """IDを指定して単一の実績ログを取得 (編集用)"""
    conn = get_db_connection()
    conn.row_factory = _dict_factory
    log = conn.execute('SELECT * FROM safety_logs WHERE id = ?', (log_id,)).fetchone()
    conn.close()
    return log

def get_safety_plan_by_id(plan_id):
    """IDを指定して単一の安全計画を取得 (編集用)"""
    conn = get_db_connection()
    conn.row_factory = _dict_factory
    plan = conn.execute('SELECT * FROM safety_plans WHERE id = ?', (plan_id,)).fetchone()
    conn.close()
    return plan

# 新しい関数: 現場の詳細情報（デフォルト作業員数など）を取得
def get_site_details(site_id):
    conn = get_db_connection()
    conn.row_factory = lambda cursor, row: {
        col[0]: row[idx] for idx, col in enumerate(cursor.description)
    }
    # sites テーブルから必要な列を取得 (列名は仮定)
    site = conn.execute(
        'SELECT id, default_employee_workers, default_partner_workers FROM sites WHERE id = ?',
        (site_id,)
    ).fetchone()
    conn.close()
    # 見つかった場合に辞書に id も含めて返す
    if site:
        site['id'] = site_id # 明示的にidを追加 (session state比較用)
        return site
    return None # 見つからない場合は None

# --- Department Functions ---
def get_departments():
    conn = get_db_connection()
    departments = conn.execute('SELECT id, name FROM departments ORDER BY name').fetchall()
    conn.close()
    return departments

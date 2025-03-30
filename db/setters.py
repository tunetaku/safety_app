import sqlite3
from .connection import get_db_connection
import streamlit as st

# --- 部署責任者向け データ更新/追加 ---
def update_log_approval(log_id, approver_name, comment):
    conn = get_db_connection()
    try:
        conn.execute('''
            UPDATE safety_logs
            SET approved = 1, approver = ?, comment = ?
            WHERE id = ?
        ''', (approver_name, comment, log_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error updating log approval: {e}")
        return False
    finally:
        conn.close()

def update_plan_approval(plan_id, approver_name, comment):
    conn = get_db_connection()
    try:
        conn.execute('''
            UPDATE safety_plans
            SET approved = 1, approver = ?, comment = ?
            WHERE id = ?
        ''', (approver_name, comment, plan_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error updating plan approval: {e}")
        return False
    finally:
        conn.close()

def add_site(site_name, department_id, start_date_str, end_date_str, emp_workers, part_workers, job_nos):
    """
    現場を新規登録し、関連する作業番号も site_jobnos テーブルに登録する。

    Args:
        site_name (str): 現場名
        department_id (int): 部署ID
        start_date_str (str): 管理開始日 (YYYY-MM-DD)
        end_date_str (str | None): 管理終了日 (YYYY-MM-DD) または None
        emp_workers (int): デフォルト作業員数（社員）
        part_workers (int): デフォルト作業員数（協力会社）
        job_nos (str): 作業番号 (カンマ区切り)

    Returns:
        bool: 登録に成功した場合は True、失敗した場合は False
    """
    conn = get_db_connection()
    cursor = conn.cursor() # カーソルを取得
    try:
        # 1. sites テーブルに現場情報を挿入
        cursor.execute('''INSERT INTO sites
                        (name, department_id, start_date, end_date, default_employee_workers, default_partner_workers)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                       (site_name, department_id, start_date_str, end_date_str, emp_workers, part_workers))

        # 2. 挿入された site の ID を取得
        site_id = cursor.lastrowid

        # 3. job_nos を分割し、site_jobnos テーブルに挿入
        if job_nos and site_id: # job_nos が空でなく、site_id が取得できた場合
            job_no_list = [j.strip() for j in job_nos.split(',') if j.strip()] # 空白を除去し、空でないものだけリスト化
            if job_no_list:
                job_data_to_insert = [(site_id, job_no) for job_no in job_no_list]
                cursor.executemany('''INSERT INTO site_jobnos (site_id, job_no)
                                    VALUES (?, ?)''', job_data_to_insert)

        conn.commit() # 全ての挿入が成功したらコミット
        return True
    except sqlite3.IntegrityError: # UNIQUE constraint failed (現場名が重複など)
        conn.rollback() # ロールバック
        print(f"Integrity error adding site or job numbers for '{site_name}'. Possibly duplicate site name.")
        # Streamlit環境で実行されている場合、st.error を使用
        if 'streamlit' in sys.modules:
             st.error(f"エラー: 現場名 '{site_name}' は既に登録されているか、他の整合性制約違反が発生しました。")
        return False
    except sqlite3.Error as e:
        conn.rollback() # ロールバック
        print(f"Database error adding site '{site_name}': {e}")
        if 'streamlit' in sys.modules:
            st.error(f"データベースエラーが発生しました: {e}")
        return False
    finally:
        conn.close()

# --- 現場責任者向け データ追加/更新 ---
def add_safety_log(date_str, site_id, employee_workers, partner_workers, task, action_check_json, author, image_path):
    conn = get_db_connection()
    try:
        conn.execute('''INSERT INTO safety_logs
                        (date, site_id, employee_workers, partner_workers, task, action_check, author, image_path)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                       (date_str, site_id, employee_workers, partner_workers, task, action_check_json, author, image_path))
        conn.commit()
        return True
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error adding safety log: {e}")
        return False
    finally:
        conn.close()

def update_safety_log(log_id, employee_workers, partner_workers, task, action_check_json, author, image_path):
    """既存の実績ログを更新する"""
    conn = get_db_connection()
    try:
        conn.execute('''UPDATE safety_logs SET
                        employee_workers = ?, partner_workers = ?, task = ?, action_check = ?, author = ?, image_path = ?
                        WHERE id = ?''',
                       (employee_workers, partner_workers, task, action_check_json, author, image_path, log_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error updating safety log {log_id}: {e}")
        return False
    finally:
        conn.close()

def add_safety_plan(site_id, planned_date_str, task, employee_workers, partner_workers, risk_check_json, risk_action, created_by):
    conn = get_db_connection()
    try:
        conn.execute('''INSERT INTO safety_plans
                        (site_id, planned_date, task, employee_workers, partner_workers, risk_check, risk_action, created_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                       (site_id, planned_date_str, task, employee_workers, partner_workers, risk_check_json, risk_action, created_by))
        conn.commit()
        return True
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error adding safety plan: {e}")
        return False
    finally:
        conn.close()

def update_safety_plan(plan_id, task, employee_workers, partner_workers, risk_check_json, risk_action, created_by):
    """既存の安全計画を更新する"""
    conn = get_db_connection()
    try:
        conn.execute('''UPDATE safety_plans SET
                        task = ?, employee_workers = ?, partner_workers = ?, risk_check = ?, risk_action = ?, created_by = ?
                        WHERE id = ?''',
                       (task, employee_workers, partner_workers, risk_check_json, risk_action, created_by, plan_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error updating safety plan {plan_id}: {e}")
        return False
    finally:
        conn.close()

def update_site_settings(site_id, is_suspended, default_emp, default_part):
    """現場の設定（休工状態、デフォルト人員）を更新する"""
    conn = get_db_connection()
    try:
        conn.execute("""
            UPDATE sites
            SET is_suspended = ?,
                default_employee_workers = ?,
                default_partner_workers = ?
            WHERE id = ?
        """, (1 if is_suspended else 0, default_emp, default_part, site_id))
        conn.commit()
        success = True
    except Exception as e:
        print(f"Error updating site settings for {site_id}: {e}")
        success = False
    finally:
        conn.close()
    return success

def update_approval_status(plan_id, log_id, approved, approver_comment, approver):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        status = 1 if approved else 0 # 承認なら1, 保留/未承認なら0

        # 予定の更新 (plan_id があれば)
        if plan_id is not None:
            cursor.execute(
                "UPDATE safety_plans SET approved = ?, comment = ?, approver = ? WHERE id = ?",
                (status, approver_comment, approver, plan_id)
            )

        # 実績の更新 (log_id があれば)
        if log_id is not None:
            cursor.execute(
                "UPDATE safety_logs SET approved = ?, comment = ?, approver = ? WHERE id = ?",
                (status, approver_comment, approver, log_id)
            )

        conn.commit()
        return True # 成功
    except Exception as e:
        print(f"Error updating approval status: {e}")
        conn.rollback()
        return False # 失敗
    finally:
        conn.close()

# 必要に応じて他の setter 関数もここに追加

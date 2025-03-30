# pages/1_現場責任者.py

import streamlit as st
import datetime as dt
from dateutil.relativedelta import relativedelta
import json
import os
import sys
import calendar # Added for monthrange

# --- Page Config --- ★追加
st.set_page_config(layout="wide")

# パスの設定
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

from db.getters import (
    get_site_details,
    get_safety_logs_by_site_and_month,
    get_safety_plans_by_site_and_month,
    get_safety_log_by_id,
    get_safety_plan_by_id,
    get_action_checks,
    get_risk_checks,
)
from db.setters import (
    add_safety_log,
    update_safety_log,
    add_safety_plan,
    update_safety_plan,
    update_site_settings
)
from config import IMAGE_DIR # 画像アップロード先

# ★ プロジェクトルートの絶対パスを取得 (pagesフォルダの親)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Helper Functions ---
def get_japanese_weekday(date_obj):
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    return weekdays[date_obj.weekday()]

def is_weekend(date_obj):
    return date_obj.weekday() >= 5 # 5:土曜日, 6:日曜日

def save_uploaded_file(uploaded_file, save_dir):
    """アップロードされたファイルを指定ディレクトリに保存"""
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    file_path = os.path.join(save_dir, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    # 保存したファイルの相対パスを返す (streamlitがアクセス可能なパス)
    # 注意: これはローカル実行時の単純な例。デプロイ環境では異なる場合がある。
    # IMAGE_DIR が 'static/images' のような形を想定
    relative_path = os.path.join(IMAGE_DIR, uploaded_file.name)
    return relative_path

# 例: 実績ログモーダル (簡略版 - 実際には既存のコードをベースに改修)
@st.dialog("実績ログ入力・編集") # Streamlit 1.38+
def show_log_modal_new(log_id=None, target_date=None, site_id=None, user_name=None, plan_details=None): # Add plan_details
    """安全実績ログの入力・編集モーダル"""
    log_data = {}
    # --- セッションステートキー定義 (コピー機能用) ---
    copy_key_prefix = f"copy_plan_to_log_{target_date}_{site_id}" # より一意なキー
    copy_triggered_key = f"{copy_key_prefix}_triggered"
    copied_plan_key = f"{copy_key_prefix}_data"

    # --- デフォルト値の初期化 ---
    default_task = ""
    default_emp = 0
    default_part = 0
    default_image_path = None
    default_action_ids_str = '[]'

    # --- 「予定の内容をコピー」ボタン (フォームの外に配置) ---
    if plan_details:
        if st.button("📋 予定の内容をコピー", key=f"copy_button_{target_date}_{log_id}"):
            st.session_state[copy_triggered_key] = True
            st.session_state[copied_plan_key] = plan_details
            # st.rerun() は不要。ボタンクリックで自動的に再実行される

    # --- デフォルト値の設定ロジック ---
    if st.session_state.get(copy_triggered_key):
        # コピーがトリガーされた場合、計画の詳細をデフォルト値として使用
        copied_plan = st.session_state.get(copied_plan_key, {})
        default_task = copied_plan.get('task', '')
        default_emp = copied_plan.get('employee_workers', 0)
        default_part = copied_plan.get('partner_workers', 0)
        # Clean up session state after using it
        del st.session_state[copy_triggered_key]
        if copied_plan_key in st.session_state:
            del st.session_state[copied_plan_key]
    elif log_id:
        # 編集モードの場合、既存のログデータをデフォルト値として使用
        log_data = get_safety_log_by_id(log_id) or {}
        default_task = log_data.get('task', '')
        default_emp = log_data.get('employee_workers', 0)
        default_part = log_data.get('partner_workers', 0)
        default_image_path = log_data.get('image_path')
        default_action_ids_str = log_data.get('action_check_ids', '[]')
    # 新規作成モード（コピーなし）の場合は、初期化されたデフォルト値がそのまま使われる

    # --- モーダルのタイトル ---
    if log_id:
        st.write(f"{target_date} 実績ログ編集")
    else:
        st.write(f"{target_date} 新規実績ログ")

    # --- フォーム --- # このキーも一意にする
    with st.form(key=f"log_form_{target_date}_{log_id}", clear_on_submit=False):
        task = st.text_area("本日の作業内容", value=default_task, height=150)
        col1, col2 = st.columns(2)
        with col1:
            employee_workers = st.number_input("作業員数（社員）", min_value=0, value=default_emp, step=1)
        with col2:
            partner_workers = st.number_input("作業員数（協力会社）", min_value=0, value=default_part, step=1)

        # --- 活動チェック項目 --- # default_action_ids_str を使用
        default_selected_action_ids = json.loads(default_action_ids_str)
        all_actions = get_action_checks() # 活動項目リストを取得
        action_map_id_to_item = {a['id']: a['item'] for a in all_actions}
        action_map_item_to_id = {v: k for k, v in action_map_id_to_item.items()}
        action_items = list(action_map_item_to_id.keys())
        # デフォルトで選択されるべき項目名のリストを作成
        default_selected_items = [action_map_id_to_item[id] for id in default_selected_action_ids if id in action_map_id_to_item]

        selected_items_log = st.multiselect(
            "本日の安全活動（該当項目を選択）",
            options=action_items,
            default=default_selected_items
        )

        # --- 画像アップロード --- # default_image_path を使用
        uploaded_image = st.file_uploader("現場写真（任意）", type=["jpg", "jpeg", "png"])
        current_image_path = default_image_path # 現在表示・保存されている画像のパス
        image_to_save = current_image_path # DBに保存するパス（変更がなければ現在のパス）
        delete_image_request = False # 削除リクエストフラグ

        if uploaded_image is not None:
            # 新しい画像がアップロードされた場合
            image_bytes = uploaded_image.getvalue()
            # 保存先ディレクトリ（例：static/images/site_id/date）- 相対パス
            today_str = target_date
            image_dir = os.path.join('static', 'images', str(site_id), today_str)
            # ファイル名（例：upload_timestamp.png）
            timestamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
            image_filename = f"upload_{timestamp}.{uploaded_image.name.split('.')[-1]}"
            # DB保存用パス (static/images/...)
            image_relative_path = os.path.join(image_dir, image_filename).replace("\\", "/")
            
            # --- 絶対パスの計算 --- 
            absolute_save_dir = os.path.join(PROJECT_ROOT, image_dir) # 絶対ディレクトリパス
            image_save_path = os.path.join(absolute_save_dir, image_filename) # 絶対ファイルパス

            # --- デバッグ出力 (確認後削除) --- 
            # st.write(f"DEBUG: IMAGE_DIR = {IMAGE_DIR}") # 不要なので削除
            st.write(f"DEBUG: image_save_path = {image_save_path}")
            # --- デバッグ出力ここまで --- #

            try:
                # 絶対ディレクトリを作成 
                os.makedirs(absolute_save_dir, exist_ok=True)
                # 絶対パスでファイルを書き込み 
                with open(image_save_path, "wb") as f:
                    f.write(image_bytes)
                st.success(f"画像を {image_relative_path} に保存しました。") # メッセージは相対パス
                image_to_save = image_relative_path # DBには相対パスを保存
            except Exception as e:
                st.error(f"画像の保存に失敗しました: {e} (Path: {image_save_path})") # エラーには絶対パス表示
                # image_to_save は current_image_path のまま
        elif current_image_path:
            st.write("現在の画像:")
            # 絶対パスに変換して表示試行 
            display_image_path = os.path.join(PROJECT_ROOT, current_image_path)
            # st.write(f"DEBUG: display_image_path = {display_image_path}") # 表示パスのデバッグ出力
            if os.path.exists(display_image_path):
                st.image(display_image_path, width=300)
                # --- ボタンをチェックボックスに変更 --- ★修正
                delete_image_request = st.checkbox("現在の画像を削除する", key=f"delete_image_chk_{target_date}_{log_id}")
            else:
                st.caption(f"画像が見つかりません: {display_image_path}") # 見つからない場合も絶対パス表示
            # --- 元のボタンとrerunは削除 --- ★修正
            # if st.button("画像を削除", key=f"delete_image_{target_date}_{log_id}"):
            #      image_to_save = None # 削除フラグ（NoneをDBに保存）
            #      # 画像表示を即時更新するため再実行（フォーム送信前）
            #      st.rerun()

        submitted = st.form_submit_button("保存")
        if submitted:
            # 選択された項目リストからIDリストに変換
            selected_action_ids = [action_map_item_to_id[item] for item in selected_items_log if item in action_map_item_to_id]

            # --- 画像パスの最終決定 --- ★修正
            final_image_to_save = image_to_save # まず現在の値を引き継ぐ

            if uploaded_image is not None:
                 # アップロード処理中に image_to_save が更新されているはずなので、それを final_image_to_save に反映
                 final_image_to_save = image_to_save
            elif current_image_path and delete_image_request: # 削除チェックボックスがオンの場合
                 final_image_to_save = None # DBにはNoneを保存

            success = False
            if log_id: # 更新
                success = update_safety_log(
                    log_id=log_id,
                    task=task,
                    employee_workers=employee_workers,
                    partner_workers=partner_workers,
                    action_check_json=json.dumps(selected_action_ids),
                    author=user_name,
                    image_path=final_image_to_save # 最終決定したパス
                )
                if success:
                    st.success(f"{target_date} の実績ログを更新しました。")
                else:
                    st.error("実績ログの更新に失敗しました。")
            else: # 新規作成
                # target_date は既に文字列なので、そのまま渡す
                success = add_safety_log(
                    site_id=site_id,
                    date_str=target_date, # strftime を削除し、target_date を直接使用
                    task=task,
                    employee_workers=employee_workers,
                    partner_workers=partner_workers,
                    action_check_json=json.dumps(selected_action_ids),
                    author=user_name,
                    image_path=final_image_to_save
                )
                if success:
                    st.success(f"{target_date} の実績ログを新規作成しました。")
                else:
                    st.error("実績ログの作成に失敗しました。")

            if success:
                return True # 成功を示すためにTrueを返す
            else:
                return False # 失敗を示すためにFalseを返す (任意)


# 同様に show_plan_modal_new を作成 (add_safety_plan, update_safety_plan を呼び出す)
# ... (show_plan_modal_new の実装) ...
@st.dialog("安全計画入力・編集")
def show_plan_modal_new(plan_id=None, target_date=None, site_id=None, user_name=None,
                        default_employee_workers=0, default_partner_workers=0): # Add default worker counts
    """安全計画の入力・編集モーダルを表示"""
    plan_data = {}
    if plan_id:
        plan_data = get_safety_plan_by_id(plan_id) or {}
        target_date = plan_data.get('planned_date', target_date)

    st.subheader(f"{target_date} の安全計画 ({'編集' if plan_id else '新規入力'})")

    try:
        site_settings = get_site_details(site_id)
        if not site_settings:
            st.error("現場情報の取得に失敗しました。")
            site_settings = {} # Fallback
    except Exception as e:
        st.error(f"現場情報取得エラー: {e}")
        site_settings = {}
        
    default_employee_workers = plan_data.get('employee_workers', site_settings.get('default_employee_workers', 0))
    default_partner_workers = plan_data.get('partner_workers', site_settings.get('default_partner_workers', 0))
    default_task = plan_data.get('task', '')
    # --- リスクチェックのデフォルト値を新しい形式に合わせて読み込む --- #
    default_risk_check_json = plan_data.get('risk_check', '{}') # JSON文字列
    default_risk_action = plan_data.get('risk_action', '')

    # JSONをパースしてデフォルト値を取得 (常に新形式を想定)
    try:
        risk_data = json.loads(default_risk_check_json)
        if not isinstance(risk_data, dict): # 念のため型チェック
            risk_data = {} # 不正なら空の辞書
        default_risk_level_int = risk_data.get('level', 1) # デフォルトは低=1
        default_risk_ids = risk_data.get('items', [])    # デフォルトは空リスト
        if not isinstance(default_risk_ids, list): # 念のため型チェック
             default_risk_ids = [] # リストでなければ空にする
    except json.JSONDecodeError:
        # パース失敗時のデフォルト値
        default_risk_level_int = 1
        default_risk_ids = []

    # リスクレベルの数値を文字列に変換 (st.radio用)
    risk_level_map_int_to_str = {1: "低", 2: "中", 3: "高"}
    default_risk_level_str = risk_level_map_int_to_str.get(default_risk_level_int, "低")

    # リスク項目IDを項目名に変換 (st.multiselect用)
    all_risks = get_risk_checks() # リスク項目リストを取得
    risk_map_id_to_item = {a['id']: a['item'] for a in all_risks}
    risk_map_item_to_id = {v: k for k, v in risk_map_id_to_item.items()}
    risk_options_simple = [item['item'] for item in all_risks] # 表示用リスト
    # デフォルト選択項目を安全に計算 (存在しないIDは無視)
    default_selected_risks = [risk_map_id_to_item[rid] for rid in default_risk_ids if rid in risk_map_id_to_item]



    with st.form("plan_form"):
        task = st.text_area("作業内容(予定)", value=default_task, height=100)
        # 作業員数を2列で表示
        col1_workers, col2_workers = st.columns(2)
        with col1_workers:
            employee_workers = st.number_input(
                "作業員数(社員)", 
                min_value=0, 
                value=default_employee_workers, # Use passed default
                key=f"plan_emp_workers_{plan_id or 'new'}" # Unique key
            )
        with col2_workers:
            partner_workers = st.number_input(
                "作業員数(協力会社)", 
                min_value=0, 
                value=default_partner_workers,   # Use passed default
                key=f"plan_part_workers_{plan_id or 'new'}" # Unique key
            )
        # --- リスク評価 --- #
        #リスク評価のレベルをラジオで選ぶ
        risk_level = st.radio("リスクレベル", options=["低", "中", "高"], index=["低", "中", "高"].index(default_risk_level_str))
        st.markdown("**リスク評価**")
        selected_risk_items_plan = st.multiselect(
            "リスク項目を選択",
            options=risk_options_simple,
            default=default_selected_risks
        )

        risk_action = st.text_area("具体的対策", value=default_risk_action, height=100)

        submitted = st.form_submit_button("保存")
        if submitted:
            # --- リスクレベルと項目を新しい形式で保存 --- #
            # 1. リスクレベルのマッピング
            risk_level_map_str_to_int = {"低": 1, "中": 2, "高": 3}
            # 2. 選択されたレベルを数値に変換 (デフォルトは「低」= 1)
            selected_level_int = risk_level_map_str_to_int.get(risk_level, 1)
            # 3. 選択された項目リストからIDリストに変換 (既存)
            selected_risk_ids_to_save = [risk_map_item_to_id[item] for item in selected_risk_items_plan]
            # 4. 保存用辞書を作成
            risk_data_to_save = {
                "level": selected_level_int,
                "items": selected_risk_ids_to_save
            }
            # 5. JSON文字列に変換
            risk_check_json_to_save = json.dumps(risk_data_to_save)

            success = False
            if plan_id: # 更新
                success = update_safety_plan(
                    plan_id=plan_id,
                    task=task,
                    employee_workers=employee_workers,
                    partner_workers=partner_workers,
                    risk_check_json=risk_check_json_to_save, # 新しい形式のJSONを渡す
                    risk_action=risk_action,
                    created_by=user_name # 更新者も記録
                )
            else: # 新規追加
                success = add_safety_plan(
                    site_id=site_id,
                    planned_date_str=target_date,
                    task=task,
                    employee_workers=employee_workers,
                    partner_workers=partner_workers,
                    risk_check_json=risk_check_json_to_save, # 新しい形式のJSONを渡す
                    risk_action=risk_action,
                    created_by=user_name
                )

            if success:
                st.success("安全計画を保存しました。")
                return True # 成功したらTrueを返して閉じる
            else:
                st.error("安全計画の保存に失敗しました。")
                return False # 失敗を示すためにFalseを返す (任意)


# --- Main Script ---
# ユーザー情報取得 (新しい session_state キーを参照)
if 'user_name' not in st.session_state or not st.session_state.user_name:
    st.warning("ユーザー名が設定されていません。[設定]ページでユーザー情報を入力してください。")
    st.stop()
if 'user_role' not in st.session_state or st.session_state.user_role != '現場責任者':
    st.error("このページは現場責任者のみアクセスできます。役割を確認してください。")
    st.stop()
# ★★★ 修正点: 'current_site' の存在と形式をチェック ★★★
if 'current_site' not in st.session_state or \
   st.session_state.current_site is None or \
   not isinstance(st.session_state.current_site, dict) or \
   'id' not in st.session_state.current_site or \
   'name' not in st.session_state.current_site:
    st.warning("担当現場が設定されていません。[設定]ページで現場を選択してください。")
    st.stop()

current_user_name = st.session_state.user_name
current_user_role = st.session_state.user_role
current_site_info = st.session_state.current_site
current_site_id = current_site_info['id']
current_site_name = current_site_info['name']

# --- サイドバー: 現場設定フォーム ---
with st.sidebar:
    st.header("現場設定")
    try:
        site_settings = get_site_details(current_site_id)
        if not site_settings:
            st.error("現場情報の取得に失敗しました。")
            site_settings = {} # Fallback
    except Exception as e:
        st.error(f"現場情報取得エラー: {e}")
        site_settings = {}

    with st.form("site_settings_form"):
        st.subheader(f"設定: {current_site_name}") # Use fetched name

        is_suspended = st.checkbox(
            "休工中",
            value=bool(site_settings.get('is_suspended', 0)),
            help="チェックを入れると、部署責任者画面の現場リストで「休工中」と表示されます。"
        )
        default_emp = st.number_input(
            "社員デフォルト人員",
            min_value=0,
            value=site_settings.get('default_employee_workers', 0),
            help="安全計画や実績ログを新規追加する際の初期値として使用されます。"
        )
        default_part = st.number_input(
            "協力会社デフォルト人員",
            min_value=0,
            value=site_settings.get('default_partner_workers', 0),
            help="安全計画や実績ログを新規追加する際の初期値として使用されます。"
        )

        submitted = st.form_submit_button("設定を保存")
        if submitted:
            success = update_site_settings(current_site_id, is_suspended, default_emp, default_part)
            if success:
                st.success("現場設定を更新しました。")
                # Update site name in session state if it could change (unlikely here)
                st.rerun()
            else:
                st.error("現場設定の更新に失敗しました。")

# --- メインコンテンツエリア ---
# Get default workers for the site (using updated session state if available)
try:
    site_settings = get_site_details(current_site_id)
    if not site_settings:
        st.error("現場情報の取得に失敗しました。")
        site_settings = {} # Fallback
except Exception as e:
    st.error(f"現場情報取得エラー: {e}")
    site_settings = {}

default_employee_workers = site_settings.get('default_employee_workers', 0)
default_partner_workers = site_settings.get('default_partner_workers', 0)

# --- 月のナビゲーション状態管理 ---
if 'current_month' not in st.session_state:
    st.session_state.current_month = dt.date.today().replace(day=1)

# --- ヘッダーと月ナビゲーション ---
st.markdown('<div class="sticky-header">', unsafe_allow_html=True) # Sticky Header Start
st.subheader(f"現場名: {current_site_name}") # Use fetched name

# 月の表示とナビゲーションボタン
month_col1, month_col2, month_col3 = st.columns([1, 2, 1])
with month_col1:
    if st.button("◀️ 前の月"):
        st.session_state.current_month = st.session_state.current_month - relativedelta(months=1)
        st.rerun()
with month_col2:
    st.markdown(f"<h4 style='text-align: center; margin-bottom: 0;'>{st.session_state.current_month.strftime('%Y年%m月')}</h4>", unsafe_allow_html=True)
with month_col3:
    if st.button("次の月 ▶️"):
        st.session_state.current_month = st.session_state.current_month + relativedelta(months=1)
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True) # Sticky Header End

# --- データ取得 ---
try:
    # 月全体のログとプランを取得
    logs_data = get_safety_logs_by_site_and_month(current_site_id, st.session_state.current_month.year, st.session_state.current_month.month)
    plans_data = get_safety_plans_by_site_and_month(current_site_id, st.session_state.current_month.year, st.session_state.current_month.month)
except Exception as e:
    st.error(f"データの取得中にエラーが発生しました: {e}")
    st.stop()

# --- テーブルヘッダー ---
col_h1, col_h2, col_h3 = st.columns([1, 3, 3]) # 列幅の比率調整可
with col_h1:
    st.markdown("**日付**")
with col_h2:
    st.markdown("**作業予定 (RKY)**")
with col_h3:
    st.markdown("**作業実績**")
st.divider()

# --- テーブル本体 (一覧表形式) ---
num_days_in_month = calendar.monthrange(st.session_state.current_month.year, st.session_state.current_month.month)[1]

for day in range(1, num_days_in_month + 1):
    current_date = dt.date(st.session_state.current_month.year, st.session_state.current_month.month, day)
    day_str_ymd = current_date.strftime('%Y-%m-%d')
    day_str_md = current_date.strftime('%m/%d')
    weekday_str = get_japanese_weekday(current_date)
    is_wkd = is_weekend(current_date)

    # その日のデータ
    plan_on_date = plans_data.get(day_str_ymd) # 辞書から直接取得 (Noneの可能性あり)
    log_on_date = logs_data.get(day_str_ymd)   # 辞書から直接取得

    col_date, col_p, col_l = st.columns([1, 4, 4], gap="small") # Use gap="small" for compactness

    # --- 日付列 ---
    with col_date:
        date_display = f"{day_str_md}({weekday_str})"
        if is_wkd:
            # Add subtle weekend indication if desired, e.g., gray color
            st.markdown(f"<span style='color: gray;'>{date_display}</span>", unsafe_allow_html=True)
        else:
            st.markdown(date_display)

    # --- 作業予定列 ---
    with col_p:
        badges_html = ""
        if plan_on_date and isinstance(plan_on_date, list) and len(plan_on_date) > 0:
            # リストの最初の要素を取得 (当面、日付ごとに1つの計画のみ表示)
            plan_details = plan_on_date[0]
            plan_id = plan_details.get('id') # .get()で安全に取得
            task = plan_details.get('task', 'N/A')
            approved = plan_details.get('approved', 0)
            approver = plan_details.get('approver')

            # 承認状態バッジ
            badge_html = ""
            if approved == 1: # 承認済
                badge_bg = "#28a745" # 緑
                badge_icon = "✅"
                badge_text = "承認済"
                if approver: badge_text += f" ({approver})"
            elif approved == 2: # 却下
                badge_bg = "#dc3545" # 赤
                badge_icon = "❌"
                badge_text = "却下"
                if approver: badge_text += f" ({approver})"
            else: # 未承認
                badge_bg = "#ffc107" # 黄
                badge_icon = "🕓"
                badge_text = "未承認"
            badge_html = f'<span style="background-color:{badge_bg}; color:white; padding: 2px 5px; border-radius: 3px; font-size: 0.8em;">{badge_icon} {badge_text}</span>'

            # 予定バッジ
            plan_badge = '<span style="background-color: #007bff; color:white; padding: 2px 5px; border-radius: 3px; font-size: 0.8em;">PLAN</span>'

            st.markdown(f"{plan_badge} {badge_html}", unsafe_allow_html=True)
            st.caption(f"{task[:30]}..." if len(task) > 30 else task) # タスク概要

            # 編集ボタン
            if plan_id and st.button("編集", key=f"edit_plan_{day_str_ymd}", disabled=is_wkd, type="secondary"):
                 saved = show_plan_modal_new(
                     plan_id=plan_id,
                     target_date=day_str_ymd, 
                     site_id=current_site_id,
                     user_name=current_user_name
                 )
                 if saved:
                     st.rerun()
        else:
            # 追加ボタン
            if st.button("➕ 計画追加", key=f"add_plan_{day_str_ymd}", disabled=is_wkd, use_container_width=True):
                saved = show_plan_modal_new(
                    plan_id=None,
                    target_date=day_str_ymd,
                    site_id=current_site_id,
                    user_name=current_user_name,
                    default_employee_workers=default_employee_workers, # Pass default
                    default_partner_workers=default_partner_workers    # Pass default
                )
                if saved:
                    st.rerun()

    # --- 作業実績列 ---
    with col_l:
        if log_on_date and isinstance(log_on_date, list) and len(log_on_date) > 0:
            # リストの最初の要素を取得
            log_details = log_on_date[0]
            log_id = log_details.get('id')
            task = log_details.get('task', 'N/A')
            image_path = log_details.get('image_path')

            # 実績バッジ
            log_badge = '<span style="background-color: #28a745; color:white; padding: 2px 5px; border-radius: 3px; font-size: 0.8em;">LOG</span>'
            image_icon = ""
            if image_path:
                image_full_path = os.path.join(IMAGE_DIR, os.path.basename(image_path))
                if os.path.exists(image_full_path):
                    image_icon = f'<img src="{image_full_path}" width="50" />'

            st.markdown(f"{log_badge}{image_icon}", unsafe_allow_html=True)
            st.caption(f"{task[:30]}..." if len(task) > 30 else task)

            # 編集ボタン
            if log_id and st.button("編集", key=f"edit_log_{day_str_ymd}", disabled=is_wkd, type="secondary"):
                saved = show_log_modal_new(
                    log_id=log_id,
                    target_date=day_str_ymd, 
                    site_id=current_site_id,
                    user_name=current_user_name
                )
                if saved:
                    st.rerun()
        else:
            # 追加ボタン
            if st.button("➕ 実績追加", key=f"add_log_{day_str_ymd}", disabled=is_wkd, use_container_width=True):
                # 対応する日の計画データを取得 (コピー機能用)
                plan_for_this_day = plans_data.get(day_str_ymd)
                plan_detail_for_modal = plan_for_this_day[0] if plan_for_this_day else None

                saved = show_log_modal_new(
                    log_id=None,
                    target_date=day_str_ymd,
                    site_id=current_site_id,
                    user_name=current_user_name,
                    plan_details=plan_detail_for_modal # Pass plan details
                )
                if saved:
                    st.rerun()

    st.divider() # Keep divider for visual separation between days

# --- フッター等あればここに追加 ---

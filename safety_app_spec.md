# 安全日誌アプリ 設計概要

本アプリは、現場の安全日誌と作業予定を一元管理するためのStreamlitベースのWebアプリです。ユーザーの役割に応じて、実績・予定の記録、承認、閲覧などが行えます。

---

## ユーザー種別と役割

| ユーザー種別         | 機能                                                                 |
|----------------------|----------------------------------------------------------------------|
| 現場責任者           | 実績の入力、予定の入力、行動チェックの記録                          |
| 部署責任者           | 日誌・予定の承認、コメント入力、現場の新規登録                       |
| 管理部門スタッフ     | 全体のダッシュボード閲覧（編集不可）                                 |
| アプリ管理者（裏方） | 部署の登録（DBに直接追加、UIなし）                                   |

---

## データベース構成（SQLite）

### `departments`

- 部署マスタテーブル

```sql
CREATE TABLE departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
);
```

---

### `sites`

- 各現場の情報を管理し、部署と紐づく
- 管理開始日・終了日、休工中フラグ、デフォルト人員を保持

```sql
CREATE TABLE sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    department_id INTEGER,
    start_date TEXT,
    end_date TEXT,
    is_suspended INTEGER DEFAULT 0,
    default_employee_workers INTEGER DEFAULT 0,
    default_partner_workers INTEGER DEFAULT 0,
    FOREIGN KEY(department_id) REFERENCES departments(id)
);
```

---

### `site_jobnos`

- 1つの現場に複数の作業番号（job_no）を関連付ける中間テーブル

```sql
CREATE TABLE site_jobnos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER,
    job_no TEXT,
    FOREIGN KEY(site_id) REFERENCES sites(id)
);
```

---

### `action_checks` / `risk_checks`

- チェックマスタ（行動チェック、リスクレベル）

```sql
CREATE TABLE action_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item TEXT UNIQUE
);

CREATE TABLE risk_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item TEXT UNIQUE
);
```

---

### `safety_logs`

- 実績記録（現場責任者が日々入力）
- 複数のアクションチェックをJSON形式で保存

```sql
CREATE TABLE safety_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    site_id INTEGER,
    employee_workers INTEGER,
    partner_workers INTEGER,
    task TEXT,
    action_check TEXT,
    author TEXT,
    approved INTEGER DEFAULT 0,
    comment TEXT,
    approver TEXT,
    image_path TEXT,
    FOREIGN KEY(site_id) REFERENCES sites(id)
);
```

---

### `safety_plans`

- 予定記録（作業予定＋リスク評価）
- リスクレベルはJSON形式（例：{ "level": "リスク小" }）
- リスク対策をテキストで記録
- 承認ステータス・コメントを保持

```sql
CREATE TABLE safety_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER,
    planned_date TEXT,
    task TEXT,
    employee_workers INTEGER,
    partner_workers INTEGER,
    risk_check TEXT,
    risk_action TEXT,
    created_by TEXT,
    approved INTEGER DEFAULT 0,
    comment TEXT,
    approver TEXT,
    FOREIGN KEY(site_id) REFERENCES sites(id)
);
```

---

## UI設計

### `現場責任者ページ`
- 「今日の実績」フォームと「次の予定」フォームを分離
- 実績 → safety_logs に保存（action_check は複数チェック形式）
- 予定 → safety_plans に保存（risk_check はラジオ＋対策コメント）

### `部署責任者ページ`
- カレンダーから日付選択 → 担当現場一覧表示（予定・実績）
- 予定または実績の承認・コメント入力が可能
- 現場の新規登録フォーム付き（DBに sites + site_jobnos を登録）

### `管理部門ページ`
- 全データを対象とした検索・ダッシュボード
- 編集不可の閲覧専用
- フィルタ・CSV出力機能付き

---

## 備考

- アクションチェック・リスクチェックはJSONで保存
- ログインレス構造（localStorage にユーザー情報を保存）
- 各フォーム送信後は `st.experimental_rerun()` により即時リフレッシュ

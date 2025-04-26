import streamlit as st
import requests
import json
import os
from pathlib import Path

# BrushupのAPIに関する設定
base_url = "https://api.brushup.net/v2/" 

# タイトルの設定
st.title("Brushup API 連携アプリ")

# API Keyの入力フィールド
# Streamlit Cloudの管理画面で設定したシークレットにアクセス
api_key = st.secrets["api_key"]

# ヘッダーの設定（共通部分）
headers = {
    "accept": "application/json",
    "Content-Type": "application/json",
    "X-Brushup-User-Api-Key": api_key
}

# API呼び出し関数
def brushup_get(endpoint): 
    response = requests.get(f"{base_url}{endpoint}", headers=headers)
    
    # レスポンスのステータスコードを確認
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"エラーが発生しました: ステータスコード {response.status_code}")
        try:
            return response.json()
        except:
            return {"error": response.text}

# プロジェクト内のアイテム一覧を取得する関数
def fetch_project_items(project_id):
    if not project_id:
        return False
        
    # プロジェクト内のアイテム一覧を取得
    items_endpoint = f"projects/{project_id}/items?sort=modified&order=desc&limit=100"
    items_result = brushup_get(items_endpoint)
    
    if items_result:
        # レスポンスが辞書型の場合
        if isinstance(items_result, dict):
            # 'items'キーがあるか確認
            if 'items' in items_result:
                st.session_state.project_items = items_result['items']
            else:
                # データ構造に合わせて適切に処理
                st.session_state.project_items = [items_result]
        
        # レスポンスがリスト型の場合
        elif isinstance(items_result, list):
            st.session_state.project_items = items_result
        
        # アイテムが存在する場合は表示
        if len(st.session_state.project_items) > 0:
            # st.sidebar.success(f"{len(st.session_state.project_items)}件のアイテムを取得しました")
            return True
        else:
            st.warning("アイテムが見つかりませんでした")
            return False
    return False

def brushup_post(endpoint, body):
    try:
        # リクエストの詳細をデバッグ表示
        st.write("リクエスト先:", f"{base_url}{endpoint}")
        st.write("リクエストボディ:", body)
        
        response = requests.post(f"{base_url}{endpoint}", headers=headers, json=body)
        
        # レスポンスのステータスコードを確認
        st.write("レスポンスステータスコード:", response.status_code)
        
        # レスポンスの内容を取得
        try:
            response_json = response.json()
            st.write("レスポンス内容:", response_json)
        except json.JSONDecodeError:
            st.write("レスポンス内容(テキスト):", response.text)
            response_json = None
        
        if response.status_code == 200:
            return response_json
        else:
            error_message = f"エラーが発生しました。ステータスコード: {response.status_code}"
            if response_json and isinstance(response_json, dict) and 'message' in response_json:
                error_message += f", メッセージ: {response_json['message']}"
            st.error(error_message)
            return response_json
    except Exception as e:
        st.error(f"例外が発生しました: {str(e)}")
        return None

# ファイルアップロード関数を追加
def upload_file_to_brushup(file_content, file_name):
    upload_endpoint = f"{base_url}contents/uploads"
    
    # ヘッダーの設定（Content-Typeは自動設定される）
    upload_headers = {
        "X-Brushup-User-Api-Key": api_key
    }
    
    # リクエストの準備
    files = {"upload_file": (file_name, file_content)}
    
    try:
        # APIリクエストの送信
        with st.spinner("ファイルをアップロード中..."):
            response = requests.post(upload_endpoint, files=files, headers=upload_headers)
        
        # デバッグ情報を表示
        # st.write("アップロードステータスコード:", response.status_code)
        # st.write("レスポンスヘッダー:", dict(response.headers))
        
        if response.status_code == 200:
            # st.success("ファイルが正常にアップロードされました！")
            
            # JSONレスポンスの処理
            try:
                json_response = response.json()
                # st.write("アップロードレスポンス:", json_response)
                
                # UUIDの表示と保存
                if "uuid" in json_response:
                    uuid = json_response['uuid']
                    st.session_state.uploaded_uuid = uuid
                    # st.success(f"アップロードしたファイルのUUID: {uuid}")
                    return uuid
                else:
                    st.warning("UUIDが見つかりませんでした。レスポンス内容を確認してください。")
            except json.JSONDecodeError:
                st.error("レスポンスの解析に失敗しました")
                st.write("レスポンス内容(テキスト):", response.text)
        else:
            st.error(f"ファイルのアップロードに失敗しました。ステータスコード: {response.status_code}")
            try:
                st.write("エラーレスポンス:", response.json())
            except:
                st.write("エラーレスポンス(テキスト):", response.text)
        
        return None
                
    except Exception as e:
        st.error(f"ファイルアップロード中にエラーが発生しました: {str(e)}")
        return None

# セッションステートの初期化
if 'uploaded_uuid' not in st.session_state:
    st.session_state.uploaded_uuid = ""
if 'item_id' not in st.session_state:
    st.session_state.item_id = ""
if 'project_items' not in st.session_state:
    st.session_state.project_items = [] 
if 'refresh_items' not in st.session_state:
    st.session_state.refresh_items = False
if 'last_created_item_id' not in st.session_state:
    st.session_state.last_created_item_id = None


# メインコンテンツエリア
tab1, tab2 = st.tabs(["Brushup校正依頼", "各種設定"])

with tab1: 
    #プロジェクトIDからアイテムIDリストをセレクトボックス表示
    project_id = st.sidebar.selectbox(
        "①プロジェクトIDを選択",
        options=["185690", "181437", "プロジェクト3"],  
        key="project_id_selectbox"
    ) 
    if st.session_state.refresh_items:
        st.success("アイテムリストを更新しました！")
        st.session_state.refresh_items = False  
    if project_id: 
        fetch_project_items(project_id) 
    jobid = st.sidebar.text_input("①JobIDを入力")        
    if jobid and st.button("アイテムを作成"):
        st.write("### アイテム作成処理を開始します") 
        if not project_id:
            st.error("プロジェクトIDが選択されていません。先にプロジェクトIDを選択してください。")
        else: 
            endpoint = f"projects/{project_id}/items" 
            body = {
                "item_nm": jobid 
            } 
            st.write("リクエスト情報:")
            st.write(f"- エンドポイント: {base_url}{endpoint}")
            st.write(f"- プロジェクトID: {project_id}")
            st.write(f"- アイテム名: {jobid}") 
            with st.spinner("アイテムを作成中..."):
                result = brushup_post(endpoint, body) 
            if result:
                if isinstance(result, dict) and 'id' in result:
                    # st.success(f"アイテムが正常に作成されました！ ID: {result['id']}")
                    st.json(result) 
                    st.session_state.last_created_item_id = result['id'] 
                    st.session_state.refresh_items = True
                    st.rerun()
                else:
                    st.warning("アイテムの作成結果が予期しない形式です。レスポンスを確認してください。")
                    st.json(result)
 
        
    # アイテムが存在する場合は表示（移動：JobID入力の後に配置）
    if project_id and len(st.session_state.project_items) > 0:
        # アイテムの情報からセレクトボックス用のオプションを作成
        item_options = []
        for item in st.session_state.project_items:
            # itemの型を確認
            if isinstance(item, dict):
                item_id = item.get("id", "不明")
                item_name = item.get("item_nm", "名称不明")
                item_options.append(f"{item_id}: {item_name}")
            else:
                # 辞書型でない場合は文字列として表示
                item_options.append(str(item))
        
        if item_options:
            # セレクトボックスでアイテムを選択
            selected_item = st.sidebar.selectbox("②アイテム選択", item_options, key="item_selector") 
            # 選択されたアイテムのIDを取得（例: "12345: アイテム名" から "12345"を抽出）
            if selected_item and ":" in selected_item:
                selected_id = selected_item.split(":")[0].strip()
                st.session_state.item_id = selected_id 
    elif project_id:
        st.warning("アイテムが見つかりませんでした") 

# サイドバーにファイルアップロード機能を配置 
    st.sidebar.subheader("③ファイルアップロード")
    
    # ローカルフォルダパスの入力
    local_folder_path = "C:\PoCDirectory\BrushupAPI\PDFs"
    
    # アップロード方法の選択
    upload_method = st.sidebar.radio("アップロード方法を選択", ["アイテム名でファイル選択", "手動でファイルを選択"],index=1)
    
    uploaded_file = None
    
    if upload_method == "アイテム名でファイル選択" and st.session_state.item_id:
        # 選択されたアイテムに対応するitem_nmを取得
        item_name = None
        for item in st.session_state.project_items:
            if isinstance(item, dict) and str(item.get("id", "")) == st.session_state.item_id:
                item_name = item.get("item_nm", "")
                break
        
        if not item_name:
            st.warning("選択されたアイテムの名前（item_nm）を取得できませんでした。")
        else:
            # アイテム名と同名のファイルパスを作成（拡張子なし）
            base_filename = f"{item_name}"
            
            # フォルダ内のファイルリストを取得
            folder_path = Path(local_folder_path)
            matching_files = []
            
            try:
                if os.path.exists(folder_path):
                    for file in os.listdir(folder_path):
                        # ファイル名（拡張子なし）がアイテム名と一致するかチェック
                        file_path = folder_path / file
                        if file_path.is_file() and file_path.stem == base_filename:
                            matching_files.append(file)
                else:
                    st.warning(f"指定されたフォルダが存在しません: {local_folder_path}")
            except Exception as e:
                st.error(f"フォルダの読み取り中にエラーが発生しました: {str(e)}")
            
            if matching_files:
                # 一致するファイルが複数ある場合は選択できるようにする
                selected_file = st.selectbox(
                    "アイテム名に一致するファイルが見つかりました",
                    options=matching_files
                )
                
                # ファイルをアップロードするボタン
                if st.button("このファイルをアップロード"):
                    try:
                        # ファイルを読み込む
                        file_path = folder_path / selected_file
                        with open(file_path, "rb") as file:
                            file_content = file.read()
                        
                        # ファイルのサイズを確認
                        st.write(f"ファイルサイズ: {len(file_content)} バイト")
                        
                        # アップロード関数を呼び出し
                        uuid = upload_file_to_brushup(file_content, selected_file)
                        if uuid:
                            st.session_state.uploaded_uuid = uuid
                            
                    except Exception as e:
                        st.error(f"ファイル処理中にエラーが発生しました: {str(e)}")
            else:
                st.warning(f"指定されたフォルダにアイテム名({item_name})と同名のファイルが見つかりませんでした。")
    elif upload_method == "アイテム名でファイル選択" and not st.session_state.item_id:
        st.warning("先にアイテムを選択してください。")
    
    else:  # 手動でファイルを選択する場合
        # ファイルアップローダーウィジェットの作成
        uploaded_file = st.file_uploader("ファイルを選択してください", type=["docx", "csv", "txt", "pdf", "jpg", "png", "jpeg"])

        # ファイルがアップロードされた場合の処理
        if uploaded_file is not None:
            # ファイル情報の表示
            st.write("ファイル名:", uploaded_file.name)
            st.write("ファイルサイズ:", uploaded_file.size, "bytes")
            
            if st.button("アップロード開始"):
                # ファイルの内容を取得
                file_content = uploaded_file.getvalue()
                
                # アップロード関数を呼び出し
                uuid = upload_file_to_brushup(file_content, uploaded_file.name)
                if uuid:
                    st.session_state.uploaded_uuid = uuid

    # UUIDの入力フィールド（アップロードしたファイルのUUIDが自動的に入力される）
    uuid = st.sidebar.text_input("ファイルUUID", value=st.session_state.uploaded_uuid)
    
    # コメント内容の入力フィールド
    comment_text = st.text_area("コメント内容", "")
    
    # コメントを投稿するボタン - 単一のボタンに統合
    if st.button("Brushupへ投稿する"):
        # 必要な情報が揃っているかチェック
        if not api_key:
            st.warning("API Keyを入力してください")
        elif not uuid:
            st.warning("ファイルのUUIDが必要です。先にファイルをアップロードしてください。")
        elif not st.session_state.item_id:
            st.warning("項目IDを入力してください。")
        else:
            # リクエストの準備
            comment_endpoint = f"items/{st.session_state.item_id}/comments"
            comment_body = {
                "comment_text": comment_text,
                "attachment_file": {
                    "uuid": uuid
                }
            }
            
            # テキストコメントがある場合は追加
            if comment_text:
                comment_body["content"] = comment_text
            
            try:
                # APIリクエストの送信
                with st.spinner("コメントを投稿中..."):
                    response = requests.post(f"{base_url}{comment_endpoint}", headers=headers, json=comment_body)
                
                # レスポンスの詳細を表示
                st.write("コメント投稿ステータスコード:", response.status_code)
                
                if response.status_code == 200:
                    st.success("Brushupへの投稿完了")
                    
                    # JSONレスポンスの処理
                    try:
                        json_response = response.json()
                        st.json(json_response)
                    except json.JSONDecodeError:
                        st.error("レスポンスの解析に失敗しました")
                        st.write("レスポンス内容(テキスト):", response.text)
                else:
                    st.error(f"コメントの投稿に失敗しました。ステータスコード: {response.status_code}")
                    try:
                        st.write("エラーレスポンス:", response.json())
                    except:
                        st.write("エラーレスポンス(テキスト):", response.text)
                    
            except Exception as e:
                st.error(f"コメント投稿中にエラーが発生しました: {str(e)}")

with tab2:    
    # API操作オプション
    st.subheader("その他のAPIを実行")
    api_options = [
        "step_groups",
        f"projects/{project_id}/items"
    ]

    # ユーザーに分かりやすいラベル
    display_options = [
        "ステップグループ一覧",
        "アイテム追加"
    ]

    # セレクトボックスでオプションを選択
    selected_label = st.selectbox("API操作を選択してください", display_options, key="api_operation")
    selected_index = display_options.index(selected_label)
    endpoint = api_options[selected_index]

    if st.button("APIを実行", key="execute_api_button"):
        # 選択されたオプションに応じて処理を分岐
        if selected_label == "アイテム追加":
            # POSTリクエストの場合
            body = {
                "id": 0,
                "item_nm": "FFGSTESTAPI",
            }
            result = brushup_post(endpoint, body)
        else:
            # GETリクエストの場合
            result = brushup_get(endpoint)
        
        # 結果の表示
        if result:
            st.write("APIレスポンス:")
            st.json(result)

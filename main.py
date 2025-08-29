import os
import shutil
import hashlib
import json
import natsort
import csv
import datetime
import loader
import parser
import finder
import assembler

# プロジェクトのルートディレクトリを定義
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# --- 設定項目 ---
INPUT_PDF_PATHS = [
    r"C:\Users\81804\Desktop\.vscode\pdfrev\input\パターン3変更後.pdf",
]
# -----------------

def setup_session_directory():
    """タイムスタンプ付きのセッション結果フォルダとサブフォルダを作成する"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    session_root = os.path.join(PROJECT_ROOT, f"result_{timestamp}")
    
    paths = {
        "session_root": session_root,
        "output": os.path.join(session_root, "output"),
        "supplemental": os.path.join(session_root, "supplemental_data")
    }

    os.makedirs(paths["output"], exist_ok=True)
    os.makedirs(paths["supplemental"], exist_ok=True)
    
    print(f"結果保存フォルダを作成しました: {session_root}")
    return paths

def get_cache_folder_name(pdf_paths):
    """入力PDFパスから一意のキャッシュフォルダ名を生成する"""
    path_string = "".join(sorted(pdf_paths))
    hash_id = hashlib.md5(path_string.encode()).hexdigest()[:8]
    base_name = os.path.basename(pdf_paths[0])
    clean_base_name = os.path.splitext(base_name)[0]
    folder_name = f"png_cache_{clean_base_name}_{hash_id}"
    return os.path.join(PROJECT_ROOT, folder_name)

def process_one_revision(target_revision, png_folder, revision_data, session_paths):
    """一つの変更記号に対応する処理を行い、結果を各フォルダに保存する"""
    print("-" * 30)
    print(f"変更記号 '{target_revision}' の処理を開始します...")

    print(f"-> ページを探索しています...")
    # found_pages_map は { '見つかった論理ページ': '物理ファイルパス' } の辞書
    found_pages_map = finder.find_pages_for_revision(
        png_folder,
        revision_data,
        target_revision
    )

    # 探索結果ログを supplemental_data フォルダに保存
    search_log_path = os.path.join(session_paths["supplemental"], f"search_log_{target_revision}.csv")
    with open(search_log_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['TargetPage', 'Status', 'FoundFile'])
        
        if target_revision in revision_data:
            for page in revision_data[target_revision]:
                if page in found_pages_map:
                    writer.writerow([page, 'Found', os.path.basename(found_pages_map[page])])
                else:
                    writer.writerow([page, 'NotFound', ''])

    found_page_paths = list(found_pages_map.values())
    if not found_page_paths:
        print(f"-> 変更記号 '{target_revision}' に該当するページが見つかりませんでした。")
        return

    print(f"-> 見つかった {len(found_page_paths)} ページをPDFにまとめています...")
    temp_assembly_folder = os.path.join(session_paths["session_root"], f"temp_assembly_{target_revision}")
    os.makedirs(temp_assembly_folder, exist_ok=True)
    for page_path in found_page_paths:
        shutil.copy(page_path, temp_assembly_folder)

    # 抽出PDFを output フォルダに保存
    final_pdf_path = os.path.join(session_paths["output"], f"extracted_rev_{target_revision}.pdf")
    assembler.pngs_to_pdf(temp_assembly_folder, final_pdf_path)
    print(f"-> ✅ 完了: '{final_pdf_path}' にPDFを出力しました。")

    shutil.rmtree(temp_assembly_folder)

def main():
    """メイン処理フロー"""
    # === ステップ1: セッションフォルダとキャッシュフォルダの準備 ===
    session_paths = setup_session_directory()
    cache_folder = get_cache_folder_name(INPUT_PDF_PATHS)
    json_cache_path = os.path.join(cache_folder, "analysis_cache.json")
    full_revision_data = {}

    if not (os.path.exists(cache_folder) and os.listdir(cache_folder)):
        print(f"PNGキャッシュ '{cache_folder}' を新規に作成します...")
        loader.process_multiple_pdfs(pdf_paths=INPUT_PDF_PATHS, dpi=400, output_folder_name=cache_folder, merge_first=True)
        if not (os.path.exists(cache_folder) and os.listdir(cache_folder)):
            print("エラー: PNGファイルへの変換に失敗しました。処理を中断します。"); return
    print(f"PNGキャッシュ '{cache_folder}' の準備が完了しました。")
    print("-" * 30)

    # === ステップ2: 変更履歴の解析（キャッシュ利用） ===
    if os.path.exists(json_cache_path):
        print(f"既存の解析結果 '{os.path.basename(json_cache_path)}' を再利用します。")
        with open(json_cache_path, 'r', encoding='utf-8') as f:
            full_revision_data = json.load(f)['revision_data']
    else:
        print("変更履歴一覧表の場所を探索・解析しています... (初回のみ)")
        special_pages_paths = parser._find_special_pages(cache_folder)
        if not special_pages_paths["revision_history"]:
            print("エラー: 変更履歴一覧表が見つかりませんでした。"); return

        for rev_page_path in special_pages_paths["revision_history"]:
            single_page_data = parser.parse_revision_history(rev_page_path)
            if single_page_data:
                for key, value in single_page_data.items():
                    if not isinstance(value, list): continue
                    if key in full_revision_data: full_revision_data[key].extend(value)
                    else: full_revision_data[key] = value
        
        if full_revision_data:
            print(f"解析結果を '{json_cache_path}' に保存しています...")
            with open(json_cache_path, 'w', encoding='utf-8') as f:
                json.dump({'revision_data': full_revision_data}, f, ensure_ascii=False, indent=4)
    
    if not full_revision_data:
        print("エラー: 変更履歴の解析に失敗しました。"); return
        
    print("変更履歴の解析が完了しました。")
    
    # 解析結果のサマリーを supplemental_data フォルダに保存
    summary_csv_path = os.path.join(session_paths["supplemental"], "revision_summary.csv")
    with open(summary_csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['RevisionSymbol', 'PageCount', 'PageList'])
        for symbol, pages_list in sorted(full_revision_data.items(), key=lambda item: natsort.natsort_keygen()(item[0])):
            writer.writerow([symbol, len(pages_list), ", ".join(pages_list)])
    print(f"解析結果のサマリーを '{summary_csv_path}' に保存しました。")
    print("----------------------------\n")

    # === ステップ3: 対話形式ループ ===
    available_revisions = sorted(full_revision_data.keys(), key=natsort.natsort_keygen())
    while True:
        prompt_text = f"抽出したい変更記号を入力してください ({', '.join(available_revisions)}) (終了するにはqを入力): "
        user_input = input(prompt_text).strip()

        if user_input.lower() in ['q', 'quit']: print("処理を終了します。"); break
        
        if user_input in full_revision_data:
            process_one_revision(user_input, cache_folder, full_revision_data, session_paths)
        else:
            print(f"エラー: 記号 '{user_input}' は変更履歴一覧に存在しません。")

    # === ステップ4: 終了処理 ===
    print("-" * 30)
    print("結果は以下のフォルダに保存されています：")
    print(session_paths["session_root"])

if __name__ == '__main__':
    main()
import os
import shutil
import hashlib
import json
import natsort  # ★★★ この行を追加 ★★★
import loader
import parser
import finder
import assembler

# --- 設定項目 ---
# 最初に処理するPDFファイルのパス
INPUT_PDF_PATHS = [
    r"C:\Users\81804\Desktop\.vscode\pdfrev\入力データ（変更後pdf）\パターン3変更後.pdf",
]
# -----------------

def get_cache_folder_name(pdf_paths):
    """入力されたPDFパスのリストから一意のキャッシュフォルダ名を生成する"""
    path_string = "".join(sorted(pdf_paths))
    hash_id = hashlib.md5(path_string.encode()).hexdigest()[:8]
    base_name = os.path.basename(pdf_paths[0])
    clean_base_name = os.path.splitext(base_name)[0]
    return f"png_cache_{clean_base_name}_{hash_id}"

def process_one_revision(target_revision, png_folder, revision_data):
    """
    一つの変更記号に対応するページの探索とPDF化を行う関数
    """
    print("-" * 30)
    print(f"変更記号 '{target_revision}' の処理を開始します...")

    print(f"-> ページを探索しています...")
    found_pages = finder.find_pages_for_revision(
        png_folder,
        revision_data,
        target_revision
    )

    if not found_pages:
        print(f"-> 変更記号 '{target_revision}' に該当するページが見つかりませんでした。")
        return

    print(f"-> 見つかった {len(found_pages)} ページをPDFにまとめています...")
    temp_assembly_folder = f"temp_assembly_{target_revision}"
    os.makedirs(temp_assembly_folder, exist_ok=True)
    for page_path in found_pages:
        shutil.copy(page_path, temp_assembly_folder)

    final_pdf_path = f"output/extracted_rev_{target_revision}.pdf"
    output_dir = os.path.dirname(final_pdf_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    assembler.pngs_to_pdf(temp_assembly_folder, final_pdf_path)
    print(f"-> ✅ 完了: '{final_pdf_path}' にPDFを出力しました。")

    shutil.rmtree(temp_assembly_folder)

def main():
    """
    メイン処理フロー。PNGと解析結果をキャッシュし、対話形式で複数の変更記号を処理する。
    """
    print("=== 図面リビジョン抽出処理を開始します ===")
    
    # 1. キャッシュフォルダとキャッシュファイルのパスを定義
    cache_folder = get_cache_folder_name(INPUT_PDF_PATHS)
    json_cache_path = os.path.join(cache_folder, "analysis_cache.json")
    full_revision_data = {}

    # 2. PNGキャッシュの準備
    if not (os.path.exists(cache_folder) and os.listdir(cache_folder)):
        print(f"PNGキャッシュ '{cache_folder}' を新規に作成します...")
        loader.process_multiple_pdfs(
            pdf_paths=INPUT_PDF_PATHS,
            dpi=400,
            output_folder_name=cache_folder,
            merge_first=True
        )
        if not (os.path.exists(cache_folder) and os.listdir(cache_folder)):
            print("エラー: PNGファイルへの変換に失敗しました。処理を中断します。")
            return
    print(f"PNGキャッシュ '{cache_folder}' の準備が完了しました。")
    print("-" * 30)

    # 3. 変更履歴の解析（キャッシュがあれば読み込み、なければ解析して保存）
    if os.path.exists(json_cache_path):
        print(f"既存の解析結果 '{os.path.basename(json_cache_path)}' を再利用します。")
        try:
            with open(json_cache_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                full_revision_data = cached_data['revision_data']
        except (json.JSONDecodeError, KeyError, IOError) as e:
            print(f"  [警告] 解析結果の読み込みに失敗しました ({e})。再解析を実行します。")
            os.remove(json_cache_path)

    if not full_revision_data:
        print("変更履歴一覧表の場所を探索・解析しています... (初回のみ)")
        
        special_pages_paths = parser._find_special_pages(cache_folder)
        if not special_pages_paths["revision_history"]:
            print("エラー: 変更履歴一覧表が見つかりませんでした。")
            return

        for rev_page_path in special_pages_paths["revision_history"]:
            single_page_data = parser.parse_revision_history(rev_page_path)
            if single_page_data:
                for key, value in single_page_data.items():
                    if not isinstance(value, list): continue
                    if key in full_revision_data: full_revision_data[key].extend(value)
                    else: full_revision_data[key] = value
        
        if full_revision_data:
            print(f"解析結果を '{json_cache_path}' に保存しています...")
            toc_pages = [int(os.path.splitext(os.path.basename(p))[0]) for p in special_pages_paths['toc']]
            rev_history_pages = [int(os.path.splitext(os.path.basename(p))[0]) for p in special_pages_paths['revision_history']]
            
            cache_data_to_save = {
                'special_pages': {'toc': toc_pages, 'revision_history': rev_history_pages},
                'revision_data': full_revision_data
            }
            with open(json_cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data_to_save, f, ensure_ascii=False, indent=4)
    
    if not full_revision_data:
        print("エラー: 変更履歴の解析に失敗しました。")
        return
        
    print("変更履歴の解析が完了しました。")
    print("\n--- 解析された変更履歴一覧 ---")
    available_revisions = sorted(full_revision_data.keys(), key=natsort.natsort_keygen())
    for symbol in available_revisions:
        pages_list = full_revision_data[symbol]
        print(f"記号: {symbol} (対象ページ数: {len(pages_list)})")
    print("----------------------------\n")

    # 4. 対話形式ループ
    while True:
        prompt_text = f"抽出したい変更記号を入力してください ({', '.join(available_revisions)}) (終了するにはqを入力): "
        user_input = input(prompt_text).strip().upper()

        if user_input in ['Q', 'QUIT']:
            print("処理を終了します。")
            break
        
        if user_input in full_revision_data:
            process_one_revision(user_input, cache_folder, full_revision_data)
        else:
            print(f"エラー: 記号 '{user_input}' は変更履歴一覧に存在しません。")

    # 5. 終了前のクリーンアップ確認
    print("-" * 30)
    while True:
        cleanup_choice = input(f"PNGキャッシュフォルダ '{cache_folder}' を削除しますか？ (y/n): ").strip().lower()
        if cleanup_choice in ['y', 'yes']:
            print(f"キャッシュフォルダ '{cache_folder}' を削除しています...")
            shutil.rmtree(cache_folder)
            print("削除しました。")
            break
        elif cleanup_choice in ['n', 'no']:
            print("キャッシュを保持して終了します。")
            break
        else:
            print("無効な入力です。'y'または'n'で入力してください。")

if __name__ == '__main__':
    main()
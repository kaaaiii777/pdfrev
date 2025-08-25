import os
import shutil
import loader
import parser
import finder
import assembler

# --- 設定項目 ---
# 入力するPDFファイルのパス（リスト形式で複数指定可能）
INPUT_PDF_PATHS = [
    r"C:\Users\81804\Desktop\.vscode\pdfrev\入力データ（変更後pdf）\パターン3変更後.pdf",
    # "02_別の図面.pdf", # 2つ目以降のPDFをここに追加
    # "03_さらに別の図面.pdf",
]

# 抽出したい変更記号
TARGET_REVISION = "G"

# 中間ファイル（PNG）を保存するフォルダ名
PNG_OUTPUT_FOLDER = "temp_png_images"

# 最終的に出力するPDFのパス
# 複数のPDFを元にするため、ファイル名を少し汎用的に変更
FINAL_PDF_PATH = f"output/extracted_rev_{TARGET_REVISION}.pdf"
# -----------------

def main():
    """
    メイン処理フローを実行する。
    1. 複数のPDFを1つに結合し、PNGに変換
    2. 変更履歴を解析
    3. 該当ページを探索
    4. ページをPDFに結合
    """
    print("=== 図面リビジョン抽出処理を開始します ===")
    print(f"入力ファイル: {', '.join([os.path.basename(p) for p in INPUT_PDF_PATHS])}")

    # 1. PDF -> PNG 変換
    print("複数のPDFを結合し、PNGに変換しています...")
    loader.process_multiple_pdfs(
        pdf_paths=INPUT_PDF_PATHS,
        dpi=400,
        output_folder_name=PNG_OUTPUT_FOLDER,
        merge_first=True
    )
    
    if not os.path.exists(PNG_OUTPUT_FOLDER) or not os.listdir(PNG_OUTPUT_FOLDER):
        print("エラー: PNGファイルへの変換に失敗しました。処理を中断します。")
        return
    print("-" * 20)

    # 2. 変更履歴一覧表の解析
    print("変更履歴一覧表を解析しています...")
    special_pages = parser._find_special_pages(PNG_OUTPUT_FOLDER)

    if not special_pages["revision_history"]:
        print("エラー: 変更履歴一覧表が見つかりませんでした。処理を中断します。")
        if os.path.exists(PNG_OUTPUT_FOLDER):
            shutil.rmtree(PNG_OUTPUT_FOLDER)
        return

    print("発見された変更履歴一覧表を1ページずつ解析します...")
    full_revision_data = {}
    for rev_page_path in special_pages["revision_history"]:
        print(f"  -> 解析中: {os.path.basename(rev_page_path)}")
        single_page_data = parser.parse_revision_history(rev_page_path)
        
        if single_page_data:
            # ★★★ 変更点: シンプルなデータ構造のマージ処理 ★★★
            for key, value in single_page_data.items():
                if not isinstance(value, list):
                    print(f"  [警告] 記号 '{key}' のデータ形式が不正（リストでない）です。スキップします。")
                    continue
                
                if key in full_revision_data:
                    full_revision_data[key].extend(value)
                else:
                    full_revision_data[key] = value

    if not full_revision_data:
        print("エラー: 変更履歴の解析に失敗しました。処理を中断します。")
        if os.path.exists(PNG_OUTPUT_FOLDER):
            shutil.rmtree(PNG_OUTPUT_FOLDER)
        return
        
    print("変更履歴の解析が完了しました。")

    # ★★★ 変更点: 「記号」と「ページ番号」を表示する ★★★
    print("\n--- 解析された変更履歴一覧 ---")
    for symbol, pages_list in full_revision_data.items():
        # ページリストをカンマ区切りの文字列に変換
        pages_str = ", ".join(pages_list)
        print(f"記号: {symbol}")
        print(f"  頁  : {pages_str}")
    print("----------------------------\n")

    # 変数をそのまま後続の処理に渡す
    revision_data = full_revision_data

    # 3. 該当ページの探索
    print(f"変更記号 '{TARGET_REVISION}' のページを探索します...")
    found_pages = finder.find_pages_for_revision(
        PNG_OUTPUT_FOLDER,
        revision_data,
        TARGET_REVISION
    )

    if not found_pages:
        print(f"変更記号 '{TARGET_REVISION}' に該当するページが見つかりませんでした。")
        if os.path.exists(PNG_OUTPUT_FOLDER):
            shutil.rmtree(PNG_OUTPUT_FOLDER)
        return
    print("-" * 20)

    # 4. 見つかったページをPDFに結合
    print("見つかったページをPDFにまとめています...")
    temp_assembly_folder = "temp_for_assembly"
    os.makedirs(temp_assembly_folder, exist_ok=True)
    for page_path in found_pages:
        shutil.copy(page_path, temp_assembly_folder)

    output_dir = os.path.dirname(FINAL_PDF_PATH)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    assembler.pngs_to_pdf(temp_assembly_folder, FINAL_PDF_PATH)
    print(f"'{FINAL_PDF_PATH}' にPDFを出力しました。")

    # 5. 一時フォルダを削除
    print("一時フォルダをクリーンアップします...")
    shutil.rmtree(PNG_OUTPUT_FOLDER)
    shutil.rmtree(temp_assembly_folder)

    print("\n=== 全ての処理が完了しました ===")


if __name__ == '__main__':
    main()
    
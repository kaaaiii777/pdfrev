import os
import re
import natsort
from gemini_handler import get_text_from_image

def find_pages_for_revision(png_folder, revision_data, target_revision):
    """
    指定された変更記号に対応するページだけを、二分探索を用いて効率的に見つける。
    探索失敗時のリトライ機能と、重複ページ番号検出時のOCR再試行機能を追加。
    """
    if target_revision not in revision_data or not revision_data[target_revision]:
        print(f"エラー: 変更記号 '{target_revision}' は変更履歴一覧に存在しないか、ページが空です。")
        return []

    # --- 1. 初期設定 ---
    png_files = sorted(
        [f for f in os.listdir(png_folder) if f.lower().endswith('.png')],
        key=lambda x: int(os.path.splitext(x)[0])
    )
    
    target_pages_to_find = set(revision_data[target_revision])
    
    ocr_cache = {}
    found_pages_map = {}
    ns_key = natsort.natsort_keygen()
    
    # ★★★ 変更点: 発見済みのページ番号とパスを記録する辞書を追加 ★★★
    seen_page_numbers_map = {} # { page_str: image_path }

    # --- 2. ヘルパー関数の定義 ---
    def _get_page_number_at_index(index, accessed_paths):
        """指定されたインデックスの画像のページ番号をOCRまたはキャッシュから取得する。"""
        if not (0 <= index < len(png_files)):
            return None
            
        image_path = os.path.join(png_folder, png_files[index])
        accessed_paths.add(image_path)
        
        if image_path in ocr_cache:
            return ocr_cache[image_path]

        # ★★★ 変更点: 重複検出とOCR再試行のループを追加 ★★★
        max_ocr_attempts = 2 # OCRの最大試行回数
        for attempt in range(max_ocr_attempts):
            prompt = "この図面画像の右下に記載されているページ番号（例：'A-104'）だけを抽出してください。図面番号（例：'W426297'）は無視してください。"
            page_number_text = get_text_from_image(image_path, prompt)
            
            # 重複チェック
            if page_number_text and page_number_text in seen_page_numbers_map:
                original_path = seen_page_numbers_map[page_number_text]
                if original_path != image_path:
                    print(f"\n  [警告] 重複ページ番号 '{page_number_text}' を検出。")
                    print(f"    -> 今回: {os.path.basename(image_path)}, 前回: {os.path.basename(original_path)}")
                    
                    # 元のキャッシュと記録を削除
                    if original_path in ocr_cache: del ocr_cache[original_path]
                    del seen_page_numbers_map[page_number_text]
                    
                    if attempt < max_ocr_attempts - 1:
                        print(f"  -> '{os.path.basename(image_path)}'のOCRを再試行します...")
                        continue # このページのOCRをやり直す

            # 重複がない場合は、今回の結果を記録して返す
            if page_number_text and page_number_text not in seen_page_numbers_map:
                seen_page_numbers_map[page_number_text] = image_path
            
            break # ループを抜ける

        extracted_num = None
        if page_number_text:
            match = re.search(r'([a-zA-Z0-9\-]+)', page_number_text)
            if match:
                extracted_num = match.group(1)
        
        print(f"  [DEBUG] file: {os.path.basename(image_path):>8s} | AI raw output: '{page_number_text}' | Extracted: '{extracted_num}'")

        ocr_cache[image_path] = extracted_num
        return extracted_num

    # --- 3. メインの二分探索ループ ---
    for target_page in natsort.natsorted(list(target_pages_to_find)):
        
        print(f"\n探索ターゲット: '{target_page}'")
        found = False
        max_attempts = 3

        for attempt in range(max_attempts):
            if attempt > 0:
                print(f"  -> 再探索 ({attempt + 1}/{max_attempts}回目)...")

            low, high = 0, len(png_files) - 1
            accessed_paths_in_attempt = set()

            while low <= high:
                mid = (low + high) // 2
                current_page_num = _get_page_number_at_index(mid, accessed_paths_in_attempt)

                if current_page_num is None:
                    neighbor_page_num = _get_page_number_at_index(mid + 1, accessed_paths_in_attempt)
                    if neighbor_page_num:
                        if ns_key(neighbor_page_num) < ns_key(target_page): low = mid + 2
                        else: high = mid - 1
                    else:
                        high = mid - 1
                    continue

                if ns_key(current_page_num) < ns_key(target_page):
                    low = mid + 1
                elif ns_key(current_page_num) > ns_key(target_page):
                    high = mid - 1
                else: # ターゲットを発見
                    print(f"  -> ページ '{current_page_num}' を発見しました: {png_files[mid]}")
                    found_pages_map[current_page_num] = os.path.join(png_folder, png_files[mid])
                    found = True
                    break
            
            if found:
                break
            
            if attempt < max_attempts - 1:
                for path in accessed_paths_in_attempt:
                    if path in ocr_cache:
                        del ocr_cache[path]

        if not found:
             print(f"  -> ページ '{target_page}' は見つかりませんでした。({max_attempts}回試行)")

    # --- 4. 最終結果の整形 ---
    final_found_paths = []
    for page_num in revision_data[target_revision]:
        if page_num in found_pages_map:
            final_found_paths.append(found_pages_map[page_num])
        else:
            print(f"  [警告] 対象ページ '{page_num}' は最終結果に含まれませんでした。")
            
    # ★★★ 変更点: main.pyが辞書を期待しているため、辞書を返す ★★★
    return found_pages_map
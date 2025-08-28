import os
import re
import natsort
from gemini_handler import get_text_from_image

def find_pages_for_revision(png_folder, revision_data, target_revision):
    """
    指定された変更記号に対応するページだけを、二分探索を用いて効率的に見つける。
    探索失敗時に最大2回までリトライする機能を追加。
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
    
    ocr_cache = {}       # OCR結果をキャッシュする辞書 {image_path: page_number}
    found_pages_map = {} # 見つかったページを格納する辞書 {page_number: image_path}
    ns_key = natsort.natsort_keygen() # 自然順ソート用のキー生成関数

    # --- 2. ヘルパー関数の定義 ---
    # ★★★ 変更点: アクセスしたパスを記録するための引数を追加 ★★★
    def _get_page_number_at_index(index, accessed_paths):
        """指定されたインデックスの画像のページ番号をOCRまたはキャッシュから取得する。"""
        if not (0 <= index < len(png_files)):
            return None
            
        image_path = os.path.join(png_folder, png_files[index])
        accessed_paths.add(image_path) # この探索でアクセスしたパスとして記録
        
        if image_path in ocr_cache:
            return ocr_cache[image_path]

        prompt = "この図面画像の右下に記載されているページ番号（例：'A-104'）だけを抽出してください。図面番号（例：'W426297'）は無視してください。"
        page_number_text = get_text_from_image(image_path, prompt)
        
        # デバッグ用のプリント文はキャッシュ保存の直前に移動
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
        max_attempts = 3 # 合計試行回数

        # ★★★ 変更点: リトライ（再試行）のためのループを追加 ★★★
        for attempt in range(max_attempts):
            if attempt > 0:
                print(f"  -> 再探索 ({attempt + 1}/{max_attempts}回目)...")

            low, high = 0, len(png_files) - 1
            accessed_paths_in_attempt = set() # この試行でアクセスしたパスを記録

            while low <= high:
                mid = (low + high) // 2
                current_page_num = _get_page_number_at_index(mid, accessed_paths_in_attempt)

                if current_page_num is None:
                    neighbor_page_num = _get_page_number_at_index(mid + 1, accessed_paths_in_attempt)
                    if neighbor_page_num:
                        if ns_key(neighbor_page_num) < ns_key(target_page):
                            low = mid + 2
                        else:
                            high = mid - 1
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
            
            # 発見できたらリトライループを抜ける
            if found:
                break
            
            # 失敗した場合、次の試行の前にキャッシュをクリア
            if attempt < max_attempts - 1:
                for path in accessed_paths_in_attempt:
                    if path in ocr_cache:
                        del ocr_cache[path]

        # 最終的な結果を報告
        if not found:
             print(f"  -> ページ '{target_page}' は見つかりませんでした。({max_attempts}回試行)")


    # --- 4. 最終結果の整形 ---
    final_found_paths = []
    for page_num in revision_data[target_revision]:
        if page_num in found_pages_map:
            final_found_paths.append(found_pages_map[page_num])
        else:
            print(f"  [警告] 対象ページ '{page_num}' は最終結果に含まれませんでした。")
            
    return final_found_paths


if __name__ == '__main__':
    # (テストコードは変更なし)
    test_png_folder = "temp_png_images"
    test_rev_data = {
        'P': ['A-5', '10', 'B-1'], 
        'C': ['100', 'A-2']
    }
    target_rev = 'P'
    
    if os.path.exists(test_png_folder):
        found_files = find_pages_for_revision(test_png_folder, test_rev_data, target_rev)
        print("\n--- Page Finder Result ---")
        if found_files:
            print(f"変更記号 '{target_rev}' に該当するファイルが見つかりました:")
            sorted_files = natsort.natsorted(found_files, key=lambda x: os.path.splitext(os.path.basename(x))[0])
            for f in sorted_files:
                print(f"- {os.path.basename(f)}")
        else:
            print(f"変更記号 '{target_rev}' に該当するページは見つかりませんでした。")
    else:
        print(f"テスト用のPNGフォルダが見つかりません: {test_png_folder}")
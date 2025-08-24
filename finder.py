# finder.py
import os
import re
import natsort
from gemini_handler import get_text_from_image

def find_pages_for_revision(png_folder, revision_data, target_revision):
    """
    指定された変更記号に対応するページを、二分探索を用いて効率的に見つける。
    - natsortによる自然順比較
    - OCR結果のキャッシュ
    - 複数ターゲットの同時探索
    - OCR失敗時のフォールバック
    """
    if target_revision not in revision_data:
        print(f"エラー: 変更記号 '{target_revision}' は変更履歴一覧に存在しません。")
        return []

    # --- 1. 初期設定 ---
    png_files = sorted(
        [f for f in os.listdir(png_folder) if f.lower().endswith('.png')],
        key=lambda x: int(os.path.splitext(x)[0])
    )
    
    # 全ての探したいページ番号をセットにまとめる
    all_target_pages = set()
    for pages in revision_data.values():
        all_target_pages.update(pages)

    ocr_cache = {}  # OCR結果をキャッシュする辞書 {image_path: page_number}
    found_pages_map = {} # 見つかったページを格納する辞書 {page_number: image_path}
    ns_key = natsort.natsort_keygen() # 自然順ソート用のキー生成関数

    # --- 2. ヘルパー関数の定義 ---
    def _get_page_number_at_index(index):
        """指定されたインデックスの画像のページ番号をOCRまたはキャッシュから取得する。"""
        if not (0 <= index < len(png_files)):
            return None # 範囲外
            
        image_path = os.path.join(png_folder, png_files[index])
        
        # キャッシュがあればOCRせずに返す
        if image_path in ocr_cache:
            return ocr_cache[image_path]

        # OCR実行
        prompt = "この図面画像の右下に記載されているページ番号（例：'A-104'）だけを抽出してください。図面番号（例：'W426297'）は無視してください。"
        page_number_text = get_text_from_image(image_path, prompt)
        
        extracted_num = None
        if page_number_text:
            # ハイフンやアルファベットを許容しつつ、不要な文字を削除
            # 例: "Page: A-101" -> "A-101"
            match = re.search(r'([a-zA-Z0-9\-]+)', page_number_text)
            if match:
                extracted_num = match.group(1)

        # OCR結果をキャッシュに保存 (失敗した場合はNoneを保存)
        ocr_cache[image_path] = extracted_num
        
        # 偶然見つかった別のターゲットページも記録
        if extracted_num in all_target_pages and extracted_num not in found_pages_map:
            print(f"  (偶然発見) -> ページ '{extracted_num}' を発見しました: {png_files[index]}")
            found_pages_map[extracted_num] = image_path

        return extracted_num

    # --- 3. メインの二分探索ループ ---
    # まだ見つかっていないページが残っている限り探索を続ける
    remaining_pages_to_find = all_target_pages.copy()
    
    while remaining_pages_to_find:
        # 残っているページのうち、自然順で最初のものをターゲットにする
        target_page = natsort.natsorted(list(remaining_pages_to_find))[0]
        
        print(f"\n探索ターゲット: '{target_page}'")
        low, high = 0, len(png_files) - 1
        found_in_this_loop = False

        while low <= high:
            mid = (low + high) // 2
            current_page_num = _get_page_number_at_index(mid)

            # OCR失敗時のフォールバック処理
            if current_page_num is None:
                print(f"  [警告] index:{mid} のページ番号が読み取れません。隣のページを参考にします...")
                # 隣(右側)のページを読んで探索範囲を絞るヒントにする
                neighbor_page_num = _get_page_number_at_index(mid + 1)
                if neighbor_page_num:
                    if ns_key(neighbor_page_num) < ns_key(target_page):
                        low = mid + 2 # 隣のページですら小さいので、もっと右側にある
                    else:
                        high = mid - 1 # 隣のページが大きいか同じなので、左側にあるはず
                else:
                    # 隣も読めない場合は探索範囲を狭めてリトライ
                    high = mid - 1
                continue

            # 二分探索の比較と範囲絞り込み
            if ns_key(current_page_num) < ns_key(target_page):
                low = mid + 1
            elif ns_key(current_page_num) > ns_key(target_page):
                high = mid - 1
            else: # ターゲットを発見した場合
                print(f"  -> ページ '{current_page_num}' を発見しました: {png_files[mid]}")
                found_pages_map[current_page_num] = os.path.join(png_folder, png_files[mid])
                found_in_this_loop = True
                break
        
        # ターゲットが見つかったかどうかにかかわらず、発見済みのページは探索対象から除く
        remaining_pages_to_find.discard(target_page)
        # 探索の過程で偶然見つかったページも除く
        remaining_pages_to_find -= set(found_pages_map.keys())

    # --- 4. 最終結果の整形 ---
    # target_revision に指定されたページリストに対応するファイルパスを返す
    final_found_paths = []
    for page_num in revision_data[target_revision]:
        if page_num in found_pages_map:
            final_found_paths.append(found_pages_map[page_num])
        else:
            print(f"  [警告] 対象ページ '{page_num}' が見つかりませんでした。")
            
    return final_found_paths


if __name__ == '__main__':
    # このファイルを直接実行した際のテストコード
    test_png_folder = "temp_png_images" # テストしたいPNGフォルダを指定
    # ページ番号にハイフンやアルファベットが含まれるケースを想定
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
            # 自然順でソートして表示
            sorted_files = natsort.natsorted(found_files, key=lambda x: os.path.splitext(os.path.basename(x))[0])
            for f in sorted_files:
                print(f"- {os.path.basename(f)}")
        else:
            print(f"変更記号 '{target_rev}' に該当するページは見つかりませんでした。")
    else:
        print(f"テスト用のPNGフォルダが見つかりません: {test_png_folder}")
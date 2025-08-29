import os
import re
import natsort
import logging
from gemini_handler import get_text_from_image

# ロガーを取得
logger = logging.getLogger(__name__)

def find_pages_for_revision(png_folder, revision_data, target_revision):
    """
    シンプルな二分探索を使い、ページを見つける。
    より堅牢な単調増加チェック機能を追加。
    """
    if target_revision not in revision_data or not revision_data[target_revision]:
        logger.error(f"変更記号 '{target_revision}' は変更履歴一覧に存在しないか、ページが空です。")
        return {}

    png_files = sorted(
        [f for f in os.listdir(png_folder) if f.lower().endswith('.png')],
        key=lambda x: int(os.path.splitext(x)[0])
    )
    
    target_pages_to_find = set(revision_data[target_revision])
    ocr_cache, found_pages_map = {}, {}
    ns_key = natsort.natsort_keygen()

    def _get_page_number_at_index(index):
        """指定インデックスのページ番号を取得。堅牢な単調増加チェックを行う。"""
        if not (0 <= index < len(png_files)): return None
        image_path = os.path.join(png_folder, png_files[index])
        
        if image_path in ocr_cache: return ocr_cache[image_path]

        prompt = "この図面画像の右下に記載されているページ番号（例：'A-104'）だけを抽出してください。図面番号（例：'W426297'）は無視してください。"
        page_number_text = get_text_from_image(image_path, prompt)
        
        extracted_num = None
        if page_number_text:
            if '/' in page_number_text:
                extracted_num = None
            else:
                match = re.search(r'([a-zA-Z0-9\-]+)', page_number_text)
                if match: extracted_num = match.group(1)

        if index > 0 and extracted_num is not None:
            for i in range(index - 1, -1, -1):
                prev_image_path = os.path.join(png_folder, png_files[i])
                if prev_image_path in ocr_cache:
                    prev_page_num = ocr_cache[prev_image_path]
                    if prev_page_num is not None:
                        if ns_key(extracted_num) < ns_key(prev_page_num):
                            logger.warning(f"\n  [警告] 単調増加ルール違反を検出。")
                            logger.warning(f"    -> 近い過去のページ {os.path.basename(prev_image_path)} (頁: {prev_page_num}) に対し、")
                            logger.warning(f"    -> 今回のページ {os.path.basename(image_path)} (頁: {extracted_num}) が小さすぎます。")
                            logger.warning(f"    -> '{extracted_num}' は不正なOCR結果とみなし、このページの読み取りを無効化します。")
                            ocr_cache[image_path] = None
                            return None
                        break
        
        # ★★★ 変更点: ログレベルを DEBUG から INFO に変更 ★★★
        logger.info(f"  -> file: {os.path.basename(image_path):>8s} | AI raw output: '{page_number_text}' | Extracted: '{extracted_num}'")

        ocr_cache[image_path] = extracted_num
        return extracted_num

    for target_page in natsort.natsorted(list(target_pages_to_find)):
        # 元のprintの改行を再現するために \n を追加
        logger.info(f"探索ターゲット: '{target_page}'")
        found = False
        
        low, high = 0, len(png_files) - 1
        for _ in range(len(png_files) + 1):
            if low > high: break
            mid = (low + high) // 2
            
            current_page_num = _get_page_number_at_index(mid)

            if current_page_num is None:
                high = mid - 1
                continue

            if ns_key(current_page_num) < ns_key(target_page):
                low = mid + 1
            elif ns_key(current_page_num) > ns_key(target_page):
                high = mid - 1
            else:
                logger.info(f"  -> ページ '{current_page_num}' を発見しました: {png_files[mid]}")
                found_pages_map[target_page] = os.path.join(png_folder, png_files[mid])
                found = True
                break
        
        if not found:
             logger.warning(f"  -> ページ '{target_page}' は見つかりませんでした。")

    return found_pages_map
import os
import re
import natsort
from PIL import Image
from gemini_handler import get_text_from_image

# --- グローバル変数としてお手本画像を最初に一度だけ読み込む ---
EXAMPLE_PROMPT_PARTS = []
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
EXAMPLE_DIR = os.path.join(PROJECT_ROOT, "prompt_examples")

if os.path.exists(EXAMPLE_DIR):
    print(f"お手本画像を '{EXAMPLE_DIR}' から読み込んでいます...")
    EXAMPLE_PROMPT_PARTS.append("あなたは図面の専門家です。提示されたお手本画像を参考に、新しい画像からページ番号を抽出してください。ページ番号以外の余計な文字列は含めないでください。")
    
    example_files = sorted([f for f in os.listdir(EXAMPLE_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    
    if not example_files:
        print(f"  [警告] '{EXAMPLE_DIR}'フォルダは空です。お手本なしで実行します。")
        EXAMPLE_PROMPT_PARTS = []
    else:
        for filename in example_files:
            try:
                img_path = os.path.join(EXAMPLE_DIR, filename)
                img = Image.open(img_path)
                if img.mode != 'RGB': img = img.convert('RGB')
                EXAMPLE_PROMPT_PARTS.append("以下はお手本です。赤枠で囲われた部分がページ番号です。")
                EXAMPLE_PROMPT_PARTS.append(img)
            except Exception as e:
                print(f"  [警告] お手本画像 {filename} の読み込みに失敗しました: {e}")
else:
    print(f"  [警告] お手本画像フォルダ '{EXAMPLE_DIR}' が見つかりません。通常のテキストプロンプトを使用します。")


def find_pages_for_revision(png_folder, revision_data, target_revision):
    """
    Few-shotプロンプトと二分探索を使いページを見つける。
    （リトライ機能は削除）
    """
    if target_revision not in revision_data or not revision_data[target_revision]:
        print(f"エラー: 変更記号 '{target_revision}' は変更履歴一覧に存在しないか、ページが空です。")
        return {}

    png_files = sorted(
        [f for f in os.listdir(png_folder) if f.lower().endswith('.png')],
        key=lambda x: int(os.path.splitext(x)[0])
    )
    
    target_pages_to_find = set(revision_data[target_revision])
    ocr_cache, found_pages_map, seen_page_numbers_map = {}, {}, {}
    ns_key = natsort.natsort_keygen()

    def _get_page_number_at_index(index):
        """指定インデックスのページ番号を取得。重複検出時にキャッシュを無効化する。"""
        if not (0 <= index < len(png_files)): return None
        image_path = os.path.join(png_folder, png_files[index])
        
        if image_path in ocr_cache: return ocr_cache[image_path]

        # ★★★ 変更点: OCRの再試行ループを削除 ★★★
        page_number_text = None
        try:
            target_image = Image.open(image_path)
            if target_image.mode != 'RGB': target_image = target_image.convert('RGB')

            if EXAMPLE_PROMPT_PARTS:
                prompt_parts = EXAMPLE_PROMPT_PARTS + ["これを踏まえて、次の新しい画像からページ番号だけを抽出してください。", target_image]
                page_number_text = get_text_from_image(prompt_parts)
            else:
                prompt = "この図面画像の右下の四角の中に記載されているページ番号（例：'A-104'）だけを抽出してください。図面番号（例：'W426297'）は無視してください。ページ番号に"/"は含まれない"
                page_number_text = get_text_from_image(target_image, prompt)
        except Exception as e:
            print(f"\n  [エラー] OCR中にエラーが発生しました: {e}")
            page_number_text = None

        if page_number_text and page_number_text in seen_page_numbers_map:
            original_path = seen_page_numbers_map[page_number_text]
            if original_path != image_path:
                print(f"\n  [警告] 重複ページ番号 '{page_number_text}' を検出。")
                print(f"    -> 今回: {os.path.basename(image_path)}, 前回: {os.path.basename(original_path)}")
                if original_path in ocr_cache: del ocr_cache[original_path]
                del seen_page_numbers_map[page_number_text]
        
        if page_number_text and page_number_text not in seen_page_numbers_map:
            seen_page_numbers_map[page_number_text] = image_path
        
        extracted_num = None
        if page_number_text:
            match = re.search(r'([a-zA-Z0-9\-]+)', page_number_text)
            if match: extracted_num = match.group(1)

        print(f"  [DEBUG] file: {os.path.basename(image_path):>8s} | AI raw output: '{page_number_text}' | Extracted: '{extracted_num}'")

        ocr_cache[image_path] = extracted_num
        return extracted_num

    for target_page in natsort.natsorted(list(target_pages_to_find)):
        print(f"\n探索ターゲット: '{target_page}'")
        found = False
        
        # ★★★ 変更点: 探索の再試行ループを削除 ★★★
        low, high = 0, len(png_files) - 1
        while low <= high:
            mid = (low + high) // 2
            # ヘルパー関数の呼び出しをシンプルに
            current_page_num = _get_page_number_at_index(mid)
            if current_page_num is None:
                high = mid - 1
                continue
            if ns_key(current_page_num) < ns_key(target_page): low = mid + 1
            elif ns_key(current_page_num) > ns_key(target_page): high = mid - 1
            else:
                print(f"  -> ページ '{current_page_num}' を発見しました: {png_files[mid]}")
                found_pages_map[target_page] = os.path.join(png_folder, png_files[mid])
                found = True
                break
        
        if not found:
             print(f"  -> ページ '{target_page}' は見つかりませんでした。")

    return found_pages_map
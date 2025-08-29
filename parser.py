import os
import json
import re
import logging
from gemini_handler import get_text_from_image

# ロガーを取得
logger = logging.getLogger(__name__)

def _find_special_pages(png_folder):
    """
    PNG画像から、連続する目次と変更履歴一覧表のページをすべて特定する。
    目次と変更履歴一覧表の間に他のページが存在する可能性を考慮する。
    """
    special_pages = {"toc": [], "revision_history": []}
    
    png_files = sorted(
        [f for f in os.listdir(png_folder) if f.lower().endswith('.png')],
        key=lambda x: int(os.path.splitext(x)[0])
    )

    if not png_files:
        logger.warning("PNGフォルダに画像がありません。")
        return special_pages

    page_index = 0

    # --- フェーズ1: 目次の探索 ---
    logger.info("フェーズ1: 目次の探索を開始します。")
    
    first_page_file = png_files[0]
    first_image_path = os.path.join(png_folder, first_page_file)
    logger.info(f"  [仮定] 最初のページ '{first_page_file}' を目次として追加します。")
    special_pages["toc"].append(first_image_path)
    page_index = 1

    while page_index < len(png_files):
        png_file = png_files[page_index]
        image_path = os.path.join(png_folder, png_file)
        prompt = "この画像の下部中央に書かれている表のタイトルを読み取ってください。"
        title = get_text_from_image(image_path, prompt)

        if title and "目次" in title:
            logger.info(f"  [発見] 連続する目次ページ: {png_file}")
            special_pages["toc"].append(image_path)
            page_index += 1
        else:
            logger.info(f"  '{png_file}' は目次ではありません。目次の探索を終了します。")
            break
    
    # --- フェーズ2: 変更履歴一覧表の探索 ---
    logger.info("フェーズ2: 変更履歴一覧表の探索を開始します。")
    
    while page_index < len(png_files):
        png_file = png_files[page_index]
        image_path = os.path.join(png_folder, png_file)
        prompt = "この画像の下部中央に書かれている表のタイトルを読み取ってください。"
        title = get_text_from_image(image_path, prompt)

        if title and "変更履歴一覧表" in title:
            logger.info(f"  [発見] 変更履歴一覧表ページ: {png_file}")
            special_pages["revision_history"].append(image_path)
            page_index += 1
        else:
            if special_pages["revision_history"]:
                logger.info(f"  '{png_file}' は変更履歴一覧表ではありません。探索を終了します。")
                break
            else:
                logger.info(f"  [スキップ] '{png_file}' は変更履歴一覧表ではありません。探索を続行します。")
                page_index += 1

    logger.info("全ての探索が完了しました。")
    return special_pages

def parse_revision_history(image_path):
    """変更履歴一覧表の画像を解析し、変更記号とページの対応辞書を返す。"""
    prompt = """
    この画像は「変更履歴一覧表」です。
    表の内容を読み取り、各「変更記号」に対応する「変更頁」のリストをJSON形式で出力してください。
    
    例:
    {
        "C": ["023", "105", "422", "423", "514"],
        "P": ["561", "562", "591"]
    }
    """
    response_text = get_text_from_image(image_path, prompt)
    
    if not response_text:
        return None
        
    try:
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            data = json.loads(json_str)
            
            for key, value in data.items():
                if isinstance(value, str):
                    pages = re.split(r'[,\s]+', value)
                    data[key] = [p.strip() for p in pages if p.strip()]
            return data
        else:
            logger.warning("Geminiの応答からJSONを抽出できませんでした。")
            return None
    except json.JSONDecodeError:
        logger.error("Geminiの応答をJSONとして解析できませんでした。")
        return None

if __name__ == '__main__':
    # このファイルを直接実行した際のテストコード
    test_png_folder = "temp_png_images" 
    if os.path.exists(test_png_folder):
        pages = _find_special_pages(test_png_folder)
        
        print("\n--- 目次ページ一覧 ---")
        print(pages["toc"])
        
        print("\n--- 変更履歴一覧表ページ一覧 ---")
        print(pages["revision_history"])

        if pages["revision_history"]:
            full_revision_data = {}
            for rev_page_path in pages["revision_history"]:
                print(f"\n--- '{os.path.basename(rev_page_path)}' を解析中... ---")
                single_page_data = parse_revision_history(rev_page_path)
                if single_page_data:
                    for key, value in single_page_data.items():
                        if key in full_revision_data:
                            full_revision_data[key].extend(value)
                        else:
                            full_revision_data[key] = value
            
            print("\n--- 結合後の変更履歴データ ---")
            print(json.dumps(full_revision_data, indent=4, ensure_ascii=False))
    else:
        print(f"テスト用のPNGフォルダが見つかりません: {test_png_folder}")
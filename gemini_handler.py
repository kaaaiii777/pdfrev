import os
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv
import logging

# ロガーを取得
logger = logging.getLogger(__name__)

# .envファイルから環境変数を読み込む
load_dotenv()

# APIキーを設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    # ログを出力してから例外を発生させる
    logger.critical("GEMINI_API_KEYが.envファイルに設定されていません。")
    raise ValueError("GEMINI_API_KEYが.envファイルに設定されていません。")

try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    logger.critical(f"Google AIの初期設定に失敗しました: {e}")
    raise

def get_text_from_image(*args):
    """
    指定された画像とプロンプトをGemini APIに送信し、テキスト応答を取得する。
    引数の与え方によって、2つのモードで動作する。
    """
    try:
        # 高度な画像認識に最適なAPIモデルIDを指定
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        content = []
        if len(args) == 1 and isinstance(args[0], list):
            # モード1: Few-shotプロンプト
            content = args[0]
        elif len(args) == 2:
            # モード2: 通常プロンプト
            image_source, prompt = args[0], args[1]
            image = None
            if isinstance(image_source, str):
                if not os.path.exists(image_source):
                    logger.error(f"画像ファイルが見つかりません: {image_source}")
                    raise FileNotFoundError(f"画像ファイルが見つかりません: {image_source}")
                image = Image.open(image_source)
            elif isinstance(image_source, Image.Image):
                image = image_source
            
            if image and isinstance(prompt, str):
                content = [prompt, image]
            else:
                raise TypeError("不正な引数です。get_text_from_image('画像パス', 'プロンプト') または get_text_from_image([パーツのリスト])の形式で呼び出してください。")
        else:
            raise ValueError(f"不正な数の引数です。{len(args)}個の引数が渡されました。")

        if content:
            response = model.generate_content(content)
            return response.text.strip()
        else:
            return None

    except Exception as e:
        logger.error(f"Gemini APIとの通信に失敗しました - {e}")
        return None

if __name__ == '__main__':
    # このファイルを直接実行する場合のテストコード
    # アプリケーション全体とは別の、基本的なロギング設定をここで行う
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)-8s - %(module)-15s - %(message)s')
    
    logger.info("--- Gemini API Handler Test ---")
    
    test_image = "test_image.png" # テストしたい画像ファイル名に書き換えてください
    if os.path.exists(test_image):
        test_prompt = "この画像に書かれている内容を30字以内で説明してください。"
        result = get_text_from_image(test_image, test_prompt)
        logger.info("--- Gemini API Test Result ---")
        logger.info(result)
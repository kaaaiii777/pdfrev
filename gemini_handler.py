# gemini_handler.py
import os
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# APIキーを設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEYが.envファイルに設定されていません。")
genai.configure(api_key=GEMINI_API_KEY)

def get_text_from_image(image_path, prompt):
    """
    指定された画像とプロンプトをGemini APIに送信し、テキスト応答を取得する。

    Args:
        image_path (str): 解析する画像のパス。
        prompt (str): Geminiに与える指示プロンプト。

    Returns:
        str: Geminiからのテキスト応答。エラー時はNone。
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-pro')
        image = Image.open(image_path)
        response = model.generate_content([prompt, image])
        return response.text.strip()
    except Exception as e:
        print(f"エラー: Gemini APIとの通信に失敗しました - {e}")
        return None

if __name__ == '__main__':
    # このファイルを直接実行した際のテストコード
    # 添付されていた変更履歴の画像でテスト
    test_image = "01_変更前_W426297_P変更一式_page_4.png" 
    if os.path.exists(test_image):
        test_prompt = "この画像から「変更履歴一覧表」を読み取り、変更記号と変更頁をJSON形式で出力してください。"
        result = get_text_from_image(test_image, test_prompt)
        print("--- Gemini API Test Result ---")
        print(result)
    else:
        print(f"テスト用の画像ファイルが見つかりません: {test_image}")
    
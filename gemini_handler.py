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

def get_text_from_image(*args):
    """
    指定された画像とプロンプトをGemini APIに送信し、テキスト応答を取得する。
    引数の与え方によって、2つのモードで動作する。
    
    モード1 (Few-shotプロンプト): 
        get_text_from_image(['テキスト', Image, 'テキスト', Image, ...])
    
    モード2 (通常プロンプト):
        get_text_from_image(Image, "プロンプトテキスト")
        get_text_from_image("画像パス", "プロンプトテキスト")

    Returns:
        str: Geminiからのテキスト応答。エラー時はNone。
    """
    try:
        # ★★★ 変更点: より高性能な画像認識モデルを指定 ★★★
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        # ★★★ 変更点: 引数の形式に応じてコンテンツを構築 ★★★
        content = []
        if len(args) == 1 and isinstance(args[0], list):
            # モード1: Few-shotプロンプト (引数がリスト一つ)
            # finder.pyからの呼び出しに対応
            content = args[0]
        elif len(args) == 2:
            # モード2: 通常プロンプト (引数が2つ)
            # parser.pyからの呼び出しや、finder.pyのフォールバックに対応
            image_arg, prompt_arg = args[0], args[1]
            image = None
            if isinstance(image_arg, str): # 引数が画像パスの場合
                if not os.path.exists(image_arg):
                    raise FileNotFoundError(f"画像ファイルが見つかりません: {image_arg}")
                image = Image.open(image_arg)
            elif isinstance(image_arg, Image.Image): # 引数がImageオブジェクトの場合
                image = image_arg
            
            if image and isinstance(prompt_arg, str):
                content = [prompt_arg, image]
            else:
                raise TypeError("不正な引数です。get_text_from_image('画像パス', 'プロンプト') または get_text_from_image([パーツのリスト])の形式で呼び出してください。")
        else:
            raise ValueError(f"不正な数の引数です。{len(args)}個の引数が渡されました。")

        # コンテンツが正常に構築された場合のみAPIを呼び出す
        if content:
            response = model.generate_content(content)
            return response.text.strip()
        else:
            return None

    except Exception as e:
        print(f"エラー: Gemini APIとの通信に失敗しました - {e}")
        return None

if __name__ == '__main__':
    # このファイルを直接実行した際のテストコード
    print("--- Gemini API Handler Test ---")
    
    # テスト用の画像パス (parser.pyのテストで使うような画像)
    test_image_path = "test_image_for_parser.png" 
    
    # テスト用のお手本画像のパス
    example_image_path = os.path.join("prompt_examples", "example1.png") # フォルダ名とファイル名は適宜変更してください

    # --- テスト1: 通常のプロンプト ---
    print("\n[テスト1: 通常のプロンプト (parser.pyのような使い方)]")
    if os.path.exists(test_image_path):
        test_prompt = "この画像から「変更履歴一覧表」を読み取り、変更記号と変更頁をJSON形式で出力してください。"
        result = get_text_from_image(test_image_path, test_prompt)
        print(result)
    else:
        print(f"テスト用の画像ファイルが見つかりません: {test_image_path}")

    # --- テスト2: Few-shotプロンプト ---
    print("\n[テスト2: Few-shotプロンプト (finder.pyのような使い方)]")
    if os.path.exists(example_image_path) and os.path.exists(test_image_path):
        example_img_obj = Image.open(example_image_path)
        target_img_obj = Image.open(test_image_path)
        
        few_shot_prompt = [
            "以下はお手本です。赤枠で囲われた部分がページ番号です。",
            example_img_obj,
            "これを踏まえて、次の新しい画像からページ番号だけを抽出してください。",
            target_img_obj
        ]
        
        result = get_text_from_image(few_shot_prompt)
        print(f"Few-shotプロンプトによる抽出結果: {result}")
    else:
        print(f"テスト用のお手本画像または対象画像が見つかりません。")
    
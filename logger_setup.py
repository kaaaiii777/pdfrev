import logging
import sys

def setup_logging(log_file_path):
    """
    アプリケーション全体のロギングを設定する。
    ファイルとコンソールの両方に出力する。
    """
    # ルートロガーを取得し、最低レベルをDEBUGに設定
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # 既存のハンドラをすべて削除（重複防止）
    if logger.hasHandlers():
        logger.handlers.clear()

    # フォーマッターを定義
    formatter = logging.Formatter('%(asctime)s - %(levelname)-8s - %(module)-15s - %(message)s')

    # 1. コンソールへの出力用ハンドラ
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO) # コンソールにはINFO以上を表示
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. ファイルへの出力用ハンドラ
    try:
        file_handler = logging.FileHandler(log_file_path, 'w', 'utf-8')
        file_handler.setLevel(logging.DEBUG) # ファイルにはDEBUG以上をすべて記録
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logging.error(f"ログファイルの作成に失敗しました: {e}")

    logging.info("ロギング設定が完了しました。")
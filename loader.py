import os
import fitz  # PyMuPDF (fitz)
import shutil
import logging

# ロガーを取得
logger = logging.getLogger(__name__)

def merge_pdfs(pdf_paths, output_path):
    """
    複数のPDFファイルを1つのPDFに結合する関数
    """
    try:
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        merged_doc = fitz.open()
        
        for pdf_path in pdf_paths:
            if not os.path.isfile(pdf_path):
                logger.warning(f"ファイル '{pdf_path}' が見つかりません。スキップします。")
                continue
            
            try:
                doc = fitz.open(pdf_path)
                merged_doc.insert_pdf(doc)
                doc.close()
                logger.info(f"'{os.path.basename(pdf_path)}' を結合しました。")
            except Exception as e:
                logger.error(f"'{pdf_path}' の処理中に問題が発生しました - {e}")
                continue
        
        if merged_doc.page_count > 0:
            merged_doc.save(output_path)
            merged_doc.close()
            logger.info(f"結合されたPDFを '{output_path}' に保存しました。")
            return True
        else:
            logger.error("結合するPDFファイルが見つかりませんでした。")
            merged_doc.close()
            return False
            
    except Exception as e:
        logger.error(f"PDF結合中に問題が発生しました - {e}")
        return False

def convert_pdf_to_png(pdf_file_path, dpi, output_folder_name):
    """
    指定されたPDFファイルをPNG画像に変換します。
    """
    if not os.path.isfile(pdf_file_path):
        logger.error(f"指定されたファイル '{pdf_file_path}' が見つかりません。")
        return

    if not pdf_file_path.lower().endswith(".pdf"):
        logger.error(f"指定されたファイル '{pdf_file_path}' はPDFファイルではありません。")
        return

    output_path = output_folder_name
    os.makedirs(output_path, exist_ok=True)
    
    base_name = os.path.splitext(os.path.basename(pdf_file_path))[0]

    try:
        doc = fitz.open(pdf_file_path)
        total_pages = len(doc)
        logger.info(f"'{os.path.basename(pdf_file_path)}' のPNG変換を開始します (全{total_pages}ページ)...")
        
        last_reported_progress = -1

        for page_num in range(total_pages):
            # 10%ごとに進捗をログに出力
            progress = int(((page_num + 1) / total_pages) * 10)
            if progress > last_reported_progress:
                logger.info(f"  -> 変換進捗: {progress * 10}%...")
                last_reported_progress = progress

            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=dpi)
            
            output_png_filename = f"{page_num + 1}.png"
            output_png_path = os.path.join(output_path, output_png_filename)
            pix.save(output_png_path)
        
        doc.close()
        logger.info(f"'{os.path.basename(pdf_file_path)}' の変換が完了しました。")

    except Exception as e:
        logger.error(f"'{os.path.basename(pdf_file_path)}' の変換中に問題が発生しました - {e}")

def process_multiple_pdfs(pdf_paths, dpi, output_folder_name, merge_first=True):
    """
    複数のPDFファイルを処理する関数
    """
    if not pdf_paths:
        logger.error("処理するPDFファイルが指定されていません。")
        return False
    
    if merge_first:
        logger.info("複数PDFを結合してから処理します...")
        
        os.makedirs(output_folder_name, exist_ok=True)
        temp_merged_pdf = os.path.join(output_folder_name, "temp_merged.pdf")
        
        if merge_pdfs(pdf_paths, temp_merged_pdf):
            convert_pdf_to_png(temp_merged_pdf, dpi, output_folder_name)
            
            try:
                os.remove(temp_merged_pdf)
                logger.info("一時ファイルを削除しました。")
            except Exception as e:
                logger.warning(f"一時ファイルの削除に失敗しました: {e}")
            
            return True
        else:
            logger.error("PDFの結合に失敗しました。")
            return False
    else:
        logger.info("各PDFを個別に処理します...")
        # (省略)
        return True
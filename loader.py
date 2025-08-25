import os
import fitz  # PyMuPDF (fitz)
import shutil

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
                print(f"警告: ファイル '{pdf_path}' が見つかりません。スキップします。")
                continue
            
            try:
                doc = fitz.open(pdf_path)
                merged_doc.insert_pdf(doc)
                doc.close()
                print(f"'{os.path.basename(pdf_path)}' を結合しました。")
            except Exception as e:
                print(f"エラー: '{pdf_path}' の処理中に問題が発生しました - {e}")
                continue
        
        if merged_doc.page_count > 0:
            merged_doc.save(output_path)
            merged_doc.close()
            print(f"結合されたPDFを '{output_path}' に保存しました。")
            return True
        else:
            print("エラー: 結合するPDFファイルが見つかりませんでした。")
            merged_doc.close()
            return False
            
    except Exception as e:
        print(f"エラー: PDF結合中に問題が発生しました - {e}")
        return False

def convert_pdf_to_png(pdf_file_path, dpi, output_folder_name):
    """
    指定されたPDFファイルをPNG画像に変換します。
    """
    if not os.path.isfile(pdf_file_path):
        print(f"エラー: 指定されたファイル '{pdf_file_path}' が見つかりません。")
        return

    if not pdf_file_path.lower().endswith(".pdf"):
        print(f"エラー: 指定されたファイル '{pdf_file_path}' はPDFファイルではありません。")
        return

    if os.path.isabs(output_folder_name):
        output_path = output_folder_name
    else:
        pdf_dir = os.path.dirname(pdf_file_path)
        if not pdf_dir:
            pdf_dir = "."
        output_path = os.path.join(pdf_dir, output_folder_name)

    os.makedirs(output_path, exist_ok=True)
    
    base_name = os.path.splitext(os.path.basename(pdf_file_path))[0]

    try:
        doc = fitz.open(pdf_file_path)

        total_pages = len(doc)
        print(f"'{os.path.basename(pdf_file_path)}' のPNG変換を開始します (全{total_pages}ページ)...")

        bar_width = 40 # プログレスバーの幅（文字数）

        for page_num in range(total_pages):
            # ★★★ 変更点: プログレスバー形式での進捗表示 ★★★
            percentage = (page_num + 1) / total_pages
            filled_len = int(bar_width * percentage)
            bar = '█' * filled_len + '-' * (bar_width - filled_len)
            percentage_display = int(percentage * 100)
            print(f"  -> 変換中: |{bar}| {percentage_display}%", end='\r')

            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=dpi)
            
            output_png_filename = f"{page_num + 1}.png"
            output_png_path = os.path.join(output_path, output_png_filename)
            pix.save(output_png_path)
        
        doc.close()
        
        # ループが終わった後に改行を追加して表示を確定
        print() 
        print(f"'{os.path.basename(pdf_file_path)}' の変換が完了しました。\n")

    except Exception as e:
        print(f"エラー: '{os.path.basename(pdf_file_path)}' の変換中に問題が発生しました - {e}\n")

def process_multiple_pdfs(pdf_paths, dpi, output_folder_name, merge_first=True):
    """
    複数のPDFファイルを処理する関数
    """
    if not pdf_paths:
        print("エラー: 処理するPDFファイルが指定されていません。")
        return False
    
    if merge_first:
        print("複数PDFを結合してから処理します...")
        
        temp_merged_pdf = "temp_merged.pdf"
        
        if merge_pdfs(pdf_paths, temp_merged_pdf):
            convert_pdf_to_png(temp_merged_pdf, dpi, output_folder_name)
            
            try:
                os.remove(temp_merged_pdf)
                print("一時ファイルを削除しました。")
            except Exception as e:
                print(f"一時ファイルの削除に失敗しました: {e}")
            
            return True
        else:
            print("PDFの結合に失敗しました。")
            return False
    else:
        # (個別処理の部分は変更なし)
        print("各PDFを個別に処理します...")
        
        page_offset = 0
        for i, pdf_path in enumerate(pdf_paths):
            print(f"PDF {i+1}/{len(pdf_paths)}: {os.path.basename(pdf_path)} を処理中...")
            
            individual_output = f"{output_folder_name}_part{i+1}"
            
            convert_pdf_to_png(pdf_path, dpi, individual_output)
            
            if os.path.exists(individual_output):
                png_files = [f for f in os.listdir(individual_output) if f.lower().endswith('.png')]
                png_files.sort(key=lambda x: int(x.split('.')[0]))
                
                for png_file in png_files:
                    old_path = os.path.join(individual_output, png_file)
                    new_page_num = page_offset + int(png_file.split('.')[0])
                    new_png_file = f"{new_page_num}.png"
                    new_path = os.path.join(output_folder_name, new_png_file)
                    
                    shutil.move(old_path, new_path)
                
                shutil.rmtree(individual_output)
                page_offset += len(png_files)
        
        print(f"全{len(pdf_paths)}個のPDFファイルの処理が完了しました。")
        return True
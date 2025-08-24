import os
import fitz  # PyMuPDF (fitz)
import shutil # フォルダ削除のため (後で使う可能性のある関数)

def merge_pdfs(pdf_paths, output_path):
    """
    複数のPDFファイルを1つのPDFに結合する関数
    
    Args:
        pdf_paths (list): 結合するPDFファイルのパスのリスト
        output_path (str): 出力PDFファイルのパス
    
    Returns:
        bool: 成功時True、失敗時False
    """
    try:
        # 出力ディレクトリを作成
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # 新しいPDFドキュメントを作成
        merged_doc = fitz.open()
        
        # 各PDFファイルを順番に追加
        for pdf_path in pdf_paths:
            if not os.path.isfile(pdf_path):
                print(f"警告: ファイル '{pdf_path}' が見つかりません。スキップします。")
                continue
                
            try:
                # PDFファイルを開く
                doc = fitz.open(pdf_path)
                
                # 全ページを結合ドキュメントに追加
                merged_doc.insert_pdf(doc)
                
                # ドキュメントを閉じる
                doc.close()
                print(f"'{os.path.basename(pdf_path)}' を結合しました。")
                
            except Exception as e:
                print(f"エラー: '{pdf_path}' の処理中に問題が発生しました - {e}")
                continue
        
        # 結合されたPDFを保存
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
    PDFと同じディレクトリにフォルダを作成し、その中にページ番号でPNGを保存します。

    Args:
        pdf_file_path (str): 変換したいPDFファイルのパス
        dpi (int): 変換するPNG画像の解像度（Dots Per Inch）。デフォルトは400
        output_folder_name (str): 変換されたPNG画像を格納する出力フォルダの名前。
                                 このフォルダはPDFファイルと同じディレクトリに作成されます。

    Returns:
        None: 成功時はメッセージを出力、失敗時はエラーメッセージを出力

    Raises:
        FileNotFoundError: 指定されたPDFファイルが存在しない場合
        ValueError: 指定されたファイルがPDFでない場合
        Exception: PDF変換中にエラーが発生した場合
    """

    # PDFファイルの存在確認
    if not os.path.isfile(pdf_file_path):
        print(f"エラー: 指定されたファイル '{pdf_file_path}' が見つかりません。")
        return

    # PDFファイルの拡張子確認
    if not pdf_file_path.lower().endswith(".pdf"):
        print(f"エラー: 指定されたファイル '{pdf_file_path}' はPDFファイルではありません。")
        return

    # 出力フォルダのパスを生成
    # output_folder_nameが絶対パスの場合はそのまま使用、相対パスの場合はPDFファイルのディレクトリを基準にする
    if os.path.isabs(output_folder_name):
        output_path = output_folder_name
    else:
        # PDFファイルのディレクトリパスを取得
        pdf_dir = os.path.dirname(pdf_file_path)
        if not pdf_dir:
            pdf_dir = "."  # カレントディレクトリの場合
        output_path = os.path.join(pdf_dir, output_folder_name)

    # 出力フォルダが存在しない場合は作成
    os.makedirs(output_path, exist_ok=True)
    # print(f"変換されたPNG画像は '{output_path}' フォルダ内に保存されます。\n")

    # 拡張子を除いたファイル名を取得 (例: document.pdf -> document)
    base_name = os.path.splitext(os.path.basename(pdf_file_path))[0]

    # print(f"PDFファイル: '{os.path.basename(pdf_file_path)}' を処理中...")
    # print(f"  -> 保存先フォルダ: '{output_path}'")

    try:
        # PDFドキュメントを開く
        doc = fitz.open(pdf_file_path)

        # PDFの各ページをPNGに変換
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)  # ページを読み込む
            
            # ページをピクセルマップ（画像データ）として取得。ここでDPIを設定。
            # 高DPI設定により、高解像度のPNG画像が生成される
            pix = page.get_pixmap(dpi=dpi)         

            # 出力PNGファイル名を生成 (例: 1.png, 2.png)
            # ページ番号は1から開始（0ベースではない）
            output_png_filename = f"{page_num + 1}.png"
            
            # PNGファイルの保存パスを生成
            output_png_path = os.path.join(output_path, output_png_filename)

            # PNGとして保存
            pix.save(output_png_path)
            # print(f"    -> '{output_png_filename}' を保存しました。")
        
        # ドキュメントを閉じる (リソース解放)
        doc.close()
        # print(f"'{os.path.basename(pdf_file_path)}' の変換が完了しました。\n")

    except Exception as e:
        print(f"エラー: '{os.path.basename(pdf_file_path)}' の変換中に問題が発生しました - {e}\n")

def process_multiple_pdfs(pdf_paths, dpi, output_folder_name, merge_first=True):
    """
    複数のPDFファイルを処理する関数
    
    Args:
        pdf_paths (list): 処理するPDFファイルのパスのリスト
        dpi (int): 変換するPNG画像の解像度
        output_folder_name (str): 出力フォルダの名前
        merge_first (bool): Trueの場合はPDFを結合してから処理、Falseの場合は個別処理
    
    Returns:
        bool: 成功時True、失敗時False
    """
    if not pdf_paths:
        print("エラー: 処理するPDFファイルが指定されていません。")
        return False
    
    if merge_first:
        # PDFを結合してから処理
        print("複数PDFを結合してから処理します...")
        
        # 一時的な結合PDFファイルのパスを生成
        temp_merged_pdf = os.path.join(os.path.dirname(output_folder_name), "temp_merged.pdf")
        
        # PDFを結合
        if merge_pdfs(pdf_paths, temp_merged_pdf):
            # 結合されたPDFをPNGに変換
            convert_pdf_to_png(temp_merged_pdf, dpi, output_folder_name)
            
            # 一時ファイルを削除
            try:
                os.remove(temp_merged_pdf)
                print("一時ファイルを削除しました。")
            except:
                pass
            
            return True
        else:
            print("PDFの結合に失敗しました。")
            return False
    else:
        # 個別処理
        print("各PDFを個別に処理します...")
        
        page_offset = 0
        for i, pdf_path in enumerate(pdf_paths):
            print(f"PDF {i+1}/{len(pdf_paths)}: {os.path.basename(pdf_path)} を処理中...")
            
            # 個別の出力フォルダを作成
            individual_output = f"{output_folder_name}_part{i+1}"
            
            # PDFをPNGに変換
            convert_pdf_to_png(pdf_path, dpi, individual_output)
            
            # 変換されたPNGファイルをメインの出力フォルダに移動（ページ番号を調整）
            if os.path.exists(individual_output):
                png_files = [f for f in os.listdir(individual_output) if f.lower().endswith('.png')]
                png_files.sort(key=lambda x: int(x.split('.')[0]))
                
                for png_file in png_files:
                    old_path = os.path.join(individual_output, png_file)
                    new_page_num = page_offset + int(png_file.split('.')[0])
                    new_png_file = f"{new_page_num}.png"
                    new_path = os.path.join(output_folder_name, new_png_file)
                    
                    # ファイルを移動
                    shutil.move(old_path, new_path)
                
                # 個別フォルダを削除
                shutil.rmtree(individual_output)
                page_offset += len(png_files)
        
        print(f"全{len(pdf_paths)}個のPDFファイルの処理が完了しました。")
        return True

# スクリプトが直接実行された場合の処理
if __name__ == "__main__":
    print("--- PDF to PNG Converter ---")
    print("コード内で指定されたPDFファイルをPNGに変換します。\n")
    
    target_pdf_path = "11_変更後_W426297_Q変更一式.pdf" 

    # DPI設定 - 高解像度で変換することで、後続の差分検出精度が向上
    conversion_dpi = 400

    output_folder_name = "png_images/after"
    # -----------------------------------

    # 入力されたパスが存在し、かつそれがファイルであることを確認
    if not os.path.isfile(target_pdf_path):
        print(f"エラー: 指定されたパス '{target_pdf_path}' は有効なファイルではありません。")
        print("コード内の 'target_pdf_path' を正しいPDFファイルパスに設定してください。")
    else:
        convert_pdf_to_png(target_pdf_path, dpi=conversion_dpi)
from PIL import Image
import os

def pngs_to_pdf(png_folder, output_pdf_path):
    """
    指定フォルダ内のPNG画像を1つのPDFにまとめて保存する関数
    
    この関数は、差分検出で生成されたPNG画像を1つのPDFファイルにまとめて
    保存します。画像はファイル名の辞書順でソートされてPDFに追加されます。
    
    Args:
        png_folder (str): PNG画像が入っているフォルダのパス
        output_pdf_path (str): 出力するPDFファイルのパス（.pdf拡張子を含む）
    
    Returns:
        None: 成功時はメッセージを出力、失敗時はエラーメッセージを出力
    
    Raises:
        ValueError: PNGファイルが見つからない場合
        Exception: PDF保存時にエラーが発生した場合
    """
    # PNGファイル一覧を取得（ソートして順番を固定）
    # ファイル名の辞書順でソートすることで、一貫した順序を保証
    png_files = sorted([
        os.path.join(png_folder, f)
        for f in os.listdir(png_folder)
        if f.lower().endswith('.png')  # 大文字小文字を区別しない
    ])
    
    # PNGファイルが存在しない場合のエラーハンドリング
    if not png_files:
        print("PNGファイルが見つかりません。")
        return

    # 画像を開いてRGB形式に変換
    # PIL.Image.open()で画像を読み込み、convert("RGB")でRGB形式に統一
    images = [Image.open(f).convert("RGB") for f in png_files]
    
    # 1枚目を基準にしてPDF保存
    # save_all=True: 複数画像を1つのPDFに保存
    # append_images: 2枚目以降の画像を追加
    images[0].save(output_pdf_path, save_all=True, append_images=images[1:])
    print(f"{output_pdf_path} にPDFを保存しました。")

if __name__ == '__main__':
    # テスト用の実行コード
    # diff_outputフォルダ内のPNG画像をoutput.pdfにまとめる
    pngs_to_pdf("diff_output", "output.pdf")
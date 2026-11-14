from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrinter
from pathlib import Path
import sys

app = QApplication(sys.argv)
logo = Path("assets/logo.png").resolve()
print("Logo URI:", logo.as_uri())

printer = QPrinter(QPrinter.HighResolution)
printer.setOutputFormat(QPrinter.PdfFormat)
printer.setOutputFileName("test_print.pdf")

doc = QTextDocument()
html = f'<html><body dir="rtl"><img src="{logo.as_uri()}" width="60" height="60"><p style="font-size: 14pt;">اختبار الطباعة باللغة العربية</p></body></html>'
doc.setHtml(html)
doc.print_(printer)
print("PDF generated successfully, file exists:", Path("test_print.pdf").exists())
if Path("test_print.pdf").exists():
    Path("test_print.pdf").unlink()

import sys
import base64
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QTextEdit, QPushButton, 
                             QDialog)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QGuiApplication

# ==========================================
# 现代样式定义 (QSS)
# ==========================================
LIGHT_THEME = """
QWidget { background-color: #F9FAFB; color: #111827; font-family: "Segoe UI", "Microsoft YaHei"; }
QTextEdit { background-color: #FFFFFF; border: 1px solid #D1D5DB; border-radius: 8px; padding: 10px; font-size: 13px; color: #374151; selection-background-color: #93C5FD; }
QTextEdit:focus { border: 1px solid #3B82F6; }
QPushButton { padding: 8px 16px; border-radius: 6px; font-weight: bold; font-size: 13px; }
#PrimaryBtn { background-color: #3B82F6; color: white; border: none; }
#PrimaryBtn:hover { background-color: #2563EB; }
#SecondaryBtn { background-color: transparent; border: 1px solid #D1D5DB; color: #374151; }
#SecondaryBtn:hover { background-color: #F3F4F6; }
#DangerBtn { background-color: transparent; border: 1px solid #FCA5A5; color: #EF4444; }
#DangerBtn:hover { background-color: #FEF2F2; }
#GhostBtn { background-color: transparent; border: none; color: #6B7280; }
#GhostBtn:hover { background-color: #F3F4F6; color: #374151; }
QDialog { background-color: #F9FAFB; }
"""

DARK_THEME = """
QWidget { background-color: #111827; color: #F9FAFB; font-family: "Segoe UI", "Microsoft YaHei"; }
QTextEdit { background-color: #1F2937; border: 1px solid #374151; border-radius: 8px; padding: 10px; font-size: 13px; color: #D1D5DB; selection-background-color: #1E3A8A; }
QTextEdit:focus { border: 1px solid #3B82F6; }
QPushButton { padding: 8px 16px; border-radius: 6px; font-weight: bold; font-size: 13px; }
#PrimaryBtn { background-color: #3B82F6; color: white; border: none; }
#PrimaryBtn:hover { background-color: #60A5FA; }
#SecondaryBtn { background-color: transparent; border: 1px solid #4B5563; color: #D1D5DB; }
#SecondaryBtn:hover { background-color: #374151; }
#DangerBtn { background-color: transparent; border: 1px solid #991B1B; color: #FCA5A5; }
#DangerBtn:hover { background-color: #7F1D1D; }
#GhostBtn { background-color: transparent; border: none; color: #9CA3AF; }
#GhostBtn:hover { background-color: #1F2937; color: #F3F4F6; }
QDialog { background-color: #111827; }
"""

# ==========================================
# 错误详情弹窗 (带滚动条)
# ==========================================
class ErrorDetailDialog(QDialog):
    def __init__(self, error_lines: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚠️ 发现无效链接")
        self.setMinimumSize(450, 300)
        
        layout = QVBoxLayout(self)
        
        info_label = QLabel(f"检测到 {len(error_lines)} 行格式不合法，已自动跳过：")
        info_label.setStyleSheet("color: #EF4444; font-weight: bold; font-size: 14px;")
        layout.addWidget(info_label)
        
        # 带有滚动条的只读文本框
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlainText("\n".join(error_lines))
        layout.addWidget(self.text_edit)
        
        close_btn = QPushButton("我知道了")
        close_btn.setObjectName("SecondaryBtn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)


# ==========================================
# 前端 UI 层 (PyQt6)
# ==========================================
class ThunderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.is_dark = False
        
        # 定时器，用于管理底部状态栏提示，防止闪烁
        self.status_timer = QTimer(self)
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(self.reset_status)

        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        self.setWindowTitle("Thunder Link Studio - 迅雷链接编解码")
        self.setFixedSize(720, 680)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 30, 30, 20)
        main_layout.setSpacing(15)

        # 1. 头部
        header_layout = QHBoxLayout()
        title_label = QLabel("⚡ Thunder Studio")
        title_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        
        self.theme_btn = QPushButton("🌓 切换深色")
        self.theme_btn.setObjectName("GhostBtn")
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.clicked.connect(self.toggle_theme)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.theme_btn)
        main_layout.addLayout(header_layout)

        # 2. 输入区
        input_label = QLabel("输入链接 (支持多行批量处理)")
        input_label.setStyleSheet("color: #6B7280; font-size: 12px; font-weight: bold;")
        main_layout.addWidget(input_label)

        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("在此粘贴... \n解密需输入: thunder://QUFodHRw...\n加密需输入: http/https/ftp/ed2k/magnet 开头的链接")
        main_layout.addWidget(self.input_text)

        # 3. 操作按钮区
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        decode_btn = QPushButton("🔓 解密为真实地址")
        decode_btn.setObjectName("PrimaryBtn")
        decode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        decode_btn.setFixedHeight(40)
        decode_btn.clicked.connect(lambda: self.process_links('decode'))

        encode_btn = QPushButton("🔒 加密为迅雷链接")
        encode_btn.setObjectName("SecondaryBtn")
        encode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        encode_btn.setFixedHeight(40)
        encode_btn.clicked.connect(lambda: self.process_links('encode'))

        clear_btn = QPushButton("🗑️ 清空")
        clear_btn.setObjectName("DangerBtn")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setFixedHeight(40)
        clear_btn.clicked.connect(self.clear_all)

        btn_layout.addWidget(decode_btn)
        btn_layout.addWidget(encode_btn)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        # 4. 输出区头部
        output_header_layout = QHBoxLayout()
        output_label = QLabel("转换结果")
        output_label.setStyleSheet("color: #6B7280; font-size: 12px; font-weight: bold;")
        
        copy_btn = QPushButton("📋 一键复制")
        copy_btn.setObjectName("GhostBtn")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.clicked.connect(self.copy_result)

        output_header_layout.addWidget(output_label)
        output_header_layout.addStretch()
        output_header_layout.addWidget(copy_btn)
        main_layout.addLayout(output_header_layout)

        # 5. 输出区
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        main_layout.addWidget(self.output_text)

        # 6. 底部状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        main_layout.addWidget(self.status_label)

    def apply_theme(self):
        style = DARK_THEME if self.is_dark else LIGHT_THEME
        self.setStyleSheet(style)
        self.theme_btn.setText("☀️ 切换浅色" if self.is_dark else "🌙 切换深色")

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        self.apply_theme()

    def show_toast(self, message: str, is_error: bool = False):
        """防抖提示，狂点也不会闪烁"""
        self.status_timer.stop() 
        color = "#EF4444" if is_error else ("#10B981" if self.is_dark else "#059669")
        self.status_label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
        self.status_label.setText(message)
        self.status_timer.start(3000) 

    def reset_status(self):
        """重置状态栏"""
        self.status_label.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        self.status_label.setText("就绪")

    def validate_and_decode(self, url: str) -> dict:
        """核心解码校验：严格判断是否为有效 Base64 和 thunder://"""
        if not url.startswith("thunder://"):
            return {'success': False, 'reason': '缺少 thunder:// 协议头'}
        
        b64_str = url[10:]
        try:
            # 严格检测 Base64
            decoded_bytes = base64.b64decode(b64_str, validate=True)
            try:
                decoded_str = decoded_bytes.decode('gbk')
            except UnicodeDecodeError:
                decoded_str = decoded_bytes.decode('utf-8')
                
            if decoded_str.startswith("AA") and decoded_str.endswith("ZZ"):
                return {'success': True, 'result': decoded_str[2:-2]}
            return {'success': True, 'result': decoded_str}
        except Exception:
            return {'success': False, 'reason': 'Base64 编码损坏或格式非法'}

    def validate_and_encode(self, url: str) -> dict:
        """加密前严格校验：必须是合法的常见下载协议"""
        valid_prefixes = ('http://', 'https://', 'ftp://', 'ed2k://', 'magnet:?')
        
        # 忽略大小写判断前缀，拦截普通纯文本和乱码
        if not url.lower().startswith(valid_prefixes):
            return {'success': False, 'reason': '非标准下载协议 (需 http/https/ftp/ed2k/magnet 等)'}
        
        try:
            raw_str = f"AA{url}ZZ"
            b64_bytes = base64.b64encode(raw_str.encode('gbk'))
            return {'success': True, 'result': f"thunder://{b64_bytes.decode('utf-8')}"}
        except Exception:
            return {'success': False, 'reason': '包含无法进行 GBK 编码的特殊字符'}

    def process_links(self, action: str):
        raw_text = self.input_text.toPlainText().strip()
        if not raw_text:
            self.show_toast("⚠️ 请先输入需要转换的文本！", True)
            return

        lines = raw_text.split('\n')
        results = []
        error_records = [] 

        for index, line in enumerate(lines):
            line = line.strip()
            if not line: continue
            
            line_num = index + 1
            if action == 'decode':
                res = self.validate_and_decode(line)
            else:
                if line.startswith("thunder://"):
                    res = {'success': True, 'result': line} # 已经是迅雷链接则原样跳过
                else:
                    # 使用全新的严格校验加密逻辑
                    res = self.validate_and_encode(line)

            if res['success']:
                results.append(res['result'])
            else:
                # 限制预览长度，防止文本过长撑爆弹窗
                preview = line[:30] + "..." if len(line) > 30 else line
                error_records.append(f"第 {line_num} 行：[{res['reason']}] -> {preview}")

        # 将正确的结果直接显示
        self.output_text.setPlainText("\n".join(results))

        # 如果存在非法行，弹出错误明细对话框
        if error_records:
            self.show_toast(f"✅ 完成，但过滤了 {len(error_records)} 条非法输入", True)
            dialog = ErrorDetailDialog(error_records, self)
            dialog.exec()
        else:
            self.show_toast(f"✅ 成功处理 {len(results)} 条链接！")

    def clear_all(self):
        self.input_text.clear()
        self.output_text.clear()
        self.show_toast("🗑️ 已清空工作区")

    def copy_result(self):
        text = self.output_text.toPlainText()
        if not text:
            self.show_toast("⚠️ 没有可复制的内容！", True)
            return
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text)
        self.show_toast("📋 结果已复制到剪贴板！")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ThunderApp()
    window.show()
    sys.exit(app.exec())
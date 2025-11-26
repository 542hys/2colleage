import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from views.global_config_view import GlobalConfigView

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("路径设置测试")
        self.resize(600, 300)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # 创建路径配置视图
        self.global_view = GlobalConfigView()
        layout.addWidget(self.global_view)
        
        # 监听协议变更
        self.global_view.protocol_combo.currentIndexChanged.connect(self.on_protocol_changed)
    
    def on_protocol_changed(self, index):
        protocol_map = {0: "glink", 1: "uart", 2: "bc", 3: "interrupt"}
        protocol_name = protocol_map.get(index, "未知")
        print(f"协议已切换到: {protocol_name}")
        print(f"配置文件路径可见性: {self.global_view.config_row_widget.isVisible()}")
        print(f"输入标签文本: {self.global_view.input_label.text()}")

if __name__ == "__main__":
    # 设置当前工作目录为项目根目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())
import sys
from PyQt5.QtWidgets import QApplication
from main_controller import MainController
from app_manager import ApplicationManager
'''
TODOLIST：
1. 解决硬编码问题，用配置文件代替
2. 完善步骤配置对话框，添加检查或错误处理机制，存在空字段时提示用户
3. 完善步骤配置对话框，添加combo或其他控件来选择协议类型？
4. 图形界面迭代优化
5. 处理流程步的拖拽、复制等热键或其他方式，可能需要直接解析粘贴的数据
6. 处理各个类型流程配置文件的流程步编辑和数据文件导出，可能涉及协议处理
'''

import sys
from PyQt5.QtWidgets import QApplication

def main():
    app = QApplication(sys.argv)
    
    # 创建应用管理器
    app_manager = ApplicationManager()
    app_manager.app = app
    
    # 创建第一个主窗口
    app_manager.create_window()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()


# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     app.setStyle("Fusion")
#     controller = MainController()
#     controller.main_window.show()
#     sys.exit(app.exec_())
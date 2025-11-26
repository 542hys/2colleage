import os
import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QGroupBox, QLabel, QLineEdit, QPushButton, QHBoxLayout, QFileDialog,
    QMessageBox, QComboBox, QWidget, QGridLayout  # 添加消息框用于显示错误
)
from PyQt5.QtCore import Qt, QObject, pyqtSignal

class ConfigManager(QObject):
    """配置管理器 (单例模式)"""
    config_changed = pyqtSignal(dict)  # 配置变更信号
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = {}
            base_dir = Path(__file__).parent.parent
            cls._instance._config_file = base_dir / "global_config.json"
            cls._instance.load_config()
        return cls._instance
    
    def _get_default_protocols(self):
        return {
            "glink": {
                "input_path": "..//..//Platform//DATA//ExDriverGLink//input",
                "output_path": "..//..//Platform//DATA//ExDriverGLink//output",
                "config_path": "..//..//Platform//ExDrivers//GLINK//glink.config"
            },
            "uart": {
                "input_path": "..//..//Platform//DATA//ExDriverUart//input",
                "output_path": "..//..//Platform//DATA//ExDriverUart//output",
                "config_path": "..//..//Platform//Uart//uart.config"
            },
            "bc": {
                "input_path": "..//..//Platform//DATA//ExDriverBC//input",
                "output_path": "..//..//Platform//DATA//ExDriverBC//output",
                "config_path": "..//..//Platform//BC//bc.config"
            },
            "interrupt": {
                "input_path": "..//..//Platform//DATA//ExDriverInterrupt//input",
                "output_path": "..//..//Platform//DATA//ExDriverInterrupt//output",
                "config_path": "..//..//Platform//MARS//Ports//WIN32//port.config"
            },
            "switch": {
                "input_path": "..//..//Platform//DATA//ExDriverSwitch//input",
                "output_path": "..//..//Platform//DATA//ExDriverSwitch//output",
                "config_path": "..//..//Platform//Switch//switch.config"
            }
        }
    
    def load_config(self):
        """从文件加载配置"""
        try:
            if os.path.exists(self._config_file):
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            else:
                self._config = {}
            
            if "protocols" not in self._config:
                self._config["protocols"] = {}
            
            default_protocols = self._get_default_protocols()
            
            for protocol, defaults in default_protocols.items():
                if protocol not in self._config["protocols"]:
                    self._config["protocols"][protocol] = defaults.copy()
                else:
                    for key, value in defaults.items():
                        if key not in self._config["protocols"][protocol]:
                            self._config["protocols"][protocol][key] = value
            
            if "input_path" in self._config and "protocols" not in self._config:
                self._config["protocols"] = {
                    "glink": {
                        "input_path": self._config.get("input_path", default_protocols["glink"]["input_path"]),
                        "output_path": self._config.get("output_path", default_protocols["glink"]["output_path"]),
                        "config_path": default_protocols["glink"]["config_path"]
                    }
                }
                for protocol, defaults in default_protocols.items():
                    if protocol != "glink":
                        self._config["protocols"][protocol] = defaults.copy()
        except Exception as e:
            print(f"加载配置失败: {str(e)}")
            self._config = {"protocols": self._get_default_protocols()}
    
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4)
        except Exception as e:
            print(f"保存配置失败: {str(e)}")
    
    def get_config(self, key=None, default=None):
        """获取配置值"""
        if key is None:
            return self._config.copy()
        return self._config.get(key, default)
    
    def set_config(self, key, value):
        """设置配置值并通知变更"""
        if self._config.get(key) != value:
            self._config[key] = value
            self.save_config()
            self.config_changed.emit(self._config.copy())
    
    def update_config(self, new_config):
        """批量更新配置"""
        changed = False
        for key, value in new_config.items():
            if self._config.get(key) != value:
                self._config[key] = value
                changed = True
        
        if changed:
            self.save_config()
            self.config_changed.emit(self._config.copy())
    
    def get_protocol_config(self, protocol):
        """获取指定协议的配置"""
        return self._config.get("protocols", {}).get(protocol, {})
    
    def set_protocol_config(self, protocol, config):
        """设置指定协议的配置"""
        if "protocols" not in self._config:
            self._config["protocols"] = {}
        self._config["protocols"][protocol] = config
        self.save_config()
        self.config_changed.emit(self._config.copy())

    def get_all_protocol_configs(self):
        """获取全部协议的路径配置"""
        protocols = self._config.get("protocols", {})
        return {k: (v.copy() if isinstance(v, dict) else {}) for k, v in protocols.items()}

    def set_all_protocol_configs(self, protocols, merge=True):
        """批量设置所有协议的路径配置"""
        if not isinstance(protocols, dict):
            return
        defaults = self._get_default_protocols()
        if merge:
            merged = self.get_all_protocol_configs()
            if not merged:
                merged = {k: defaults.get(k, {}).copy() for k in defaults.keys()}
        else:
            merged = {k: defaults.get(k, {}).copy() for k in defaults.keys()}
        for proto, cfg in protocols.items():
            if not isinstance(cfg, dict):
                continue
            base = merged.get(proto, defaults.get(proto, {}).copy())
            for key in ("input_path", "output_path", "config_path"):
                if key in cfg and cfg[key] is not None:
                    base[key] = cfg[key]
            merged[proto] = base
        self._config["protocols"] = merged
        self.save_config()
        self.config_changed.emit(self._config.copy())


class GlobalConfigView(QGroupBox):
    """全局配置视图 - 支持配置管理"""
    load_signal = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__("路径配置", parent)
        
        # 设置紧凑样式
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #a0a0a0;
                border-radius: 5px;
                margin-top: 1ex;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        
        form_layout = QGridLayout()
        form_layout.setContentsMargins(12, 12, 12, 12)
        form_layout.setHorizontalSpacing(12)
        form_layout.setVerticalSpacing(10)
        form_layout.setAlignment(Qt.AlignTop)
        form_layout.setColumnStretch(1, 1)
        form_layout.setColumnMinimumWidth(0, 120)
        self.form_layout = form_layout
        
        # 协议选择下拉框
        self.protocol_label = QLabel("协议类型:")
        self.protocol_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["GLink", "串口", "1553-BC", "中断", "开关量"])
        self.protocol_combo.currentIndexChanged.connect(self.on_protocol_changed)
        
        # 数据输出目录（原输入目录）
        self.input_label = QLabel("数据输出目录:")
        self.input_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("选择数据输出目录...")
        input_button = QPushButton("浏览...")
        input_button.setFixedWidth(120)
        input_button.clicked.connect(self.select_input_dir)
        
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(input_button)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)
        self.input_row_widget = QWidget()
        self.input_row_widget.setLayout(input_layout)
        
        # 配置文件路径
        self.config_label = QLabel("配置文件路径:")
        self.config_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.config_edit = QLineEdit()
        self.config_edit.setPlaceholderText("选择配置文件路径...")
        config_button = QPushButton("浏览...")
        config_button.setFixedWidth(120)
        config_button.clicked.connect(self.select_config_dir)
        
        config_layout = QHBoxLayout()
        config_layout.addWidget(self.config_edit)
        config_layout.addWidget(config_button)
        config_layout.setContentsMargins(0, 0, 0, 0)
        config_layout.setSpacing(8)
        self.config_row_widget = QWidget()
        self.config_row_widget.setLayout(config_layout)
        
        # 保存按钮
        self.save_btn = QPushButton("保存配置")
        self.save_btn.setFixedWidth(120)
        self.save_btn.clicked.connect(self.save_config)
        
        # 恢复默认设置按钮
        self.reset_btn = QPushButton("恢复默认设置")
        self.reset_btn.setFixedWidth(120)
        self.reset_btn.clicked.connect(self.reset_to_default)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addStretch()
        
        row = 0
        form_layout.addWidget(self.protocol_label, row, 0)
        form_layout.addWidget(self.protocol_combo, row, 1)
        row += 1
        form_layout.addWidget(self.input_label, row, 0)
        form_layout.addWidget(self.input_row_widget, row, 1)
        row += 1
        form_layout.addWidget(self.config_label, row, 0)
        form_layout.addWidget(self.config_row_widget, row, 1)
        row += 1
        form_layout.addLayout(btn_layout, row, 0, 1, 2)
        
        self.setLayout(form_layout)
        self._align_form_labels()
        self.setFixedHeight(220)  # 调整高度适应新字段
        
        # 获取配置管理器实例
        self.config_manager = ConfigManager()
        self.config_manager.config_changed.connect(self.on_config_changed)
        
        # 加载初始配置
        self.config_manager.load_config()
        self.load_current_protocol_config()
        self._align_form_labels()
        
        print("配置视图初始化完成")
    
    def get_current_protocol_key(self):
        """获取当前选择的协议键名"""
        protocol_map = {
            0: "glink",
            1: "uart",
            2: "bc",
            3: "interrupt",
            4: "switch"
        }
        return protocol_map.get(self.protocol_combo.currentIndex(), "glink")
    
    def _align_form_labels(self):
        """确保标签列宽一致，避免行隐藏时错位"""
        labels = [
            getattr(self, "protocol_label", None),
            getattr(self, "input_label", None),
            getattr(self, "config_label", None)
        ]
        widths = [label.sizeHint().width() for label in labels if label]
        if not widths:
            return
        max_width = max(widths + [getattr(self, "_label_column_width", 0)])
        self._label_column_width = max_width
        if hasattr(self, "form_layout"):
            self.form_layout.setColumnMinimumWidth(0, self._label_column_width)
        for label in labels:
            if label:
                label.setMinimumWidth(self._label_column_width)
    
    def load_current_protocol_config(self):
        """加载当前协议的配置"""
        protocol_key = self.get_current_protocol_key()
        protocol_config = self.config_manager.get_protocol_config(protocol_key)
        
        if protocol_key == "interrupt" or protocol_key == "switch":
            input_path = self.format_path(protocol_config.get("output_path", ""))
            config_path = ""
        else:
            input_path = self.format_path(protocol_config.get("input_path", ""))
            config_path = self.format_path(protocol_config.get("config_path", ""))
        
        self.input_edit.setText(input_path)
        self.config_edit.setText(config_path)
        self.update_path_field_visibility()
        self._align_form_labels()
    
    def update_path_field_visibility(self):
        """根据协议类型显示/隐藏配置路径"""
        is_interrupt_or_switch = self.get_current_protocol_key() in ["interrupt", "switch"]
        if self.config_row_widget:
            self.config_row_widget.setVisible(not is_interrupt_or_switch)
        if self.config_label:
            self.config_label.setVisible(not is_interrupt_or_switch)
    
    def on_protocol_changed(self):
        """协议选择改变时，加载对应协议的配置"""
        self.load_current_protocol_config()
    
    def on_config_changed(self, config):
        """当配置变更时更新UI"""
        # 如果当前显示的协议配置被更新，刷新显示
        self.load_current_protocol_config()
    
    def select_input_dir(self):
        """选择数据输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择数据输出目录"
        )
        if dir_path:
            self.input_edit.setText(dir_path)
            self.save_current_protocol_config()
            self.load_signal.emit()  # 发出加载信号
    
    def select_config_dir(self):
        """选择配置文件路径"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择配置文件", "", "配置文件 (*.config);;所有文件 (*)"
        )
        if file_path:
            self.config_edit.setText(file_path)
            self.save_current_protocol_config()
            self.load_signal.emit()  # 发出加载信号
    
    def save_current_protocol_config(self):
        """保存当前协议的配置"""
        protocol_key = self.get_current_protocol_key()
        current_cfg = self.config_manager.get_protocol_config(protocol_key)
        protocol_config = dict(current_cfg) if isinstance(current_cfg, dict) else {}
        if protocol_key in ["interrupt", "switch"]:
            protocol_config["output_path"] = self.input_edit.text()
            protocol_config.pop("config_path", None)
            protocol_config.pop("input_path", None)
        else:
            protocol_config["input_path"] = self.input_edit.text()
            protocol_config["config_path"] = self.config_edit.text()
        self.config_manager.set_protocol_config(protocol_key, protocol_config)
    
    def get_data(self):
        """获取当前视图数据（当前协议的配置）"""
        protocol_key = self.get_current_protocol_key()
        protocol_config = self.config_manager.get_protocol_config(protocol_key)
        data = {
            "output_path": protocol_config.get("output_path", "") if isinstance(protocol_config, dict) else ""
        }
        if protocol_key in ["interrupt", "switch"]:
            data["input_path"] = ""
            data["config_path"] = ""
            data["output_path"] = self.input_edit.text()
        else:
            data["input_path"] = self.input_edit.text()
            data["config_path"] = self.config_edit.text()
        return data

    def set_data(self, data):
        """从外部同步配置到管理器并刷新当前显示"""
        if not isinstance(data, dict):
            return

        def merge_config(original_cfg, new_cfg):
            merged = dict(original_cfg) if isinstance(original_cfg, dict) else {}
            if not isinstance(new_cfg, dict):
                return merged
            protocol_key = self.get_current_protocol_key()
            keys = ["output_path"]
            if protocol_key != "interrupt":
                keys.extend(["input_path", "config_path"])
            else:
                merged.pop("input_path", None)
                merged.pop("config_path", None)
            for key in keys:
                if key in new_cfg and new_cfg[key] is not None:
                    merged[key] = new_cfg[key]
            return merged

        try:
            protocols_data = data.get("protocols")
            if isinstance(protocols_data, dict):
                self.config_manager.set_all_protocol_configs(protocols_data, merge=True)
            else:
                current_key = self.get_current_protocol_key()
                current_cfg = self.config_manager.get_protocol_config(current_key)
                merged = merge_config(current_cfg, data)
                if merged != current_cfg:
                    self.config_manager.set_protocol_config(current_key, merged)
        except Exception as e:
            print(f"同步配置失败: {e}")
        finally:
            self.load_current_protocol_config()
    
    def save_config(self):
        """保存当前配置到文件 - 添加路径验证"""
        config_data = self.get_data()
        
        # 验证路径
        errors = self.validate_paths(config_data)
        
        if errors:
            # 显示错误消息
            error_msg = "\n".join(errors)
            QMessageBox.warning(
                self, 
                "路径验证失败", 
                f"以下路径存在问题:\n\n{error_msg}\n\n请修正后重试。"
            )
            print("配置保存失败: 路径验证未通过")
            return
        
        # 所有路径有效，保存当前协议的配置
        self.save_current_protocol_config()
        
        protocol_name = self.protocol_combo.currentText()
        QMessageBox.information(self, "成功", f"{protocol_name}协议配置已保存")
        print(f"{protocol_name}协议配置已保存")
    
    def reset_all_to_default_silent(self):
        """静默恢复所有协议的默认设置（启动时调用，不显示消息框）"""
        default_configs = {
            "glink": {
                "input_path": "..//..//Platform//DATA//ExDriverGLink//input",
                "output_path": "..//..//Platform//DATA//ExDriverGLink//output",
                "config_path": "..//..//Platform//ExDrivers//GLINK//glink.config"
            },
            "uart": {
                "input_path": "..//..//Platform//DATA//ExDriverUart//input",
                "output_path": "..//..//Platform//DATA//ExDriverUart//output",
                "config_path": "..//..//Platform//Uart//uart.config"
            },
            "bc": {
                "input_path": "..//..//Platform//DATA//ExDriverBC//input",
                "output_path": "..//..//Platform//DATA//ExDriverBC//output",
                "config_path": "..//..//Platform//BC//bc.config"
            },
            "interrupt": {
                "input_path": "..//..//Platform//DATA//ExDriverInterrupt//input",
                "output_path": "..//..//Platform//DATA//ExDriverInterrupt//output",
                "config_path": "..//..//Platform//MARS//Ports//WIN32//port.config"
            }
        }
        
        # 恢复所有协议的默认设置
        for protocol_key, default_config in default_configs.items():
            self.config_manager.set_protocol_config(protocol_key, default_config)
        
        # 刷新当前显示的协议配置
        self.load_current_protocol_config()
        
        print("所有协议（GLink、串口、1553-BC、中断）已恢复默认设置（启动时初始化）")
    
    def reset_to_default(self):
        """恢复当前协议的默认设置"""
        protocol_key = self.get_current_protocol_key()
        default_configs = {
            "glink": {
                "input_path": "..//..//Platform//DATA//ExDriverGLink//input",
                "output_path": "..//..//Platform//DATA//ExDriverGLink//output",
                "config_path": "..//..//Platform//ExDrivers//GLINK//glink.config"
            },
            "uart": {
                "input_path": "..//..//Platform//DATA//ExDriverUart//input",
                "output_path": "..//..//Platform//DATA//ExDriverUart//output",
                "config_path": "..//..//Platform//Uart//uart.config"
            },
            "bc": {
                "input_path": "..//..//Platform//DATA//ExDriverBC//input",
                "output_path": "..//..//Platform//DATA//ExDriverBC//output",
                "config_path": "..//..//Platform//BC//bc.config"
            },
            "interrupt": {
                "input_path": "..//..//Platform//DATA//ExDriverInterrupt//input",
                "output_path": "..//..//Platform//DATA//ExDriverInterrupt//output",
                "config_path": "..//..//Platform//MARS//Ports//WIN32//port.config"
            }
        }
        
        default_config = default_configs.get(protocol_key, default_configs["glink"])
        
        self.input_edit.setText(default_config["input_path"])
        self.config_edit.setText(default_config["config_path"])
        
        self.config_manager.set_protocol_config(protocol_key, default_config)
        
        protocol_name = self.protocol_combo.currentText()
        QMessageBox.information(self, "成功", f"{protocol_name}协议已恢复默认设置")
        print(f"{protocol_name}协议已恢复默认设置")
    
    def format_path(self, path):
        """格式化路径，处理点号代表当前目录"""
        if path == ".":
            return os.getcwd()
        elif path.startswith("./") or path.startswith(".\\"):
            return os.path.join(os.getcwd(), path[2:])
        return path


    def validate_paths(self, config):
        """确保路径可用；若目录/文件不存在则自动创建"""
        errors = []
        
        input_path = config.get("input_path", "").strip()
        if input_path:
            formatted_input = self.format_path(input_path)
            try:
                Path(formatted_input).mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                errors.append(f"数据输出目录创建失败: {formatted_input} ({exc})")
        
        config_path = config.get("config_path", "").strip()
        if config_path:
            formatted_config = self.format_path(config_path)
            config_file = Path(formatted_config)
            try:
                if config_file.parent:
                    config_file.parent.mkdir(parents=True, exist_ok=True)
                if not config_file.exists():
                    config_file.touch()
            except Exception as exc:
                errors.append(f"配置文件路径处理失败: {formatted_config} ({exc})")
        
        return errors
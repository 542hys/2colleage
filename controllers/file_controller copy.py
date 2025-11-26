from main_model import DataModel
import xml.etree.ElementTree as ET
import json
import struct
from PyQt5.QtCore import QStandardPaths
from PyQt5.QtWidgets import (QFileDialog, QMessageBox,
)
from models.step_model import StepModel
from config import (
    GLINK_TEST_HEADER, DEFAULT_TIMEOUT_KEY, MAX_RETRIES_KEY, ENVIRONMENT_KEY,
    STEP_NAME_KEY, STEP_TIME_KEY, STEP_PROTOCOL_KEY, STEP_DATA_FORMAT_KEY,
    STEP_DATA_CONTENT_KEY, STEP_EXPECT_KEY, HEX_FORMAT, BINARY_FORMAT
)
import traceback
from xml.dom import minidom
import os

class FileController:
    def __init__(self, model, main_window, global_controller, 
                 window_controller, step_list_controller, step_detail_controller):
        '''初始化文件控制器,负责文件相关操作'''
        self.model = model
        self.main_window = main_window
        self.global_controller = global_controller  # 全局配置控制器
        self.window_controller = window_controller  # 窗口控制器
        self.step_list_controller = step_list_controller  # 步骤列表控制器
        self.step_detail_controller = step_detail_controller 
        
    # 负责文件保存、打开等逻辑

    def connect_signals(self):
        """连接所有视图信号"""   
        # 主窗口菜单
        self.main_window.new_action.triggered.connect(self.new_config)
        self.main_window.open_action.triggered.connect(self.open_config)
        self.main_window.save_action.triggered.connect(self.save_config)
        self.main_window.save_as_action.triggered.connect(self.save_config_as)
        # self.main_window.export_action.triggered.connect(self.export_data)
        self.main_window.export_action.triggered.connect(self.export_steps_by_type)
        # self.main_window.export_steps_by_type_action.triggered.connect(self.export_steps_by_type)
        

    def new_config(self):
        """创建新配置"""
        if self.model.is_dirty():
            reply = QMessageBox.question(
                self.main_window, "未保存的更改",
                "当前配置有未保存的更改，是否保存?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Save:
                self.save_config()
            elif reply == QMessageBox.Cancel:
                return
        
        self.model.steps.clear()
        self.model.file_path = None
        print(f"file_controller model: {len(self.model.steps)}")
        self.global_controller.update_global_view()
        self.step_list_controller.clear_step_data()
        self.step_list_controller.update_step_list()
        print(f"filecontroller new config: {len(self.step_list_controller.step_list_view.steps)}")
        ### 需要maincontroller给一个step_detail_view的引用
        self.step_detail_controller.clear_step_detail()
        ### 需要maincontroller给一个函数接口
        self.window_controller.update_window_title()

    def save_to_file(self, file_path):
        """保存到指定XML文件"""
        ##目前打开保存后的文件再添加中断或开关量还会有data_region字段
        try:
            self.global_controller.update_global_model()
            root = ET.Element("config")

            # 全局参数
            global_elem = ET.SubElement(root, "global_params")
            for k, v in self.model.global_params.items():
                param = ET.SubElement(global_elem, k)
                param.text = str(v)

            # 步骤
            # steps_elem = ET.SubElement(root, "steps")
            # for step in self.model.steps:
            #     step_elem = ET.SubElement(steps_elem, "step")
            #     for k, v in step.items():
            #         field = ET.SubElement(step_elem, k)
            #         field.text = str(v)

            ####
            steps_elem = ET.SubElement(root, "steps")
            for step in self.model.steps:
                step_elem = ET.SubElement(steps_elem, "step")
                
                # 保存base字典
                base_elem = ET.SubElement(step_elem, "base")
                for k, v in step.get_base_step_data().items():
                    print(f"save field: {k} value: {v}")
                    field = ET.SubElement(base_elem, k)
                    field.text = str(v)
                
                # 保存type字典
                type_elem = ET.SubElement(step_elem, "type")
                for k, v in step.get_type_step_data().items():
                    print(f"save field: {k} value: {v}")
                    field = ET.SubElement(type_elem, k)
                    # 这里可以用k对应的dtype是否为union代替
                    # 将union的列表结构序列化为json字段
                    if k == "data_region" and isinstance(v, (list, dict)):
                        # field.text = f"<![CDATA[{json.dumps(v, ensure_ascii=False)}]]>"
                        field.text = json.dumps(v, ensure_ascii=False)
                    else:
                        field.text = str(v)
                
                # 保存expand字典
                expand_elem = ET.SubElement(step_elem, "expand")
                for k, v in step.get_expand_step_data().items():
                    print(f"save field: {k} value: {v}")
                    field = ET.SubElement(expand_elem, k)
                    field.text = str(v)


            ####

            # tree = ET.ElementTree(root)
            # tree.write(file_path, encoding="utf-8", xml_declaration=True)


            #####
            # 创建XML树
            tree = ET.ElementTree(root)
            
            # 使用minidom美化XML输出
            rough_string = ET.tostring(root, encoding="utf-8", method="xml")
            reparsed = minidom.parseString(rough_string)
            
            # 使用2空格缩进
            pretty_xml = reparsed.toprettyxml(indent="  ", encoding="utf-8")
            
            # 移除多余的空白行（minidom会添加空行）
            pretty_xml_str = b'\n'.join(
                line for line in pretty_xml.splitlines() 
                if line.strip()
            ).decode("utf-8")
            
            # 写入文件
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(pretty_xml_str)

            #####

            self.model.reset_dirty()
            QMessageBox.information(
                self.main_window,
                "保存成功",
                f"配置已保存到: {file_path}"
            )
        except Exception as e:
            print(traceback.format_exc())
            QMessageBox.critical(
                self.main_window,
                "保存错误",
                f"保存文件时出错: {str(e)}"
            )

    def open_config(self):
        """打开XML配置文件"""
        if self.model.is_dirty():
            reply = QMessageBox.question(
                self.main_window, "未保存的更改",
                "当前配置有未保存的更改，是否保存?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if reply == QMessageBox.Save:
                self.save_config()
            elif reply == QMessageBox.Cancel:
                return

        default_dir = self.model.global_params.get("input_path", QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation))
        # print(f"....................................{default_dir}")
        # default_dir = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window,
            "打开流程配置",
            default_dir,
            "流程配置文件 (*.xml);;所有文件 (*)"
        )

        if file_path:
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
                # 解析全局参数
                global_elem = root.find("global_params")
                global_params = {child.tag: child.text for child in global_elem}
                # 解析步骤
                # steps_elem = root.find("steps")
                # steps = []
                # for step_elem in steps_elem.findall("step"):
                #     step = {child.tag: child.text for child in step_elem}
                #     steps.append(step)
                # self.model.global_params = global_params
                # self.model.steps = steps
                # self.model.file_path = file_path

                ####
                steps = []
                steps_elem = root.find("steps")
                if steps_elem is not None:
                    for step_elem in steps_elem.findall("step"):
                        # 创建新的StepModel实例
                        step = StepModel()
                        
                        # 读取base字典
                        stype = 0
                        base_elem = step_elem.find("base")
                        if base_elem is not None:
                            base_dict = {}
                            self.load_data_to_dict(base_dict, base_elem)
                            # base_dict = {child.tag: child.text for child in base_elem}
                            step.update_base_data(base_dict)
                            stype = step.get_step_type()
                        
                        # 读取type字典
                        type_elem = step_elem.find("type")
                        
                        if type_elem is not None:
                            type_dict = {}
                            self.load_data_to_dict(type_dict, type_elem)
                        #     type_dict = {}
                        #     for child in type_elem:
                        #         if child.tag == "data_region":
                        #             text = child.text
                        #             if text and text.startswith("<![CDATA[") and text.endswith("]]>"):
                        #                 text = text[9:-3]
                        #             try:
                        #                 type_dict[child.tag] = json.loads(text)
                        #             except Exception:
                        #                 type_dict[child.tag] = text
                        #         else:
                        #             type_dict[child.tag] = child.text
                            step.update_type_data(stype, type_dict)
                        
                        # 读取expand字典
                        #expand字典可以同样用type_data的方法
                        expand_elem = step_elem.find("expand")
                        if expand_elem is not None:
                            expand_dict = {}
                            self.load_data_to_dict(expand_dict, expand_elem)
                            # expand_dict = {child.tag: child.text for child in expand_elem}
                            step.update_expand_data(expand_dict)
                        
                        steps.append(step)


                ####
                self.model.steps = steps

                print("steps loaded:", len(steps))
                print("first step:", steps[0].get_base_step_data() if steps else None)
                self.global_controller.update_global_view()
                self.step_list_controller.update_step_list()
                #self.refresh_graph_view()
                if self.model.steps:
                    self.step_list_controller.set_selected_step(-1)
                self.window_controller.update_window_title()
            except Exception as e:
                print(traceback.format_exc())
                QMessageBox.critical(
                    self.main_window,
                    "打开文件错误",
                    f"无法打开文件: {str(e)}"
                )

    def load_data_to_dict(self, dict, data_elem):
        for child in data_elem:
            dict[child.tag] = self.text2dtype(child.tag, child.text)
            # if child.tag == "data_region":
            #     text = child.text
            #     if text and text.startswith("<![CDATA[") and text.endswith("]]>"):
            #         text = text[9:-3]
            #     try:
            #         dict[child.tag] = json.loads(text)
            #     except Exception:
            #         dict[child.tag] = text
            # else:
            #     dict[child.tag] = self.text2dtype(child.tag, child.text)
        # expand_dict = {child.tag: self.text2dtype(child.tag, child.text) for child in expand_elem}

    def text2dtype(self, dtype_tag, text):
        import models.step_model as step_model
        dtype = str(dtype_tag)
        print(f"text2dtype dtype: {dtype}")
        filed_type = step_model.get_field_type(dtype)
        # print(f"text2dtype dtype: {dtype}")
        if filed_type != 'union':
            pdtype = step_model.get_dtype(dtype)
            # standard = step_model.get_dtype("step_type")
            val = pdtype(text)
            print(f"text2dtype dtype_tag: {dtype_tag};text: {text} pdtype: {pdtype} val type {type(val)}")
            return val
        else:
            val = []
            data_list = json.loads(text)
            for item in data_list:
                data_type = item.get("data_type") 
                value = item.get("value")
                
                pdtype = step_model.get_dtype_by_idx(int(data_type))
                print(f"union {item} data_type:{data_type}, value: {value} pdtye:{pdtype}")
                val.append({
                "data_type": int(data_type),
                "value": pdtype(value)
            })
            return val



    
    def save_config(self):
        """保存配置"""
        if self.model.file_path:
            self.save_to_file(self.model.file_path)
        else:
            self.save_config_as()

    def save_config_as(self):
        """另存为XML配置"""
        default_dir = self.model.global_params.get("input_path", QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation))
        # default_dir = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        file_path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "保存流程配置",
            default_dir,
            "流程配置文件 (*.xml);;所有文件 (*)"
        )
        if file_path:
            if not file_path.endswith('.xml'):
                file_path += '.xml'
            self.save_to_file(file_path)
            self.model.file_path = file_path
            self.window_controller.update_window_title()
    
    def export_data(self):
        """导出测试数据"""
        if not self.model.steps:
            QMessageBox.warning(
                self.main_window, 
                "无法导出", 
                "没有配置测试步骤，无法导出数据"
            )
            return
        
        # 获取文档目录
        default_dir = self.model.global_params.get("output_path", QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation))
        default_dir = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        
        file_path, _ = QFileDialog.getSaveFileName(
            self.main_window, 
            "导出数据", 
            default_dir, 
            "数据文件 (*.txt);;所有文件 (*)"
        )
        
        if file_path:
            try:
                # 确保文件扩展名
                if not file_path.endswith('.txt'):
                    file_path += '.txt'
                
                self.generate_data_file(file_path)
                
                QMessageBox.information(
                    self.main_window, 
                    "导出成功", 
                    f"测试数据已导出到: {file_path}"
                )
            except Exception as e:
                print(traceback.format_exc())
                QMessageBox.critical(
                    self.main_window, 
                    "导出错误", 
                    f"导出数据时出错: {str(e)}"
                )
    
    def generate_data_file(self, file_path):
        """生成数据文件"""
        # 根据Glink协议生成特定格式的数据文件
        with open(file_path, 'wb') as f:  # 二进制模式写入
            
            # 文件头：Glink测试数据标识
            f.write(GLINK_TEST_HEADER)
            
            # 写入全局参数
            f.write(struct.pack('I', self.model.global_params[DEFAULT_TIMEOUT_KEY]))
            f.write(struct.pack('I', self.model.global_params[MAX_RETRIES_KEY]))
            
            # 环境字符串
            env = self.model.global_params[ENVIRONMENT_KEY].encode('utf-8')
            f.write(struct.pack('I', len(env)))
            f.write(env)
            
            # 写入步骤数量
            f.write(struct.pack('I', len(self.model.steps)))
            
            # 写入每个步骤
            for step in self.model.steps:
                # 步骤名称
                name = step[STEP_NAME_KEY].encode('utf-8')
                f.write(struct.pack('I', len(name)))
                f.write(name)
                
                # 时间
                f.write(struct.pack('I', int(step[STEP_TIME_KEY])))
                
                # 协议类型
                protocol = step[STEP_PROTOCOL_KEY].encode('utf-8')
                f.write(struct.pack('I', len(protocol)))
                f.write(protocol)
                
                # 数据格式
                data_format = step[STEP_DATA_FORMAT_KEY].encode('utf-8')
                f.write(struct.pack('I', len(data_format)))
                f.write(data_format)
                
                # 数据内容
                if step[STEP_DATA_FORMAT_KEY] == HEX_FORMAT:
                    # 处理十六进制数据
                    hex_data = step[STEP_DATA_CONTENT_KEY].strip().replace(' ', '')
                    if len(hex_data) % 2 != 0:
                        raise ValueError("十六进制数据长度必须为偶数")
                    data = bytes.fromhex(hex_data)
                elif step[STEP_DATA_FORMAT_KEY] == BINARY_FORMAT:
                    # 处理二进制数据
                    bin_data = step[STEP_DATA_CONTENT_KEY].replace(' ', '')
                    data = bytes([int(bin_data[i:i+8], 2) for i in range(0, len(bin_data), 8)])
                else:
                    # 其他格式使用转换函数处理
                    data_content = step[STEP_DATA_CONTENT_KEY]
                    # 尝试判断数据类型并转换
                    try:
                        # 尝试转换为整数
                        int_val = int(data_content)
                        data = self.convert_int_to_hex(int_val)
                    except ValueError:
                        try:
                            # 尝试转换为浮点数
                            float_val = float(data_content)
                            data = self.convert_float_to_hex(float_val)
                        except ValueError:
                            # 按字符串处理
                            data = self.convert_string_to_hex(data_content)
                
                f.write(struct.pack('I', len(data)))
                f.write(data)
                
                # 预期响应
                expect = step.get(STEP_EXPECT_KEY, "").encode('utf-8')
                f.write(struct.pack('I', len(expect)))
                f.write(expect)

    def convert_string_to_hex(self, string_data):
        """将字符串转换为16进制数据"""
        if not string_data:
            return b''
        # 将字符串编码为UTF-8，然后转换为16进制
        utf8_bytes = string_data.encode('utf-8')
        hex_string = utf8_bytes.hex()
        return bytes.fromhex(hex_string)

    def convert_float_to_hex(self, float_data, precision=6):
        """将浮点数转换为16进制数据"""
        try:
            # 将浮点数转换为字符串，保留指定精度
            float_str = f"{float_data:.{precision}f}"
            # 转换为UTF-8字节，然后转为16进制
            utf8_bytes = float_str.encode('utf-8')
            hex_string = utf8_bytes.hex()
            return bytes.fromhex(hex_string)
        except (ValueError, TypeError):
            return b''

    def convert_int_to_hex(self, int_data):
        """将整数转换为16进制数据"""
        try:
            # 将整数转换为字符串
            int_str = str(int(int_data))
            # 转换为UTF-8字节，然后转为16进制
            utf8_bytes = int_str.encode('utf-8')
            hex_string = utf8_bytes.hex()
            return bytes.fromhex(hex_string)
        except (ValueError, TypeError):
            return b''

    def convert_data_to_hex(self, data, data_type='string'):
        """通用数据转换函数，根据数据类型转换为16进制"""
        if data_type == 'string':
            return self.convert_string_to_hex(data)
        elif data_type == 'float':
            return self.convert_float_to_hex(data)
        elif data_type == 'int':
            return self.convert_int_to_hex(data)
        else:
            # 默认按字符串处理
            return self.convert_string_to_hex(str(data))
    


    
    import os
    from PyQt5.QtWidgets import QFileDialog

    def export_steps_by_type(self):
        """按类型出到txt"""
        # 1. 選擇目錄
        default_dir = self.model.global_params.get("output_path", QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation))
        
        # default_dir = getattr(self, "DEFAULT_CONFIG_DIR", "./configs")
        dir_path = QFileDialog.getExistingDirectory(
            self.main_window,
            "选择流程配置文件目录",
            default_dir
        )
        if not dir_path:
            return

        # 2. 遍歷所有xml文件
        steps_by_type = {}
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                if file.endswith('.xml'):
                    file_path = os.path.join(root, file)
                    try:
                        steps = self.read_steps_from_xml(file_path)
                        for step in steps:
                            step_type = step.get_step_type()
                            if step_type not in steps_by_type:
                                steps_by_type[step_type] = []
                            steps_by_type[step_type].append(step)
                    except Exception as e:
                        print(f"读取文件失败: {file_path}, {e}")

        # 3. 導出到txt
        for step_type, steps in steps_by_type.items():
            txt_path = os.path.join(dir_path, f"{step_type}.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                for step in steps:
                    # 根據需求格式化每個step
                    line = self.format_step_for_txt(step)
                    f.write(line + "\n")

        QMessageBox.information(
            self.main_window,
            "導出完成",
            f"已按類型導出到: {dir_path}"
        )

    def read_steps_from_xml(self, file_path):
        """从xml文件读取所有StepModel"""
        import xml.etree.ElementTree as ET
        from models.step_model import StepModel
        steps = []
        tree = ET.parse(file_path)
        root = tree.getroot()
        steps_elem = root.find("steps")
        if steps_elem is not None:
            for step_elem in steps_elem.findall("step"):
                step = StepModel()
                # base
                base_elem = step_elem.find("base")
                if base_elem is not None:
                    base_dict = {}
                    self.load_data_to_dict(base_dict, base_elem)
                    step.update_base_data(base_dict)
                # type
                type_elem = step_elem.find("type")
                if type_elem is not None:
                    type_dict = {}
                    self.load_data_to_dict(type_dict, type_elem)
                    step.update_type_data(step.get_step_type(), type_dict)
                # expand
                expand_elem = step_elem.find("expand")
                if expand_elem is not None:
                    expand_dict = {}
                    self.load_data_to_dict(expand_dict, expand_elem)
                    step.update_expand_data(expand_dict)
                steps.append(step)
        return steps

    def format_step_for_txt(self, step):
        """根据需求格式化step为txt行"""
        # 这里仅示例，根据你的需求调整字段
        base = step.get_base_step_data()
        type_data = step.get_type_step_data()
        expand = step.get_expand_step_data()
        # 例如只导出base和type的主要字段
        fields = []
        for k, v in base.items():
            fields.append(f"{k}:{v}")
        for k, v in type_data.items():
            fields.append(f"{k}:{v}")
        for k, v in expand.items():
            fields.append(f"{k}:{v}")
        return "\t".join(fields)
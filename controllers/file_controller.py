from main_model import DataModel
import xml.etree.ElementTree as ET
import json
import struct
import uuid
from PyQt5.QtCore import QStandardPaths
from PyQt5.QtWidgets import (QFileDialog, QMessageBox,
)
from models.step_model import StepModel
from models.template_manager import template_manager
from config import (
    GLINK_TEST_HEADER, DEFAULT_TIMEOUT_KEY, MAX_RETRIES_KEY, ENVIRONMENT_KEY,
    STEP_NAME_KEY, STEP_TIME_KEY, STEP_PROTOCOL_KEY, STEP_DATA_FORMAT_KEY,
    STEP_DATA_CONTENT_KEY, STEP_EXPECT_KEY, HEX_FORMAT, BINARY_FORMAT
)
import traceback
from xml.dom import minidom
import os
from utils.glink_config import get_glink_config
from views.global_config_view import ConfigManager
from utils.protocol_template_utils import (
    calc_crc_tail_metrics,
    calc_serial_extended_metrics,
    calc_serial_standard_metrics,
    normalize_data_region_value,
)

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
        self.template_manager = template_manager
        
    # 负责文件保存、打开等逻辑

    def connect_signals(self):
        """连接所有视图信号"""   
        # 主窗口菜单
        self.main_window.new_action.triggered.connect(self.new_config)
        self.main_window.open_action.triggered.connect(self.open_config)
        self.main_window.save_action.triggered.connect(self.save_config)
        self.main_window.save_as_action.triggered.connect(self.save_config_as)
        # 界面已隐藏“导出测试数据”菜单，仍兼容旧字段存在时的连接
        if hasattr(self.main_window, 'export_action') and self.main_window.export_action is not None:
            try:
                self.main_window.export_action.triggered.connect(self.export_glink_txts)
            except Exception:
                pass
        

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
        self.step_list_controller.clear_step_data()
        self.step_list_controller.update_step_list()
        print(f"filecontroller new config: {len(self.step_list_controller.step_list_view.steps)}")
        ### 需要maincontroller给一个step_detail_view的引用
        self.step_detail_controller.clear_step_detail()
        ### 需要maincontroller给一个函数接口
        try:
            config_manager = ConfigManager()
            protocol_configs = config_manager.get_all_protocol_configs()
            self.model.global_params["protocols"] = protocol_configs
            current_key = self.global_controller.global_view.get_current_protocol_key()
            active_cfg = protocol_configs.get(current_key, {})
            for key in ("input_path", "output_path", "config_path"):
                self.model.global_params[key] = active_cfg.get(key, "")
        except Exception:
            pass
        self.global_controller.update_global_view()
        self.window_controller.update_window_title()

    def save_to_file(self, file_path):
        """保存到指定XML文件"""
        ##目前打开保存后的文件再添加中断或开关量还会有data_region字段
        try:
            self.global_controller.update_global_model()
            root = ET.Element("config")
            config_manager = ConfigManager()
            protocol_configs = config_manager.get_all_protocol_configs()

            # 保存路径设置（12条路径）
            if protocol_configs:
                path_elem = ET.SubElement(root, "path_settings")
                for proto, cfg in protocol_configs.items():
                    proto_elem = ET.SubElement(path_elem, "protocol")
                    proto_elem.set("name", proto)
                    keys_to_save = ("input_path", "output_path", "config_path")
                    if proto == "interrupt":
                        keys_to_save = ("output_path",)
                    for key in keys_to_save:
                        value = cfg.get(key, "")
                        value = "" if value is None else str(value)
                        sub_elem = ET.SubElement(proto_elem, key)
                        sub_elem.text = value
                        root.set(f"{proto}_{key}", value)
                # 兼容旧字段：使用当前协议的路径写入通用属性
                try:
                    current_proto = self.global_controller.global_view.get_current_protocol_key()
                except Exception:
                    current_proto = "glink"
                active_cfg = protocol_configs.get(current_proto, {})
                if current_proto == "interrupt":
                    keys_to_copy = ("output_path",)
                else:
                    keys_to_copy = ("input_path", "output_path", "config_path")
                for key in keys_to_copy:
                    value = active_cfg.get(key, "")
                    if value is not None:
                        root.set(key, str(value))
                self.model.global_params["protocols"] = protocol_configs

            # 全局参数
            global_elem = ET.SubElement(root, "global_params")
            for k, v in self.model.global_params.items():
                if k == "protocols":
                    continue
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
                # 检查是否是周期GLINK且包含文件数据
                step_type = step.get_base_step_data().get("step_type", -1)
                expand_data = step.get_expand_step_data()
                periodic_file_data = expand_data.get("periodic_file_data")
                
                # 只处理周期GLINK (step_type == 1) 且有文件数据的情况
                if step_type == 1 and periodic_file_data:  # glink_fileds_periodic
                    print(f"检测到周期GLINK步骤，包含 {len(periodic_file_data)} 行数据，开始展开...")
                    # 展开为多个步骤
                    base_data = step.get_base_step_data()
                    type_data = step.get_type_step_data()
                    file_path_value = type_data.get("file_path") or expand_data.get("periodic_file_path")
                    period_value = type_data.get("period")
                    group_id = expand_data.get("periodic_group_id")
                    if not group_id:
                        group_id = f"periodic_{uuid.uuid4().hex}"
                        expand_data["periodic_group_id"] = group_id
                    if file_path_value:
                        expand_data["periodic_file_path"] = file_path_value
                        type_data["file_path"] = file_path_value
                    
                    # 第一行的time来自base_step_data中的time（仿真时间）
                    first_time = float(base_data.get("time", 0.0))
                    period = float(period_value if period_value not in (None, "") else 0.0)
                    
                    for row_idx, row_data in enumerate(periodic_file_data):
                        step_elem = ET.SubElement(steps_elem, "step")
                        
                        # 保存base字典（更新time字段：第一行=first_time，往后每行+period）
                        base_elem = ET.SubElement(step_elem, "base")
                        base_data_copy = base_data.copy()
                        base_data_copy["time"] = first_time + row_idx * period
                        for k, v in base_data_copy.items():
                            print(f"save field: {k} value: {v}")
                            field = ET.SubElement(base_elem, k)
                            field.text = str(v)
                        
                        # 保存type字典（更新data_region，移除start_time、period、file_path）
                        type_elem = ET.SubElement(step_elem, "type")
                        type_data_copy = {}
                        for k, v in type_data.items():
                            # 跳过start_time字段，period/file_path需要保存
                            if k in ("start_time",):
                                continue
                            type_data_copy[k] = v
                        if file_path_value is not None:
                            type_data_copy["file_path"] = file_path_value
                        if period_value is not None:
                            type_data_copy["period"] = period_value
                        
                        # 设置data_region为当前行的数据
                        type_data_copy["data_region"] = row_data
                        
                        for k, v in type_data_copy.items():
                            print(f"save field: {k} value: {v}")
                            field = ET.SubElement(type_elem, k)
                            if k == "data_region":
                                if isinstance(v, (list, dict)):
                                    if v:  # 非空列表或字典
                                        field.text = json.dumps(v, ensure_ascii=False)
                                    else:  # 空列表或字典
                                        field.text = "[]"
                                elif v is None:
                                    field.text = "None"
                                else:
                                    field.text = str(v)
                            else:
                                # 对于local_site、recip_site、sub_address字段，直接保存字符串（保留16进制格式）
                                field.text = str(v)
                        
                        # 保存expand字典（移除periodic_file_data，追加分组信息）
                        expand_elem = ET.SubElement(step_elem, "expand")
                        for k, v in expand_data.items():
                            if k in ("periodic_file_data", "periodic_file_path"):
                                continue
                            print(f"save field: {k} value: {v}")
                            field = ET.SubElement(expand_elem, k)
                            field.text = str(v)
                        field = ET.SubElement(expand_elem, "periodic_group_id")
                        field.text = group_id
                        field = ET.SubElement(expand_elem, "periodic_group_index")
                        field.text = str(row_idx)
                        field = ET.SubElement(expand_elem, "periodic_group_first")
                        field.text = "1" if row_idx == 0 else "0"
                        if file_path_value:
                            field = ET.SubElement(expand_elem, "periodic_file_path")
                            field.text = str(file_path_value)
                        
                        # 保存protocol_data字典
                        protocol_elem = ET.SubElement(step_elem, "protocol")
                        # 检查协议类型，如果为-1（无），则不保存protocol_data
                        protocol_type = step.get_type_step_data().get("protocol_type", -1)
                        if protocol_type == -1:
                            # 协议类型为"无"，清空protocol_data并只保存空的protocol元素
                            step.set_protocol_data({})
                            print("协议类型为'无'，已清空protocol_data（周期步骤）")
                        else:
                            protocol_data = step.get_protocol_data()
                            if protocol_data:
                                # 检查消息控制字，如果是0x0001或0x0003，添加帧计数属性
                                ctrl_word_str = protocol_data.get("消息控制字", "0")
                                try:
                                    # 安全转换消息控制字
                                    if isinstance(ctrl_word_str, str):
                                        ctrl_word_str = ctrl_word_str.strip().lower().replace('×', 'x').replace('Ｘ', 'x')
                                        if ctrl_word_str.startswith('0x'):
                                            ctrl_word = int(ctrl_word_str, 16)
                                        else:
                                            ctrl_word = int(ctrl_word_str, 16) if all(c in '0123456789abcdef' for c in ctrl_word_str) else int(float(ctrl_word_str))
                                    else:
                                        ctrl_word = int(ctrl_word_str)
                                    
                                    # 如果消息控制字的位0=1（即0x0001或0x0003），添加帧计数属性
                                    if (ctrl_word & 0x01) == 0x01:
                                        protocol_elem.set("帧计数", "true")
                                        print(f"保存protocol: 消息控制字为0x{ctrl_word:04X}，添加帧计数属性")
                                except (ValueError, TypeError) as e:
                                    print(f"保存protocol: 解析消息控制字失败: {ctrl_word_str}, 错误: {e}")
                                
                                for k, v in protocol_data.items():
                                    print(f"save protocol field: {k} value: {v}")
                                    field = ET.SubElement(protocol_elem, k)
                                    field.text = str(v) if v is not None else ""
                else:
                    # 普通步骤，正常保存
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
                        print(f"save field: {k} value: {v}, type: {type(v)}")
                        field = ET.SubElement(type_elem, k)
                        # 这里可以用k对应的dtype是否为union代替
                        # 将union的列表结构序列化为json字段
                        if k == "data_region":
                            if isinstance(v, (list, dict)):
                                if v:  # 非空列表或字典
                                    field.text = json.dumps(v, ensure_ascii=False)
                                else:  # 空列表或字典
                                    field.text = "[]"
                            elif v is None:
                                field.text = "None"
                            else:
                                field.text = str(v)
                        elif k in ("local_site", "recip_site", "sub_address", "base_address"):
                            # 对于这些字段，优先使用全局原始输入字符串，如果没有则使用当前值
                            raw_input = step.get_raw_input_string(k)
                            if raw_input is not None:
                                # 使用全局原始输入字符串保存（保留16进制格式如0x11）
                                field.text = raw_input
                                print(f"  保存 {k} 使用原始输入字符串: '{raw_input}'")
                            elif v is None:
                                field.text = ""
                            elif isinstance(v, str):
                                # 已经是字符串，直接保存（保留0x前缀）
                                field.text = v
                                print(f"  保存 {k} 为字符串: '{v}'")
                            else:
                                # 如果是数字，转换为字符串（但会丢失16进制格式，这种情况不应该发生）
                                field.text = str(v)
                                print(f"  警告：{k} 的值 {v} 不是字符串，转换为 '{field.text}'（可能丢失16进制格式）")
                        else:
                            field.text = str(v)
                    
                    # 保存expand字典
                    expand_elem = ET.SubElement(step_elem, "expand")
                    for k, v in step.get_expand_step_data().items():
                        if k not in ("periodic_file_data", "periodic_file_path"):  # 不保存临时数据
                            print(f"save field: {k} value: {v}")
                            field = ET.SubElement(expand_elem, k)
                            field.text = str(v)
                    
                    # 保存protocol_data字典
                    protocol_elem = ET.SubElement(step_elem, "protocol")
                    # 检查协议类型，如果为-1（无），则不保存protocol_data
                    protocol_type = step.get_type_step_data().get("protocol_type", -1)
                    if protocol_type == -1:
                        # 协议类型为"无"，清空protocol_data并只保存空的protocol元素
                        step.set_protocol_data({})
                        print("协议类型为'无'，已清空protocol_data")
                    else:
                        protocol_data = step.get_protocol_data()
                        if protocol_data:
                            # 检查消息控制字，如果是0x0001或0x0003，添加帧计数属性
                            ctrl_word_str = protocol_data.get("消息控制字", "0")
                            try:
                                # 安全转换消息控制字
                                if isinstance(ctrl_word_str, str):
                                    ctrl_word_str = ctrl_word_str.strip().lower().replace('×', 'x').replace('Ｘ', 'x')
                                    if ctrl_word_str.startswith('0x'):
                                        ctrl_word = int(ctrl_word_str, 16)
                                    else:
                                        ctrl_word = int(ctrl_word_str, 16) if all(c in '0123456789abcdef' for c in ctrl_word_str) else int(float(ctrl_word_str))
                                else:
                                    ctrl_word = int(ctrl_word_str)
                                
                                # 如果消息控制字的位0=1（即0x0001或0x0003），添加帧计数属性
                                if (ctrl_word & 0x01) == 0x01:
                                    protocol_elem.set("帧计数", "true")
                                    print(f"保存protocol: 消息控制字为0x{ctrl_word:04X}，添加帧计数属性")
                            except (ValueError, TypeError) as e:
                                print(f"保存protocol: 解析消息控制字失败: {ctrl_word_str}, 错误: {e}")
                            
                            for k, v in protocol_data.items():
                                print(f"save protocol field: {k} value: {v}")
                                field = ET.SubElement(protocol_elem, k)
                                field.text = str(v) if v is not None else ""


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
                self.model.file_path = file_path
                config_manager = ConfigManager()

                # 解析全局参数
                global_elem = root.find("global_params")
                global_params = {}
                if global_elem is not None:
                    for child in global_elem:
                        global_params[child.tag] = child.text if child.text is not None else ""

                # 根节点上通用的输入/输出/配置路径属性
                root_general_attrs = {}
                for key in ("input_path", "output_path", "config_path"):
                    attr_val = root.get(key)
                    if attr_val is not None:
                        root_general_attrs[key] = attr_val
                        global_params[key] = attr_val

                # 收集每个协议的路径设置
                protocol_updates = {}
                existing_protocols = config_manager.get_all_protocol_configs()
                protocol_keys = list(existing_protocols.keys()) or ["glink", "uart", "bc", "interrupt"]

                # 读取形如 glink_input_path 的属性
                for proto in protocol_keys:
                    for key in ("input_path", "output_path", "config_path"):
                        attr_name = f"{proto}_{key}"
                        attr_value = root.get(attr_name)
                        if attr_value is not None:
                            protocol_updates.setdefault(proto, {})[key] = attr_value

                # 读取 path_settings 节点
                path_settings_elem = root.find("path_settings")
                if path_settings_elem is not None:
                    for proto_elem in path_settings_elem.findall("protocol"):
                        proto_name = proto_elem.get("name")
                        if not proto_name:
                            continue
                        for key in ("input_path", "output_path", "config_path"):
                            node = proto_elem.find(key)
                            if node is not None and node.text is not None:
                                protocol_updates.setdefault(proto_name, {})[key] = node.text

                # 如果只有通用属性，则默认归入 glink
                if root_general_attrs and "glink" in protocol_keys:
                    protocol_updates.setdefault("glink", {}).update(root_general_attrs)

                if protocol_updates:
                    config_manager.set_all_protocol_configs(protocol_updates, merge=True)

                all_protocols = config_manager.get_all_protocol_configs()
                active_proto = "glink"
                try:
                    active_proto = self.global_controller.global_view.get_current_protocol_key()
                except Exception:
                    pass
                active_cfg = all_protocols.get(active_proto, {})
                for key in ("input_path", "output_path", "config_path"):
                    if key not in global_params or not global_params.get(key):
                        global_params[key] = active_cfg.get(key, "")
                    else:
                        # 同步当前激活协议的值，保证模型使用最新路径
                        active_cfg[key] = global_params[key]
                self.model.global_params = global_params
                self.model.global_params["protocols"] = all_protocols
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
                        
                        # 读取protocol字典
                        protocol_elem = step_elem.find("protocol")
                        if protocol_elem is not None:
                            protocol_dict = {}
                            for child in protocol_elem:
                                protocol_dict[child.tag] = child.text if child.text else ""
                            step.set_protocol_data(protocol_dict)
                        
                        steps.append(step)


                ####
                merged_steps = self._merge_periodic_steps(steps)
                self.model.steps = merged_steps

                print("steps loaded:", len(merged_steps))
                print("first step:", merged_steps[0].get_base_step_data() if merged_steps else None)
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
        print(f"text2dtype dtype: {dtype}, text: {text}, text type: {type(text)}")
        filed_type = step_model.get_field_type(dtype)
        # print(f"text2dtype dtype: {dtype}")
        if filed_type != 'union':
            # 对于local_site、recip_site、sub_address、base_address字段，保留原始字符串格式
            if dtype in ("local_site", "recip_site", "sub_address", "base_address"):
                # 确保返回字符串，即使text是None也要处理
                if text is None:
                    return ""
                # 保留原始字符串，不转换为int
                # 注意：保留原始输入格式，包括全角乘号×（保存时保留）
                result = str(text).strip()
                print(f"text2dtype 保留字符串格式: {dtype} = '{result}'")
                return result
            pdtype = step_model.get_dtype(dtype)
            val = pdtype(text)
            print(f"text2dtype dtype_tag: {dtype_tag};text: {text} pdtype: {pdtype} val type {type(val)}")
            return val
        else:
            # 容错解析 union：空/None/非法JSON 返回空列表
            try:
                raw = (text or "").strip()
                if raw.lower() in ("none", ""):
                    return []
                data_list = json.loads(raw)
                if not isinstance(data_list, list):
                    return []
                val = []
                for item in data_list:
                    # 支持对象或原始值
                    if isinstance(item, dict) and "data_type" in item and "value" in item:
                        data_type = item.get("data_type")
                        value = item.get("value")
                        pdtype = step_model.get_dtype_by_idx(int(data_type))
                        print(f"union {item} data_type:{data_type}, value: {value} pdtye:{pdtype}")
                        val.append({
                            "data_type": int(data_type),
                            "value": pdtype(value)
                        })
                    else:
                        # 保留原值，后续导出阶段会统一标准化为HEX
                        val.append(item)
                return val
            except Exception:
                return []



    def _safe_int(self, value, default=0):
        try:
            if value is None:
                return default
            if isinstance(value, int):
                return value
            if isinstance(value, float):
                return int(value)
            text = str(value).strip()
            if not text:
                return default
            return int(float(text)) if '.' in text else int(text)
        except Exception:
            return default

    def _merge_periodic_steps(self, steps):
        """将通过periodic_group_id拆分的周期步骤重新合并为单个StepModel"""
        grouped = {}
        merged = []
        for step in steps:
            expand = step.get_expand_step_data() or {}
            group_id = expand.get("periodic_group_id")
            if group_id:
                grouped.setdefault(group_id, []).append(step)
            else:
                merged.append(step)

        for group_id, items in grouped.items():
            items.sort(key=lambda s: self._safe_int(s.get_expand_step_data().get("periodic_group_index"), 0))
            first = None
            for s in items:
                marker = str(s.get_expand_step_data().get("periodic_group_first", "")).strip()
                if marker == "1":
                    first = s
                    break
            if first is None:
                first = items[0]

            data_rows = []
            file_path = None
            for s in items:
                type_data = s.get_type_step_data()
                row = type_data.get("data_region")
                if row is not None:
                    data_rows.append(row)
                if not file_path:
                    fp = type_data.get("file_path") or s.get_expand_step_data().get("periodic_file_path")
                    if fp:
                        file_path = fp

            expand = first.get_expand_step_data()
            expand["periodic_file_data"] = data_rows
            if file_path:
                expand["periodic_file_path"] = file_path
                first.get_type_step_data()["file_path"] = file_path
            if data_rows:
                first.get_type_step_data()["data_region"] = data_rows[0]
            merged.append(first)
        return merged


    
    def save_config(self):
        """保存配置"""
        if self.model.file_path:
            self.save_to_file(self.model.file_path)
        else:
            self.save_config_as()

    def save_and_export(self):
        """先保存流程配置，再导出测试数据。
        若当前流程未命名（未保存过），先弹出另存为，用户取消则中止。
        """
        # 确保已保存到文件
        if not self.model.file_path:
            self.save_config_as()
            if not self.model.file_path:
                # 用户取消保存
                return
        else:
            # 已有路径则直接保存一次
            self.save_to_file(self.model.file_path)

        # 保存成功后执行目录批量导出（读取输入目录下所有XML）
        self.export_glink_txts()

    def save_config_as(self):
        """另存为XML配置"""
        # 先同步一次全局配置，确保使用最新的输入路径
        try:
            self.global_controller.update_global_model()
        except Exception:
            pass
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
        # default_dir = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        
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
        """按类型导出到文件，支持自定义文件名和16进制格式"""
        # 1. 选择输出目录和文件名
        default_dir = getattr(self, "DEFAULT_CONFIG_DIR", "./configs")
        input_dir = self.model.global_params.get("input_path", QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation))
        output_dir = self.model.global_params.get("output_path", QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation))
        
        
        file_path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "选择导出文件",
            output_dir,
            "文本文件 (*.txt);;16进制文件 (*.hex);;所有文件 (*)"
        )
        if not file_path:
            return

        # 2. 选择导出格式选项
        from PyQt5.QtWidgets import QInputDialog, QMessageBox
        
        # 询问是否包含字段名
        include_field_names, ok = QInputDialog.getItem(
            self.main_window,
            "导出选项",
            "是否包含字段名:",
            ["是", "否"],
            1,  # 默认选择"否"
            False
        )
        if not ok:
            return
        
        include_field_names = (include_field_names == "是")
        
        # 询问分隔符
        separator, ok = QInputDialog.getItem(
            self.main_window,
            "导出选项", 
            "选择字段分隔符:",
            ["制表符(Tab)", "逗号(,)", "空格( )"],
            0,
            False
        )
        if not ok:
            return
        
        # 转换分隔符
        sep_map = {
            "制表符(Tab)": "\t",
            "逗号(,)": ",",
            "空格( )": " "
        }
        field_separator = sep_map.get(separator, "\t")
        
        # 3. 遍历所有xml文件
        steps_by_type = {}
        # config_dir = os.path.dirname(file_path)
        config_dir = input_dir if input_dir else default_dir
        
        # 统计信息
        total_files = 0
        processed_files = 0
        skipped_files = 0
        
        print(f"开始扫描目录: {config_dir}")
        
        for root, dirs, files in os.walk(config_dir):
            for file in files:
                if file.endswith('.xml'):
                    total_files += 1
                    file_path_xml = os.path.join(root, file)
                    
                    # 跳过一些明显不是配置文件的目录
                    skip_dirs = ['.gradle', '.IntelliJIdea', 'AndroidStudioProjects', 'build', 'target', 'bin', 'intermediates', 'lint_vital_partial_results']
                    if any(skip_dir in root for skip_dir in skip_dirs):
                        print(f"跳过系统目录: {os.path.basename(file_path_xml)}")
                        skipped_files += 1
                        continue
                    
                    # 跳过Android资源文件目录
                    if 'res/values' in root or 'res/values-' in root:
                        print(f"跳过Android资源目录: {os.path.basename(file_path_xml)}")
                        skipped_files += 1
                        continue
                    
                    try:
                        steps = self.read_steps_from_xml(file_path_xml)
                        if steps:
                            for step in steps:
                                step_type = step.get_step_type()
                                if step_type not in steps_by_type:
                                    steps_by_type[step_type] = []
                                steps_by_type[step_type].append(step)
                            processed_files += 1
                            print(f"成功处理: {os.path.basename(file_path_xml)} (找到 {len(steps)} 个步骤)")
                        else:
                            skipped_files += 1
                    except Exception as e:
                        print(f"读取文件失败: {os.path.basename(file_path_xml)}, 错误: {str(e)[:100]}")
                        skipped_files += 1
        
        print(f"\n扫描完成:")
        print(f"  总文件数: {total_files}")
        print(f"  成功处理: {processed_files}")
        print(f"  跳过文件: {skipped_files}")
        
        if not steps_by_type:
            QMessageBox.warning(
                self.main_window,
                "未找到配置",
                "在指定目录中未找到任何有效的配置文件"
            )
            return

        # 4. 根据文件扩展名选择导出格式
        file_ext = os.path.splitext(file_path)[1].lower()
        is_hex_format = file_ext == '.hex'
        
        # 5. 导出到文件
        try:
            if is_hex_format:
                # 16进制格式导出
                self.export_steps_to_hex(file_path, steps_by_type, include_field_names, field_separator)
            else:
                # 文本格式导出
                self.export_steps_to_txt(file_path, steps_by_type, include_field_names, field_separator)
            
            QMessageBox.information(
                self.main_window,
                "导出完成",
                f"已按类型导出到: {file_path}"
            )
        except Exception as e:
            print(traceback.format_exc())
            QMessageBox.critical(
                self.main_window,
                "导出错误",
                f"导出文件时出错: {str(e)}"
            )

    def read_steps_from_xml(self, file_path):
        """从xml文件读取所有StepModel，增强错误处理"""
        import xml.etree.ElementTree as ET
        from models.step_model import StepModel
        import time
        
        steps = []
        
        try:
            # 首先检查文件大小，跳过过大的文件
            file_size = os.path.getsize(file_path)
            if file_size > 10 * 1024 * 1024:  # 10MB
                print(f"跳过大文件: {os.path.basename(file_path)} (大小: {file_size / 1024 / 1024:.1f}MB)")
                return steps
            
            # 检查文件是否为空
            if file_size == 0:
                print(f"跳过空文件: {os.path.basename(file_path)}")
                return steps
            
            # 尝试快速验证XML格式
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    first_line = f.readline().strip()
                    if not first_line.startswith('<?xml') and not first_line.startswith('<'):
                        print(f"跳过非XML文件: {os.path.basename(file_path)}")
                        return steps
            except Exception:
                # 如果读取失败，尝试二进制模式
                try:
                    with open(file_path, 'rb') as f:
                        first_bytes = f.read(100)
                        if not first_bytes.startswith(b'<?xml') and not first_bytes.startswith(b'<'):
                            print(f"跳过非XML文件: {os.path.basename(file_path)}")
                            return steps
                except Exception:
                    print(f"无法读取文件: {os.path.basename(file_path)}")
                    return steps
            
            # 设置解析超时
            start_time = time.time()
            timeout = 5  # 5秒超时
            
            # 使用更安全的解析方式
            try:
                # 先尝试快速解析
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if time.time() - start_time > timeout:
                        print(f"文件读取超时: {os.path.basename(file_path)}")
                        return steps
                
                # 检查内容是否包含必要的标签
                # 支持多种配置文件格式（不要求step标签）
                if ('<config>' in content or '<configuration>' in content or
                    '<settings>' in content or '<data>' in content or
                    '<workflow>' in content or '<steps>' in content):
                    # 这是配置文件
                    pass
                elif '<resources>' in content and ('<string>' in content or '<dimen>' in content or '<bool>' in content):
                    # 这是Android资源文件，跳过
                    print(f"跳过Android资源文件: {os.path.basename(file_path)}")
                    return steps
                else:
                    print(f"跳过非配置文件: {os.path.basename(file_path)}")
                    return steps
                
                # 解析XML
                if time.time() - start_time > timeout:
                    print(f"文件解析超时: {os.path.basename(file_path)}")
                    return steps
                
                tree = ET.parse(file_path)
                root = tree.getroot()
                
                if time.time() - start_time > timeout:
                    print(f"XML解析超时: {os.path.basename(file_path)}")
                    return steps
                
                # 支持任意层级的 steps/step 结构
                step_nodes = []
                steps_elem = root.find("steps")
                if steps_elem is not None:
                    step_nodes.extend(steps_elem.findall("step"))
                # 同时查找任意层级的 step
                if not step_nodes:
                    step_nodes.extend(root.findall('.//step'))

                for step_elem in step_nodes:
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
                        
                        # 从XML加载后，如果字段是字符串格式（可能是16进制），保存到全局原始输入字符串
                        for field in ("local_site", "recip_site", "sub_address", "base_address"):
                            if field in type_dict:
                                value = type_dict[field]
                                if isinstance(value, str):
                                    step.set_raw_input_string(field, value)
                                    print(f"从XML加载原始输入字符串: {field} = '{value}'")
                    # expand
                    expand_elem = step_elem.find("expand")
                    if expand_elem is not None:
                        expand_dict = {}
                        self.load_data_to_dict(expand_dict, expand_elem)
                        step.update_expand_data(expand_dict)
                    # protocol
                    protocol_elem = step_elem.find("protocol")
                    if protocol_elem is not None:
                        protocol_dict = {}
                        for child in protocol_elem:
                            protocol_dict[child.tag] = child.text if child.text else ""
                        step.set_protocol_data(protocol_dict)
                    steps.append(step)
                    
                    # 检查是否超时
                    if time.time() - start_time > timeout:
                        print(f"步骤处理超时: {os.path.basename(file_path)}")
                        break
                            
            except ET.ParseError as e:
                print(f"XML格式错误，跳过文件: {os.path.basename(file_path)}, 错误: {str(e)[:100]}")
                return steps
            except Exception as e:
                print(f"解析文件失败: {os.path.basename(file_path)}, 错误: {str(e)[:100]}")
                return steps
                
        except Exception as e:
            print(f"读取文件失败: {os.path.basename(file_path)}, 错误: {str(e)[:100]}")
            return steps
            
        return steps

    def export_glink_txts(self):
        """按需求导出四类GLINK文本数据，按(站点/子地址/长度)分文件或汇总文件"""
        from PyQt5.QtWidgets import QMessageBox
        config_manager = ConfigManager()

        def resolve_path(path_value):
            if not path_value:
                return ""
            path_value = str(path_value).strip()
            if not path_value:
                return ""
            if path_value == ".":
                return os.getcwd()
            if os.path.isabs(path_value):
                return path_value
            return os.path.abspath(os.path.join(os.getcwd(), path_value))

        protocol_dirs = {}
        interrupt_output_dir = ""
        for key in ("glink", "uart", "bc", "interrupt", "switch"):
            cfg = config_manager.get_protocol_config(key) or {}
            if key == "interrupt":
                interrupt_output_dir = resolve_path(cfg.get("output_path", ""))
            protocol_dirs[key] = resolve_path(cfg.get("output_path", ""))  # 开关量协议使用output_path作为输出目录

        def clear_txt_files(target_dir):
            """清空导出目录下的所有txt文件"""
            if not target_dir or not os.path.isdir(target_dir):
                return
            removed = 0
            for name in os.listdir(target_dir):
                path = os.path.join(target_dir, name)
                if os.path.isfile(path) and name.lower().endswith(".txt"):
                    try:
                        os.remove(path)
                        removed += 1
                    except Exception as e:
                        print(f"删除旧TXT失败: {path}, 错误: {e}")
            if removed:
                print(f"清空目录 {target_dir} 下 {removed} 个txt文件")

        steps_from_file = []
        current_file = getattr(self.model, "file_path", None)
        if current_file and os.path.isfile(current_file):
            try:
                steps_from_file = self.read_steps_from_xml(current_file)
            except Exception as e:
                print(f"从当前XML重新加载步骤失败: {e}")

        all_steps = steps_from_file or list(self.model.steps)
        if not all_steps:
            QMessageBox.warning(self.main_window, "未找到配置", "当前流程没有可导出的步骤，请先保存流程。")
            return

        # 使用配置加载工具，根据step_type动态加载配置
        from utils.config_loader import get_config_by_step_type
        
        # 配置缓存，避免重复加载
        config_cache = {}
        
        def get_config_for_step(step_type: int):
            """根据step_type获取配置，使用缓存避免重复加载"""
            if step_type not in config_cache:
                config_cache[step_type] = get_config_by_step_type(step_type)
            return config_cache[step_type]
        
        def output_allowed(name: str, step_type: int) -> bool:
            """根据step_type检查输出是否被允许
            注意：所有txt文件都要输出，和keep all逻辑一致。
            配置字段只用于保存到config文件，不影响导出逻辑。
            """
            # 始终返回True，所有文件都导出（相当于keep all逻辑）
            return True

        def safe_parse_numeric(value, default=0):
            """将各种格式的数值安全转换为整数"""
            if value is None:
                return default
            if isinstance(value, (int, float)):
                try:
                    return int(value)
                except Exception:
                    return default
            try:
                text = str(value).strip()
            except Exception:
                return default
            if not text:
                return default
            text = text.replace('×', 'x').replace('Ｘ', 'x')
            sign = 1
            if text.startswith('-'):
                sign = -1
                text = text[1:].strip()
            lowered = text.lower()
            try:
                if lowered.startswith('0x'):
                    return sign * int(lowered, 16)
                if lowered.startswith('0b'):
                    return sign * int(lowered, 2)
                if lowered.startswith('0o'):
                    return sign * int(lowered, 8)
                if '.' in lowered:
                    return sign * int(float(lowered))
                return sign * int(lowered)
            except Exception:
                return default

        def split_array_values(value):
            """将数组字段的文本拆分为列表"""
            if value is None:
                return []
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                text = value.strip()
                if not text:
                    return []
                try:
                    decoded = json.loads(text)
                    if isinstance(decoded, list):
                        return decoded
                except Exception:
                    pass
                for sep in ('[', ']', ',', '，', ';', '；', '\t', '\r', '\n'):
                    text = text.replace(sep, ' ')
                return [tok for tok in text.split(' ') if tok]
            return [value]

        def _strip_hex_prefix(token: str) -> str:
            if not token:
                return ""
            token = str(token).strip()
            if not token:
                return ""
            if token.lower().startswith("0x"):
                token = token[2:]
            return token.replace(" ", "")

        def _tokens_to_byte_stream(tokens):
            """将normalize后的0xXXXX标记还原为实际字节序列（字符串形式，每字节2位）"""
            byte_chunks = []
            for token in tokens or []:
                stripped = _strip_hex_prefix(token)
                if not stripped:
                    continue
                if len(stripped) % 2 == 1:
                    stripped = "0" + stripped
                try:
                    value = int(stripped, 16)
                except ValueError:
                    continue
                byte_count = len(stripped) // 2
                for i in range(byte_count):
                    byte_val = (value >> (8 * i)) & 0xFF
                    byte_chunks.append(f"{byte_val:02X}")
            return "".join(byte_chunks)

        LITTLE_ENDIAN_WORD_SWAP_DTYPES = {"UINT32", "FLOAT32", "REAL32", "FLOAT64", "REAL64", "DOUBLE"}

        def swap_16bit_words_for_little_endian(chunk_bytes):
            """按16位（2字节）为单位反转顺序，实现小端输出"""
            if not chunk_bytes or len(chunk_bytes) < 4:
                return chunk_bytes
            if len(chunk_bytes) % 2 != 0:
                return chunk_bytes
            words = [chunk_bytes[i:i+2] for i in range(0, len(chunk_bytes), 2)]
            words.reverse()
            return b"".join(words)

        def format_hex_items_for_output(hex_items):
            """拼接所有字节后按16位（4个hex字符）切片输出，剩余2个字符按8位输出"""
            if not hex_items:
                return []
            hex_stream = "".join(_strip_hex_prefix(tok) for tok in hex_items if tok).upper()
            if not hex_stream:
                return []
            formatted = []
            for idx in range(0, len(hex_stream), 4):
                chunk = hex_stream[idx: idx + 4]
                if not chunk:
                    continue
                formatted.append(f"0x{chunk}")
            return formatted

        def merge_adjacent_byte_tokens(hex_items):
            """将相邻的8位标记与后续标记组合成16位输出，以满足0x12 0x3456 -> 0x1234 0x56的规则"""
            if not hex_items:
                return []

            merged = []
            i = 0
            while i < len(hex_items):
                item = hex_items[i]
                stripped = _strip_hex_prefix(item)
                if not stripped:
                    i += 1
                    continue

                if len(stripped) <= 2:
                    val1 = int(stripped, 16) if stripped else 0
                    if i + 1 < len(hex_items):
                        next_item = hex_items[i + 1]
                        next_stripped = _strip_hex_prefix(next_item)
                        if next_stripped and len(next_stripped) <= 2:
                            val2 = int(next_stripped, 16)
                            merged.append(f"0x{((val1 << 8) | val2):04X}")
                            i += 2
                            continue
                        elif next_stripped and len(next_stripped) > 2:
                            next_val = int(next_stripped, 16)
                            high_byte = (next_val >> 8) & 0xFF
                            low_byte = next_val & 0xFF
                            merged.append(f"0x{((val1 << 8) | high_byte):04X}")
                            merged.append(f"0x{low_byte:02X}")
                            i += 2
                            continue
                    merged.append(f"0x{val1:04X}")
                    i += 1
                else:
                    merged.append(item)
                    i += 1
            return merged

        def bytes_to_hex_words(byte_data: bytes, big_endian: bool):
            """将字节序列按16位对齐转换为十六进制文本"""
            if not byte_data:
                return []
            result = []
            length = len(byte_data)
            for idx in range(0, length, 2):
                if idx + 1 < length:
                    if big_endian:
                        word = (byte_data[idx] << 8) | byte_data[idx + 1]
                    else:
                        word = byte_data[idx] | (byte_data[idx + 1] << 8)
                    result.append(f"0x{word:04X}")
                else:
                    result.append(f"0x{byte_data[idx]:02X}")
            return result

        def scalar_value_to_bytes(dtype_str: str, value, big_endian: bool):
            """根据数据类型将值转换为字节序列"""
            dtype = (dtype_str or "").upper()
            endian_prefix = '>' if big_endian else '<'
            try:
                if dtype in ("UINT8", "INT8"):
                    val = safe_parse_numeric(value) & 0xFF
                    return bytes([val])
                if dtype in ("UINT16", "INT16"):
                    val = safe_parse_numeric(value) & 0xFFFF
                    return bytes([(val >> 8) & 0xFF, val & 0xFF]) if big_endian else bytes([val & 0xFF, (val >> 8) & 0xFF])
                if dtype in ("UINT32", "INT32"):
                    val = safe_parse_numeric(value) & 0xFFFFFFFF
                    if big_endian:
                        return bytes([
                            (val >> 24) & 0xFF,
                            (val >> 16) & 0xFF,
                            (val >> 8) & 0xFF,
                            val & 0xFF
                        ])
                    return bytes([
                        val & 0xFF,
                        (val >> 8) & 0xFF,
                        (val >> 16) & 0xFF,
                        (val >> 24) & 0xFF
                    ])
                if dtype in ("UINT64", "INT64"):
                    val = safe_parse_numeric(value) & 0xFFFFFFFFFFFFFFFF
                    if big_endian:
                        return bytes([(val >> shift) & 0xFF for shift in range(56, -8, -8)])
                    return bytes([(val >> shift) & 0xFF for shift in range(0, 64, 8)])
                if dtype in ("FLOAT32", "REAL32", "FLOAT", "REAL"):
                    if isinstance(value, str):
                        s_val = value.strip().lower()
                        if s_val.startswith("0x"):
                            try:
                                bits = int(s_val, 16) & 0xFFFFFFFF
                                return bits.to_bytes(4, byteorder='big' if big_endian else 'little')
                            except ValueError:
                                pass
                    fv = float(value) if value not in (None, "") else 0.0
                    return struct.pack(endian_prefix + 'f', fv)
                if dtype in ("FLOAT64", "REAL64", "DOUBLE"):
                    if isinstance(value, str):
                        s_val = value.strip().lower()
                        if s_val.startswith("0x"):
                            try:
                                bits = int(s_val, 16) & 0xFFFFFFFFFFFFFFFF
                                return bits.to_bytes(8, byteorder='big' if big_endian else 'little')
                            except ValueError:
                                pass
                    fv = float(value) if value not in (None, "") else 0.0
                    return struct.pack(endian_prefix + 'd', fv)
                if dtype in ("BOOL", "BOOLEAN"):
                    lv = str(value).strip().lower() if value is not None else "0"
                    iv = 1 if lv in ("1", "true", "yes", "y", "on", "是") else 0
                    return bytes([iv])
                if dtype in ("STR", "STRING"):
                    return str(value or "").encode('utf-8')
                # 默认按照16位处理
                val = safe_parse_numeric(value) & 0xFFFF
                return bytes([(val >> 8) & 0xFF, val & 0xFF]) if big_endian else bytes([val & 0xFF, (val >> 8) & 0xFF])
            except Exception:
                return b""

        def convert_template_fields_to_hex(step_obj, protocol_type_value, big_endian, defer_little_endian=False):
            """将协议模板的字段转换为十六进制序列（跳过“时间”字段）"""
            try:
                template = self.template_manager.get_template_by_step_and_protocol(
                    step_obj.get_step_type(),
                    protocol_type_value
                )
            except Exception:
                template = None
            if not template:
                return [], 0, ""

            protocol_data = step_obj.get_protocol_data() or {}
            fields = sorted(template.get("fields", []), key=lambda f: f.get("seq", 0))
            hex_items = []
            total_bytes = 0
            display_big_endian = True if defer_little_endian else big_endian
            is_little_endian = not big_endian
            raw_bytes = bytearray()
            segment_lengths = []
            time_field_index = -1  # 记录时间字段在hex_items中的起始位置
            time_field_length = 0  # 记录时间字段的长度（16位值的个数）
            template_id = template.get("id", "")
            data_region_str = normalize_data_region_value(
                step_obj.get_type_step_data().get("data_region")
            )
            special_metrics = {}
            if template_id == "serial_std":
                special_metrics = calc_serial_standard_metrics(data_region_str)
            elif template_id == "serial_ext":
                special_metrics = calc_serial_extended_metrics(data_region_str)
            elif template_id == "crc_tail":
                special_metrics = calc_crc_tail_metrics(data_region_str)
            overrides = special_metrics.get("overrides") if special_metrics else {}

            for field in fields:
                element = field.get("element")
                if not element:
                    continue
                # 注意："时间"字段现在需要包含在导出数据中
                dtype = str(field.get("dtype", "")).upper()
                # 特殊处理"数据区"字段：从step的type_data中获取data_region
                if element == "数据区":
                    if special_metrics:
                        raw_value = overrides.get("数据区", data_region_str)
                    else:
                        raw_value = step_obj.get_type_step_data().get("data_region")
                        if raw_value is None:
                            raw_value = protocol_data.get(element)
                        if raw_value in (None, ""):
                            raw_value = field.get("value", "")
                else:
                    if overrides and element in overrides:
                        raw_value = overrides[element]
                    else:
                        raw_value = protocol_data.get(element)
                        if raw_value in (None, ""):
                            raw_value = field.get("value", "")

                field_hex = []
                field_bytes = 0

                # 特殊处理"数据区"字段：如果是union列表，使用normalize_hex_items处理
                if element == "数据区" and special_metrics:
                    data_hex_items = special_metrics.get("data_hex_items", [])
                    byte_seq = special_metrics.get("data_bytes", [])
                    if data_hex_items:
                        field_hex = data_hex_items
                        field_bytes = len(byte_seq)
                        raw_bytes.extend(byte_seq)
                        segment_lengths.append(len(data_hex_items))
                elif element == "数据区" and isinstance(raw_value, (list, dict)) and raw_value:
                    # 对于数据区，使用normalize_hex_items处理union列表
                    msg_len = step_obj.get_type_step_data().get("msg_len", 0)
                    data_hex_items, data_bytes, _, data_raw_hex, data_segments = normalize_hex_items(
                        raw_value,
                        msg_len,
                        big_endian,
                        defer_little_endian=defer_little_endian
                    )
                    if data_hex_items:
                        field_hex = data_hex_items
                        field_bytes = data_bytes
                        # 将raw_hex_string转换为字节并添加到raw_bytes
                        if data_raw_hex:
                            try:
                                data_bytes_obj = bytes.fromhex(data_raw_hex)
                                raw_bytes.extend(data_bytes_obj)
                            except ValueError:
                                pass
                        segment_lengths.extend(data_segments)
                elif dtype.endswith("_ARRAY"):
                    base_dtype = dtype[:-6]
                    base_dtype = base_dtype.upper()
                    values = split_array_values(raw_value)
                    for item in values:
                        chunk = scalar_value_to_bytes(base_dtype, item, display_big_endian)
                        if not chunk:
                            continue
                        if is_little_endian and base_dtype in LITTLE_ENDIAN_WORD_SWAP_DTYPES:
                            chunk = swap_16bit_words_for_little_endian(chunk)
                        raw_bytes.extend(chunk)
                        chunk_words = bytes_to_hex_words(chunk, display_big_endian)
                        field_hex.extend(chunk_words)
                        if chunk_words:
                            field_bytes += len(chunk)
                            segment_lengths.append(len(chunk_words))
                else:
                    dtype_upper = dtype.upper()
                    chunk = scalar_value_to_bytes(dtype_upper, raw_value, display_big_endian)
                    if chunk:
                        if is_little_endian and dtype_upper in LITTLE_ENDIAN_WORD_SWAP_DTYPES:
                            chunk = swap_16bit_words_for_little_endian(chunk)
                        raw_bytes.extend(chunk)
                        chunk_words = bytes_to_hex_words(chunk, display_big_endian)
                        field_hex.extend(chunk_words)
                        if chunk_words:
                            field_bytes += len(chunk)
                            segment_lengths.append(len(chunk_words))

                # 记录时间字段的位置和长度
                if element == "时间" and field_hex:
                    time_field_index = len(hex_items)
                    time_field_length = len(field_hex)

                if field_hex:
                    hex_items.extend(field_hex)
                    total_bytes += field_bytes

            # 特殊处理时间字段：如果是小端序，交换前4个和后4个字符（前两个16位值和后两个16位值）
            if time_field_index >= 0 and time_field_length > 0 and not display_big_endian:
                # 时间字段是32位（4字节），即2个16位值，需要交换它们
                if time_field_length == 2 and time_field_index + 1 < len(hex_items):
                    # 交换两个16位值
                    hex_items[time_field_index], hex_items[time_field_index + 1] = \
                        hex_items[time_field_index + 1], hex_items[time_field_index]
                elif time_field_length > 2:
                    # 如果时间字段超过2个16位值，交换前一半和后一半
                    half = time_field_length // 2
                    for i in range(half):
                        if time_field_index + i < len(hex_items) and time_field_index + time_field_length - 1 - i < len(hex_items):
                            hex_items[time_field_index + i], hex_items[time_field_index + time_field_length - 1 - i] = \
                                hex_items[time_field_index + time_field_length - 1 - i], hex_items[time_field_index + i]

            if template.get("merge_8bit_to_16bit", True) and hex_items:
                hex_items = merge_adjacent_byte_tokens(hex_items)

            raw_hex_string = "".join(_strip_hex_prefix(tok) for tok in hex_items if tok).upper()
            total_bytes = len(raw_hex_string) // 2
            segment_lengths = [1] * len(hex_items)
                
            
            return hex_items, total_bytes, raw_hex_string, segment_lengths

        # 分类并导出
        non_period_nc = {}  # key=(recip_site, sub_address, msg_len) -> list of (time, hexlist)
        period_nc = {}
        non_period_nt_lines = []  # (time, desc, hexlist)
        period_nt = {}

        def get_int(d, k, default=0):
            try:
                v = d.get(k, default)
                return int(v)
            except Exception:
                return default
        
        def get_int_or_parse_hex(d, k, default=0):
            """获取整数值，如果是字符串且为16进制格式则解析（支持全角乘号×）"""
            try:
                v = d.get(k, default)
                print(f"get_int_or_parse_hex: k={k}, v={v}, type={type(v).__name__}")
                if isinstance(v, str):
                    # 处理全角乘号×（U+00D7）和全角Ｘ（U+FF38），统一转换为小写x
                    v_str = v.strip()
                    if not v_str:
                        print("  值为空，返回默认")
                        return default
                    # 替换全角乘号×为半角x
                    v_str = v_str.replace('×', 'x').replace('Ｘ', 'x').replace('×', 'x')
                    v_str = v_str.lower()
                    print(f"  处理后: '{v_str}'")
                    if v_str.startswith('0x'):
                        result = int(v_str, 16)
                        print(f"  解析16进制 '{v_str}' -> {result}")
                        return result
                    elif 'x' in v_str:
                        # 如果有x但没0x前缀（如"×15"或"0×15"），尝试添加0x前缀后解析
                        # 移除所有的x和开头的0
                        hex_part = v_str.replace('x', '').replace('X', '')
                        # 如果开头有0，去掉（因为我们要添加0x）
                        if hex_part.startswith('0'):
                            hex_part = hex_part[1:]
                        v_str = '0x' + hex_part
                        result = int(v_str, 16)
                        print(f"  解析16进制（添加前缀） '{v_str}' -> {result}")
                        return result
                    else:
                        # 尝试解析为整数（十进制）
                        result = int(v_str)
                        print(f"  解析十进制 '{v_str}' -> {result}")
                        return result
                else:
                    result = int(v)
                    print(f"  直接转换 {v} -> {result}")
                    return result
            except Exception as e:
                print(f"get_int_or_parse_hex 解析失败: k={k}, v={v}, error={e}")
                return default
        
        def format_recip_for_filename(recip_value):
            """格式化recip_site用于文件名（16进制格式）"""
            if isinstance(recip_value, str):
                recip_str = recip_value.strip().lower()
                if recip_str.startswith('0x'):
                    recip_int = int(recip_str, 16)
                else:
                    try:
                        recip_int = int(recip_str, 16)
                    except ValueError:
                        recip_int = int(recip_str)
            else:
                recip_int = int(recip_value)
            return f"0x{recip_int:03X}"
        
        def format_subaddr_for_filename(subaddr_value):
            """格式化sub_address用于文件名（十进制格式，无0x前缀）"""
            if isinstance(subaddr_value, str):
                subaddr_str = subaddr_value.strip().lower()
                if subaddr_str.startswith('0x'):
                    subaddr_int = int(subaddr_str, 16)
                else:
                    subaddr_int = int(subaddr_str)
            else:
                subaddr_int = int(subaddr_value)
            return f"{subaddr_int:02d}"

        def to_time3(x):
            try:
                return float(x)
            except Exception:
                return 0.0

        def normalize_hex_items(data_region, msg_len, big_endian, defer_little_endian=False):
            # 将 data_region 标准化为十六进制标记列表（0x前缀）。
            # 支持 union 列表、JSON 字符串等来源；按数据类型区分：
            # - UINT8/16/32: 固定宽度的十六进制单标记（0xXX/0xXXXX/0xXXXXXXXX）
            # - INT8/16/32: 以补码形式输出固定宽度十六进制单标记
            # - FLOAT32/64: 以配置端序输出为若干 0xXX 标记（大端='>'，小端='<'）
            # - BOOL: 0x01/0x00
            # - STR: 若已是以空格分隔的 0x.. 序列则直接拆分，否则按UTF-8字节输出 0xXX 序列
            import html
            import struct as _struct
            import json as _json
            from typing import Any
            try:
                import models.step_model as step_model
            except Exception:
                step_model = None

            display_big_endian = True if defer_little_endian else big_endian
            is_little_endian = not big_endian
            endian_prefix = '>' if display_big_endian else '<'

            def to_int(val: Any) -> int:
                if isinstance(val, (int, float)):
                    return int(val)
                if isinstance(val, str):
                    s = val.strip().lower()
                    if s.startswith('0x'):
                        return int(s, 16)
                    try:
                        return int(float(s))
                    except Exception:
                        return 0
                return 0

            def value_to_bytes(val: Any, dtype_str: str, big_endian: bool) -> bytes:
                """将值转换为字节数组，考虑端序"""
                u = dtype_str.upper()
                endian_prefix_local = '>' if big_endian else '<'
                try:
                    if u in ("UINT8", "INT8"):
                        return bytes([val & 0xFF])
                    elif u in ("UINT16", "INT16"):
                        val = val & 0xFFFF
                        if big_endian:
                            return bytes([val >> 8, val & 0xFF])
                        else:
                            return bytes([val & 0xFF, val >> 8])
                    elif u in ("UINT32", "INT32"):
                        val = val & 0xFFFFFFFF
                        if big_endian:
                            return bytes([val >> 24, (val >> 16) & 0xFF, (val >> 8) & 0xFF, val & 0xFF])
                        else:
                            return bytes([val & 0xFF, (val >> 8) & 0xFF, (val >> 16) & 0xFF, val >> 24])
                    elif u in ("FLOAT32", "REAL32", "FLOAT", "REAL"):
                        if isinstance(val, str):
                            s_val = val.strip().lower()
                        if s_val.startswith("0x"):
                            try:
                                bits = int(s_val, 16) & 0xFFFFFFFF
                                return bits.to_bytes(4, byteorder='big' if big_endian else 'little')
                            except ValueError:
                                pass
                        fv = float(val) if val is not None else 0.0
                        return _struct.pack(endian_prefix_local + 'f', fv)
                    elif u in ("FLOAT64", "REAL64", "DOUBLE"):
                        if isinstance(val, str):
                            s_val = val.strip().lower()
                        if s_val.startswith("0x"):
                            try:
                                bits = int(s_val, 16) & 0xFFFFFFFFFFFFFFFF
                                return bits.to_bytes(8, byteorder='big' if big_endian else 'little')
                            except ValueError:
                                pass
                        fv = float(val) if val is not None else 0.0
                        return _struct.pack(endian_prefix_local + 'd', fv)
                    elif u in ("BOOL", "BOOLEAN"):
                        iv = 1 if (str(val).strip().lower() in ("1", "true", "yes")) else 0
                        return bytes([iv])
                    elif u in ("STR", "STRING"):
                        s = str(val) if val is not None else ""
                        parts = [p for p in s.split() if p]
                        if parts and all(p.lower().startswith('0x') for p in parts):
                            # 解析十六进制字符串
                            result = []
                            for part in parts:
                                hex_val = int(part, 16)
                                if hex_val <= 0xFF:
                                    result.append(hex_val)
                                else:
                                    # 大于255的值按16位处理
                                    result.extend([hex_val >> 8, hex_val & 0xFF])
                            return bytes(result)
                        else:
                            return s.encode('utf-8')
                    else:
                        # 默认按16位处理
                        val = val & 0xFFFF
                        if big_endian:
                            return bytes([val >> 8, val & 0xFF])
                        else:
                            return bytes([val & 0xFF, val >> 8])
                except Exception:
                    return bytes([0])

            def bytes_to_hex_list(b: bytes):
                # 按16位（2字节）分组输出，最后一个字节单独输出；
                # 大端：高字节在前；小端：低字节在前（以16位为单位解释端序）
                result = []
                for i in range(0, len(b), 2):
                    if i + 1 < len(b):
                        if display_big_endian:
                            val = (b[i] << 8) | b[i + 1]
                        else:
                            # 小端按16位单位解释：低字节在前，从而对32/64位类型自然呈现为低16位在前
                            val = b[i] | (b[i + 1] << 8)
                        result.append(f"0x{val:04X}")
                    else:
                        result.append(f"0x{b[i]:02X}")
                return result

            # 归一化得到 union 列表
            union_list = []
            source_type = "normalized"
            raw_hex_string = ""
            segment_lengths = []
            if data_region is None:
                return [], 0, source_type, raw_hex_string, []
            if isinstance(data_region, list):
                if data_region and all(isinstance(item, str) for item in data_region):
                    raw_hex_string = "".join(_strip_hex_prefix(item) for item in data_region if item).upper()
                    segments = [1] * len(data_region)
                    return data_region, len(raw_hex_string) // 2, "raw_hex", raw_hex_string, segments
                union_list = data_region
            elif isinstance(data_region, str):
                s = data_region.strip()
                if not s:
                    return [], 0, source_type, raw_hex_string, []
                # 可能是 JSON
                decoded = html.unescape(s)
                try:
                    obj = _json.loads(decoded)
                    if isinstance(obj, list):
                        union_list = obj
                    else:
                        parts = [p for p in s.split() if p]
                        if all(p.lower().startswith('0x') for p in parts):
                            raw_hex_string = "".join(_strip_hex_prefix(p) for p in parts if p).upper()
                            segments = [1] * len(parts)
                            return parts, len(raw_hex_string) // 2, "raw_hex", raw_hex_string, segments
                        raw_bytes = s.encode('utf-8')
                        raw_hex_string = raw_bytes.hex().upper()
                        raw_tokens = bytes_to_hex_list(raw_bytes)
                        segments = [1] * len(raw_tokens)
                        return raw_tokens, len(raw_bytes), source_type, raw_hex_string, segments
                except Exception:
                    parts = [p for p in s.split() if p]
                    if all(p.lower().startswith('0x') for p in parts):
                        raw_hex_string = "".join(_strip_hex_prefix(p) for p in parts if p).upper()
                        segments = [1] * len(parts)
                        return parts, len(raw_hex_string) // 2, "raw_hex", raw_hex_string, segments
                    raw_bytes = s.encode('utf-8')
                    raw_hex_string = raw_bytes.hex().upper()
                    raw_tokens = bytes_to_hex_list(raw_bytes)
                    segments = [1] * len(raw_tokens)
                    return raw_tokens, len(raw_bytes), source_type, raw_hex_string, segments
            else:
                return [], 0, source_type, raw_hex_string, []

            # 紧凑型存储：将所有数据转换为字节流，然后按16位分组显示
            byte_stream = bytearray()
            hex_items = []
            total_bytes = 0

            def append_and_track(chunk_bytes):
                nonlocal total_bytes
                if not chunk_bytes:
                    return
                byte_stream.extend(chunk_bytes)
                total_bytes += len(chunk_bytes)
                words = bytes_to_hex_list(chunk_bytes)
                if words:
                    hex_items.extend(words)
                    segment_lengths.append(len(words))

            for item in union_list:
                if not isinstance(item, dict):
                    continue
                dtype_idx = item.get('data_type')
                value = item.get('value')
                dtype_str = None
                if step_model is not None:
                    try:
                        dtype_str = step_model.SUPPORTED_DTYPES[dtype_idx] if isinstance(dtype_idx, int) and 0 <= dtype_idx < len(step_model.SUPPORTED_DTYPES) else None
                    except Exception:
                        dtype_str = None
                if not dtype_str:
                    dtype_str = "UINT8"

                u = dtype_str.upper()
                try:
                    # 根据数据类型选择正确的转换方式
                    if u in ("FLOAT32", "REAL32", "FLOAT", "REAL", "FLOAT64", "REAL64", "DOUBLE"):
                        item_bytes = None
                        converted_display = value
                        if isinstance(value, str):
                            s_val = value.strip().lower()
                            if s_val.startswith("0x"):
                                hex_part = s_val[2:]
                                expected_bits = 32 if u in ("FLOAT32", "REAL32", "FLOAT", "REAL") else 64
                                expected_bytes = expected_bits // 8
                                try:
                                    bits_val = int(hex_part, 16) & ((1 << expected_bits) - 1)
                                    byteorder = 'big' if display_big_endian else 'little'
                                    item_bytes = bits_val.to_bytes(expected_bytes, byteorder=byteorder, signed=False)
                                    converted_display = f"0x{hex_part.upper()}"
                                except ValueError:
                                    item_bytes = None
                        if item_bytes is None:
                            try:
                                converted_value = float(value) if value is not None else 0.0
                            except (TypeError, ValueError):
                                converted_value = 0.0
                            converted_display = converted_value
                            endian_prefix_local = '>' if display_big_endian else '<'
                            fmt = 'f' if u in ("FLOAT32", "REAL32", "FLOAT", "REAL") else 'd'
                            item_bytes = _struct.pack(endian_prefix_local + fmt, converted_value)
                        print(f"    处理 {u}: 原始值={value}, 转换后={converted_display}")
                    else:
                        # 整数类型使用to_int转换
                        iv = to_int(value)
                        print(f"    处理 {u}: 原始值={value}, 转换后={iv}")
                        item_bytes = value_to_bytes(iv, dtype_str, display_big_endian)
                    if is_little_endian and u in LITTLE_ENDIAN_WORD_SWAP_DTYPES:
                        item_bytes = swap_16bit_words_for_little_endian(item_bytes)

                    append_and_track(item_bytes)
                    print(f"    字节: {item_bytes.hex()}")
                except Exception as err:
                    print(f"    处理 {u} 时出错，使用默认值0，错误: {err}")
                    append_and_track(bytes([0]))

            # 将字节流转换为十六进制显示
            raw_hex_string = byte_stream.hex().upper()

            display_hex_items = format_hex_items_for_output(hex_items)
            
            print(f"    最终字节流: {byte_stream.hex()}")
            print(f"    最终显示: {display_hex_items}")
            print(f"    总字节数: {total_bytes}")

            return hex_items, total_bytes, source_type, raw_hex_string, segment_lengths

        def read_hex_sequences_from_files(path_field, msg_len):
            """从 file_path 指定的一个或多个文件读取HEX行，返回 List[List[str]]"""
            seqs = []
            if not path_field:
                return seqs
            # 支持以 ; 或 , 分隔的多个文件
            parts = []
            if isinstance(path_field, str):
                parts = [p.strip() for p in path_field.replace("\n", ",").split(",") if p.strip()]
            elif isinstance(path_field, (list, tuple)):
                parts = [str(p).strip() for p in path_field if str(p).strip()]
            for p in parts:
                try:
                    with open(p, 'r', encoding='utf-8', errors='ignore') as fh:
                        for line in fh:
                            s = line.strip()
                            if not s:
                                continue
                            # 解析一行HEX
                            s = s.replace("\t", " ").replace(",", " ")
                            s = s.replace("0x", "").replace("0X", "")
                            s = "".join(s.split())
                            # 按16位（4个字符）分组，最后一个字节不补零
                            row = []
                            for i in range(0, len(s), 4):
                                if i + 4 <= len(s):
                                    # 完整的16位
                                    row.append(f"0x{s[i:i+4].upper()}")
                                else:
                                    # 最后一个不完整的字节，不补零
                                    remaining = s[i:]
                                    if len(remaining) == 2:
                                        row.append(f"0x{remaining.upper()}")
                                    elif len(remaining) == 1:
                                        row.append(f"0x{remaining.upper()}")
                        if msg_len and isinstance(msg_len, int) and msg_len > 0:
                            row = row[:msg_len]
                        if row:
                            seqs.append(row)
                except Exception:
                    continue
            return seqs

        def build_meta_columns(base, type_data):
            cols = []
            # base 关键信息
            if 'name' in base: cols.append(f"name={base.get('name')}")
            if 'step_type' in base: cols.append(f"step_type={base.get('step_type')}")
            if 'is_ignore' in base: cols.append(f"is_ignore={base.get('is_ignore')}")
            if 'endian' in base: cols.append(f"endian={base.get('endian')}")
            # type 关键信息
            for key in ('site_type','local_site','recip_site','sub_address','msg_len','protocol_type'):
                if key in type_data:
                    cols.append(f"{key}={type_data.get(key)}")
            return cols

        def iter_period_lines(base_time, period_value, sequences, default_hex):
            """生成周期行，若文件包含多行则依次按周期累加时间，否则仅使用默认数据。"""
            if sequences:
                for idx, seq in enumerate(sequences):
                    yield base_time + period_value * idx, seq, idx  # 返回时间、序列和行索引
            else:
                yield base_time, default_hex, 0  # 返回时间、默认序列和行索引0

        def prepare_step_payload(step, non_types, per_types):
            base = step.get_base_step_data() or {}
            type_data = step.get_type_step_data() or {}
            stype = step.get_step_type()

            is_non_step = stype in non_types
            is_per_step = stype in per_types
            if not (is_non_step or is_per_step):
                return None

            if get_int(base, 'is_ignore', 0) == 1:
                return None

            # 获取通用字段
            site_type = get_int(type_data, 'site_type', 0)
            recip = get_int_or_parse_hex(type_data, 'recip_site', 0)
            sub_addr = get_int_or_parse_hex(type_data, 'sub_address', 0)
            msg_len = get_int(type_data, 'msg_len', 0)
            data_region = type_data.get('data_region')
            file_path_field = type_data.get('file_path')
            file_hex_sequences = None
            
            # 获取开关量协议特定字段
            address = get_int_or_parse_hex(type_data, 'address', None)
            switch_type = get_int(type_data, 'switch_type', 8)
            switch_value = get_int(type_data, 'switch_value', 0)

            # 如果是开关量协议，直接返回基本信息，不需要处理hex数据
            if stype == 6:  # switch_quantity_fileds
                payload = {
                    "step": step,
                    "base": base,
                    "type_data": type_data,
                    "is_non_step": is_non_step,
                    "is_per_step": is_per_step,
                    "address": address,
                    "switch_type": switch_type,
                    "switch_value": switch_value,
                    "hex_items": [],
                    "file_hex_sequences": None,
                    "actual_byte_len": 0,
                    "base_time": to_time3(base.get('time', 0.0)),
                    "period_value": to_time3(type_data.get('period', 0.0)),
                    "serial_id": 0
                }
                return payload

            # 其他协议的处理逻辑
            is_big_endian = base.get('endian', 0) == 0
            hex_items, data_bytes, hex_source, raw_hex_string, hex_segments = normalize_hex_items(
                data_region,
                msg_len,
                is_big_endian,
                defer_little_endian=not is_big_endian
            )

            if not hex_items and file_path_field:
                file_hex_seqs = read_hex_sequences_from_files(file_path_field, msg_len)
                if file_hex_seqs:
                    file_hex_sequences = file_hex_seqs
                    hex_items = file_hex_seqs[0]
                    data_bytes = len(hex_items) * 2
                    hex_source = "raw_hex"
                    raw_hex_string = "".join(_strip_hex_prefix(tok) for tok in hex_items if tok).upper()
                    hex_segments = [1] * len(hex_items)

            proto_type_raw = type_data.get('protocol_type', -1)
            try:
                proto_type_val = int(proto_type_raw)
            except (TypeError, ValueError):
                proto_type_val = -1
            if proto_type_val is not None and proto_type_val >= 0:
                protocol_hex_items, protocol_bytes, protocol_raw_hex, protocol_segments = convert_template_fields_to_hex(
                    step,
                    proto_type_val,
                    is_big_endian,
                    defer_little_endian=not is_big_endian
                )
                if protocol_hex_items:
                    hex_items = protocol_hex_items
                    data_bytes = protocol_bytes
                    hex_source = "normalized"
                    raw_hex_string = protocol_raw_hex
                    hex_segments = protocol_segments

            if hex_items:
                msg_len = len(hex_items)
            elif msg_len > 0:
                hex_items = ["0x0000"] * msg_len
                data_bytes = msg_len * 2
                raw_hex_string = "0000" * msg_len
                hex_segments = [1] * len(hex_items)

            actual_byte_len = data_bytes

            if file_hex_sequences:
                file_hex_sequences = [
                    format_hex_items_for_output(seq) for seq in file_hex_sequences
                ]

            if hex_items:
                hex_items = format_hex_items_for_output(hex_items)

            payload = {
                "step": step,
                "base": base,
                "type_data": type_data,
                "is_non_step": is_non_step,
                "is_per_step": is_per_step,
                "site_type": site_type,
                "recip": recip,
                "sub_addr": sub_addr,
                "hex_items": hex_items,
                "file_hex_sequences": file_hex_sequences,
                "actual_byte_len": actual_byte_len,
                "base_time": to_time3(base.get('time', 0.0)),
                "period_value": to_time3(type_data.get('period', 0.0)),
                "serial_id": get_int(type_data, 'serialID', 0)
            }
            return payload

        def process_interrupt_steps(out_dir):
            """按需求生成中断 port.config 文件"""
            interrupt_non_types = {7}
            interrupt_per_types = {8}
            relevant_types = interrupt_non_types | interrupt_per_types
            relevant_steps = [
                step for step in all_steps if step.get_step_type() in relevant_types
            ]
            if not out_dir or not relevant_steps:
                return None

            os.makedirs(out_dir, exist_ok=True)

            def format_interrupt_display(raw_value):
                if raw_value is None:
                    return "0"
                text = str(raw_value).strip()
                return text if text else "0"

            periodic_map = {}
            periodic_sort_key = {}
            non_periodic_map = {}
            non_periodic_sort_key = {}

            for step in relevant_steps:
                base = step.get_base_step_data() or {}
                if get_int(base, "is_ignore", 0) == 1:
                    continue
                type_data = step.get_type_step_data() or {}
                interrupt_raw = type_data.get("interrupt_num")
                interrupt_display = format_interrupt_display(interrupt_raw)
                interrupt_int = get_int_or_parse_hex(
                    {"interrupt_num": interrupt_raw}, "interrupt_num", 0
                )
                step_type = step.get_step_type()

                if step_type in interrupt_per_types:
                    period_value = to_time3(type_data.get("period", 0.0))
                    period_ms = int(round(period_value * 1000))
                    if period_ms < 0:
                        period_ms = 0
                    periodic_map[interrupt_display] = period_ms
                    periodic_sort_key[interrupt_display] = interrupt_int
                else:
                    time_value = to_time3(base.get("time", 0.0))
                    time_ms = int(round(time_value * 1000))
                    if time_ms < 0:
                        time_ms = 0
                    non_periodic_map.setdefault(interrupt_display, []).append(time_ms)
                    non_periodic_sort_key[interrupt_display] = interrupt_int

            def _format_comment_text(int_key, times_ms):
                if not times_ms:
                    return "；仿真时间10s时触发90号中断"
                first_time_ms = min(times_ms)
                seconds_str = f"{first_time_ms/1000:g}"
                return f"；仿真时间{seconds_str}s时触发{int_key}号中断"

            periodic_lines = [
                "#对中断周期的配置,注意此处只需要配周期性中断，其余均认为是非周期中断",
                "",
                "#中断号=周期值(ms)",
                "",
                "[INT_PERIOD]"
            ]
            if periodic_map:
                for key in sorted(periodic_map.keys(), key=lambda k: (periodic_sort_key.get(k, 0), k)):
                    periodic_lines.append(f"{key}={periodic_map[key]}")
            periodic_lines.append("")
            periodic_lines.append("#忽略的中断号")
            periodic_lines.append("")
            periodic_lines.append("[IGNORE_INT]")
            periodic_lines.append("")
            periodic_lines.append("；核间通信中断")
            periodic_lines.append("")

            non_periodic_lines = [
                "#单次触发中断配置#对于数据触发的中断可在底层驱动中通过读文件控制数据何时到来，不在此处配置",
                "",
                "#中断号=触发时间(ms)",
                "",
                "[ISINGLE_TRIGGER_INTJ]"
            ]

            if non_periodic_map:
                first_key = min(non_periodic_map.keys(), key=lambda k: (non_periodic_sort_key.get(k, 0), k))
                comment_line = _format_comment_text(first_key, non_periodic_map[first_key])
            else:
                comment_line = "；仿真时间10s时触发90号中断"
            non_periodic_lines.append(comment_line)

            if non_periodic_map:
                for key in sorted(non_periodic_map.keys(), key=lambda k: (non_periodic_sort_key.get(k, 0), k)):
                    times = sorted(set(non_periodic_map[key]))
                    times_str = ",".join(str(val) for val in times)
                    non_periodic_lines.append(f"中断：{key}={times_str}")
            else:
                non_periodic_lines.append("中断：")

            port_config_content = "\n".join(periodic_lines + non_periodic_lines).rstrip() + "\n"
            port_config_path = os.path.join(out_dir, "port.config")
            with open(port_config_path, "w", encoding="utf-8") as f:
                f.write(port_config_content)
            return port_config_path

        def process_bus_protocol(protocol_name, spec, payloads, out_dir):
            primary_non = {}
            primary_period = {}
            secondary_non_lines = []
            secondary_period = {}

            for payload in payloads:
                if payload["is_non_step"]:
                    t = payload["base_time"]
                    if payload["site_type"] == 0:
                        key = (payload["recip"], payload["sub_addr"], payload["actual_byte_len"])
                        primary_non.setdefault(key, []).append((t, payload["hex_items"]))
                    else:
                        desc = f"ID0x{payload['recip']:03X}_SA{payload['sub_addr']:02d}_Len{payload['actual_byte_len']}"
                        secondary_non_lines.append((t, desc, payload["hex_items"]))
                else:
                    t = payload["base_time"]
                    period = payload["period_value"]
                    key = (payload["recip"], payload["sub_addr"], payload["actual_byte_len"])
                    target = primary_period if payload["site_type"] == 0 else secondary_period
                    target.setdefault(key, []).append((t, payload["hex_items"], period, payload["file_hex_sequences"]))

            primary_prefix = spec.get("primary_prefix", "Nc")
            secondary_prefix = spec.get("secondary_prefix", "Nt")
            file_pattern = spec.get("file_pattern", "{prefix}Recv_ID0x{recip:03X}_SA{sa:02d}_Len{ln}.txt")
            secondary_non_filename = spec.get("secondary_non_filename") or f"{secondary_prefix}Recv_NonPeriod.txt"

            print(f"\n[{protocol_name}] 分类结果:")
            print(f"  {primary_prefix} 非周期: {len(primary_non)} 个文件")
            print(f"  {primary_prefix} 周期: {len(primary_period)} 个文件")
            print(f"  {secondary_prefix} 非周期: {len(secondary_non_lines)} 行")
            print(f"  {secondary_prefix} 周期: {len(secondary_period)} 个文件")

            def write_primary_files(container, prefix_label):
                for (recip, sa, ln), rows in container.items():
                    rows.sort(key=lambda x: x[0])
                    fname = file_pattern.format(prefix=prefix_label, recip=recip, sa=sa, ln=ln)
                    fpath = os.path.join(out_dir, fname)
                    try:
                        with open(fpath, 'w', encoding='utf-8') as f:
                            for record in rows:
                                if len(record) == 2:
                                    t, hexlist = record
                                    line = f"{t:.3f}"
                                    if hexlist:
                                        line += "\t" + "\t".join(hexlist)
                                    f.write(line + "\n")
                                else:
                                    t, hexlist, period, sequences = record
                                    for time_val, seq, line_idx in iter_period_lines(t, period, sequences, hexlist):
                                        # 对于周期GLINK的每行，重新计算时间戳、帧计数和CRC
                                        modified_seq = seq.copy()
                                        
                                        # 1. 更新时间戳字段（索引0-1，UINT32拆分为两个UINT16）
                                        if len(modified_seq) > 1:
                                            # 将time_val转换为毫秒并取整
                                            timestamp_ms = int(round(time_val * 1000))
                                            # 拆分UINT32为两个UINT16（低16位和高16位）
                                            time_low = timestamp_ms & 0xFFFF
                                            time_high = (timestamp_ms >> 16) & 0xFFFF
                                            # 更新时间戳字段
                                            modified_seq[0] = f"0x{time_high:04X}"
                                            modified_seq[1] = f"0x{time_low:04X}"
                                        
                                        # 2. 更新帧计数字段（索引4）
                                        if len(modified_seq) > 4:
                                            # 计算帧计数：行索引+1，确保在0x0000-0xFFFF范围内
                                            frame_count = (line_idx + 1) & 0xFFFF
                                            modified_seq[4] = f"0x{frame_count:04X}"
                                        
                                        # 3. 重新计算CRC校验和（如果需要）
                                        if len(modified_seq) > 5:
                                            # 提取数据区（从索引5开始到倒数第二个元素）
                                            data_region = modified_seq[5:-1] if len(modified_seq) > 6 else []
                                            # 将数据区转换为字符串
                                            data_region_str = " ".join(data_region)
                                            # 计算CRC
                                            special_metrics = calc_crc_tail_metrics(data_region_str)
                                            crc_value = special_metrics.get("overrides", {}).get("数据区crc校验和", "0x0000")
                                            # 更新CRC字段
                                            modified_seq[-1] = crc_value
                                        
                                        line = f"{time_val:.3f}"
                                        if modified_seq:
                                            line += "\t" + "\t".join(modified_seq)
                                        f.write(line + "\n")
                        print(f"  [{protocol_name}] 写入文件: {fname}")
                    except PermissionError:
                        print(f"  [{protocol_name}] 权限错误，跳过文件: {fname}")
                    except Exception as exc:
                        print(f"  [{protocol_name}] 写入文件 {fname} 时出错: {exc}")

            write_primary_files(primary_non, primary_prefix)
            write_primary_files(primary_period, primary_prefix)

            if secondary_non_lines:
                secondary_non_lines.sort(key=lambda x: x[0])
                fpath = os.path.join(out_dir, secondary_non_filename)
                try:
                    with open(fpath, 'w', encoding='utf-8') as f:
                        for t, desc, hexlist in secondary_non_lines:
                            line = f"{t:.3f}\t{desc}"
                            if hexlist:
                                line += "\t" + "\t".join(hexlist)
                            f.write(line + "\n")
                    print(f"  [{protocol_name}] 写入文件: {secondary_non_filename}")
                except PermissionError:
                    print(f"  [{protocol_name}] 权限错误，跳过文件: {secondary_non_filename}")
                except Exception as exc:
                    print(f"  [{protocol_name}] 写入文件 {secondary_non_filename} 时出错: {exc}")

            if secondary_period:
                write_primary_files(secondary_period, secondary_prefix)

            return out_dir

        def process_uart_protocol(protocol_name, spec, payloads, out_dir):
            non_pattern = spec.get("non_file_pattern", "Uart_NonPeriod_recv_Com_ADD_{addr}.txt")
            per_pattern = spec.get("per_file_pattern", "Uart_Period_recv_Com_ADD_{addr}.txt")
            group_non = {}
            group_period = {}

            for payload in payloads:
                serial_id_val = payload.get("serial_id")
                if serial_id_val is None:
                    print(f"[{protocol_name}] 步骤缺少串口号，已跳过: step={payload.get('step')}")
                    continue
                addr_str = f"{int(serial_id_val):02d}"

                if payload["is_non_step"]:
                    group_non.setdefault(addr_str, []).append((payload["base_time"], payload["hex_items"]))
                else:
                    group_period.setdefault(addr_str, []).append(
                        (payload["base_time"], payload["hex_items"], payload["period_value"], payload["file_hex_sequences"])
                    )

            print(f"\n[{protocol_name}] 分类结果:")
            print(f"  非周期基地址文件: {len(group_non)} 个")
            print(f"  周期基地址文件: {len(group_period)} 个")

            for addr, rows in group_non.items():
                rows.sort(key=lambda x: x[0])
                fname = non_pattern.format(addr=addr)
                fpath = os.path.join(out_dir, fname)
                try:
                    with open(fpath, 'w', encoding='utf-8') as f:
                        for t, hexlist in rows:
                            line = f"{t:.3f}"
                            if hexlist:
                                line += "\t" + "\t".join(hexlist)
                            f.write(line + "\n")
                    print(f"  [{protocol_name}] 写入文件: {fname}")
                except PermissionError:
                    print(f"  [{protocol_name}] 权限错误，跳过文件: {fname}")
                except Exception as exc:
                    print(f"  [{protocol_name}] 写入文件 {fname} 时出错: {exc}")

            for addr, rows in group_period.items():
                rows.sort(key=lambda x: x[0])
                fname = per_pattern.format(addr=addr)
                fpath = os.path.join(out_dir, fname)
                try:
                    with open(fpath, 'w', encoding='utf-8') as f:
                        for t, hexlist, period, sequences in rows:
                            for time_val, seq in iter_period_lines(t, period, sequences, hexlist):
                                line = f"{time_val:.3f}"
                                if seq:
                                    line += "\t" + "\t".join(seq)
                                f.write(line + "\n")
                    print(f"  [{protocol_name}] 写入文件: {fname}")
                except PermissionError:
                    print(f"  [{protocol_name}] 权限错误，跳过文件: {fname}")
                except Exception as exc:
                    print(f"  [{protocol_name}] 写入文件 {fname} 时出错: {exc}")

            if not group_non and not group_period:
                return None
            return out_dir

        protocol_specs = [
            {
                "protocol_key": "glink",
                "display_name": "GLINK",
                "step_types": {"non": {0}, "per": {1}},
                "primary_prefix": "Nc",
                "secondary_prefix": "Nt",
                "secondary_non_filename": "NtRecv_NonPeriod.txt",
                "strict_path": True,
                "mode": "bus"
            },
            {
                "protocol_key": "bc",
                "display_name": "1553-BC",
                "step_types": {"non": {4}, "per": {5}},
                "primary_prefix": "Bc",
                "secondary_prefix": "Bt",
                "secondary_non_filename": "BtRecv_NonPeriod.txt",
                "strict_path": True,
                "mode": "bus"
            },
            {
                "protocol_key": "uart",
                "display_name": "串口",
                "step_types": {"non": {2}, "per": {3}},
                "non_file_pattern": "Uart_NonPeriod_recv_Com_ADD_{addr}.txt",
                "per_file_pattern": "Uart_Period_recv_Com_ADD_{addr}.txt",
                "strict_path": True,
                "mode": "uart"
            },
            {
                "protocol_key": "switch",
                "display_name": "开关量",
                "step_types": {"non": {6}, "per": set()},
                "non_file_pattern": "Switch_NonPeriod_{addr}.txt",
                "strict_path": True,
                "mode": "switch"
            }
        ]

        def process_switch_protocol(protocol_name, spec, payloads, out_dir):
            """处理开关量协议的导出逻辑"""
            non_pattern = spec.get("non_file_pattern", "Switch_NonPeriod_{addr}.txt")
            
            # 按地址分组数据
            group_non = {}
            
            for payload in payloads:
                address = payload.get("address")
                if address is None:
                    print(f"[{protocol_name}] 步骤缺少地址，已跳过: step={payload.get('step')}")
                    continue
                
                addr_str = f"{int(address):02x}"  # 地址转换为两位十六进制字符串
                
                if payload["is_non_step"]:
                    group_non.setdefault(addr_str, []).append((payload["base_time"], payload["hex_items"], payload.get("switch_value", 0), payload.get("switch_type", 8)))
            
            print(f"\n[{protocol_name}] 分类结果:")
            print(f"  非周期地址文件: {len(group_non)} 个")
            
            for addr, rows in group_non.items():
                rows.sort(key=lambda x: x[0])
                fname = non_pattern.format(addr=addr)
                fpath = os.path.join(out_dir, fname)
                try:
                    with open(fpath, 'w', encoding='utf-8') as f:
                        for t, hexlist, switch_value, switch_type in rows:
                            line = f"{t:.3f}"
                            # 根据switch_type将switch_value转换为对应的十六进制格式
                            if switch_type == 8:
                                hex_value = f"{int(switch_value):02x}"  # 8位开关量，2位十六进制
                            elif switch_type == 16:
                                hex_value = f"{int(switch_value):04x}"  # 16位开关量，4位十六进制
                            elif switch_type == 32:
                                hex_value = f"{int(switch_value):08x}"  # 32位开关量，8位十六进制
                            else:
                                hex_value = f"{int(switch_value):x}"  # 默认格式
                            line += f"\t{hex_value}"
                            f.write(line + "\n")
                    print(f"  [{protocol_name}] 写入文件: {fname}")
                except PermissionError:
                    print(f"  [{protocol_name}] 权限错误，跳过文件: {fname}")
                except Exception as exc:
                    print(f"  [{protocol_name}] 写入文件 {fname} 时出错: {exc}")
            
            return out_dir

        def process_protocol(spec):
            protocol_name = spec.get("display_name", spec.get("protocol_key", "未知协议"))
            protocol_key = spec.get("protocol_key", "")
            out_dir = protocol_dirs.get(protocol_key, "")
            if not out_dir:
                if spec.get("strict_path", False):
                    QMessageBox.warning(
                        self.main_window,
                        "未找到配置",
                        f"请在全局设置中为{protocol_name}配置有效的输出目录"
                    )
                return None
            os.makedirs(out_dir, exist_ok=True)
            clear_txt_files(out_dir)

            step_types = spec.get("step_types", {})
            non_types = set(step_types.get("non", set()))
            per_types = set(step_types.get("per", set()))
            relevant_types = non_types | per_types
            if not relevant_types:
                return None

            relevant_steps = [
                step for step in all_steps if step.get_step_type() in relevant_types
            ]
            if not relevant_steps:
                print(f"{protocol_name}: 无匹配步骤，跳过导出。")
                return None

            payloads = []
            for step in relevant_steps:
                payload = prepare_step_payload(step, non_types, per_types)
                if payload:
                    payloads.append(payload)

            if not payloads:
                print(f"{protocol_name}: 无有效步骤，跳过导出。")
                return None

            mode = spec.get("mode", "bus").lower()
            if mode == "uart":
                return process_uart_protocol(protocol_name, spec, payloads, out_dir)
            elif mode == "switch":
                return process_switch_protocol(protocol_name, spec, payloads, out_dir)
            return process_bus_protocol(protocol_name, spec, payloads, out_dir)

        exported_dirs = []
        for spec in protocol_specs:
            result_dir = process_protocol(spec)
            if result_dir:
                exported_dirs.append((spec.get("display_name", spec.get("protocol_key", "")), result_dir))

        interrupt_result = process_interrupt_steps(interrupt_output_dir)
        if interrupt_result:
            exported_dirs.append(("中断", interrupt_result))

        if exported_dirs:
            summary = "\n".join(f"{name}: {path}" for name, path in exported_dirs)
            QMessageBox.information(self.main_window, "导出完成", f"已导出以下协议文本:\n{summary}")
        else:
            QMessageBox.warning(self.main_window, "未导出文件", "未找到可导出的GLINK/1553-BC/串口步骤，或未配置对应输出目录。")

    def export_steps_to_txt(self, file_path, steps_by_type, include_field_names, field_separator):
        """导出为文本格式"""
        with open(file_path, "w", encoding="utf-8") as f:
            for step_type, steps in steps_by_type.items():
                # 写入步骤类型标题
                f.write(f"=== {step_type} ===\n")
                f.write(f"步骤数量: {len(steps)}\n\n")
                
                for i, step in enumerate(steps):
                    # 写入步骤编号
                    f.write(f"步骤 {i+1}:\n")
                    
                    # 格式化步骤数据
                    line = self.format_step_for_txt(step, include_field_names, field_separator)
                    f.write(line + "\n\n")

    def export_steps_to_hex(self, file_path, steps_by_type, include_field_names, field_separator):
        """导出为16进制格式"""
        with open(file_path, "wb") as f:
            # 写入文件头标识
            header = b"STEP_EXPORT_HEX_FORMAT"
            f.write(struct.pack('I', len(header)))
            f.write(header)
            
            # 写入步骤类型数量
            f.write(struct.pack('I', len(steps_by_type)))
            
            for step_type, steps in steps_by_type.items():
                # 写入步骤类型名称
                type_name = step_type.encode('utf-8')
                f.write(struct.pack('I', len(type_name)))
                f.write(type_name)
                
                # 写入该类型步骤数量
                f.write(struct.pack('I', len(steps)))
                
                for step in steps:
                    # 格式化步骤数据为16进制
                    hex_data = self.format_step_for_hex(step, include_field_names, field_separator)
                    f.write(struct.pack('I', len(hex_data)))
                    f.write(hex_data)

    def format_step_for_txt(self, step, include_field_names=True, field_separator="\t"):
        """根据需求格式化step为txt行"""
        base = step.get_base_step_data()
        type_data = step.get_type_step_data()
        expand = step.get_expand_step_data()
        
        fields = []
        
        # 处理base字段
        for k, v in base.items():
            if include_field_names:
                fields.append(f"{k}:{v}")
            else:
                fields.append(str(v))
        
        # 处理type字段
        for k, v in type_data.items():
            if include_field_names:
                fields.append(f"{k}:{v}")
            else:
                fields.append(str(v))
        
        # 处理expand字段
        for k, v in expand.items():
            if include_field_names:
                fields.append(f"{k}:{v}")
            else:
                fields.append(str(v))
        
        return field_separator.join(fields)

    def format_step_for_hex(self, step, include_field_names=True, field_separator="\t"):
        """格式化step为16进制数据"""
        # 先格式化为文本
        text_line = self.format_step_for_txt(step, include_field_names, field_separator)
        
        # 转换为16进制
        return self.convert_string_to_hex(text_line)
    

    def export_steps_by_type_bak(self):
        """按类型出到txt"""
        # 1. 選擇目錄
        default_dir = self.model.global_params.get("output_path", QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation))
        input_dir = self.model.global_params.get("input_path", QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation))
        # output_dir = self.model.global_params.get("output_path", QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation))
        
        # default_dir = getattr(self, "DEFAULT_CONFIG_DIR", "./configs")
        dir_path = QFileDialog.getExistingDirectory(
            self.main_window,
            "选择流程配置文件目录",
            default_dir
        )
        if not dir_path or not os.path.isdir(input_dir):
            return

        # 2. 遍歷所有xml文件
        steps_by_type = {}
        for root, dirs, files in os.walk(input_dir):
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

    def read_steps_from_xml_bak(self, file_path):
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
                # protocol
                protocol_elem = step_elem.find("protocol")
                if protocol_elem is not None:
                    protocol_dict = {}
                    for child in protocol_elem:
                        protocol_dict[child.tag] = child.text if child.text else ""
                    step.set_protocol_data(protocol_dict)
                steps.append(step)
        return steps

    def format_step_for_txt_bak(self, step):
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
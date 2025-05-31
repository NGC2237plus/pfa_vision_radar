"""
@FileName：   QT_串口助手.py
@Description：裁判系统模拟
@Author：     NGC2237
@Version:     1.0
@Time：       2025/4/26
@Software：   PyCharm
"""
import sys
import struct
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QTextEdit, QGroupBox, QMessageBox, QComboBox, QSpinBox, QGridLayout, QStatusBar
)
from PyQt5.QtCore import QTimer
from RM_serial_py.ser_api import Get_CRC8_Check_Sum, Get_CRC16_Check_Sum


class RadarGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("雷达服务器模拟")
        self.resize(1200, 800)
        self.ser = None
        self.robot_labels = {}
        self.state = 'R'  # 初始
        self.last_data = None
        self.double_vuln_status = 0  # 双倍易伤状态
        self.dart_target = 0  # 飞镖目标
        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.read_serial_data)
        self.timer.start(200)

    def init_ui(self):
        main_layout = QVBoxLayout()

        top_layout = QHBoxLayout()
        self.serial_combo = QComboBox()
        self.refresh_btn = QPushButton("刷新端口")
        self.refresh_btn.clicked.connect(self.refresh_serial_ports)
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(['9600', '19200', '38400', '57600', '115200'])
        self.baud_combo.setCurrentText('115200')
        self.open_btn = QPushButton("打开串口")
        self.open_btn.clicked.connect(self.toggle_serial)
        self.side_combo = QComboBox()
        self.side_combo.addItems(['红方', '蓝方'])
        self.side_combo.currentTextChanged.connect(self.update_side)

        top_layout.addWidget(QLabel("当前阵营:"))
        top_layout.addWidget(self.side_combo)
        top_layout.addWidget(QLabel("串口:"))
        top_layout.addWidget(self.serial_combo)
        top_layout.addWidget(self.refresh_btn)
        top_layout.addWidget(QLabel("波特率:"))
        top_layout.addWidget(self.baud_combo)
        top_layout.addWidget(self.open_btn)
        main_layout.addLayout(top_layout)

        middle_layout = QHBoxLayout()

        # 左侧坐标显示
        left_group = QGroupBox("机器人坐标 (单位：cm)")
        left_layout = QVBoxLayout()
        self.robot_labels = {}
        for name in ['R1', 'R2', 'R3', 'R4', 'R5', 'R7']:
            label = QLabel()
            self.robot_labels[name] = label
            left_layout.addWidget(label)
        self.update_display()
        left_group.setLayout(left_layout)
        middle_layout.addWidget(left_group, 1)

        right_layout = QVBoxLayout()

        # 接收数据区
        receive_group = QGroupBox("接收数据")
        receive_layout = QVBoxLayout()
        self.receive_hex = QTextEdit()
        self.receive_hex.setReadOnly(True)
        self.receive_hex.setStyleSheet("font-family: monospace;")
        receive_layout.addWidget(self.receive_hex)
        receive_group.setLayout(receive_layout)
        right_layout.addWidget(receive_group, 4)

        # 发送数据区
        send_group = QGroupBox("发送数据")
        send_layout = QVBoxLayout()
        self.send_hex = QTextEdit()
        self.send_hex.setReadOnly(True)
        self.send_hex.setStyleSheet("font-family: monospace;")
        send_layout.addWidget(self.send_hex)
        send_group.setLayout(send_layout)
        right_layout.addWidget(send_group, 3)

        middle_layout.addLayout(right_layout, 2)
        main_layout.addLayout(middle_layout)

        # 设置易伤位
        bottom_layout = QHBoxLayout()
        self.checkboxes = {
            'R1': QCheckBox("1号英雄"),
            'R2': QCheckBox("2号工程"),
            'R3': QCheckBox("3号步兵"),
            'R4': QCheckBox("4号步兵"),
            'R7': QCheckBox("哨兵"),
        }
        cb_group = QGroupBox("设置易伤位 (勾选为1)")
        cb_layout = QHBoxLayout()
        for cb in self.checkboxes.values():
            cb.setStyleSheet("QCheckBox { padding: 8px; }")
            cb_layout.addWidget(cb)
        cb_group.setLayout(cb_layout)

        self.send_btn = QPushButton("发送易伤标志 (0x020C)")
        self.send_btn.setStyleSheet("width: 250px;min-width: 250px;")
        self.send_btn.clicked.connect(self.send_vulnerability_flag)

        bottom_layout.addWidget(cb_group, 4)
        bottom_layout.addWidget(self.send_btn, 1)
        # 双倍易伤设置
        double_vuln_layout = QHBoxLayout()
        double_vuln_group = QGroupBox("双倍易伤设置")
        dv_layout = QHBoxLayout()

        self.dv_chance_spin = QSpinBox()
        self.dv_chance_spin.setRange(0, 2)
        self.dv_opponent_cb = QCheckBox("对方正在被触发")

        dv_layout.addWidget(QLabel("机会次数:"))
        dv_layout.addWidget(self.dv_chance_spin)
        dv_layout.addWidget(self.dv_opponent_cb)

        double_vuln_group.setLayout(dv_layout)

        dv_send_btn = QPushButton("发送双倍易伤状态 (0x020E)")
        dv_send_btn.setStyleSheet("max-width: 250px;min-width: 250px;")
        dv_send_btn.clicked.connect(self.send_double_vulnerability)

        double_vuln_layout.addWidget(double_vuln_group, 2)
        double_vuln_layout.addWidget(dv_send_btn, 1)

        # 飞镖目标
        dart_layout = QHBoxLayout()
        dart_group = QGroupBox("飞镖目标设置")
        da_layout = QHBoxLayout()

        self.dart_select_combo = QComboBox()
        self.dart_select_combo.addItems(["未选/前哨", "基地固定", "随机固定", "随机移动"])

        da_layout.addWidget(QLabel("当前目标:"))
        da_layout.addWidget(self.dart_select_combo)

        dart_group.setLayout(da_layout)

        dart_send_btn = QPushButton("发送飞镖目标 (0x0105)")
        dart_send_btn.setStyleSheet("max-width: 250px;min-width: 250px;")
        dart_send_btn.clicked.connect(self.send_dart_target)

        dart_layout.addWidget(dart_group, 1)
        dart_layout.addWidget(dart_send_btn, 1)

        # 接收双倍触发
        self.dart_status_log = QTextEdit()
        self.dart_status_log.setText("等待接收双倍触发信息...")
        self.dart_status_log.setReadOnly(True)

        # 添加 main
        main_layout.addLayout(bottom_layout)
        main_layout.addLayout(double_vuln_layout)
        main_layout.addLayout(dart_layout)
        main_layout.addWidget(self.dart_status_log)

        self.setLayout(main_layout)
        self.refresh_serial_ports()
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid #3A3939;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
            }
            QTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                padding: 5px;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: 1px solid #CCCCCC;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
        """)

    def refresh_serial_ports(self):
        self.serial_combo.clear()
        ports = serial.tools.list_ports.comports()

        for port in ports:
            display_name = f"{port.device} {port.description}".strip()
            self.serial_combo.addItem(display_name, userData=port.device)
            # print(port.description)

    def update_side(self, text):
        """切换阵营时更新显示"""
        self.state = 'R' if text == '红方' else 'B'
        self.update_display()  # 立即更新
        if self.last_data:
            self.update_robot_coords(self.last_data)

    def update_display(self):
        """更新所有坐标显示"""
        color = '#0000FF' if self.state == 'R' else '#FF0000'  # 红方显示蓝色，蓝方显示红色
        prefix = 'B' if self.state == 'R' else 'R'  # 显示对方阵营标识

        for name in self.robot_labels:
            display_name = name.replace('R', prefix)
            label = self.robot_labels[name]

            current_status = "未接收" if label.text() == "" else label.text().split("：")[1]
            label.setText(f"{display_name}：{current_status}")
            label.setStyleSheet(f"""
                color: {color};
                font-size: 30px;
                padding: 1px;
                font-weight: bold;
            """)

    def toggle_serial(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.open_btn.setText("打开串口")
            return

        port = self.serial_combo.currentData()
        baud = int(self.baud_combo.currentText())
        try:
            self.ser = serial.Serial(port, baud, timeout=1)
            self.open_btn.setText("关闭串口")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"串口打开失败: {str(e)}")

    def read_serial_data(self):
        if not self.ser or not self.ser.is_open:
            return

        if self.ser.in_waiting:
            try:
                raw = self.ser.read_all()
                hex_str = " ".join(f"{b:02X}" for b in raw)
                self.receive_hex.append(f"{hex_str}") # 显示数据

                start_idx = raw.find(b'\xA5')
                if start_idx == -1 or len(raw) < start_idx + 23:
                    return

                packet = raw[start_idx:]
                header = packet[:5]
                cmd_id = packet[5:7]

                data_len = int.from_bytes(header[1:3], 'little')
                expected_crc8 = header[4]
                if Get_CRC8_Check_Sum(header[:4], 4) != expected_crc8:
                    return

                data_start = 7
                data_end = data_start + data_len
                data = packet[data_start:data_end]

                crc16_recv = int.from_bytes(packet[data_end:data_end + 2], 'little')
                crc16_calc = Get_CRC16_Check_Sum(packet[:data_end], data_end)
                if crc16_recv != crc16_calc:
                    return

                if cmd_id == b'\x05\x03': # 0x0305 坐标
                    if len(data) >= 24:
                        self.last_data = data  # 保存最新数据
                        self.update_robot_coords(data)
                if cmd_id == b'\x01\x03':  # 0x0301 双倍触发
                    if len(data) >= 7:
                        # 解析数据
                        sub_id=struct.unpack('<H', data[0:2])[0]
                        if sub_id == 0x0121:
                            sender_id = struct.unpack('<H', data[2:4])[0]
                            receive_id=struct.unpack('<H', data[4:6])[0]
                            print(sub_id, sender_id, receive_id)
                            content = data[6]

                            msg=f"双倍触发接收: 发送者ID[{sender_id}] 机会标志[{content}]"
                            self.dart_status_log.append(msg)
            except Exception as e:
                print(f"串口读取错误: {str(e)}")

    def update_robot_coords(self, data):
        names = ['R1', 'R2', 'R3', 'R4', 'R5', 'R7']
        for i, name in enumerate(names):
            x = int.from_bytes(data[i * 4:i * 4 + 2], 'little')
            y = int.from_bytes(data[i * 4 + 2:i * 4 + 4], 'little')

            if self.state == 'R':
                display_name = name.replace('R', 'B')
                color = '#0000FF'
            else:
                display_name = name
                color = '#FF0000'

            if x == 0 and y == 0:
                text = f"{display_name}：未发送"
            else:
                x = min(max(0, x), 2800)
                y = min(max(0, y), 1500)
                text = f"{display_name}：({x}, {y})"

            label = self.robot_labels[name]
            label.setText(text)
            label.setStyleSheet(f"""
                color: {color};
                font-size: 30px;
                padding: 1px;
                font-weight: bold;
            """)
            self.robot_labels[name].setText(text)

    def send_vulnerability_flag(self):
        """发送易伤标志 (0x020C)"""
        if not self.ser or not self.ser.is_open:
            QMessageBox.warning(self, "错误", "串口未打开")
            return

        value = 0
        if self.checkboxes['R1'].isChecked():
            value |= 1 << 0
        if self.checkboxes['R2'].isChecked():
            value |= 1 << 1
        if self.checkboxes['R3'].isChecked():
            value |= 1 << 2
        if self.checkboxes['R4'].isChecked():
            value |= 1 << 3
        if self.checkboxes['R7'].isChecked():
            value |= 1 << 4

        payload = bytearray([value])
        packet = self.build_packet(payload, seq=0x01, cmd_id=[0x02, 0x0C])
        try:
            self.ser.write(packet)
            hex_str = " ".join(f"{b:02X}" for b in packet)
            self.send_hex.append(f"[0x020C] 发送: {hex_str}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"数据发送失败: {str(e)}")

    def send_double_vulnerability(self):
        """发送双倍易伤状态 (0x020E)"""
        if not self.ser or not self.ser.is_open:
            QMessageBox.warning(self, "错误", "串口未打开")
            return

        byte_data = 0
        # 机会次数 (bit 0-1)
        byte_data |= self.dv_chance_spin.value() & 0b11
        # 对方状态 (bit 2)
        if self.dv_opponent_cb.isChecked():
            byte_data |= 0b100

        payload = bytearray([byte_data])
        packet = self.build_packet(payload, seq=0x01, cmd_id=[0x02, 0x0E])

        try:
            self.ser.write(packet)
            hex_str = " ".join(f"{b:02X}" for b in packet)
            self.send_hex.append(f"[0x020E] 发送: {hex_str}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"数据发送失败: {str(e)}")

    def send_dart_target(self):
        """发送飞镖目标 (0x0105)"""
        if not self.ser or not self.ser.is_open:
            QMessageBox.warning(self, "错误", "串口未打开")
            return

        data = bytearray()
        # 字节0：剩余时间
        data.append(10)

        # 字节1
        byte1 = 0
        # bit 0-2：最近击中目标
        hit_target = 1
        byte1 |= hit_target & 0b111
        # bit 3-5：对方被击中次数
        opponent_hit = 1 << 3
        byte1 |= opponent_hit & 0b111000
        # bit 6-7：当前目标
        current_target = self.dart_select_combo.currentIndex() << 6
        byte1 |= current_target & 0b11000000
        data.append(byte1)

        # 字节2：保留
        data.append(0)

        packet = self.build_packet(data, seq=0x01, cmd_id=[0x01, 0x05])

        try:
            self.ser.write(packet)
            hex_str = " ".join(f"{b:02X}" for b in packet)
            self.send_hex.append(f"[0x0105] 发送: {hex_str}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"数据发送失败: {str(e)}")

    def build_packet(self, data: bytes, seq: int, cmd_id: list):
        frame = bytearray()
        frame.append(0xA5)
        frame.extend(struct.pack('<H', len(data)))
        frame.append(seq)
        crc8 = Get_CRC8_Check_Sum(frame[:4], 4)
        frame.append(crc8)
        frame.extend(bytes([cmd_id[1], cmd_id[0]]))
        frame.extend(data)
        crc16 = Get_CRC16_Check_Sum(frame, len(frame))
        frame.extend(struct.pack('<H', crc16))
        return frame


if __name__ == '__main__':
    state = 'R'
    app = QApplication(sys.argv)
    gui = RadarGUI()
    gui.show()
    sys.exit(app.exec_())

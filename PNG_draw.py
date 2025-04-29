import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QComboBox,
    QVBoxLayout, QHBoxLayout, QMessageBox, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QStackedWidget
)
from PyQt5.QtGui import QImage, QPainter, QColor, QPixmap
from PyQt5.QtCore import Qt, QPoint


class RectDrawer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("地图掩码绘制器")
        self.resize(800, 800)

        self.img_width, self.img_height = 1500, 2800
        self.history = []  # 历史记录列表
        self.mode = "fill"  # 当前模式：fill 或 mark

        self.init_ui()
        self.init_image()
        self.update_preview()

    def init_ui(self):
        layout = QVBoxLayout()

        # 模式选择按钮
        mode_layout = QHBoxLayout()
        self.mode_fill_btn = QPushButton("填充模式")
        self.mode_mark_btn = QPushButton("标点模式")
        self.mode_fill_btn.clicked.connect(self.switch_to_fill_mode)
        self.mode_mark_btn.clicked.connect(self.switch_to_mark_mode)
        mode_layout.addWidget(self.mode_fill_btn)
        mode_layout.addWidget(self.mode_mark_btn)
        layout.addLayout(mode_layout)

        # 输入区域堆叠布局
        self.stacked_input = QStackedWidget()

        # 填充模式输入组件
        fill_widget = QWidget()
        fill_layout = QVBoxLayout()
        # 点1输入
        coord1_layout = QHBoxLayout()
        coord1_layout.addWidget(QLabel("点1 (x, y):"))
        self.x1_input = QLineEdit()
        self.y1_input = QLineEdit()
        coord1_layout.addWidget(self.x1_input)
        coord1_layout.addWidget(self.y1_input)
        fill_layout.addLayout(coord1_layout)

        # 点2输入
        coord2_layout = QHBoxLayout()
        coord2_layout.addWidget(QLabel("点2 (x, y):"))
        self.x2_input = QLineEdit()
        self.y2_input = QLineEdit()
        coord2_layout.addWidget(self.x2_input)
        coord2_layout.addWidget(self.y2_input)
        fill_layout.addLayout(coord2_layout)

        # 颜色选择
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("选择颜色:"))
        self.color_box = QComboBox()
        self.color_box.addItems(["绿色", "蓝色"])
        color_layout.addWidget(self.color_box)
        fill_layout.addLayout(color_layout)

        fill_widget.setLayout(fill_layout)
        self.stacked_input.addWidget(fill_widget)

        # 标点模式输入组件
        mark_widget = QWidget()
        mark_layout = QVBoxLayout()
        self.mark_inputs = []
        for i in range(4):
            point_layout = QHBoxLayout()
            point_layout.addWidget(QLabel(f"点{i + 1} (x, y):"))
            x_input = QLineEdit()
            y_input = QLineEdit()
            self.mark_inputs.append((x_input, y_input))
            point_layout.addWidget(x_input)
            point_layout.addWidget(y_input)
            mark_layout.addLayout(point_layout)
        mark_widget.setLayout(mark_layout)
        self.stacked_input.addWidget(mark_widget)

        layout.addWidget(self.stacked_input)

        # 操作按钮
        self.action_button = QPushButton("填充")
        self.undo_button = QPushButton("撤销")
        self.save_button = QPushButton("保存图片")

        self.action_button.clicked.connect(self.perform_action)
        self.undo_button.clicked.connect(self.undo_last)
        self.save_button.clicked.connect(self.save_image)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.action_button)
        button_layout.addWidget(self.undo_button)
        button_layout.addWidget(self.save_button)
        layout.addLayout(button_layout)

        # 预览区域
        self.preview = QGraphicsView()
        self.scene = QGraphicsScene()
        self.preview.setScene(self.scene)
        self.preview.setMinimumHeight(600)
        layout.addWidget(self.preview)

        self.setLayout(layout)

    def init_image(self):
        self.image = QImage(self.img_width, self.img_height, QImage.Format_RGB888)
        self.image.fill(QColor(0, 0, 0))
        self.save_history()

    def save_history(self):
        self.history.append(self.image.copy())

    def update_preview(self):
        scaled = self.image.scaled(300, 560, Qt.KeepAspectRatio)
        pixmap = QPixmap.fromImage(scaled)
        self.scene.clear()
        self.scene.addItem(QGraphicsPixmapItem(pixmap))

    def user_to_img(self, x, y):
        """将用户坐标系（右下原点，x向右，y向上）转换为图像坐标系（左上原点）"""
        # return x, self.img_height - 1 - y
        return 1500 - y, 2800 - x

    def switch_to_fill_mode(self):
        self.stacked_input.setCurrentIndex(0)
        self.action_button.setText("填充")
        self.mode = "fill"

    def switch_to_mark_mode(self):
        self.stacked_input.setCurrentIndex(1)
        self.action_button.setText("绘制圆点")
        self.mode = "mark"

    def perform_action(self):
        if self.mode == "fill":
            self.fill_rectangle()
        else:
            self.mark_points()

    def fill_rectangle(self):
        try:
            x1 = int(self.x1_input.text())
            y1 = int(self.y1_input.text())
            x2 = int(self.x2_input.text())
            y2 = int(self.y2_input.text())
        except ValueError:
            QMessageBox.critical(self, "错误", "请输入合法坐标！")
            return

        # 坐标转换和验证
        px1, py1 = self.user_to_img(x1, y1)
        if not (0 <= px1 < self.img_width and 0 <= py1 < self.img_height):
            QMessageBox.critical(self, "错误", f"点1坐标超出范围！转换后坐标：({px1}, {py1})")
            return
        px2, py2 = self.user_to_img(x2, y2)
        if not (0 <= px2 < self.img_width and 0 <= py2 < self.img_height):
            QMessageBox.critical(self, "错误", f"点2坐标超出范围！转换后坐标：({px2}, {py2})")
            return

        # 绘制矩形
        color = QColor(0, 255, 0) if self.color_box.currentText() == "绿色" else QColor(0, 0, 255)
        painter = QPainter(self.image)
        painter.setBrush(color)
        painter.setPen(color)
        painter.drawRect(min(px1, px2), min(py1, py2), abs(px1 - px2), abs(py1 - py2))
        painter.end()
        # 保存历史
        self.save_history()
        # print(self.history)
        self.update_preview()

    def mark_points(self):
        points = []
        for i, (x_input, y_input) in enumerate(self.mark_inputs):
            try:
                x = int(x_input.text())
                y = int(y_input.text())
            except ValueError:
                QMessageBox.critical(self, "错误", f"点{i + 1}坐标不合法！")
                return

            # 坐标转换和验证
            img_x, img_y = self.user_to_img(x, y)
            if not (0 <= img_x < self.img_width and 0 <= img_y < self.img_height):
                QMessageBox.critical(self, "错误", f"点{i + 1}坐标超出范围！转换后坐标：({img_x}, {img_y})")
                return
            points.append((img_x, img_y))

        if len(points) != 4:
            QMessageBox.critical(self, "错误", "需要输入4个点！")
            return

        # 绘制红色圆
        painter = QPainter(self.image)
        painter.setBrush(QColor(255, 0, 0))
        painter.setPen(QColor(255, 0, 0))

        for (x, y) in points:
            painter.drawEllipse(QPoint(x,y), 20, 20)

        # 保存历史
        self.save_history()
        # print(self.history)

        painter.end()
        self.update_preview()

    def undo_last(self):
        if len(self.history) > 1:
            self.history.pop()
            self.image = self.history[-1].copy()
            self.update_preview()
        else:
            QMessageBox.information(self, "提示", "无法继续撤销")

    def save_image(self):
        filename = "mark.png" if self.mode == "mark" else "标定测试.png"
        if self.image.save(filename):
            QMessageBox.information(self, "成功", f"图片已保存为 {filename}")
        else:
            QMessageBox.critical(self, "错误", "保存失败！")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RectDrawer()
    window.show()
    sys.exit(app.exec_())

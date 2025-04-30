import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QComboBox,
    QVBoxLayout, QHBoxLayout, QMessageBox, QGraphicsView, QGraphicsScene, QStackedWidget, QGroupBox, QFileDialog,
    QListWidget, QSizePolicy
)
from PyQt5.QtGui import QImage, QPainter, QColor, QPixmap, QPainterPath
from PyQt5.QtCore import Qt, QPoint


class ResizableGraphicsView(QGraphicsView):
    """自适应尺寸的预览视图"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def resizeEvent(self, event):
        """窗口大小变化时自动调整视图"""
        if self.scene() and self.scene().items():
            self.fitInView(self.scene().itemsBoundingRect(), Qt.KeepAspectRatio)
        super().resizeEvent(event)


class MapMaskEditor(QWidget):
    """地图掩码编辑器主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("地图掩码编辑器")
        self.resize(1200, 900)

        # 初始化参数
        self.img_width, self.img_height = 1500, 2800
        self.history = []  # 操作历史记录
        self.fill_points = []  # 填充模式点坐标缓存
        self.mask_points = []
        self.current_mode = "fill"  # 当前工作模式

        self.init_ui()
        self.init_image()
        self.update_preview()

    def init_ui(self):
        """初始化用户界面"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # ================= 模式切换 =================
        mode_group = QGroupBox("工作模式")
        mode_layout = QHBoxLayout()
        self.btn_fill_mode = QPushButton("多边形填充模式")
        self.btn_mark_mode = QPushButton("点标记模式")
        self.btn_fill_mode.setCheckable(True)
        self.btn_mark_mode.setCheckable(True)
        self.btn_fill_mode.setChecked(True)
        mode_layout.addWidget(self.btn_fill_mode)
        mode_layout.addWidget(self.btn_mark_mode)
        mode_group.setLayout(mode_layout)
        main_layout.addWidget(mode_group)

        # ================= 主内容区域 =================
        content_layout = QHBoxLayout()

        # 左侧控制面板
        control_panel = self.create_control_panel()
        content_layout.addLayout(control_panel, stretch=1)

        # 右侧预览区域
        preview_group = QGroupBox("画布预览")
        preview_layout = QVBoxLayout()
        self.preview = ResizableGraphicsView()
        self.scene = QGraphicsScene()
        self.preview.setScene(self.scene)
        self.preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        preview_layout.addWidget(self.preview)
        preview_group.setLayout(preview_layout)
        content_layout.addWidget(preview_group, stretch=2)

        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)

        # ================= 事件绑定 =================
        self.btn_fill_mode.clicked.connect(self.switch_to_fill_mode)
        self.btn_mark_mode.clicked.connect(self.switch_to_mark_mode)

    def create_control_panel(self):
        """创建左侧控制面板"""
        panel_layout = QVBoxLayout()
        panel_layout.setContentsMargins(0, 0, 15, 0)

        # 堆叠式输入组件
        self.stacked_input = QStackedWidget()
        self.stacked_input.addWidget(self.create_fill_widget())
        self.stacked_input.addWidget(self.create_mark_widget())
        panel_layout.addWidget(self.stacked_input)

        # 操作按钮组
        btn_group = QGroupBox("操作控制")
        btn_layout = QHBoxLayout()
        self.btn_undo = QPushButton("撤销操作")
        self.btn_save = QPushButton("保存图像")
        btn_layout.addWidget(self.btn_undo)
        btn_layout.addWidget(self.btn_save)
        btn_group.setLayout(btn_layout)
        panel_layout.addWidget(btn_group)

        # 事件绑定
        self.btn_undo.clicked.connect(self.undo_last_action)
        self.btn_save.clicked.connect(self.save_image)

        return panel_layout

    def create_fill_widget(self):
        """创建填充模式组件"""
        widget = QGroupBox("填充参数设置")
        layout = QVBoxLayout()

        # 坐标输入
        input_group = QGroupBox("坐标输入")
        input_layout = QVBoxLayout()
        coord_layout = QHBoxLayout()
        coord_layout.addWidget(QLabel("X坐标:"))
        self.edit_fill_x = QLineEdit()
        coord_layout.addWidget(self.edit_fill_x)
        coord_layout.addWidget(QLabel("Y坐标:"))
        self.edit_fill_y = QLineEdit()
        coord_layout.addWidget(self.edit_fill_y)
        input_layout.addLayout(coord_layout)

        # 点管理按钮
        btn_layout = QHBoxLayout()
        self.btn_add_point = QPushButton("添加点")
        self.btn_clear_points = QPushButton("清空点集")
        btn_layout.addWidget(self.btn_add_point)
        btn_layout.addWidget(self.btn_clear_points)
        input_layout.addLayout(btn_layout)
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # 已添加点列表
        layout.addWidget(QLabel("已添加点列表："))
        self.point_list = QListWidget()
        self.point_list.setMaximumHeight(150)
        layout.addWidget(self.point_list)

        # 颜色选择
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("填充颜色:"))
        self.combo_color = QComboBox()
        self.combo_color.addItems(["绿色", "蓝色"])
        color_layout.addWidget(self.combo_color)
        layout.addLayout(color_layout)

        # 填充按钮
        self.btn_fill = QPushButton("执行填充")
        layout.addWidget(self.btn_fill)

        # 事件绑定
        self.btn_add_point.clicked.connect(self.add_fill_point)
        self.btn_clear_points.clicked.connect(self.clear_fill_points)
        self.btn_fill.clicked.connect(self.fill_polygon)

        widget.setLayout(layout)
        return widget

    def create_mark_widget(self):
        """创建标记模式组件"""
        widget = QGroupBox("标记参数设置")
        layout = QVBoxLayout()

        # 坐标输入
        coord_layout = QHBoxLayout()
        coord_layout.addWidget(QLabel("X坐标:"))
        self.edit_mark_x = QLineEdit()
        coord_layout.addWidget(self.edit_mark_x)
        coord_layout.addWidget(QLabel("Y坐标:"))
        self.edit_mark_y = QLineEdit()
        coord_layout.addWidget(self.edit_mark_y)
        layout.addLayout(coord_layout)

        # 标记按钮
        self.btn_mark = QPushButton("标记点")
        layout.addWidget(self.btn_mark)

        # 已添加点列表
        layout.addWidget(QLabel("已添加点列表："))
        self.mask_list = QListWidget()
        self.mask_list.setMaximumHeight(150)
        layout.addWidget(self.mask_list)

        # 事件绑定
        self.btn_mark.clicked.connect(self.mark_point)

        widget.setLayout(layout)
        return widget

    def init_image(self):
        """初始化空白画布"""
        self.image = QImage(self.img_width, self.img_height, QImage.Format_RGB32)
        self.image.fill(Qt.black)
        self.save_history()

    def user_to_img(self, x, y):
        """
        用户坐标系到图像坐标系的转换
        """
        return self.img_width - y, self.img_height - x

    def save_history(self):
        """保存当前状态到历史记录"""
        self.history.append(self.image.copy())

    def update_preview(self):
        """更新预览区域"""
        self.scene.clear()
        pixmap = QPixmap.fromImage(self.image)
        item = self.scene.addPixmap(pixmap)
        self.preview.fitInView(item, Qt.KeepAspectRatio)

    def switch_to_fill_mode(self):
        """切换到填充模式"""
        self.current_mode = "fill"
        self.stacked_input.setCurrentIndex(0)
        self.btn_fill_mode.setChecked(True)
        self.btn_mark_mode.setChecked(False)

    def switch_to_mark_mode(self):
        """切换到标记模式"""
        self.current_mode = "mark"
        self.stacked_input.setCurrentIndex(1)
        self.btn_mark_mode.setChecked(True)
        self.btn_fill_mode.setChecked(False)

    def add_fill_point(self):
        """添加多边形顶点"""
        try:
            x = int(self.edit_fill_x.text())
            y = int(self.edit_fill_y.text())
        except ValueError:
            QMessageBox.critical(self, "输入错误", "请输入有效的整数坐标！")
            return

        # 显示原始坐标
        self.point_list.addItem(f"({x}, {y})")
        self.edit_fill_x.clear()
        self.edit_fill_y.clear()

        # 坐标转换和验证
        img_x, img_y = self.user_to_img(x, y)
        if not (0 <= img_x <= self.img_width and 0 <= img_y <= self.img_height):
            QMessageBox.critical(self, "范围错误", "坐标超出图像范围！")
            self.point_list.takeItem(self.point_list.count() - 1)
            return

        self.fill_points.append((img_x, img_y))

    def clear_fill_points(self):
        """清空多边形顶点缓存"""
        self.fill_points = []
        self.point_list.clear()

    def fill_polygon(self):
        """执行多边形填充"""
        if len(self.fill_points) < 3:
            QMessageBox.critical(self, "操作错误", "至少需要3个顶点来构成多边形！")
            return

        # 创建绘制路径
        path = QPainterPath()
        path.moveTo(*self.fill_points[0])
        for point in self.fill_points[1:]:
            path.lineTo(*point)
        path.closeSubpath()

        # 设置颜色
        color = QColor(0, 255, 0) if self.combo_color.currentText() == "绿色" else QColor(0, 0, 255)

        # 执行绘制
        painter = QPainter(self.image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(color)
        painter.setPen(color)
        painter.drawPath(path)
        painter.end()

        self.save_history()
        self.update_preview()
        self.clear_fill_points()

    def mark_point(self):
        """标记单个点"""
        try:
            x = int(self.edit_mark_x.text())
            y = int(self.edit_mark_y.text())
        except ValueError:
            QMessageBox.critical(self, "输入错误", "请输入有效的整数坐标！")
            return

        self.mask_list.addItem(f"({x}, {y})")
        # 坐标转换和验证
        img_x, img_y = self.user_to_img(x, y)
        if not (0 <= img_x <= self.img_width and 0 <= img_y <= self.img_height):
            QMessageBox.critical(self, "范围错误", "坐标超出图像范围！")
            return

        # 绘制红色标记点
        painter = QPainter(self.image)
        painter.setBrush(Qt.red)
        painter.setPen(Qt.red)
        painter.drawEllipse(QPoint(img_x, img_y), 20, 20)
        painter.end()

        self.mask_points.append((img_x, img_y))
        self.save_history()
        self.update_preview()
        self.edit_mark_x.clear()
        self.edit_mark_y.clear()

    def undo_last_action(self):
        """撤销上一步操作"""
        if len(self.history) > 1:
            self.history.pop()
            self.image = self.history[-1].copy()
            self.update_preview()
        else:
            QMessageBox.information(self, "提示", "已无历史操作可撤销")

    def save_image(self):
        """保存图像到文件"""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "保存图像", "",
            "PNG图像 (*.png);;JPEG图像 (*.jpg);;所有文件 (*)",
            options=options
        )

        if file_name:
            if self.image.save(file_name):
                QMessageBox.information(self, "成功", f"图像已保存至：\n{file_name}")
            else:
                QMessageBox.critical(self, "错误", "图像保存失败！")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MapMaskEditor()
    window.show()
    sys.exit(app.exec_())

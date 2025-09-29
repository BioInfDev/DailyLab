from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QWidget, QLabel, QHBoxLayout, QVBoxLayout, QButtonGroup, QStackedWidget, \
    QPushButton, QGridLayout, QGraphicsOpacityEffect

from GUI.DLTabs import Documents, KanbanBoard

class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)

        self._setup()
        self._adjust_layout()
    def _setup(self):
        self.app_widget = QWidget()
        self.app_hat = AppHat(self)
        self.app_sidebar = AppSidebar()
        self.app_tabs = AppTabs(self.app_sidebar.changeActiveTab)

        self.setCentralWidget(self.app_widget)

        self.app_layout = QGridLayout(self.app_widget)
        self.app_layout.addWidget(self.app_hat, 0, 0, 1, 2)
        self.app_layout.addWidget(self.app_sidebar, 1, 0, 1, 1)
        self.app_layout.addWidget(self.app_tabs, 1, 1, 1, 1)

        self.app_layout.setColumnStretch(0, 0)
        self.app_layout.setColumnStretch(1, 1)

        self.app_layout.setRowStretch(0, 0)
        self.app_layout.setRowStretch(1, 1)

        self.setStyleSheet("""
            QMainWindow {
                min-width: 1000px;
                min-height: 700px;
                background-color: rgb(18, 18, 18);
            }
        """)
    def _adjust_layout(self):
        self.app_layout.setContentsMargins(0,0,0,0)
        self.app_layout.setSpacing(1)
class AppHat(QWidget):
    def __init__(self, parent: QMainWindow):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.parent = parent

        self._setup()
        self._adjust_layout()
    def _setup(self):
        opacity_effect = QGraphicsOpacityEffect(self)
        opacity_effect.setOpacity(0.8)
        self.setGraphicsEffect(opacity_effect)

        self.title = QLabel('Daily Lab')
        self.minimize_btn = QPushButton()
        self.maximize_btn = QPushButton()
        self.close_btn = QPushButton()

        self.minimize_btn.setIcon(QIcon('./GUI/icons/Minimize.png'))
        self.maximize_btn.setIcon(QIcon('./GUI/icons/Maximize.png'))
        self.close_btn.setIcon(QIcon('./GUI/icons/Close.png'))

        self.setLayout(QHBoxLayout())
        self.layout().addSpacing(40)
        self.layout().addWidget(self.title)
        self.layout().addStretch()
        self.layout().addWidget(self.minimize_btn)
        self.layout().addWidget(self.maximize_btn)
        self.layout().addWidget(self.close_btn)
        self.layout().addSpacing(5)

        self.minimize_btn.clicked.connect(self.parent.showMinimized)
        self.maximize_btn.clicked.connect(self.showMaximized)
        self.close_btn.clicked.connect(self.parent.close)

        self.setStyleSheet("""
            QWidget {
                min-height: 40px;
                max-height: 40px;
                border: none;
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                              stop: 0 rgb(200, 150, 206),
                              stop: 0.5 rgb(255, 205, 170),
                              stop: 1 rgb(255, 160, 162))
            }
            QPushButton {
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
                border: none;
                border-radius: 15px;
                qproperty-iconSize: 20px 20px;
                background-color: none;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.1);
            }
            QPushButton:pressed {
                background-color: rgba(255,255,255,0.15);
            }
            QLabel {
                font-family: 'Dylan';
                font-size: 18px;
                color: rgb(255,255,255);
                background-color: none;
            }
        """)
    def _adjust_layout(self):
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(5)

    def showMaximized(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
        else:
            self.parent.showMaximized()
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent.windowHandle().startSystemMove()
            event.accept()
        else:
            super().mousePressEvent(event)
class AppSidebar(QWidget):
    changeActiveTab = Signal(int)
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.btn_group = QButtonGroup()
        self.btn_group.idClicked.connect(self.setActiveTab)

        self._setup()
        self._adjust_layout()

        self.setStyleSheet("""
            QWidget {
                min-width: 40px;
                max-width: 40px;
                background-color: rgb(40, 40, 40);
            }
            QPushButton {
                border: none;
                min-width: 32px;
                max-width: 32px;
                min-height: 32px;
                max-height: 32px;
                margin: 4px;
                border-radius: 6px;
                qproperty-iconSize: 23px 23px;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.1);
            }
            QPushButton[clicked="true"] {
                background-color: rgba(255,255,255,0.15);
            }
        """)
    def _setup(self):
        btn_names = ('Home', 'Documents', 'Projects', 'BioInformatics', 'Kanban', 'Archive', 'Settings')
        self.setLayout(QVBoxLayout())
        for i, name in enumerate(btn_names):
            button = QPushButton()
            button.setProperty('clicked', f'{"true" if name == "Home" else "false"}')
            button.setIcon(QIcon(f"./GUI/icons/{name}.png"))

            self.layout().addWidget(button)
            self.btn_group.addButton(button, id=i)

            if name == 'Archive':
                self.layout().addStretch()
    def _adjust_layout(self):
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

    def setActiveTab(self, btn_id):
        for button in self.btn_group.buttons():
            if self.btn_group.id(button) == btn_id:
                button.setProperty('clicked', 'true')
                self.changeActiveTab.emit(btn_id)
            else:
                button.setProperty('clicked', 'false')
            button.style().unpolish(button)
            button.style().polish(button)
class AppTabs(QStackedWidget):
    def __init__(self, qsignal):
        super().__init__()
        self.qsignal = qsignal
        self.qsignal.connect(self._update_tab)

        self._setup()
        self._adjust_layout()
    def _setup(self):
        tabs = {'Home': QWidget, 'Protocols': Documents, 'Projects': QWidget, 'BioInformatics': QWidget, 'Kanban': KanbanBoard, 'Archive': QWidget, 'Settings': QWidget}
        for name, widget in tabs.items():
            tab = widget()
            self.addWidget(tab)
    def _adjust_layout(self):
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
    def _update_tab(self, index):
        self.setCurrentIndex(index)
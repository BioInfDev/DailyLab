from PySide6.QtWidgets import QWidget, QScrollArea, QHBoxLayout
from PySide6.QtCore import Qt

from GUI.DLWidgets import Sidebar, PdfView, Section


class Documents(QWidget):
    DATA_PATH = './storage/sidebar/'
    JSON_PATH = './storage/sidebar.json'
    SIDEBAR_WIDTH = 300
    def __init__(self):
        super().__init__()

        self._setup()
        self._adjustLayout()
    def _adjustLayout(self):
        self.layout().setContentsMargins(0,1,1,1)
        self.layout().setSpacing(1)
    def _setup(self):
        self.tab_sidebar = Sidebar(Documents.DATA_PATH, Documents.JSON_PATH, Documents.SIDEBAR_WIDTH)
        self.tab_viewer = PdfView(self.tab_sidebar.changeActiveDocument)

        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.tab_sidebar)
        self.layout().addWidget(self.tab_viewer)

class KanbanBoard(QScrollArea):
    def __init__(self):
        super().__init__()

        self.board = QWidget()
        self.setWidget(self.board)
        self.setWidgetResizable(True)

        self.board.setLayout(QHBoxLayout())
        self.board.layout().setAlignment(Qt.AlignmentFlag.AlignTop)
        '''
        section_1 = Section(None, '1', {}, None)
        section_2 = Section(None, '1', {}, None)

        section_1.setFixedWidth(400)
        section_2.setFixedWidth(400)
        self.board.layout().addWidget(section_1)
        self.board.layout().addWidget(section_2)
        '''

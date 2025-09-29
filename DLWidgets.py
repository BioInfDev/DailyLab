import ctypes
import hashlib
import json
import multiprocessing
import os
import shutil
from functools import partial
from multiprocessing import shared_memory, Pipe, Event

import fitz
from PySide6.QtCore import Qt, QObject, QPoint, QStandardPaths, Signal, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import QWidget, QScrollArea, QVBoxLayout, QPushButton, \
    QHBoxLayout, QGridLayout, QLabel, QFileDialog, QLineEdit, QGraphicsView, QGraphicsScene, QButtonGroup
from GUI.DLInterface import ARRInterface

class Sidebar(QScrollArea):
    changeActiveDocument = Signal(str)
    def __init__(self, path_to_data, path_to_json, width=None, height=None):
        super().__init__()
        self.data_path = path_to_data
        self.json_path = path_to_json
        self.fixed_width = width
        self.fixed_height = height

        with open(self.json_path) as _json:
            self.json_sidebar = json.load(_json)
        self.arr_submenu = ARRSubmenu()
        self.documents = QButtonGroup()
        self.documents.idClicked.connect(self.setActiveDocument)

        self._setScrollableContent()
        self._adjustLayout()
        self._setViewportContent()
        self.setStyleSheet("""
            QWidget {
                background-color: rgb(30, 30, 30);
                border: none;
            }
            QScrollArea {
                border: none;
                padding: 0;  
            }
            QScrollBar:vertical {
                margin: 0;  
                background: transparent;  
                width: 6px; 
            }
            QScrollBar::handle:vertical {
                background: #a0a0a0;
                border-radius: 3px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px; 
            }
        """)
    def _setScrollableContent(self):
        self.sidebar = QWidget()
        self.setWidget(self.sidebar)
        self.setWidgetResizable(True)
        self.sidebar.setLayout(QVBoxLayout())

        if self.fixed_width:
            self.setFixedWidth(self.fixed_width)
        if self.fixed_height:
            self.setFixedHeight(self.fixed_height)

        for json_section in self.json_sidebar['Sections']:
            self._createSection(json_section['Label'], json_section['Content'], json_section['Path'])
    def _setViewportContent(self):
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.add_section = QPushButton()
        self.add_section.setFixedHeight(50)
        if self.fixed_width:
            self.add_section.setFixedWidth(self.fixed_width)

        self.add_section.setParent(self.viewport())
        self.add_section.setIcon(QIcon('./GUI/icons/Add.png'))
        self.add_section.setStyleSheet("""
            QPushButton {
                background-color: rgb(40, 40, 40);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 5px;
                margin: 5px;
                qproperty-iconSize: 23px 23px;
            }
            QPushButton:hover {
                background-color: rgba(100, 100, 100, 0.2);
                color: rgb(255,255,255);
            }
        """)

        self.add_section.clicked.connect(partial(self._createSection, mode='New'))
    def _adjustLayout(self):
        self.sidebar.layout().setContentsMargins(2, 2, 2, 2)
        self.sidebar.layout().setSpacing(5)
        self.sidebar.layout().setAlignment(Qt.AlignmentFlag.AlignTop)
    def _adjustViewport(self):
        x_offset = 0
        y_offset = self.viewport().height() - self.add_section.height()
        self.add_section.move(x_offset, y_offset)
    def _createSection(self, section_label=None, section_content=None, section_dir=None, mode='Exists'):
        if section_label is None:
            postfix_set = {int(record['Label'].split('_')[-1]) for record in self.json_sidebar['Sections'] if
                           record['Label'].startswith('Section_')}
            free_postfix: int
            if postfix_set:
                full_set = set(range(max(postfix_set) + 1))
                free_postfix = min(full_set - postfix_set) if full_set - postfix_set else max(postfix_set) + 1
            else:
                free_postfix = 0
            section_label = f'Section_{free_postfix}'
        if section_content is None:
            section_content = {}
        if section_dir is None:
            postfix_set = {int(record['Path'].split('/')[-1].split('_')[-1]) for record in self.json_sidebar['Sections']
                           if record['Path'].split('/')[-1].startswith('Section_')}
            free_postfix: int
            if postfix_set:
                full_set = set(range(max(postfix_set) + 1))
                free_postfix = min(full_set - postfix_set) if full_set - postfix_set else max(postfix_set) + 1
            else:
                free_postfix = 0
            section_dir = self.data_path + f'Section_{free_postfix}'

        section = Section(self.arr_submenu, section_label, section_content, section_dir)
        section.sectionChanged.connect(self.updateSection)
        self.sidebar.layout().addWidget(section)

        for document in section.findChildren(_DocumentButton):
            self.documents.addButton(document)

        if mode == 'New':
            os.mkdir(section.section_dir)
            image = section.getSectionImage()
            self.json_sidebar['Sections'].append(image)
            with open(self.json_path, 'wt') as _json:
                json.dump(self.json_sidebar, _json)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adjustViewport()
    def setActiveDocument(self, protocol_id):
        for protocol in self.documents.buttons():
            protocol: _DocumentButton
            if self.documents.id(protocol) == protocol_id:
                protocol.setProperty("clicked", "true")
                self.changeActiveDocument.emit(protocol.path)
            else:
                protocol.setProperty("clicked", "false")
            protocol.style().polish(protocol)
    def updateSection(self):
        section: Section = self.sender()
        section.updateSection()
        current_image = section.getSectionImage()
        recent_image = {}
        recent_image_index = None
        for index, image in enumerate(self.json_sidebar['Sections']):
            if image['Path'] == current_image['Path']:
                recent_image = image
                recent_image_index = index
                break

        # Changes detection
        current_content = {record for record in current_image['Content'].values()}
        recent_content = {record for record in recent_image['Content'].values()}
        removed_content, added_content = (recent_content - current_content), (current_content - recent_content)

        # Commit changes
        if self.sidebar.layout().indexOf(section) == -1:
            shutil.rmtree(section.section_dir)
            del self.json_sidebar['Sections'][recent_image_index]
        else:
            self.json_sidebar['Sections'][recent_image_index] = current_image
            if removed_content:
                _removed = removed_content.pop()
                for protocol in section.findChildren(_DocumentButton):
                    if protocol.path == _removed:
                        self.documents.removeButton(protocol)
                        break
            elif added_content:
                _added = added_content.pop()
                for protocol in section.findChildren(_DocumentButton):
                    if protocol.path == _added:
                        self.documents.addButton(protocol)
                        break
        with open(self.json_path, 'wt') as _json:
            json.dump(self.json_sidebar, _json)
class Section(QWidget):
    sectionChanged = Signal()
    # подтягивать arr submenu в classmethod а не ссылкой
    def __init__(self, arr_submenu, section_label: str, section_content: dict, section_dir: str):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.arr_submenu = arr_submenu
        self.section_label = section_label
        self.section_content = section_content
        self.section_dir = section_dir

        self._setContent()
        self._adjustLayout()
        self.setStyleSheet("""
            QWidget {
                background-color: rgb(40, 40, 40);
                border-radius: 5px;
            }
        """)
    def _setContent(self):
        self.setLayout(QVBoxLayout())

        self.header = _SectionHeader(self.section_label)
        self.content = _DocumentContent(self.section_content)
        self.layout().addWidget(self.header)
        self.layout().addWidget(self.content)

        self._setConnections()
    def _adjustLayout(self):
        self.layout().setContentsMargins(5,0,5,0)
        self.layout().setSpacing(0)
    def _setConnections(self):
        self.header.toggle_btn.clicked.connect(self.toggleContent)
        self.header.submenu_btn.clicked.connect(partial(self.arr_submenu.call, self.header.submenu_btn, self.content, self.header.label, self))

        #for document in self.content.findChildren(_DocumentButton):
        #    document.settings.clicked.connect(partial(self.arr_submenu.call, document.settings, None, document, document))

        self.arr_submenu.changeReceiver.connect(self.updateSection)
    def updateSection(self, action, receiver: ARRInterface):
        print(action, receiver)
        print('horhe')
        match action:
            case 'Add':
                receiver.add()
                receiver.createDocument()
            case 'Rename':
                receiver.setEnabled(True)
            case 'Remove':
                receiver.setParent(None)
                receiver.deleteLater()

        self.section_label = self.header.label.text()
        self.section_content = {}
        for protocol in self.content.findChildren(_DocumentButton):
            protocol.name = protocol.text()
            self.section_content[protocol.name] = protocol.path
        #self.sectionChanged.emit()
    def getSectionImage(self):
        return {'Path': self.section_dir, 'Label': self.section_label, 'Content': self.section_content}

    def toggleContent(self):
        self.content.toggleAnimation()
        self.header.toggle_btn.setIcon(QIcon(f'./GUI/icons/Expand_{'active' if self.content.toggled else 'inactive'}.png'))
    def createDocument(self):
        recent_path = QFileDialog.getOpenFileName(parent=self, caption='Select PDF File',
            dir=QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation),
            filter='PDF (*.pdf)')[0]
        if recent_path:
            with open(recent_path, 'rb') as _file:
                hashable_file = _file.read()
            file_hash = hashlib.blake2s(hashable_file, digest_size = 16).hexdigest()

            if not self.isDocumentExists(file_hash):
                file_name = recent_path.split('/')[-1].split('.')[0]
                new_path = self.section_dir + '/' + file_hash

                protocol = _DocumentButton(file_name, new_path)
                protocol.settings.clicked.connect(partial(self.callARRSubmenu, protocol.settings, protocol, protocol))

                add_btnIndex = self.content.layout().indexOf(self.content.add_btn)
                self.content.layout().insertWidget(add_btnIndex, protocol)

                shutil.copyfile(recent_path, new_path)
                self.sectionChanged.emit()
    def isDocumentExists(self, file_hash):
        for path in self.section_content.values():
            _hash = path.split('/')[-1]
            if file_hash == _hash:
                return True
        return False

class _SectionHeader(QWidget):
    HEADER_HEIGHT = 40
    def __init__(self, header_label: str):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.header_label = header_label

        self._setContent()
        self._adjustLayout()
        self.setStyleSheet("""
            QPushButton {
                min-width: 30px;
                min-height: 30px;
                max-height: 30px;
                max-width: 30px;
                border:none;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: rgba(188, 188, 188, 0.2);
            }
            QLabel {
                height: 40px;
                font-family: 'Dylan';
                font-size: 15px;
                color: rgb(240,240,240);
                qproperty-alignment: AlignCenter;
            }
        """)
    def _setContent(self):
        self.setFixedHeight(_SectionHeader.HEADER_HEIGHT)
        self.setLayout(QHBoxLayout())

        self.toggle_btn = QPushButton()
        self.label = QLabel(self.header_label)
        self.submenu_btn = QPushButton()

        for widget in (self.toggle_btn, self.label, self.submenu_btn):
            self.layout().addWidget(widget)

        self.toggle_btn.setIcon(QIcon('./GUI/icons/Expand_active.png'))
        self.submenu_btn.setIcon(QIcon('./GUI/icons/Submenu.png'))
    def _adjustLayout(self):
        self.layout().setContentsMargins(0,0,0,0)
        self.layout().setSpacing(0)
class _DocumentContent(QWidget):
    def __init__(self, documents: dict):
        super().__init__()
        self.documents = documents

        self.toggle_animation = QPropertyAnimation(self, b'maximumHeight')
        self.toggle_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggle_animation.setDuration(250)
        self.toggled = True

        self._setContent()
        self._adjustLayout()
    def _setContent(self):
        self.setLayout(QVBoxLayout())
        for _name, _dir in self.documents.items():
            content_btn = _DocumentButton(_name, _dir)
            self.layout().addWidget(content_btn)
    def _adjustLayout(self):
        self.layout().setContentsMargins(0, 5, 0, 5)
        self.layout().setSpacing(5)

    def toggleAnimation(self):
        self.toggled = not self.toggled
        end_value = self.sizeHint().height() if self.toggled else 0

        self.toggle_animation.stop()
        self.toggle_animation.setStartValue(self.height())
        self.toggle_animation.setEndValue(end_value)
        self.toggle_animation.start()
class _DocumentButton(QPushButton, ARRInterface):
    BTN_HEIGHT = 40
    def __init__(self, name, path):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.name = name
        self.path = path

        self._setup()
        self._adjust_layout()
    def _setup(self):
        self.setFixedHeight(_DocumentButton.BTN_HEIGHT)
        self.setText(self.name)

        self.settings = QPushButton()
        self.settings.setIcon(QIcon('./GUI/icons/Submenu.png'))
        self.settings.setFixedSize(_DocumentButton.BTN_HEIGHT / 2, _DocumentButton.BTN_HEIGHT / 2)
        self.settings.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: rgba(199, 138, 222, 0.5);
            }
        """)
        self.settings.hide()

        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.settings)

        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(200, 150, 206, 0.7);
                font-family: 'Dylan';
                font-size: 12px;
                border-radius: 7px;
            }
            QPushButton:hover {
                background-color: rgba(142, 92, 161, 0.7);
            }
            QPushButton[clicked="true"] {
                background-color: rgba(142, 92, 161, 1);
            }
        """)
    def _adjust_layout(self):
        self.layout().setContentsMargins(0, 0, 5, 0)
        self.layout().setAlignment(Qt.AlignmentFlag.AlignRight)

    def enterEvent(self, event):
        super().enterEvent(event)
        self.settings.show()
    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.settings.hide()

class ARRSubmenu(QWidget):
    changeReceiver = Signal(str, QObject)
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowFlag(Qt.WindowType.Popup)

        self.actions = ['Add', 'Rename', 'Remove']
        self.action_receiver : dict

        self._setup()
        self._adjustLayout()
        self.setStyleSheet("""
            QWidget {
                background-color: rgb(100,100,100);
            }
            QPushButton {
                background-color:rgb(70, 70, 70);
                border-radius: 5px;
                border: none;
                height: 30px;        
            }
        """)
    def _adjustLayout(self):
        self.layout().setContentsMargins(1, 1, 1, 1)
        self.layout().setSpacing(2)
    def _setup(self):
        self.setLayout(QVBoxLayout())
        for action in self.actions:
            setting = QPushButton(action)
            setting.setObjectName(action)
            setting.clicked.connect(partial(self._pushChange, action))

            self.layout().addWidget(setting)
    def _unlink(self):
        meta_receiverChanged = self.metaObject().method(self.metaObject().indexOfSignal('changeReceiver(str, QObject)'))
        print(meta_receiverChanged)
        self.changeReceiver.disconnect()

        if self.isSignalConnected(meta_receiverChanged):
            print('here')
            self.changeReceiver.disconnect()

        for action in self.actions:
            self.findChild(QPushButton, action).hide()
        self.action_receiver = {action: None for action in self.actions}
    def _link(self, addable_receiver, renamable_receiver, removable_receiver):
        self.action_receiver = dict(zip(self.actions, (addable_receiver, renamable_receiver, removable_receiver)))
        for action, receiver in self.action_receiver.items():
            if receiver:
                self.findChild(QPushButton, action).show()
    def _pushChange(self, action):
        print('hrer')
        self.changeReceiver.emit(action, self.action_receiver[action])
        self._unlink()
        self.close()

    def call(self, source, addable_receiver = None, renamable_receiver = None, removable_receiver = None):
        x_offset = source.mapToGlobal(QPoint(0, 0)).x() + source.width()
        y_offset = source.mapToGlobal(QPoint(0, 0)).y() + source.height()
        self.move(x_offset, y_offset)
        self._link(addable_receiver, renamable_receiver, removable_receiver)
        self.show()


class PdfView(QGraphicsView):
    def __init__(self, qsignal):
        super().__init__()
        self.qsignal = qsignal
        self.qsignal.connect(self._update_scene)

        self.page_width = 595 * 144 / 72
        self.page_height = 842 * 144 / 72

        self.update_timer = QTimer()
        self.page_producer = _PageProducer()

        self.page_scene = QGraphicsScene()
        self.setScene(self.page_scene)

        self.verticalScrollBar().sliderReleased.connect(self._scrolled)

        self.setStyleSheet(""" border: none; background-color: rgb(30, 30, 30); """)
    def _update_scene(self, path_to_pdf: str) -> None:
        if self.update_timer.isActive():
            self.update_timer.stop()
            self.update_timer.timeout.disconnect()
        if self.page_producer.isAlive():
            self.page_producer.stop()

        with fitz.open(path_to_pdf) as pdf:
            page_count = pdf.page_count
        self.scene().clear()
        self.scene().setSceneRect(0, 0, self.page_width, self.page_height * page_count)
        self.verticalScrollBar().setValue(0)

        self.page_producer.refresh()
        self.update_timer.timeout.connect(self._load_page)

        self.page_producer.start(path_to_pdf)
        self.update_timer.start(250)
    def _load_page(self):
        if self.page_producer.finished.is_set():
            self.update_timer.stop()
            self.update_timer.timeout.disconnect()
        elif self.page_producer.viewer_conn.poll():
            page_size, page_num = self.page_producer.viewer_conn.recv()
            page_bytes = self.page_producer.page_buff.buf[0: page_size]
            self.page_producer.viewer_conn.send(0)

            page_image = QImage.fromData(bytes(page_bytes))
            page_pixmap = QPixmap.fromImage(page_image).scaled(self.page_width, self.page_height,
                                                               Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                                               Qt.TransformationMode.SmoothTransformation)
            page_instance = self.scene().addPixmap(page_pixmap)

            height_offset = page_num * (self.page_height + 5)
            width_offset = -(page_pixmap.width() - self.page_width) / 2
            page_instance.setPos(width_offset, height_offset)
    def _scrolled(self):
        # сначала проверить отрендерена страница или нет, после обрабатывать таймер -> убрать проверку в pages в worker'е
        self.update_timer.stop()
        with self.page_producer.page_num.get_lock():
            y_offset = self.verticalScrollBar().value()
            page_num = int(y_offset / (self.page_height + 5))
            self.page_producer.page_num.value = page_num
        self.page_producer.page_scrolled.set()
        self.update_timer.start()

    def wheelEvent(self, event):
        super().wheelEvent(event)
        if self.page_producer.isAlive() and event.isEndEvent():
            self._scrolled()
class _PageProducer:
    def __init__(self):
        self.process = None
        self.page_buff = None
        self.viewer_conn, self.worker_conn = None, None
        self.path_to_pdf = None
        self.page_num = multiprocessing.Value(ctypes.c_int)
        self.page_scrolled = Event()
        self.finished = Event()

    def start(self, path_to_df):
        self.path_to_pdf = path_to_df
        self.process.start()
    def stop(self):
        self._interruption()
    def refresh(self):
        self.process = multiprocessing.Process(target=self._page_conveyor)
        self.page_buff = shared_memory.SharedMemory(create=True, size=int(10e7))
        self.viewer_conn, self.worker_conn = Pipe()
        self.finished.clear()
    def isAlive(self):
        if self.process:
            return self.process.is_alive()
        return False

    def _interruption(self):
        self.viewer_conn.send(1)
        self.process.join()
        self.process.close()
        self.viewer_conn.close()
    def _cleanup(self):
        self.page_buff.close()
        self.page_buff.unlink()
        self.viewer_conn.close()
        self.worker_conn.close()
        self.process = None
        self.page_buff = None
        self.viewer_conn, self.worker_conn = None, None
        self.path_to_pdf = None
    def _page_conveyor(self):
        with fitz.open(self.path_to_pdf) as pdf:
            page_range = set(range(pdf.page_count))
            page_num = 0
            while True:
                if self.page_scrolled.is_set():
                    self.page_scrolled.clear()
                    if self.page_num.value in page_range:
                        page_num = self.page_num.value

                result = self._render(pdf, page_num)  # 0 - Page Loaded, 1 - Process Interrupted

                page_range.discard(page_num)
                if not page_range or result != 0:
                    self.finished.set()
                    self._cleanup()
                    break
                else:
                    page_num += 1
                    if page_num not in page_range:
                        page_num = min(page_range)
    def _render(self, pdf, page_num):
        pixmap = pdf[page_num].get_pixmap(matrix=fitz.Matrix(2, 2))  # ~ 0.02 sec/page -> 50 pages/sec | limitless stage
        page_bytes = pixmap.tobytes()  # automatically convert to png

        page_size = len(page_bytes)
        self.page_buff.buf[0: page_size] = page_bytes
        self.worker_conn.send((page_size, page_num))
        return self.worker_conn.recv()


# 1
    # Переместить добавление протоколов в ARR Submenu
    # Rename не вызывает окно, а переводит QLabel в режим редактирования - нужно заменить на QLineEdit
    # Аналогично заменить кнопки на QLineEdit (с обработкой клика) - подумать, может есть другой вариант
# 2
    # Добавить линию между header и content
# 3
    # настроить стиль скроллбаров (убрать кнопки, настроить отображение) при двиежнии мыши показывать, без движенния - нет (проверить, что при wheelEvent корректно срабатывает)
    # добавить направление добавления картинок (при wheel)
    # добавить zoom (через тачбар + виджет)
    # вызывать завершение процесса, при выходе из приложения

# 4
    # Во Viewer добавить панель: zoom, toggle режим
    
# Можно добавить парсер оглавления, и создавать гиперссылки на главы
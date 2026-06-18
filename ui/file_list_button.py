"""Кликабельный виджет-обёртка для отображения и редактирования списка файлов."""
import os
from typing import List

from PySide6.QtWidgets import QPushButton, QApplication, QMessageBox
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QFont


class FileListButton(QPushButton):
    """Кнопка показывает количество выбранных файлов.
    По клику открывает диалог редактирования списка.
    """
    clicked_with_files = Signal(list)  # список путей файлов
    clicked_empty = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_count = 0
        self._files: List[str] = []
        self.setMinimumHeight(28)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(QFont('Segoe UI', 9))
        self._update_text()
        # На случай если clicked не сработает — есть mousePressEvent
        self.clicked.connect(self._on_click)

    def set_files(self, files: List[str]) -> None:
        """Устанавливает список файлов и обновляет отображение."""
        self._files = list(files)
        self._file_count = len(self._files)
        self._update_text()

    def _update_text(self) -> None:
        if self._file_count == 0:
            self.setText('📁 Перетащите файлы или нажмите "Обзор..."')
        elif self._file_count == 1:
            name = os.path.basename(self._files[0])
            if len(name) > 50:
                name = name[:47] + '...'
            self.setText(f'✓ {name}')
        else:
            self.setText(f'✓ {self._file_count} files selected  ▶  (клик для редактирования)')

    def _on_click(self) -> None:
        """Срабатывает на клик."""
        try:
            import tempfile
            log_path = os.path.join(tempfile.gettempdir(), 'rpa-ex-click.log')
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f'CLICK: {self._file_count} files\n')
        except Exception:
            pass
        if self._file_count == 0:
            self.clicked_empty.emit()
        else:
            self.clicked_with_files.emit(self._files)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Гарантированно перехватываем клик даже если clicked не сработает."""
        try:
            import tempfile
            log_path = os.path.join(tempfile.gettempdir(), 'rpa-ex-click.log')
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f'mousePressEvent: {self._file_count} files, type={event.button()}\n')
        except Exception:
            pass
        # Вызываем базовый обработчик
        super().mousePressEvent(event)
        # Fallback — генерируем сигнал напрямую если clicked не сработает
        if event.button() == Qt.LeftButton:
            try:
                if self._file_count == 0:
                    self.clicked_empty.emit()
                else:
                    self.clicked_with_files.emit(self._files)
            except Exception as e:
                try:
                    import tempfile
                    log_path = os.path.join(tempfile.gettempdir(), 'rpa-ex-click.log')
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(f'  mousePress ERROR: {e}\n')
                except Exception:
                    pass

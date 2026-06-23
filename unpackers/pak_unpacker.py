"""Unpacker для Unreal Engine .pak архивов через pyuepak.

Использует библиотеку pyuepak для полноценной распаковки:
- Поддержка версий 1-12
- Zlib / Gzip / Oodle / LZ4 сжатие
- AES-256 шифрование (с ключом)
- Mount point и path hash seed
"""
from __future__ import annotations

import os
import sys
import traceback
from typing import List, Optional

from core.base_unpacker import (
    BaseUnpacker, UnpackOptions, UnpackResult, ProgressCallback,
)
from unpackers.rpa_unpacker import sanitize_filename, PathTraversalError


UNREAL_PAK_MAGIC = b'PAK\x00'


def _check_pyuepak():
    """Ленивый импорт pyuepak с понятной ошибкой."""
    try:
        from pyuepak import PakFile  # noqa: F401
        return True
    except ImportError as e:
        raise RuntimeError(
            'pyuepak не установлен. Установите: pip install pyuepak'
        ) from e


class UnrealPakUnpacker(BaseUnpacker):
    """Unpacker для Unreal Engine .pak архивов."""

    name = 'pak'

    @classmethod
    def detect(cls, target: str) -> bool:
        """Проверяет что файл — это .pak архив Unreal Engine."""
        if not os.path.isfile(target):
            return False
        if not target.lower().endswith('.pak'):
            return False
        try:
            with open(target, 'rb') as f:
                head = f.read(4)
            return head == UNREAL_PAK_MAGIC
        except (OSError, PermissionError):
            return False

    def analyze(self, target: str) -> dict:
        """Анализирует .pak файл и возвращает статистику."""
        info = {
            'type': 'unreal_pak',
            'detected': self.detect(target),
            'file_size': os.path.getsize(target) if os.path.isfile(target) else 0,
            'note': '',
        }
        if not info['detected']:
            return info
        try:
            _check_pyuepak()
            from pyuepak import PakFile
            pak = PakFile()
            pak.read(target)
            info['version'] = int(pak.version)
            info['file_count'] = pak.count
            info['mount_point'] = pak.mount_point
            files = pak.list_files()
            info['sample_files'] = files[:10]
            if len(files) > 10:
                info['sample_files'].append(f'... (+{len(files) - 10} more)')
        except Exception as e:
            info['note'] = f'Ошибка чтения индекса: {type(e).__name__}: {e}'
        return info

    def unpack(
        self,
        target: str,
        options: UnpackOptions,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> UnpackResult:
        """Распаковывает .pak архив в options.output_dir."""
        result = UnpackResult(success=False, output_dir=options.output_dir)

        if not self.detect(target):
            result.errors.append(
                f'{os.path.basename(target)}: не похоже на .pak (нет магии PAK\\0)'
            )
            return result

        _check_pyuepak()

        output_dir = options.output_dir
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as e:
            result.errors.append(f'Не удалось создать {output_dir}: {e}')
            return result

        # Читаем pak-файл
        try:
            from pyuepak import PakFile
            pak = PakFile()
            pak.read(target)
        except Exception as e:
            result.errors.append(
                f'{os.path.basename(target)}: ошибка чтения индекса: '
                f'{type(e).__name__}: {e}'
            )
            return result

        file_list = pak.list_files()
        total = len(file_list)
        if total == 0:
            result.warnings.append(
                f'{os.path.basename(target)}: пустой архив (0 файлов)'
            )
            result.success = True
            return result

        # Определяем общий префикс (mount point) чтобы не дублировать
        mount_point = (pak.mount_point or '').rstrip('/').rstrip('\\')

        for idx, file_path in enumerate(file_list, 1):
            try:
                # Вычисляем относительный путь
                rel = file_path.lstrip('/').lstrip('\\')
                if mount_point and rel.lower().startswith(
                    mount_point.lower().lstrip('/').lstrip('\\') + '/'
                ):
                    rel = rel[len(mount_point) + 1:]

                # Sanitize путь
                try:
                    safe_parts = sanitize_filename(rel)
                except PathTraversalError:
                    # Пропускаем небезопасные пути
                    result.skipped.append({
                        'path': file_path,
                        'reason': 'unsafe path (path traversal blocked)',
                    })
                    continue

                out_path = os.path.join(output_dir, safe_parts.replace('/', os.sep))

                # Создаём подпапки
                out_subdir = os.path.dirname(out_path)
                if out_subdir:
                    try:
                        os.makedirs(out_subdir, exist_ok=True)
                    except OSError as e:
                        result.warnings.append(
                            f'{file_path}: не удалось создать папку: {e}'
                        )
                        continue

                # Читаем данные файла
                try:
                    data = pak.read_file(file_path)
                except Exception as e:
                    result.warnings.append(
                        f'{file_path}: ошибка чтения: {type(e).__name__}: {e}'
                    )
                    if not options.continue_on_error:
                        result.errors.append(
                            f'{file_path}: {type(e).__name__}: {e}'
                        )
                        return result
                    continue

                if data is None:
                    result.warnings.append(f'{file_path}: пустые данные')
                    continue

                # Сохраняем
                try:
                    with open(out_path, 'wb') as f:
                        f.write(data)
                except OSError as e:
                    result.errors.append(f'{file_path}: ошибка записи: {e}')
                    if not options.continue_on_error:
                        return result
                    continue

                result.files_extracted.append(out_path)

                if progress_callback:
                    try:
                        progress_callback(file_path, idx, total)
                    except Exception:
                        pass

            except Exception as e:
                result.errors.append(
                    f'{file_path}: неожиданная ошибка: {type(e).__name__}: {e}'
                )
                if not options.continue_on_error:
                    return result

        result.success = len(result.errors) == 0
        return result

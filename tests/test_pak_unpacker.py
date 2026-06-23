"""Тесты для UnrealPakUnpacker."""
import os
import sys
import unittest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unpackers.pak_unpacker import (
    UnrealPakUnpacker,
    UNREAL_PAK_MAGIC,
)


class TestDetect(unittest.TestCase):
    """Тесты детекта .pak файлов."""

    def test_detect_magic(self):
        """Детект работает с правильной магией."""
        with tempfile.NamedTemporaryFile(suffix='.pak', delete=False) as f:
            f.write(UNREAL_PAK_MAGIC + b'\x00' * 100)
            path = f.name
        try:
            self.assertTrue(UnrealPakUnpacker.detect(path))
        finally:
            os.unlink(path)

    def test_detect_wrong_magic(self):
        """Детект не срабатывает на неправильной магии."""
        with tempfile.NamedTemporaryFile(suffix='.pak', delete=False) as f:
            f.write(b'XXXX' + b'\x00' * 100)
            path = f.name
        try:
            self.assertFalse(UnrealPakUnpacker.detect(path))
        finally:
            os.unlink(path)

    def test_detect_wrong_extension(self):
        """Детект не срабатывает на файлах без расширения .pak."""
        with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
            f.write(UNREAL_PAK_MAGIC + b'\x00' * 100)
            path = f.name
        try:
            self.assertFalse(UnrealPakUnpacker.detect(path))
        finally:
            os.unlink(path)

    def test_detect_nonexistent(self):
        """Детект не падает на несуществующих файлах."""
        self.assertFalse(UnrealPakUnpacker.detect('/nonexistent/file.pak'))


class TestAnalyze(unittest.TestCase):
    """Тесты метода analyze."""

    def test_analyze_non_pak_file(self):
        """analyze возвращает detected=False для не-pak файлов."""
        with tempfile.NamedTemporaryFile(suffix='.pak', delete=False) as f:
            f.write(b'NOTAPAK' + b'\x00' * 100)
            path = f.name
        try:
            u = UnrealPakUnpacker()
            info = u.analyze(path)
            self.assertFalse(info['detected'])
            self.assertEqual(info['type'], 'unreal_pak')
        finally:
            os.unlink(path)


class TestUnpack(unittest.TestCase):
    """Тесты метода unpack."""

    def test_unpack_non_pak_returns_error(self):
        """unpack возвращает ошибку для не-pak файлов."""
        with tempfile.NamedTemporaryFile(suffix='.pak', delete=False) as f:
            f.write(b'NOTAPAK' + b'\x00' * 100)
            path = f.name
        try:
            with tempfile.TemporaryDirectory() as out_dir:
                from core.base_unpacker import UnpackOptions
                u = UnrealPakUnpacker()
                opts = UnpackOptions(output_dir=out_dir)
                r = u.unpack(path, opts)
                self.assertFalse(r.success)
                self.assertGreater(len(r.errors), 0)
                # Should mention "не похоже на .pak"
                self.assertTrue(any('не похоже' in e for e in r.errors))
        finally:
            os.unlink(path)


if __name__ == '__main__':
    unittest.main()

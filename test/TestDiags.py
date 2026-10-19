import importlib
import sys
import unittest
from unittest import mock


class TestDiags(unittest.TestCase):
    def test_lists_packages_without_pkg_resources(self):
        # setuptools no longer ships pkg_resources
        with mock.patch.dict(sys.modules, {'pkg_resources': None}):
            from source.classes import diags
            importlib.reload(diags)
            lines = diags.output()
        packages = lines[lines.index('--------') + 1:]
        self.assertTrue(any(line.startswith('PyYAML') for line in packages), packages)


if __name__ == '__main__':
    unittest.main()

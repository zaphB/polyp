import unittest
import subprocess
import os

class TestBuildExample(unittest.TestCase):
  def _test_build(self, *options):

    # clean cache files
    for root, dirs, files in os.walk('test/pls'):
      for f in files:
        if f.endswith('.plb') or f.endswith('.gds') or f.endswith('.pdf'):
          os.remove(os.path.join(root, f))

    # run build process
    res = subprocess.run(['polyp', *options, 'test.pls'], cwd='test/pls')
    self.assertEqual(res.returncode, 0)

  def test_gdsBuild(self):
    self._test_build()
    self.assertTrue(os.path.exists('test/pls/test.gds'))

  def test_pdfBuild(self):
    self._test_build('-p')
    self.assertTrue(os.path.isdir('test/pls/test'))
    self.assertEqual(sorted(os.listdir('test/pls/test')),
                     sorted(['externalSymbol.pdf',
                             'legend.pdf',
                             '_main_.pdf',
                             'parametric_symbol_x14_y03.pdf',
                             'parametric_symbol_x16_y02.pdf',
                             'parametric_symbol_x18_y01.pdf',
                             'primitives.pdf']))

if __name__ == '__main__':
  unittest.main()

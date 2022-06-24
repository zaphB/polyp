import unittest
import subprocess
import os

class TestBuildExample(unittest.TestCase):
  def _test_build(self, files, opts=[], clean=True):
    # clean cache files
    if clean:
      for root, dirs, fs in os.walk('test/pls'):
        for f in fs:
          if f.endswith('.plb') or f.endswith('.gds') or f.endswith('.pdf'):
            os.remove(os.path.join(root, f))

    for f in files:
      # run build process
      res = subprocess.run(['polyp', *opts, f'{f}.pls'], cwd='test/pls')
      self.assertEqual(res.returncode, 0)

  def test_gdsBuild(self):
    files = ('test', 'globals', 'qrcode')
    self._test_build(files=files)
    for f in files:
      self.assertTrue(os.path.exists(f'test/pls/{f}.gds'))

   # zeit messen und mit clean=False vergleichen


  def test_pdfBuild(self):
    self._test_build(files=['test'], opts=['-p'])
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

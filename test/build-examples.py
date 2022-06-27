import unittest
import subprocess
import os
import time

class TestBuildExample(unittest.TestCase):
  def assertExists(self, path):
    if not os.path.exists(path):
      raise AssertionError(f'file {path} does not exist')

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
      if '-p' not in opts:
        self.assertExists(f'test/pls/{f}.gds')

  def test_gdsBuild(self):
    files = ('test', 'objects', 'qrcode')
    t0 = time.time()
    self._test_build(files=['caching'])
    dt = time.time()-t0

    t0 = time.time()
    self._test_build(files=['caching'], clean=False)
    self.assertLess(time.time()-t0, .5*dt)


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

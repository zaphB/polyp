import argparse
import gdspy
import threading
import signal
import os
import time
import traceback
import re
import polyp

def main():
  parser = argparse.ArgumentParser(description='Polyp layout renderer command line tool')
  parser.add_argument('layout', type=argparse.FileType('r'),
                      help='path to a polyp layout script (*.pls) to execute '
                           'or to a gds layout file (*.gds)')
  parser.add_argument('-n', '--no-output', action='store_true',
                      help='do not write results to file')
  parser.add_argument('-v', '--view', action='store_true',
                      help='open layout viewer to display result')
  parser.add_argument('-w', '--watch', action='store_true',
                      help='open viewer and refresh if source file changes, implies -v')
  parser.add_argument('-p', '--pdf', action='store_true',
                      help='write results as pdf file instead of gds')
  parser.add_argument('-f', '--force-rerender', action='store_true',
                      help='force rerender (including all cached .plb files)')

  args = parser.parse_args()
  try:
    if args.pdf:
      suffix = 'pdf'
    else:
      suffix = 'gds'
    if args.watch:
      if args.layout.name.endswith('.gds'):
        raise ValueError('Watching only supported for *.pls files.')
      thr = False
      parseTime = 10
      lasthash = ''
      currentLibMtl = [gdspy.current_library, False]
      try:
        while True:
          lastchange = os.stat(args.layout.name).st_mtime
          try:
            print('\n'*128+'------------------------------------------------------')
            print(' > Started rendering...')
            started = time.time()
            args.layout.seek(0)
            script = polyp.plsscript.PlsScript(args.layout, args.force_rerender)

            renderTime = time.time() - started
            print(time.strftime(' > Render time: %H:%M:%S.{:03.0f}', time.gmtime(renderTime))
                                                        .format((renderTime - int(renderTime))*1e3))

            if lasthash != script.hash:
              currentLibMtl[0] = gdspy.current_library
              time.sleep(2)
              lasthash = script.hash

              if not args.no_output:
                script.writeResults(re.sub('\.[^\.]*$', '', args.layout.name)+'.'+suffix)

              if not thr or not thr.is_alive():
                thr = threading.Thread(target=script.openViewer, args=(currentLibMtl,))
                thr.start()

              print(' > Successful.')
              parseTime = time.time() - started
            else:
              print(' > No changes.')

          except:
            print(' > Error:')
            traceback.print_exc()

          for _ in range(int((5+parseTime)*5)):
            time.sleep(.2)
            if thr and not thr.is_alive():
              break

            if lastchange != os.stat(args.layout.name).st_mtime:
              args.layout.close()
              args.layout = open(args.layout.name)
              break

          if thr and not thr.is_alive():
            break

      except KeyboardInterrupt:
        pass

      currentLibMtl[1] = True
      if thr and thr.is_alive():
        thr.join()

    else:
      script = polyp.plsscript.PlsScript(args.layout, args.force_rerender)
      if not args.no_output:
        script.writeResults(re.sub('\.[^\.]*$', '', args.layout.name)+"."+suffix)
      if args.view:
        script.openViewer()

  except Exception as e:
    if args.watch:
      print("Warning: watching not supported for .gds files.")

    try:
      gds = gdspy.GdsLibrary()
      path = args.layout.name
      args.layout.close()
      gds.read_gds(path)
      script = polyp.plsscript.PlsScript()
      script.gdsLib = gds
      if not args.no_output and suffix != 'gds':
        script.writeResults(re.sub('\.[^\.]*$', '', args.layout.name)+"."+suffix)
      if args.view:
        script.openViewer()
    except:
      raise e

if __name__ == "__main__":
  main()

# Verifica qual módulo `src.ppu` está sendo importado e o cwd no momento
import os
print('check_ppu_import start', os.getcwd())
import importlib
m = importlib.import_module('src.ppu')
print('module file:', getattr(m, '__file__', None))
print('FullPPU type:', getattr(m, 'FullPPU', None))
print('Done')

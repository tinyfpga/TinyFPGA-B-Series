from setuptools import setup, find_packages
setup(
  name = 'tinyfpgab',
  packages = find_packages(),
  install_requires = ['pyserial', 'timeit'],
  version = '1.0.0',
  description = 'A random test lib',
  author = 'Luke Valenty',
  author_email = 'lvalenty@gmail.com',
  url = 'https://github.com/tinyfpga/TinyFPGA-B-Series/tree/master/programmer', 
  download_url = 'https://github.com/tinyfpga/TinyFPGA-B-Series/releases/tinyfpgab-0.1.tar.gz', 
  keywords = ['fpga', 'tinyfpga', 'programmer'], 
  classifiers = [],
  entry_points = {
    'console_scripts': [
        'tinyfpgab = tinyfpgab.__main__:main'    
    ]    
  },
)

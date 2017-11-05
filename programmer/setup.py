from setuptools import setup, find_packages
setup(
  name = 'tinyfpgab',
  packages = find_packages(),
  install_requires = ['pyserial'],
  version = '1.0.3',
  description = 'Programmer for the TinyFPGA B-Series boards (http://tinyfpga.com)',
  author = 'Luke Valenty',
  author_email = 'lvalenty@gmail.com',
  url = 'https://github.com/tinyfpga/TinyFPGA-B-Series/tree/master/programmer', 
  keywords = ['fpga', 'tinyfpga', 'programmer'], 
  classifiers = [],
  entry_points = {
    'console_scripts': [
        'tinyfpgab = tinyfpgab.__main__:main'    
    ]    
  },
)

import os
import sys

sys.path.insert(0, os.path.abspath('../..'))

project = 'MainSequence'
copyright = '2018, David Masad'
author = 'David Masad'
version = ''
release = '0.1'
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
pygments_style = 'sphinx'
html_theme = 'alabaster'
html_static_path = ['_static']
autoclass_content = "both"
autodoc_member_order = "bysource"
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.napoleon']

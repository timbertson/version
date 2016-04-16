<img src="http://gfxmonk.net/dist/status/project/version.png">

version parses common files to find and change
the current version number of your project.

Supported file names are:

 - VERSION (obviously)
 - setup.py (python setuptools)
 - conf.py (sphinx configuration)

.. but new file formats can be added fairly easily when required.

# Usage:

	version

To print out your current version number(s) (one line per file).

	version \<number\>

To set the version number across all supported files.

	version +

To increment the minor version number (e.g 0.1.2 -> 0.1.3)
and save the results to every supported file.

	version ++

To increment the second-most minor version number
(e.g 0.1.2 -> 0.2.0)

.. and so on for more plusses, for as many as you require.

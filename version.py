#!/usr/bin/env python

import sys, os
import re
import traceback
VERBOSE=False

def version_file(val=None):
	v = "VERSION"
	if os.path.exists(v):
		if val is None:
			with open(v) as f:
				return f.read().strip()
		else:
			with open(v, 'w') as f:
				f.write(val)
			return True
version_file.desc = "VERSION"

def conf_file(val=None):
	return replace("conf.py", re.compile("""(?P<pre>(?:version|release)\s*=\s*u?['"])(?P<version>[^'"]*)"""), val)
conf_file.desc = "conf.py"

def replace(filename, regex, val):
	if not os.path.exists(filename):
		return None
	with open(filename) as f:
		lines = f.read()
	match = re.search(regex, lines)
	if val is None:
		return match.group('version') if match else None
	elif match:
		with open(filename, 'w') as f:
			f.write(re.sub(regex, r"\g<pre>%s" % (val,), lines))
		return True

def setup_py(val=None):
	return replace("setup.py", re.compile("""(?P<pre>version\s*=\s*u?['"])(?P<version>[^'"]*)"""), val)
setup_py.desc = "setup.py"

version_strategies = [setup_py, version_file, conf_file]
def version_types(new_version=None):
	def do(strategy):
		try:
			return strategy(new_version)
		except StandardError, e:
			print >> sys.stderr, "[ error: %s  (%s)]" % (e,strategy.desc)
			if VERBOSE:
				traceback.print_exc(file=sys.stderr)
	results = [Version(do(s), desc=s.desc) for s in version_strategies]
	return [r for r in results if r]

class Version(object):
	@classmethod
	def guess(cls):
		version_types()[0]

	def __init__(self, number, desc=None):
		self.number = number
		self.desc = desc
	
	def increment(self, levels=1):
		"""
		Increment the version component at `levels` least-significant
		position (1 is the least significant):

		>>> Version('1.2.3').increment()
		Version('1.2.4')
		>>> Version('1.2.3').increment(2)
		Version('1.3.0')
		>>> Version('1.2.3').increment(3)
		Version('2.0.0')

		-pre, -rc and -post suffixes are handled also:

		>>> Version('0.1.3-pre').increment()
		Version('0.1.3')
		>>> Version('0.1.3-post').increment()
		Version('0.1.4')
		>>> Version('0.1.3-post').increment(2)
		Version('0.2.0')
		>>> Version('0.1.3-rc').increment()
		Version('0.1.3')

		"""
		before, middle, after = split(self.number, levels)

		middle, suffix = split_suffix(middle)
		middle = int(middle) + 1
		if suffix is not None:
			if suffix in ('pre','rc'):
				# these suffixes mean we haven't reached
				# the stated version yet
				middle -= 1

		after = [0 for part in after]
		all_parts = ".".join(map(str, before + [middle] + after))
		return Version(all_parts)
	
	def suffix(self, suf):
		version, old_suf = split_suffix(self.number)
		return Version("%s-%s" % (version, suf))

	def __str__(self):
		return str(self.number)

	def describe(self):
		return "%-8s (%s)" % (self.desc, self.number)

	def __repr__(self):
		return "Version(%r)" % (self.number,)
	
	def __nonzero__(self):
		return self.number is not None

def prompt(msg):
	if sys.stdin.isatty():
		return raw_input(msg).strip().lower() in ('y','yes','')
	else:
		return True

def main(opts, input=None):
	"""
	
	>>> # hacky stuff to mock out functionality
	>>> import version
	>>> def version_types(new=None):
	...     if new: print ":: new %s" % (new,)
	...     return [Version('0.1.2', 'fake')]
	>>> version.version_types = version_types
	>>> class Object(object):
	... 	def __init__(self, **k):
	... 		[setattr(self, k, v) for k, v in k.items()]
	... 	def __getattr__(self, k): return None

	>>> version.main(Object(suffix='post'))
	fake     (0.1.2)
	:: new 0.1.2-post
	changed version in 1 files.

	>>> version.main(Object(suffix='post'), '+')
	fake     (0.1.2)
	:: new 0.1.3-post
	changed version in 1 files.

	>>> version.main(Object(suffix='pre'), '++')
	fake     (0.1.2)
	:: new 0.2.0-pre
	changed version in 1 files.

	>>> version.main(Object(raw=True))
	0.1.2
	"""
	versions = version_types()
	if opts.raw:
		print versions[0]
		return
	else:
		print "\n".join([version.describe() for version in versions])
	if input or opts.suffix:
		new_version = get_version(input, versions)
		if opts.suffix:
			new_version = new_version.suffix(opts.suffix)

		ok = prompt("\nchange version to %s? " % (new_version.number,))
		if not ok:
			sys.exit(0)
		changed = version_types(new_version.number)
		print "changed version in %s files." % (len(changed),)

def get_version(input, current_versions):
	"""
	>>> get_version('1234', [])
	Version('1234')
	>>> get_version('+', [Version('0.1.2')])
	Version('0.1.3')
	>>> get_version('+', [Version('0.1.9')])
	Version('0.1.10')
	>>> get_version('+', [Version('0.1')])
	Version('0.2')

	>>> get_version('++', [Version('0.1.2')])
	Version('0.2.0')
	>>> get_version('++', [Version('0.1')])
	Version('1.0')

	>>> get_version(None, [Version('0.1')])
	Version('0.1')

	"""
	if input is None:
		return current_versions[0]
	if all([char == '+' for char in input]):
		return current_versions[0].increment(len(input))
	elif input == 'date':
		import time
		v = time.strftime("%Y%m%d.%H%M")
		return Version(v)
	elif input == '=':
		return current_versions[0]
	else:
		return Version(input)

def split(version, idx):
	"""splits a version at idx from the lest-significant portion (starting at 1):

	>>> split('0.1.2', 1)
	(['0', '1'], '2', [])
	>>> split('0.1.2', 2)
	(['0'], '1', ['2'])
	>>> split('0.1.2', 3)
	([], '0', ['1', '2'])

	>>> split('0.1', 1)
	(['0'], '1', [])
	>>> split('0.1', 2)
	([], '0', ['1'])

	>>> split('0.1', 3)
	([], '0', ['1'])
	"""
	parts = version.split(".")
	middle = max(0, len(parts) - idx)
	more_significant = parts[:middle]
	less_significant = parts[middle+1:]
	return (more_significant, parts[middle], less_significant)


def split_suffix(part):
	"""
	Split a component into non-suffix and suffix component.
	If no suffix present, return (part, None)

	>>> split_suffix("1-pre")
	('1', 'pre')
	>>> split_suffix("2")
	('2', None)
	"""
	if not '-' in part:
		return (part, None)
	return tuple(part.rsplit('-', 1))

if __name__ == '__main__':
	import optparse
	p = optparse.OptionParser(usage="%prog [OPTIONS] [version]")
	p.add_option('-v', '--verbose', action='store_true', help="print more debugging info", default=False)
	p.add_option('-r', '--raw', action='store_true', help="print a single version string and nothing else")
	p.add_option('--pre',  action='store_const', const='pre', dest='suffix', help="set -pre suffix", default=None)
	p.add_option('--rc',   action='store_const', const='rc',  dest='suffix', help="set -rc suffix")
	p.add_option('--post', action='store_const', const='post',dest='suffix', help="set -post suffix")

	opts, args = p.parse_args()
	VERBOSE = opts.verbose

	try:
		main(opts, *args)
	except StandardError, e:
		print >> sys.stderr, e
		if VERBOSE: raise
	except (KeyboardInterrupt, EOFError):
		print ""

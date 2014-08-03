#!/usr/bin/env python

import sys, os
import re
import traceback
import itertools
import warnings
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

def json_file(filename):
	def _replacer(val=None):
		return replace(filename, re.compile("""(?P<pre>["']?version["']?\s*:\s*['"])(?P<version>[^'"]*)"""), val)
	_replacer.desc=filename
	return _replacer

package_json = json_file("package.json")
bower_json = json_file("bower.json")

def replace(filename, regex, val):
	if not os.path.exists(filename):
		if VERBOSE:
			print >> sys.stderr, "Skipping %s (file doesn't exist)" % (filename,)
		return None
	with open(filename) as f:
		lines = f.read()
	match = re.search(regex, lines)
	if VERBOSE and not match:
		print >> sys.stderr, "No match found in %s" % (filename,)
	if val is None:
		return match.group('version') if match else None
	elif match:
		with open(filename, 'w') as f:
			f.write(re.sub(regex, r"\g<pre>%s" % (val,), lines))
		return True

def setup_py(val=None):
	return replace("setup.py", re.compile("""(?P<pre>version\s*=\s*u?['"])(?P<version>[^'"]*)"""), val)
setup_py.desc = "setup.py"

version_strategies = [version_file, setup_py, conf_file, package_json, bower_json]
def version_types():
	versions = []
	for strat in version_strategies:
		value = _apply_strategy(strat)
		if value:
			versions.append(Version.parse(value, desc=strat.desc, expand_symbolic=True))
	return versions

def set_version(new_version):
	do = lambda s: _apply_strategy(s, new_version)
	results = map(do, version_strategies)
	successes = filter(bool, results)
	return list(successes)

def _apply_strategy(strategy, new_version=None):
	try:
		return strategy(new_version)
	except StandardError, e:
		print >> sys.stderr, "[ error: %s  (%s)]" % (e,strategy.desc)
		if VERBOSE:
			traceback.print_exc(file=sys.stderr)

def zip_cmp(pairs):
	for pair in pairs:
		c = cmp(*pair)
		if c != 0:
			return c
	return 0

class Version(object):
	@classmethod
	def guess(cls):
		return version_types()[0]
	
	@classmethod
	def parse(cls, number, desc=None, coerce=False, expand_symbolic=False):
		"""
		>>> Version.parse('2.0.1a5')
		Version('2.0.1-a5')

		>>> Version.parse('2.0.1a5', coerce=True)
		Version('2.0.1-pre-pre5')

		>>> Version.parse('2.0.1-a5', coerce=True)
		Version('2.0.1-pre-pre5')

		>>> Version.parse('2.0.1b3', coerce=True)
		Version('2.0.1-pre-post3')

		>>> Version.parse('2.0.1b3.0', coerce=True)
		Version('2.0.1-pre-post3.0')

		>>> Version.parse('2.0.1rc3', coerce=True)
		Version('2.0.1-rc3')

		>>> Version.parse('2.0.1-c3', coerce=True)
		Version('2.0.1-rc3')

		>>> Version.parse('2.0.1.pre.3', coerce=True)
		Version('2.0.1-pre-3')

		>>> Version.parse('2.0.1.pre.3.1', coerce=True)
		Version('2.0.1-pre-3.1')

		>>> Version.parse('2.0.1.pre', coerce=True)
		Version('2.0.1-pre')

		>>> import time
		>>> str(Version.parse('date', expand_symbolic=True)).startswith('0.' + time.strftime('%Y'))
		True
		"""
		if expand_symbolic:
			if number.lower() == 'date':
				import time
				return cls.parse("0." + time.strftime("%Y%m%d.%H.%M"), desc=desc)
		if coerce:
			number = number.lower()
			# combine lonely suffixes into their surrounding numbers
			number = re.sub(r'(\d+\.)?([a-z]+)(\.\d+)?', lambda match: match.group(0).replace(".", "-"), number)

		components = map(lambda s: VersionComponent.parse(s, coerce=coerce), number.split('.'))
		return cls(components, desc=desc)

	def __init__(self, components, desc=None):
		assert not isinstance(components, basestring), "use Version.parse()"
		self.number = '.'.join(map(str,components)) # XXX REMOVE
		self.components = components
		self.desc = desc
	
	def __cmp__(self, other):
		"""
		>>> sort = lambda *strs: map(str, sorted([Version.parse(x) for x in strs]))
		>>> sort('0.1','0.10','1.0')
		['0.1', '0.10', '1.0']
		>>> sort('1', '1-1', '1-pre','1-rc','1-rc1','1-post')
		['1-pre', '1-rc', '1-rc1', '1', '1-1', '1-post']
		>>> sort('1-post-pre', '1-post')
		['1-post-pre', '1-post']
		>>> Version.parse('0.1') == Version.parse('0.1.0')
		True
		>>> Version.parse('0.1') == Version.parse('0.1-0')
		True
		>>> Version.parse('0.1-1') == Version.parse('0.1-whatever1')
		False
		"""
		filler = VersionComponent(0)
		return zip_cmp(itertools.izip_longest(self.components, other.components, fillvalue=filler))

	def next(self):
		"""
		Increment the version number *minimally*, according to the zero-install
		version numbers spec (http://0install.net/interface-spec.html#versions):

		>>> Version.parse('1.0').next()
		Version('1.0-post')

		>>> Version.parse('1.0-pre').next()
		Version('1.0-pre1')
		>>> Version.parse('1.0-pre1').next()
		Version('1.0-pre2')

		>>> Version.parse('1.0-post1-pre').next()
		Version('1.0-post1-pre1')
		>>> Version.parse('1.0-post1-pre1').next()
		Version('1.0-post1-pre2')

		>>> Version.parse('1.0-rc').next()
		Version('1.0-rc1')
		>>> Version.parse('1.0-rc1').next()
		Version('1.0-rc2')

		>>> Version.parse('1.0-post').next()
		Version('1.0-post1')
		>>> Version.parse('1.0-post1').next()
		Version('1.0-post2')
		>>> Version.parse('1.0-post07').next()
		Version('1.0-post8')
		>>> Version.parse('1.0-post9').next()
		Version('1.0-post10')

		# arbitrary suffixes are supported, if present:
		>>> Version.parse('1.0-foo').next()
		Version('1.0-foo1')
		"""

		last = self.components[-1]
		components = self.components[:-1] + [last.next()]
		return Version(components)

	def increment(self, levels=1):
		"""
		Increment the version component at `levels` least-significant
		position (1 is the least significant):

		>>> Version.parse('1.2.3').increment()
		Version('1.2.4')
		>>> Version.parse('1.2.3').increment(2)
		Version('1.3.0')
		>>> Version.parse('1.2.3').increment(3)
		Version('2.0.0')

		-pre, -rc and -post suffixes are handled also:

		>>> Version.parse('0.1.3-pre').increment()
		Version('0.1.3')
		>>> Version.parse('0.1.3-post').increment()
		Version('0.1.4')
		>>> Version.parse('0.1.3-post').increment(2)
		Version('0.2.0')
		>>> Version.parse('0.1.3-rc').increment()
		Version('0.1.3')

		"""
		before, middle, after = rsplit_list(self.components, levels)
		middle = middle.increment()
		after = [VersionComponent(0) for part in after]
		all_parts = before + [middle] + after
		return Version(components=all_parts)
	
	def suffix(self, suf):
		version, old_suf = split_suffix(self.number)
		return Version.parse("%s-%s" % (version, suf))

	def __str__(self):
		return str(self.number)

	def describe(self):
		return "%-8s (%s)" % (self.desc, self.number)

	def __repr__(self):
		return "Version(%r)" % (self.number,)
	
	def __nonzero__(self):
		return self.number is not None

	def __hash__(self):
		"""

		>>> list(sorted(set(map(Version.parse, ("0.1", "0.2", "0.1")))))
		[Version('0.1'), Version('0.2')]
		"""
		return hash(self.number)

def prompt(msg):
	if sys.stdin.isatty():
		return raw_input(msg).strip().lower() in ('y','yes','')
	else:
		return True

def main(opts, input=None):
	"""
	
	>>> # hacky stuff to mock out functionality
	>>> import version
	>>> def set_version(new):
	...     print ":: new %s" % (new,)
	...     return [True]
	>>> def version_types():
	...     return [Version.parse('0.1.2', 'fake')]
	>>> version.version_types = version_types
	>>> version.set_version = set_version
	>>> version.prompt = lambda *a: True
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
		changed = set_version(new_version.number)
		print "changed version in %s files." % (len(changed),)

def get_version(input, current_versions):
	"""
	>>> get_version('1234', [])
	Version('1234')
	>>> get_version('+', [Version.parse('0.1.2')])
	Version('0.1.3')
	>>> get_version('+', [Version.parse('0.1.9')])
	Version('0.1.10')
	>>> get_version('+', [Version.parse('0.1')])
	Version('0.2')

	>>> get_version('++', [Version.parse('0.1.2')])
	Version('0.2.0')
	>>> get_version('++', [Version.parse('0.1')])
	Version('1.0')

	>>> get_version(None, [Version.parse('0.1')])
	Version('0.1')

	>>> get_version('.', [Version.parse('0.1')])
	Version('0.1-post')

	"""
	if input is None:
		return current_versions[0]
	if all([char == '+' for char in input]):
		return current_versions[0].increment(len(input))
	elif input == '=':
		return current_versions[0]
	elif input == '.':
		return current_versions[0].next()
	else:
		return Version.parse(input, expand_symbolic=True)

def rsplit_list(parts, idx):
	"""splits a version at idx from the lest-significant portion (starting at 1):
	>>> rsplit_list([0,1,2], 1)
	([0, 1], 2, [])
	>>> rsplit_list([0,1,2], 2)
	([0], 1, [2])
	>>> rsplit_list([0,1,2], 3)
	([], 0, [1, 2])

	>>> rsplit_list([0,1], 1)
	([0], 1, [])
	>>> rsplit_list([0,1], 2)
	([], 0, [1])

	>>> rsplit_list([0,1], 3)
	([], 0, [1])
	"""
	middle = max(0, len(parts) - idx)
	more_significant = parts[:middle]
	less_significant = parts[middle+1:]
	return (more_significant, parts[middle], less_significant)

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

sentinel=object()
def take_re(pattern, val, default=sentinel):
	"""
	>>> take_re('f.', 'foop')
	('fo', 'op')

	>>> take_re(re.compile('f.'), 'ofoop')
	Traceback (most recent call last):
	ValueError: Value 'ofoop' does not match regex 'f.'

	>>> take_re('f.', 'ofoop', None)
	(None, 'ofoop')
	"""
	match = re.match(pattern, val)
	if not match:
		if default is sentinel:
			raise ValueError("Value %r does not match regex %r" % (val, getattr(pattern, 'pattern', pattern)))
		return (default, val)
	found = match.group(0)
	return (found, val[len(found):])

def _replace_suffix_aliases(s):
	alpha, number = take_re(_alphas_re, s, '')
	if alpha == 'a':
		return ['pre', 'pre' + number]
	if alpha == 'b':
		return ['pre', 'post' + number]
	if alpha == 'c':
		return ['rc' + number]
	# everything else, we leave as-is
	return [s]

_digits_re = re.compile('\d+')
_alphas_re = re.compile('[a-z]+')

class VersionComponent(object):
	"""
	>>> VersionComponent.parse("1").value
	1
	>>> VersionComponent.parse("1-pre2").suffixes
	[pre2]
	>>> VersionComponent.parse("1-pre2").suffixes[0].rank
	2
	>>> str(VersionComponent.parse("10-pre2"))
	'10-pre2'

	>>> str(VersionComponent.parse("b2"))
	'0-b2'

	alpha an beta both need to map to "pre-something". This
	isn't pretty, but should preserve ordering in all cases:

	>>> str(VersionComponent.parse("b2", coerce=True))
	'0-pre-post2'

	>>> str(VersionComponent.parse("a2", coerce=True))
	'0-pre-pre2'

	>>> str(VersionComponent.parse("1a2", coerce=True))
	'1-pre-pre2'

	>>> str(VersionComponent.parse("1_a2", coerce=True))
	'1-pre-pre2'

	>>> str(VersionComponent.parse("1-c2", coerce=True))
	'1-rc2'

	>>> str(VersionComponent.parse("rc2", coerce=True))
	'0-rc2'

	>>> str(VersionComponent.parse("p2", coerce=True))
	'0-p2'
	"""
	@classmethod
	def parse(cls, val, coerce=False):
		try:
			seps = '-_' if coerce else '-'
			value, suffixes = take_re(_digits_re, val, '')
			suffixes = suffixes.lstrip(seps)
			suffixes = re.split('[%s]' % (seps,), suffixes)
			if coerce:
				suffixes = itertools.chain(*map(_replace_suffix_aliases, suffixes))
			suffixes = filter(None, suffixes)
			suffixes = map(Suffix.parse, suffixes)
			value = int(value) if value else 0
			return cls(value, suffixes)
		except (ValueError) as e:
			raise ValueError("Can't parse version component %s: %s" % (val, e))

	def __init__(self, value, suffixes=[]):
		self.value = value
		self.suffixes = suffixes
	
	def __str__(self):
		return '-'.join(map(str, [self.value] + self.suffixes))

	def __repr__(self):
		return "<VersionComponent %s>" % (self,)
	
	def __cmp__(self, other):
		my_parts = [self.value] + self.suffixes
		other_parts = [other.value] + other.suffixes
		return zip_cmp(itertools.izip_longest(my_parts, other_parts, fillvalue = Suffix(None)))
	
	def next(self):
		if not self.suffixes:
			new_suffixes = [Suffix.parse(None).next()]
		else:
			new_suffixes = self.suffixes[:-1] + [self.suffixes[-1].next()]
		return type(self)(self.value, new_suffixes)

	def increment(self):
		value = self.value + 1
		if self.suffixes and self.suffixes[0] < Suffix():
			# -pre or -rc increment by simply removing the suffix
			value = self.value
		return VersionComponent(value)

KNOWN_SUFFIXES = ['pre', 'rc', None, 'post']
class Suffix(object):
	"""
	>>> list(map(str, sorted([
	... Suffix.parse('pre'),
	... Suffix.parse('post'),
	... Suffix.parse('rc'),
	... Suffix.parse('pre1'),
	... Suffix.parse('post1'),
	... Suffix.parse('rc3'),
	... Suffix.parse('pre2'),
	... Suffix.parse(None),
	... ])))
	['pre', 'pre1', 'pre2', 'rc', 'rc3', '', 'post', 'post1']
	>>> bool(Suffix.parse('pre'))
	True
	>>> bool(Suffix.parse(None))
	False
	"""
	def __init__(self, name=None, rank=0):
		self.name = name
		self.rank = rank
	
	@classmethod
	def parse(cls, suffix):
		if suffix is None:
			return cls()
		else:
			name, rank = cls._split(suffix)
			return cls(name, rank)
	
	def __nonzero__(self):
		return self.name is not None
	
	def __repr__(self):
		return ''.join([str(part) for part in (self.name, self.rank) if part])

	def next(self):
		"""
		>>> Suffix.parse('rc').next()
		rc1
		>>> Suffix.parse('rc9').next()
		rc10
		>>> Suffix.parse(None).next()
		post
		"""
		if not self:
			return Suffix('post', 0)
		else:
			return Suffix(self.name, self.rank + 1)
	
	@classmethod
	def _split(self, suffix):
		"""
		>>> Suffix._split('pre')
		('pre', 0)
		>>> Suffix._split('rc5')
		('rc', 5)
		>>> Suffix._split('rc11')
		('rc', 11)
		"""
		text, digits = take_re(_alphas_re, suffix, None)
		return (text, int(digits or '0'))

	def __cmp__(self, other):
		"""
		>>> Suffix(None) == Suffix('',0)
		True
		"""
		return cmp(
			( self._name_ord(), self.rank),
			(other._name_ord(), other.rank))

	def _name_ord(self):
		try:
			return KNOWN_SUFFIXES.index(self.name or None)
		except ValueError:
			return len(KNOWN_SUFFIXES)


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

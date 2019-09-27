<%! import pyhpy %>
<%block name="PAGE_CSS">
    <link rel="stylesheet" type="text/css" href="${pyhpy.url('/static/css/muck.css')}">
    <link rel="stylesheet" type="text/css" href="${pyhpy.url('/static/css/home.css')}">
</%block>
<%block name="LOGO_NAME"><div class=name>Muck</div></%block>
<%block name="LOGO_SLOGAN"><div id=slogan>loves jigsaw puzzles &amp; IKEA furniture</div></%block>
<%block name="LOGO_IMAGE"><div class=asciiLogo><%text>
            ____ 
           /\  __\_ 
          /  \/ \___\ 
          \     /___/ 
       /\_/     \    \ 
      /          \____\ 
  ___/\       _  /    / 
 / \/  \     /_\/____/ 
 \     /     \___\ 
 /     \_/\  /   / 
/          \/___/ 
\  _       /   / 
 \/_|     /___/ 
    /     \___\ 
    \  /\_/___/ 
     \/___/ 
</%text></div></%block>


`muck` is a general-purpose build tool, sort of like [make](https://www.gnu.org/software/make/), but with a different design philosophy:  `make` is "top-down" (you specify the high-level target you want to build, and `make` gathers and assembles the necessary pieces), `muck` is "bottom-up" (it looks at the available pieces, and figures out what can be built with them).  The Muck model enables automatic discovery of dependencies, and also enables you to write Muckfiles in *any* programming language.

`muck` excels in situations where dependencies are numerous, dynamic, or difficult-to-know.  (A good example of this situation is static websites.)

`muck` is based on [Fabricate](https://github.com/brushtechnology/fabricate).  It uses `strace` to monitor execution and extract dependency information.


=== Example Muckfile ===

Here is a very simple exmple, so that you can easily compare Makefiles vs Muckfiles:

```
#!/usr/bin/env python3

# This Muckfile will do the same thing as this Makefile:
# (Notice that the Makefile needs to list the .h files,
#  while the Muckfile does not.)
#
# mycmd: a.c b.c a.h b.h c.h d.h
#     gcc -o mycmd a.c b.c -I.

import os

if os.environ['MUCK_REL_PATH']=='a.c': print('gcc -o mycmd a.c b.c -I.')
```

Here is a more realistic example, used for building static websites:

```
#!/usr/bin/env python

# Muckfiles can be written in any language.  They just need to print shell commands to stdout.
#
# Muck provides a few environment variables as inputs:
#
#     MUCK_IN_ROOT   -- The input root directory.  Example:  /path/to/proj/in
#     MUCK_OUT_ROOT  -- The output root directory. Example:  /path/to/proj/out
#     MUCK_REL_PATH  -- The file to process, relative to the MUCK_IN_ROOT.  Ex: a/b.c
#
# Muckfiles should be "functional";  For the same set of inputs (env vars),
# they should always produce the same set of outputs (shell commands).

import os, sys
from fnmatch import fnmatch

# Pre-calculate a few things to make our command recipes simpler:
relPath = os.environ['MUCK_REL_PATH']
filename = os.path.basename(relPath)
inRoot, outRoot = os.environ['MUCK_IN_ROOT'], os.environ['MUCK_OUT_ROOT']
inPath  = os.path.join(inRoot,  os.environ['MUCK_REL_PATH'])
outPath = os.path.join(outRoot, os.environ['MUCK_REL_PATH'])
inDir, outDir = os.path.dirname(inPath), os.path.dirname(outPath)

def end(string=None):
    if string: print(string)
    sys.exit()

def mk_outdir(): print('''
{ set +x; } 2>/dev/null  # Silently disable tracing
mkdir -p %(outDir)r
set -x                   # Re-enable tracing
'''%globals())

def SKIP(verbose=False):
    if verbose: print >>sys.stderr, 'Skipping:', relPath
    sys.exit()

def ENTER_SUBDIR(): end('''
{ set +x; } 2>/dev/null  # Silently disable tracing
true                     # The command doesn't actually matter, as long as it succeeds.
echo DIR DONE: $MUCK_REL_PATH/
find . >/dev/null        # So we re-visit this dir if any content changes.
''')

def COPY():
    mk_outdir()
    end('cp --preserve=all %(inPath)r %(outPath)r'%globals())

def MAKO():
    noext, ext = os.path.splitext(relPath)    # Chop off the .mako extension.
    assert ext == '.mako'
    values = {'noext':noext}; values.update(globals())
    mk_outdir()
    end('python -m pyhpy.cmd --template-dir=%(inRoot)r --module-dir=%(inRoot)r /%(relPath)r >%(noext)r'%values)

def MARKDOWN(): end('../PyHPy/bin/MARKDOWN')



if fnmatch(filename, '_*'):           SKIP()
if os.path.isdir(relPath):            ENTER_SUBDIR()


# A simple way to enable building of specific items (for improved development iteration time):
for pat in os.environ.get('MUCK_REL_PATH_PREFIXES', '').split('|'):   # If the env var is not set, the resulting 'pat' will be '', which matches everything.
    if relPath.startswith(pat): break
else: SKIP(True)


if fnmatch(filename, '.*'):           SKIP()
if fnmatch(filename, '*.meta'):       SKIP()
if fnmatch(filename, '*.pyc'):        SKIP()
if fnmatch(filename, '*.mako.py'):    SKIP()  # Mako-generated module
if fnmatch(filename, '*.mako'):       MAKO()
if fnmatch(filename, '*.md'):         MARKDOWN()
if fnmatch(filename, '*'):            COPY()  # Default processor
```


=== Usage ===

    muck IN_DIR OUT_DIR


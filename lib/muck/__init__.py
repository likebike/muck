#!/usr/bin/env python

# Created by Christopher Sebastian, 2016-03-01

# Name brainstorm session:
#     jumble craft transform metamorphose morph convert redo regen process trans glue tape
#     haystack rummage weld muddle hunt process compile render conjure do invoke distill
#     churn fudge publish remake instruct change cook cobble classify myke mike muck use
#     abuse squander eat "Here, use this.  HUT" use uzit buse abuz buze


import os, sys, subprocess, json, atexit, stat
import muck.fabricate

DEBUG = int(os.environ.get('DEBUG','0'))    # Helps you understand why things are getting rebuilt.
DEPDIR = os.environ.get('DEPDIR', '/')      # Allows you to restrict dependency paths to improve performance.

MUCKFILE = 'Muckfile'
MUCKCMDS = '.muck_commands'
MUCKDEPS = '.muck_deps'

def listdir(dirPath):
    # I have applied some hacks to fabricate.py to enable me to depend on directory listings.  See :MUCK_LISTDIR: stuff.
    try: os.close(os.open(dirPath, os.O_RDONLY))
    except: pass
    return os.listdir(dirPath)

def childEnv(inRoot, relPath, outRoot):
    if relPath.startswith('./'): relPath = relPath[2:]
    env = dict(os.environ)
    # Set some environment variables that might be useful:
    env['MUCK_IN_ROOT'] = inRoot
    env['MUCK_REL_PATH'] = relPath
    env['MUCK_OUT_ROOT'] = outRoot
    env['PYTHON'] = sys.executable
    # Also, make sure that the Python running this script is first on $PATH:
    # This way, scripts can use the same Python with "#!/usr/bin/env python".
    pathPieces = [os.path.dirname(sys.executable)]
    if 'PATH' in os.environ: 
        for p in os.environ['PATH'].split(os.pathsep):
            if p not in pathPieces: pathPieces.append(p)
    env['PATH'] = os.pathsep.join(pathPieces)
    return env
def extractMuckVars(env):
    out = {}
    for k,v in env.items():
        if k.upper().startswith('MUCK'): out[k] = v
    return out
def extractUserMuckVars(env):  # User-defined MUCK env vars.
    out = {}
    for k,v in extractMuckVars(env).items():
        if k in ['MUCK_IN_ROOT', 'MUCK_REL_PATH', 'MUCK_OUT_ROOT']: continue
        out[k] = v
    return out
def envString(env): return ' '.join(['%s=%s'%(k,v) for k,v in sorted(env.items())])

def chmod_add(path, permissions): os.chmod(path, os.stat(path).st_mode | permissions)

class CD(object):
    def __init__(self, path): self.old_dir, self.new_dir = os.getcwd(), path
    def __enter__(self): os.chdir(self.new_dir)
    def __exit__(self, *args): os.chdir(self.old_dir)


# reload() protection:
try: _muckRoots, _muckers
except NameError: _muckRoots, _muckers = {}, {}
class NoMuckRoot(Exception): pass
def getMuckRoot(path): # Traverse up the path until we find a Muckfile:
    assert os.path.isabs(path)
    if path not in _muckRoots:
        if os.path.isdir(path) and  os.path.exists(os.path.join(path, MUCKFILE)): _muckRoots[path] = path
        elif not path or path=='/': raise NoMuckRoot('Unable to find %s'%(MUCKFILE,))
        else: _muckRoots[path] = getMuckRoot(os.path.dirname(path))
    return _muckRoots[path]

def copyPathTraversal(origDir1, newDir1, origDir2):
    assert os.path.isdir(origDir1) and os.path.isdir(newDir1) and os.path.isdir(origDir2)
    newDir2 = os.path.normpath(os.path.join(origDir2, os.path.relpath(newDir1, origDir1)))
    return newDir2

def getMucker(inRoot, outRoot):
    assert getMuckRoot(inRoot) == inRoot
    if inRoot not in _muckers: _muckers[inRoot] = muck._Mucker(inRoot, outRoot)
    return _muckers[inRoot]

def FAIL(code):
    print >> sys.stderr, '\nBuild Failed!  Exit Code %r'%(code,)
    sys.exit(1)

# Override some fabricate.py functionality:
def muck_hasher(path):
    if not isinstance(path, bytes): path = path.encode('utf-8')
    try:
        with open(path, 'rb') as f: return muck.fabricate.md5func(f.read()).hexdigest()
    except IOError:
        if hasattr(os, 'readlink') and os.path.islink(path):
            return muck.fabricate.md5func(os.readlink(path)).hexdigest()
        if path.startswith(':MUCK_LISTDIR:'):     #  Note that 'rsync' does a terrible job of syncing directory modification times -- it sets the dir mtime *before* descending into it, therefore if any contents get updated the synced dir mtime is lost.  Therefore, we can't just delegate this work over to mtime_hasher -- we need to use the directory listing for maximum reliability.
            dirPath = path[len(':MUCK_LISTDIR:'):]
            try:
                dirList = ' '.join(sorted(os.listdir(dirPath)))
                return muck.fabricate.md5func(dirList).hexdigest()
            except: pass
    return None

            
    
FAB_COUNT = 0
class _Fab(muck.fabricate.Builder):
    def __init__(self, inRoot, *args, **kwargs):
        self.inRoot = inRoot
        kwargs['runner'] = 'strace_runner'      # Hard-code StraceRunner since I have never tested with anything else (and don't plan to).
        kwargs['hasher'] = muck_hasher
        super(_Fab, self).__init__(*args, **kwargs)
        self.runner.build_dir = self.inRoot   # StraceRunner uses its build_dir for path chopping.
    def muckCommand(self, command): return envString(self.muckVars) + ' ' + command + ' ' + self.muckInput
    def _run(self, *args, **kwargs):
        assert not self.parallel_ok   #  This hack does not work for parallel code.  I'll improve it if/when I encounter the need to.
        assert not hasattr(self, 'muckVars')  and  not hasattr(self, 'muckInput')  # Try to catch unexpected behavior.
        self.muckVars, self.muckInput = {}, kwargs.get('input', None)
        if 'env' in kwargs: self.muckVars=extractMuckVars(kwargs['env'])
        assert self.muckVars['MUCK_IN_ROOT'] == self.inRoot  and  self.runner.build_dir == self.inRoot
        with CD(self.inRoot): # We must change our own CWD because fabricate.py does not know how to extract the 'cwd' argument from the Popen kwargs.  If this ends up being a concurrency issue, i'll need to adjust fabricate.py to handle per-builder CWD.
            x = super(_Fab, self)._run(*args, **kwargs)
            del self.muckVars, self.muckInput            # Try to catch unexpected behavior.
            return x
    def cmdline_outofdate(self, command):
        global FAB_COUNT
        result = super(_Fab, self).cmdline_outofdate(self.muckCommand(command))
        if result: FAB_COUNT += 1    ### Questionable logic, definitely not concurrency-safe.
        return result
    def done(self, command, deps, output): return super(_Fab, self).done(self.muckCommand(command), deps, output)

class _Mucker(object):
    def __init__(self, inRoot, outRoot, debug=DEBUG):
        assert os.path.isabs(inRoot)
        self.inRoot = inRoot
        self.muckfilePath = os.path.join(self.inRoot, MUCKFILE)
        assert os.path.exists(self.muckfilePath), '%s not found!'%(self.muckfilePath,)
        chmod_add(self.muckfilePath, stat.S_IXUSR)
        assert inRoot not in _muckers, 'Already created a mucker with this inRoot!'
        self.hashKey = '__hash(%s)__'%(MUCKFILE,)
        assert os.path.isabs(outRoot)
        self.outRoot = outRoot
        self.cmdsPath = os.path.join(inRoot, MUCKCMDS)
        self._cmdsCache = None
        self.fab = _Fab(self.inRoot, ignore=r'^\.{1,2}$|^/(dev|proc|sys)/', dirs=[DEPDIR], depsname=os.path.join(inRoot, MUCKDEPS), quiet=True, debug=debug)  # ignore: . .. /dev/ /proc/ /sys/
    def writeCommandsCache(self):
        if self._cmdsCache:
            with open(self.cmdsPath, 'w') as f: json.dump(self._cmdsCache, f, indent=2, sort_keys=True)
            os.chmod(self.cmdsPath, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IWGRP|stat.S_IROTH|stat.S_IWOTH)
    def getCommandsCache(self):
        if self._cmdsCache == None:
            try: self._cmdsCache = json.load(open(self.cmdsPath))
            except: self._cmdsCache = {}
            atexit.register(self.writeCommandsCache)
            curHash = muck.fabricate.md5_hasher(self.muckfilePath)
            if self._cmdsCache.get(self.hashKey, None) != curHash: self._cmdsCache = {self.hashKey:curHash}
        return self._cmdsCache
    def getCommand(self, relPath):
        cmdsCache = self.getCommandsCache()
        key = envString(extractUserMuckVars(os.environ))
        if key: key += ' '
        key += relPath + ' --> ' + os.path.relpath(self.outRoot, self.inRoot)
        if key not in cmdsCache:
            with CD(self.inRoot):
                proc = subprocess.Popen([self.muckfilePath], env=childEnv(self.inRoot, relPath, self.outRoot), stdout=subprocess.PIPE)
                result = proc.stdout.read().strip()
                retcode = proc.wait()
                if retcode != 0: FAIL(retcode)
            # 'result' can be one of the following:
            #     * Nothing  (indicates a skip)
            #     * A multi-line sh command like "../bin/render" or "gcc -c '/a/b/c.c'"
            cmdsCache[key] = result
        return cmdsCache[key]
    def run(self, relPath):
        cmd = self.getCommand(relPath)
        if not cmd: return
        try: self.fab.run(['/bin/sh', '-euxs'],
                          # cwd=self.inRoot,  # I do not send 'cwd' because fabricate.py doesn't know how to deal with it, and all the strace-detected paths get messed up.  I do some tricks in _Fab to compensate for this.
                          env=childEnv(self.inRoot, relPath, self.outRoot),
                          input=cmd)   # Send our command to stdin.
        except fabricate.ExecutionError as e: FAIL(e.args[2])

def build(inRoot, relPath, outRoot):
    assert os.path.isabs(inRoot) and not os.path.isabs(relPath) and os.path.isabs(outRoot)
    assert inRoot[-1]!='/'  and  relPath[-1]!='/'  and  outRoot[-1]!='/'
    assert getMuckRoot(inRoot) == inRoot
    inPath = os.path.normpath(os.path.join(inRoot, relPath))
    assert os.path.exists(inPath)
    thisMucker = getMucker(inRoot, outRoot)
    def _build(relPath):
        if not thisMucker.getCommand(relPath): return # Check whether this item should be skipped.
        xPath = os.path.normpath(os.path.join(inRoot, relPath))
        if relPath != '.':   # '.' means that we *are* processing a muckRoot already.
            xRoot = getMuckRoot(xPath)
            if xRoot == xPath: return buildInfinity(xRoot, '.', copyPathTraversal(inRoot, xRoot, outRoot))
            assert xRoot == inRoot
        if os.path.islink(xPath) and os.path.isdir(xPath):
            print >> sys.stderr, 'Directory symlinks are not yet supported:', xPath  # Need to handle infinite cycles and other crazy stuff.
            return
        if os.path.isdir(xPath):
            for x in sorted(os.listdir(xPath)):
                if relPath == '.'  and  x in [MUCKFILE, MUCKCMDS, MUCKDEPS]: continue  # Ignore Muck-related files.
                _build(os.path.join(relPath, x))
        thisMucker.run(relPath)
    _build(relPath)
    
def buildInfinity(inRoot, relPath, outRoot, isTopLevel=False):
    global FAB_COUNT
    someWorkWasPerformed = False
    # print >> sys.stderr, 'Starting:', os.path.join(inRoot, MUCKFILE)   # Due to the way that the 'infinity' process works, I do not show when we start a new root;  It would be confusing to users.
    while True:
        startFabCount = FAB_COUNT
        if isTopLevel:   # Really, it's better to always reset each individual cache on each loop, rather than just at the top level, but I'm seeing if this can provide some performance boost while still being logically correct.
            for n,m in _muckers.items(): m.fab.hash_cache = {}   # Reset all the caches so that changes get noticed.
        build(inRoot, relPath, outRoot)
        if FAB_COUNT==startFabCount: break
        someWorkWasPerformed = True
    if someWorkWasPerformed: print >> sys.stderr, 'Done:', os.path.join(inRoot, MUCKFILE)

def main():
    inPath = os.getcwd()
    if len(sys.argv) >= 2: inPath = os.path.abspath(sys.argv[1])
    assert os.path.exists(inPath)
    try: inRoot = getMuckRoot(inPath)
    except NoMuckRoot as e:
        print >> sys.stderr, e
        sys.exit(1)
    relPath = os.path.relpath(inPath, inRoot)
    outRoot = inRoot
    if len(sys.argv) >= 3: outRoot = os.path.abspath(sys.argv[2])
    buildInfinity(inRoot, relPath, outRoot, isTopLevel=True)

if __name__ == '__main__': main()








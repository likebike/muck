#!/usr/bin/env python

# Created by Christopher Sebastian, 2016-03-01

# Name brainstorm session:
#     jumble craft transform metamorphose morph convert redo regen process trans glue tape
#     haystack rummage weld muddle hunt process compile render conjure do invoke distill
#     churn fudge publish remake instruct change cook cobble classify myke mike muck use
#     abuse squander eat "Here, use this.  HUT" use uzit buse abuz


import os, sys, fnmatch, re, subprocess, json, string, atexit, stat
import muck.fabricate

MUCKFILE = 'Muckfile'
MUCKCMDS = '.muck_commands'
MUCKDEPS = '.muck_deps'

def childEnv(inRoot, relPath, outRoot):
    env = dict(os.environ)
    # Set some environment variables that might be useful:
    env['MUCK_IN_DIR'] = inRoot
    env['MUCK_REL_PATH'] = relPath
    env['MUCK_OUT_DIR'] = outRoot
    env['PYTHON'] = sys.executable
    # Also, make sure that the Python running this script is first on $PATH:
    # This way, scripts can use the same Python with "#!/usr/bin/env python".
    pathPieces = [os.path.dirname(sys.executable)]
    if 'PATH' in os.environ: 
        for p in os.environ['PATH'].split(os.pathsep):
            if p not in pathPieces: pathPieces.append(p)
    env['PATH'] = os.pathsep.join(pathPieces)
    return env

def chmod_add(path, permissions): os.chmod(path, os.stat(path).st_mode | permissions)

class CD(object):
    def __init__(self, path): self.old_dir, self.new_dir = os.getcwd(), path
    def __enter__(self): os.chdir(self.new_dir)
    def __exit__(self, *args): os.chdir(self.old_dir)


# reload() protection:
try: _muckRoots, _muckers
except NameError: _muckRoots, _muckers = {}, {}
class NotAMuckRoot(Exception): pass
def getMuckRoot(path): # Traverse up the path until we find a Muckfile:
    assert os.path.isabs(path)
    if path not in _muckRoots:
        if os.path.isdir(path) and  os.path.exists(os.path.join(path, MUCKFILE)): _muckRoots[path] = path
        elif not path or path=='/': raise NotAMuckRoot('Unable to find %s'%(MUCKFILE,))
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

# Override some fabricate.py functionality:
FAB_COUNT = 0
class _Fab(muck.fabricate.Builder):
    def __init__(self, inRoot, *args, **kwargs):
        self.inRoot = inRoot
        kwargs['runner'] = 'strace_runner'      # Hard-code StraceRunner since I have never tested with anything else (and don't plan to).
        super(_Fab, self).__init__(*args, **kwargs)
        self.runner.build_dir = self.inRoot   # StraceRunner uses its build_dir for path chopping.
    def muckCommand(self, command): return ' '.join(['%s=%s'%(k,v) for k,v in sorted(self.muckVars.items())]) + ' ' + command + ' ' + self.muckInput
    def _run(self, *args, **kwargs):
        assert not self.parallel_ok   #  This hack does not work for parallel code.  I'll improve it if/when I encounter the need to.
        assert not hasattr(self, 'muckVars')  and  not hasattr(self, 'muckInput')  # Try to catch unexpected behavior.
        self.muckVars, self.muckInput = {}, kwargs.get('input', None)
        if 'env' in kwargs:
            for k,v in kwargs['env'].items():
                if k.upper().startswith('MUCK'): self.muckVars[k] = v
        assert self.muckVars['MUCK_IN_DIR'] == self.inRoot  and  self.runner.build_dir == self.inRoot
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
    def __init__(self, inRoot, outRoot, debug=False):
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
        self.fab = _Fab(self.inRoot, ignore=r'^\.{1,2}$|^/(dev|proc|sys)/', dirs=['/'], depsname=os.path.join(inRoot, MUCKDEPS), quiet=True, debug=debug)  # ignore: . .. /dev/ /proc/ /sys/
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
        key = ' --> '.join((relPath, os.path.relpath(self.outRoot, self.inRoot)))
        if key not in cmdsCache:
            with CD(self.inRoot):
                result = subprocess.Popen([self.muckfilePath], env=childEnv(self.inRoot, relPath, self.outRoot), stdout=subprocess.PIPE).stdout.read().strip()
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
        except fabricate.ExecutionError as e:
            print >> sys.stderr, '\nBuild Failed!  Exit Code %r'%(e.args[2],)
            # print >> sys.stderr, 'There was an error while running this command: %s\n'%(cmd,)
            # import traceback; traceback.print_exc()
            sys.exit(1)

def buildRoot(inRoot, relPath, outRoot):
    assert os.path.isabs(inRoot) and not os.path.isabs(relPath) and os.path.isabs(outRoot)
    assert inRoot[-1]!='/'  and  relPath[-1]!='/'  and  outRoot[-1]!='/'
    assert getMuckRoot(inRoot) == inRoot
    inPath = os.path.normpath(os.path.join(inRoot, relPath))
    assert os.path.exists(inPath)
    thisMucker = getMucker(inRoot, outRoot)
    def build(relPath):
        if not thisMucker.getCommand(relPath): return # Check whether this item should be skipped.
        xPath = os.path.join(inRoot, relPath)
        xRoot = getMuckRoot(xPath)
        if xRoot == xPath: return buildInfinity(xRoot, '.', copyPathTraversal(inRoot, xRoot, outRoot))
        assert xRoot == inRoot
        if os.path.islink(xPath) and os.path.isdir(xPath):
            print >> sys.stderr, 'Directory symlinks are not yet supported:', xPath  # Need to handle infinite cycles and other crazy stuff.
        elif os.path.isdir(xPath):
            for x in sorted(os.listdir(xPath)): build(os.path.join(relPath, x))
        else: thisMucker.run(relPath)
    if relPath == '.':
        # We are processing a new Muck Root directory.  Need to iterate over directory contents.
        for x in sorted(os.listdir(inRoot)):
            if x in [MUCKFILE, MUCKCMDS, MUCKDEPS]: continue  # Ignore Muck-related files.
            build(x)
    else: build(relPath)
    
def buildInfinity(inRoot, relPath, outRoot, isTopLevel=False):
    global FAB_COUNT
    someWorkWasPerformed = False
    # print >> sys.stderr, 'Starting:', os.path.join(inRoot, MUCKFILE)   # Due to the way that the 'infinity' process works, I do not show when we start a new root;  It would be confusing to users.
    while True:
        startFabCount = FAB_COUNT
        if isTopLevel:   # Really, it's better to always reset each individual cache on each loop, rather than just at the top level, but I'm seeing if this can provide some performance boost while still being logically correct.
            for n,m in _muckers.items(): m.fab.hash_cache = {}   # Reset all the caches so that changes get noticed.
        buildRoot(inRoot, relPath, outRoot)
        if FAB_COUNT==startFabCount: break
        someWorkWasPerformed = True
    if someWorkWasPerformed: print >> sys.stderr, 'Done:', os.path.join(inRoot, MUCKFILE)

def main():
    inPath = os.getcwd()
    if len(sys.argv) >= 2: inPath = os.path.abspath(sys.argv[1])
    assert os.path.exists(inPath)
    try: inRoot = getMuckRoot(inPath)
    except NotAMuckRoot as e:
        print >> sys.stderr, e
        sys.exit(1)
    relPath = os.path.relpath(inPath, inRoot)
    outRoot = inRoot
    if len(sys.argv) >= 3: outRoot = os.path.abspath(sys.argv[2])
    buildInfinity(inRoot, relPath, outRoot, isTopLevel=True)

if __name__ == '__main__': main()








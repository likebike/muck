#!/usr/bin/env python

# Created by Christopher Sebastian, 2016-03-01

import os, sys, fnmatch, re, subprocess, json, string, atexit, stat
import myke.fabricate


# def walk(path):
#     for dirpath, dirnames, filenames in os.walk(path):
#         symlinks = []
#         for i,filename in reversed(list(enumerate(filenames))):
#             absPath = os.path.join(dirpath, filename)
#             if os.path.islink(absPath):
#                 symlinks.append(filename)
#                 filenames.pop(i)
#         for i,dirname in reversed(list(enumerate(dirnames))):
#             absPath = os.path.join(dirpath, dirname)
#             if os.path.islink(absPath):
#                 symlinks.append(dirname)
#                 dirnames.pop(i)
#         dirnames.sort(); filenames.sort(); symlinks.sort();  # So the real references can be returned.
#         yield dirpath, dirnames, filenames, symlinks
# 
# 
# def walkAndClassify(rootDir, outDir):
#     results = {}
#     for dirpath, dirnames, filenames, symlinks in pyhpy.sync.walk(rootDir):
#         def projRelPath(f):
#             absPath = os.path.join(dirpath, f)
#             assert absPath.startswith(rootDir)
#             relPath = absPath[len(rootDir):]  # Path relative to rootDir.  /path/to/root/a/b/c becomes /a/b/c
#             assert relPath[0] == os.sep
#             return relPath
#         for dirname in list(dirnames):
#             cmd = getCommand(rootDir, projRelPath(dirname), outDir)
#             if len(cmd)==1  and  os.path.basename(cmd[0])=='SKIP': dirnames.remove(dirname)
#         for filename in (filenames+symlinks): results[projRelPath(filename)] = getCommand(rootDir, projRelPath(filename), outDir)
#     return results
    

MYKEFILE = 'Mykefile'

def childEnv(inRoot, relPath, outRoot):
    env = dict(os.environ)
    # Set some environment variables that might be useful:
    env['MYKE_IN_DIR'] = inRoot
    env['MYKE_REL_PATH'] = relPath
    env['MYKE_OUT_DIR'] = outRoot
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

# reload() protection:
try: _mykeRoots, _mykers
except NameError: _mykeRoots, _mykers = {}, {}

def getMykeRoot(path): # Traverse up the path until we find a Mykefile:
    path = os.path.abspath(path)
    if path not in _mykeRoots:
        if os.path.isdir(path) and  os.path.exists(os.path.join(path, MYKEFILE)): _mykeRoots[path] = path
        elif not path or path=='/': raise ValueError('Unable to find %s'%(MYKEFILE,))
        else: _mykeRoots[path] = getMykeRoot(os.path.dirname(path))
    return _mykeRoots[path]

def copyPathTraversal(origPath1, newPath1, origPath2):
    assert os.path.exists(origPath1)
    startDir = origPath1
    if os.path.isfile(origPath1): startDir = os.path.dirname(origPath1)
    assert os.path.isdir(newPath1)
    return os.path.abspath(os.path.join(origPath2, os.path.relpath(newPath1, startDir)))

def getMyker(path, outDir):
    root = getMykeRoot(path)
    if root not in _mykers: _mykers[root] = myke._Myker(root, copyPathTraversal(path, root, outDir))
    return _mykers[root]

class _Myker(object):
    def __init__(self, mykeRoot, outRoot, debug=False):
        self.mykeRoot = os.path.abspath(mykeRoot)
        self.mykefilePath = os.path.join(self.mykeRoot, MYKEFILE)
        assert os.path.exists(self.mykefilePath), '%s not found!'%(self.mykefilePath,)
        chmod_add(self.mykefilePath, stat.S_IXUSR)
        assert mykeRoot not in _mykers, 'Already created a myker with this mykeRoot!'
        self.hashKey = '__hash(%s)__'%(MYKEFILE,)
        self.outRoot = os.path.abspath(outRoot)
        self.cmdsPath = os.path.join(mykeRoot, '.myke_commands')
        self._cmdsCache = None
        self.fab = _Fab(self.mykeRoot, ignore=r'^\.{1,2}$|^/(dev|proc|sys)/', dirs=['/'], depsname=os.path.join(mykeRoot, '.myke_deps'), quiet=True, debug=debug)  # ignore: . .. /dev/ /proc/ /sys/
    def writeCommandsCache(self):
        if self._cmdsCache:
            with open(self.cmdsPath, 'w') as f: json.dump(self._cmdsCache, f, indent=2, sort_keys=True)
            os.chmod(self.cmdsPath, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IWGRP|stat.S_IROTH|stat.S_IWOTH)
    def getCommandsCache(self):
        curHash = myke.fabricate.md5_hasher(self.mykefilePath)   # This can obviously be optimized by only calculating the hash every several seconds -- not on every request.
        if self._cmdsCache == None:
            try: self._cmdsCache = json.load(open(self.cmdsPath))
            except: self._cmdsCache = {}
            atexit.register(self.writeCommandsCache)
        if self._cmdsCache.get(self.hashKey, None) != curHash: self._cmdsCache = {self.hashKey:curHash}
        return self._cmdsCache
    def relPath(self, path):   # I could have just used os.path.relpath, but this implementation is more restrictive so I'll keep it for now.
        path = os.path.abspath(path)
        if path == self.mykeRoot: return '.'  # Special case
        assert path.startswith(self.mykeRoot)
        relPath = path[len(self.mykeRoot):]
        assert relPath.startswith('/'), 'Unexpected path: %r --> %r'%(path, relPath)
        assert not relPath.endswith('/')
        return relPath[1:]
    def getCommand(self, path):
        cmdsCache, relPath = self.getCommandsCache(), self.relPath(path)
        key = ' --> '.join((relPath, os.path.relpath(self.outRoot, self.mykeRoot)))
        if key not in cmdsCache:
            result = subprocess.Popen([self.mykefilePath], env=childEnv(self.mykeRoot, relPath, self.outRoot), stdout=subprocess.PIPE).stdout.read().strip()
            # 'result' can be one of the following:
            #     * Nothing  (indicates a skip)
            #     * A multi-line sh command like "../bin/render" or "gcc -c '/a/b/c.c'"
            cmdsCache[key] = result
        return cmdsCache[key]
    def run(self, path):
        cmd = self.getCommand(path)
        if not cmd: return
        try: self.fab.run(['/bin/sh', '-euxs'],
                          # cwd=self.mykeRoot,  # I do not send 'cwd' because fabricate.py doesn't know how to deal with it, and all the strace-detected paths get messed up.  I do some tricks in _Fab to compensate for this.
                          env=childEnv(self.mykeRoot, self.relPath(path), self.outRoot),
                          input=cmd)   # Send our command to stdin.
        except fabricate.ExecutionError as e:
            print >> sys.stderr, '\nBuild Failed!  Exit Code %r'%(e.args[2],)
            # print >> sys.stderr, 'There was an error while running this command: %s\n'%(cmd,)
            # import traceback; traceback.print_exc()
            sys.exit(1)

def build(inPath, outDir):
    inPath, outDir = os.path.abspath(inPath), os.path.abspath(outDir)
    assert os.path.exists(inPath)

    # Ask the parent Mykefile whether we should skip this item:
    if inPath == '/': pass  # Special case becase '/' is its own parent.
    else:
        parentMyker = getMyker(os.path.dirname(inPath), copyPathTraversal(inPath, os.path.dirname(inPath), outDir))
        if not parentMyker.getCommand(inPath): return
    
    # If we get here, we are not skipping this item.  Get this item's command:
    getMyker(inPath, outDir).run(inPath)




# Override some fabricate.py functionality:
class _Fab(myke.fabricate.Builder):
    def __init__(self, mykeRoot, *args, **kwargs):
        self.mykeRoot = mykeRoot
        kwargs['runner'] = 'strace_runner'      # Hard-code StraceRunner since I have never tested with anything else (and don't plan to).
        super(_Fab, self).__init__(*args, **kwargs)
        self.runner.build_dir = self.mykeRoot   # StraceRunner uses its build_dir for path chopping.
    def mykeCommand(self, command): return ' '.join(['%s=%s'%(k,v) for k,v in sorted(self.mykeVars.items())]) + ' ' + command + ' ' + self.mykeInput
    def _run(self, *args, **kwargs):
        assert not self.parallel_ok   #  This hack does not work for parallel code.  I'll improve it if/when I encounter the need to.
        assert not hasattr(self, 'mykeVars')  and  not hasattr(self, 'mykeInput')  # Try to catch unexpected behavior.
        self.mykeVars, self.mykeInput = {}, kwargs.get('input', None)
        if 'env' in kwargs:
            for k,v in kwargs['env'].items():
                if k.upper().startswith('MYKE'): self.mykeVars[k] = v
        assert self.mykeVars['MYKE_IN_DIR'] == self.mykeRoot  and  self.runner.build_dir == self.mykeRoot
        os.chdir(self.mykeRoot)  # We must change our own CWD because fabricate.py does not know how to extract the 'cwd' argument from the Popen kwargs.  If this ends up being a concurrency issue, i'll need to adjust fabricate.py to handle per-builder CWD.
        x = super(_Fab, self)._run(*args, **kwargs)
        del self.mykeVars, self.mykeInput            # Try to catch unexpected behavior.
        return x
    def cmdline_outofdate(self, command): return super(_Fab, self).cmdline_outofdate(self.mykeCommand(command))
    def done(self, command, deps, output): return super(_Fab, self).done(self.mykeCommand(command), deps, output)
    
    

    # processed = {}
    # while True:    # Support auto-generation of files/templates.  (Loop until the filesystem is stable.)
    #     toProcess = walkAndClassify(inDir, outDir)
    #     if sorted(processed) == sorted(toProcess): break
    #     for projRelPath,cmd in sorted(toProcess.items()):
    #         if projRelPath in [depsname, routesname]: continue    # Skip our build-tracking files.
    #         if projRelPath in processed: continue   # Only process items once.
    #         try: builder.run(cmd, cwd=inDir, env=childEnv(inDir, projRelPath, outDir))
    #         except:
    #             print >> sys.stderr, '\nBuild Failed!'
    #             print >> sys.stderr, 'There was an error while running this command: %s\n'%(' '.join(map(repr,cmd)),)
    #             sys.exit(1)
    #     processed = toProcess
    # return processed

if __name__ == '__main__':
    assert len(sys.argv) == 3
    build(sys.argv[1], sys.argv[2])


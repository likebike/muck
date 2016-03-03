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
SKIP = 'SKIP'

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
        self.fab = _Fab(self.mykeRoot, ignore=r'^\.{1,2}$|^/(dev|proc|sys)/', dirs=['/'], depsname=os.path.join(mykeRoot, '.myke_deps'), debug=debug)  # ignore: . .. /dev/ /proc/ /sys/
    def writeCommandsCache(self):
        if self._cmdsCache:
            try:
                self._cmdsCache[self.hashKey] = myke.fabricate.md5_hasher(self.mykefilePath)
                with open(self.cmdsPath, 'w') as f: json.dump(self._cmdsCache, f, indent=2, sort_keys=True)
            finally: self._cmdsCache.pop(self.hashKey)
            os.chmod(self.cmdsPath, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IWGRP|stat.S_IROTH|stat.S_IWOTH)
    def getCommandsCache(self):
        if self._cmdsCache == None:
            self._cmdsCache = {}
            try:
                self._cmdsCache = json.load(open(self.cmdsPath))
                if self._cmdsCache[self.hashKey] != myke.fabricate.md5_hasher(self.mykefilePath):
                    # The loaded commands cache is invalid because the Mykefile has been changed.
                    self._cmdsCache = {}
            except: self._cmdsCache = {}
            atexit.register(self.writeCommandsCache)
        return self._cmdsCache
    def relPath(self, path):   # I could have just used os.path.relpath, but this implementation is more restrictive so I'll keep it for now.
        path = os.path.abspath(path)
        assert path.startswith(self.mykeRoot)
        relPath = path[len(self.mykeRoot):]
        assert relPath[0] == '/'
        assert relPath[-1] != '/'
        return relPath[1:]
    def getCommand(self, path):
        cmdsCache, relPath = self.getCommandsCache(), self.relPath(path)
        key = ' --> '.join((relPath, os.path.relpath(self.outRoot, self.mykeRoot)))
        if key not in cmdsCache:
            result = subprocess.Popen([self.mykefilePath], env=childEnv(self.mykeRoot, relPath, self.outRoot), stdout=subprocess.PIPE).stdout.read().strip()
            assert result, '%r produced blank result!'%(self.mykefilePath,)
            # 'result' can be one of the following:
            #     * A special value, like 'SKIP'
            #     * A path like '../bin/render'
            #     * A JSON list of strings, like '["gcc", "-c", "/a/b/c.c"]'
            if result in [SKIP]: cmdsCache[key] = result
            else:
                path = os.path.abspath(os.path.join(self.mykeRoot, result))
                if os.path.exists(path): cmdsCache[key] = [path]
                else:
                    # Assume it's a command in a JSON list of strings.
                    try:
                        cmd = json.loads(result)
                        if type(cmd) != list: raise ValueError('Expected a JSON list of strings')
                        cmdsCache[key] = map(str, cmd)
                    except: raise ValueError('Error while processing %r -- Invalid %s output: %r'%(relPath, MYKEFILE, result))
        return cmdsCache[key]
    def run(self, path):
        try:
            cmd = self.getCommand(path)
            if cmd == SKIP: return
            self.fab.run(cmd, # cwd=self.mykeRoot,  # I do not send 'cwd' because fabricate.py doesn't know how to deal with it, and all the strace-detected paths get messed up.  I do some tricks in _Fab to compensate for this.
                         env=childEnv(self.mykeRoot, self.relPath(path), self.outRoot))
        except:
            print >> sys.stderr, '\nBuild Failed!'
            print >> sys.stderr, 'There was an error while running this command: %s\n'%(' '.join(map(repr,cmd)),)
            import traceback
            traceback.print_exc()
            sys.exit(1)

def build(inPath, outDir):
    inPath, outDir = os.path.abspath(inPath), os.path.abspath(outDir)
    assert os.path.exists(inPath)

    # Ask the parent Mykefile whether we should skip this item:
    if inPath == '/': pass  # Special case becase '/' is its own parent.
    else:
        parentMyker = getMyker(os.path.dirname(inPath), copyPathTraversal(inPath, os.path.dirname(inPath), outDir))
        if parentMyker.getCommand(inPath) == SKIP: return
    
    # If we get here, we are not skipping this item.  Get this item's command:
    getMyker(inPath, outDir).run(inPath)




# Override some fabricate.py functionality:
class _Fab(myke.fabricate.Builder):
    def __init__(self, mykeRoot, *args, **kwargs):
        self.mykeRoot = mykeRoot
        kwargs['runner'] = 'strace_runner'      # Hard-code StraceRunner since I have never tested with anything else (and don't plan to).
        super(_Fab, self).__init__(*args, **kwargs)
        self.runner.build_dir = self.mykeRoot   # StraceRunner uses its build_dir for path chopping.
    def mykeCommand(self, command): return ' '.join(['%s=%s'%(k,v) for k,v in sorted(self.mykeVars.items())]) + ' ' + command
    def echo_command(self, command, echo=None): return super(_Fab, self).echo_command(self.mykeCommand(command), echo=echo)
    def _run(self, *args, **kwargs):
        assert not self.parallel_ok   #  This hack does not work for parallel code.  I'll improve it if/when I encounter the need to.
        assert not hasattr(self, 'mykeVars')  # Try to catch unexpected behavior.
        self.mykeVars = {}
        if 'env' in kwargs:
            for k,v in kwargs['env'].items():
                if k.upper().startswith('MYKE'): self.mykeVars[k] = v
        assert self.mykeVars['MYKE_IN_DIR'] == self.mykeRoot  and  self.runner.build_dir == self.mykeRoot
        os.chdir(self.mykeRoot)  # We must change our own CWD because fabricate.py does not know how to extract the 'cwd' argument from the Popen kwargs.  If this ends up being a concurrency issue, i'll need to adjust fabricate.py to handle per-builder CWD.
        x = super(_Fab, self)._run(*args, **kwargs)
        del self.mykeVars            # Try to catch unexpected behavior.
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


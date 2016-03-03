#!/usr/bin/env python

# Created by Christopher Sebastian, 2016-03-01

import os, sys, fnmatch, re, subprocess, json, string, atexit
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
    

MYKEFILE='Mykefile'

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
try: _mykeRoots, _builders
except NameError: _mykeRoots, _builders = {}, {}

def getMykeRoot(path): # Traverse up the path until we find a Mykefile:
    path = os.path.abspath(path)
    if path not in _mykeRoots:
        if os.path.isdir(path) and  os.path.exists(os.path.join(path, MYKEFILE)): _mykeRoots[path] = path
        elif not path or path=='/': raise ValueError('Unable to find %s'%(MYKEFILE,))
        else: _mykeRoots[path] = getMykeRoot(os.path.dirname(path))
    return _mykeRoots[path]

def getBuilder(path):
    root = getMykeRoot(path)
    if root not in _builders: _builders[root] = Builder(root)
    return _builders[root]

class _Builder(object):
    def __init__(self, mykeRoot, outRoot, debug=False):
        self.mykeRoot = os.path.abspath(mykeRoot)
        self.mykefilePath = os.path.join(self.mykeRoot, MYKEFILE)
        assert os.path.exists(self.mykefilePath), '%s not found!'%(self.mykefilePath,)
        chmod_add(self.mykefilePath, stat.S_IXUSR)
        assert mykeRoot not in _builders, 'Already created a builder with this mykeRoot!'
        self.outRoot = os.path.abspath(outRoot)
        self.cmdsPath = os.path.join(mykeRoot, '.myke_commands')
        self._cmdsCache = None
        self.fab = myke.fabricate.Builder(ignore='^/(dev|proc|sys)/', dirs=['/'], depsname=os.path.join(mykeRoot, '.myke_deps'), debug=debug)
    def writeCommandsCache(self):
        if self._cmdsCache:
            with open(self.cmdsPath, 'w') as f: json.dump(self._cmdsCache, f, indent=2, sort_keys=True)
            os.chmod(self.cmdsPath, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IWGRP|stat.S_IROTH|stat.S_IWOTH)
    def getCommandsCache(self):
        if self._cmdsCache == None:
            self._cmdsCache = {}
            try: self._cmdsCache = json.load(open(self.cmdsPath))
            except: pass
            atexit.register(self.writeCommandsCache)
        return self._cmdsCache
    def getCommand(self, path):
        path = os.path.abspath(path)
        assert path.startswith(self.mykeRoot)
        relPath = path[len(self.mykeRoot):]
        assert relPath[0] == '/'
        cmdsCache = self.getCommandsCache()
        key = ' '.join((relPath, os.path.relpath(self.outRoot, self.mykeRoot)))
        if key not in cmdsCache:
            result = subprocess.Popen([self.mykefilePath], env=childEnv(self.mykeRoot, relPath, self.outRoot), stdout=subprocess.PIPE).stdout.read().strip()
            assert result, '%r produced blank result!'%(self.mykefilePath,)
            # 'result' is either a path like '_myke_SKIP', '../bin/render'
            # OR it's a JSON list of strings, like '["gcc", "-c", "/a/b/c.c"]'
            path = os.path.abspath(os.path.join(self.mykeRoot, result))
            if os.path.exists(path): cmdsCache[key] = [path]
            else:
                # Assume it's a command in a JSON list of strings.
                try:
                    cmd = json.loads(result)
                    if type(cmd) != list: raise ValueError('Expected a JSON list of strings')
                    cmdsCache[key] = map(str, cmd)
                except: raise ValueError('Error while processing %r -- Invalid Router output: %r'%(projRelPath, result))
        return cmdsCache[key]

def build(inPath, outDir):
    inPath, outDir = os.path.abspath(inPath), os.path.abspath(outDir)
    assert os.path.exists(inPath)

    # Ask the parent Mykefile whether we should skip this item:
    if inPath == '/': pass  # Special case.
    else:
        parentBuilder = getBuilder(os.path.dirname(inPath))
        parentCommand = parentBuilder.getCommand(inPath)
        if os.path.basename(parentCommand).endswith('SKIP'): return
    
    notaskip

    
    if os.path.isdir(inPath):
        asdf

    

    processed = {}
    while True:    # Support auto-generation of files/templates.  (Loop until the filesystem is stable.)
        toProcess = walkAndClassify(inDir, outDir)
        if sorted(processed) == sorted(toProcess): break
        for projRelPath,cmd in sorted(toProcess.items()):
            if projRelPath in [depsname, routesname]: continue    # Skip our build-tracking files.
            if projRelPath in processed: continue   # Only process items once.
            try: builder.run(cmd, cwd=inDir, env=childEnv(inDir, projRelPath, outDir))
            except:
                print >> sys.stderr, '\nBuild Failed!'
                print >> sys.stderr, 'There was an error while running this command: %s\n'%(' '.join(map(repr,cmd)),)
                sys.exit(1)
        processed = toProcess
    return processed

if __name__ == '__main__':
    assert len(sys.argv) == 3
    build(sys.argv[1], sys.argv[2])


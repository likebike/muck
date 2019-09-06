import os, shutil, subprocess, codecs, sys
import pyhpy



def getACL(path):
    curACLs = []
    if sys.platform.startswith('win'): return curACLs  # Not supported on Windows.
    popen = subprocess.Popen('getfacl --absolute-names %r'%(path,),
                             stdout=subprocess.PIPE,
                             shell=True)
    for line in popen.stdout:
        line = line.strip()
        if not line: continue
        if line.startswith('#'): continue
        curACLs.append(line)
    retcode = popen.wait()
    if retcode != 0: raise ValueError('Error getting ACL: %r'%(path,))
    return curACLs
def cpACL(srcPath, dstPath):
    if sys.platform.startswith('win'): return  # Not supported on Windows.
    retcode = subprocess.call('getfacl --absolute-names %r | setfacl --set-file=- %r'%(srcPath, dstPath), shell=True)
    if retcode != 0:
        raise ValueError('Error copying ACL: %r  -->  %r'%(srcPath, dstPath))
def getStats(path, includeSize=True, includeMTime=False):
    # Return the important, comparable filesystem stats that can
    # be used to compare file metadata.
    s = os.stat(path)
    acl = None
    if int(os.environ.get('ACL_CHECK', 1)): acl = getACL(path)
    stats= {'mode':s.st_mode,
            'uid':s.st_uid,
            'gid':s.st_gid,
            'acl':acl}
    if includeMTime: stats['mtime'] = s.st_mtime
    if includeSize: stats['size'] = s.st_size
    return stats
def cpStats(srcPath, dstPath, touch=True):
    if int(os.environ.get('ACL_CHECK', 1)): cpACL(srcPath, dstPath)
    shutil.copystat(srcPath, dstPath)
    if touch: os.utime(dstPath, None) # set the modtime to now.
def cpData(srcPath, dstPath, touch=True):
    dstDir = os.path.dirname(dstPath)
    if not os.path.isdir(dstDir):
        #print 'Creating Directory:'
        #print '\t%s'%(dstDir,)
        os.makedirs(dstDir)
    shutil.copy2(srcPath,dstPath) # Copy data, permissions, modtime.
    if touch: os.utime(dstPath, None) # set the modtime to now.

def syncNormalFile(srcPath, dstPath):
    dstModTime = 0
    if os.path.exists(dstPath): dstModTime = pyhpy.getmtime(dstPath, includeMeta=False)
    srcModTime = pyhpy.getmtime(srcPath, includeMeta=False)
    if srcModTime > dstModTime:
        #print 'Copying Normal File: %r > %r'%(srcModTime, dstModTime)
        #print '\t%s  -->  %s'%(srcPath,dstPath)
        cpData(srcPath, dstPath)
        cpStats(srcPath, dstPath, touch=False)
    if getStats(srcPath) != getStats(dstPath):
        #print 'Copying Filesystem Metadata:'
        #print '\t%s  -->  %s'%(srcPath,dstPath)
        cpStats(srcPath, dstPath, touch=False)


def syncSymlink(srcPath, dstPath):
    linkto = os.readlink(srcPath)
    needToCreate = True
    if os.path.islink(dstPath):
        if os.readlink(dstPath) == linkto: needToCreate = False
    if needToCreate:
        dstDir = os.path.dirname(dstPath)
        if not os.path.isdir(dstDir):
            #print 'Creating Directory:'
            #print '\t%s'%(dstDir,)
            os.makedirs(dstDir)
        #print 'Creating Symlink:'
        #print '\t%s  -->  %s'%(dstPath,linkto)
        if os.path.exists(dstPath): os.remove(dstPath)
        os.symlink(linkto, dstPath)

def syncFileOrSymlink(srcPath, dstPath):
    if not os.path.exists(srcPath): raise ValueError('Does Not Exist: %r'%(srcPath,))
    if os.path.islink(srcPath): return syncSymlink(srcPath, dstPath)
    if not os.path.isfile(srcPath): raise ValueError('Not a file or symlink: %r'%(srcPath,))
    return syncNormalFile(srcPath, dstPath)


def syncMakoTemplate(srcPath, dstPath):
    lastModTime = pyhpy.getmtime(srcPath)
    for dep in pyhpy.mako_render.getMakoTemplateDeps(srcPath):
        assert os.path.isabs(dep)
        if not os.path.exists(dep):
            #print 'Dependency of %r does not exist: %r'%(srcPath, dep,)
            continue
        lastModTime = max(lastModTime, pyhpy.getmtime(dep))
    dstModTime = 0
    if os.path.exists(dstPath): dstModTime = pyhpy.getmtime(dstPath)
    if lastModTime > dstModTime:
        dstDir = os.path.dirname(dstPath)
        if not os.path.isdir(dstDir):
            #print 'Creating Directory:'
            #print '\t%s'%(dstDir,)
            os.makedirs(dstDir)
        #print 'Evaluating Mako Template:'
        #print '\t%s  -->  %s'%(srcPath,dstPath)
        result = pyhpy.mako_render.makoRender(srcPath, {})    #### 2013-09-28 -- I need to double-check the logic for the {} ...
        outFile = codecs.open(dstPath, 'wb', encoding='utf-8')
        outFile.write(result)
        outFile.close()
        cpStats(srcPath,dstPath)
    if getStats(srcPath, includeSize=False) != \
       getStats(dstPath, includeSize=False):
        #print 'Copying Filesystem Metadata:'
        #print '\t%s  -->  %s'%(srcPath,dstPath)
        cpStats(srcPath,dstPath)


def syncData(data, dstPath, encoding='utf-8'):
    '''Writes the provided 'data' to 'dstPath', if necessary.'''
    if (not os.path.exists(dstPath)) or codecs.open(dstPath, encoding=encoding).read()!=data:
        #print 'Writing Data -->  %s'%(dstPath,)
        dstDir = os.path.dirname(dstPath)
        if not os.path.isdir(dstDir):
            #print 'Creating Directory:'
            #print '\t%s'%(dstDir,)
            os.makedirs(dstDir)
        outF = codecs.open(dstPath, 'wb', encoding=encoding)
        outF.write(data)
        outF.close()


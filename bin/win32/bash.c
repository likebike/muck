/* Written by Christopher Sebastian, 2011-09-19. */

/* usage:  adminBash [scriptPath.sh]
 *
 * Starting in Windows Vista, application permission levels are controlled by
 * "Manifests".  There are "internal" and "external" manifests.  Internal
 * manifests are compiled directly into the EXE.  External manifests are stored
 * in a separate file named "theapp.exe.manifest".
 *
 * For now, this program uses external manifests because they are more
 * convenient for editing.
 *
 * Here is the contents of the manifest that we will use:
 *
 ****************************************************
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0"> 
    <assemblyIdentity version="1.0.0.0"
                      processorArchitecture="X86"
                      name="runAsAdmin"
                      type="win32"/> 
    <description>Medtronic Design Automation Script Helper</description> 
    <!-- Identify the application security requirements. -->
    <ms_asmv2:trustInfo xmlns:ms_asmv2="urn:schemas-microsoft-com:asm.v2">
        <ms_asmv2:security>
            <ms_asmv2:requestedPrivileges>
                <ms_asmv2:requestedExecutionLevel level="requireAdministrator"
                                                  uiAccess="false"/>
            </ms_asmv2:requestedPrivileges>
        </ms_asmv2:security>
    </ms_asmv2:trustInfo>
</assembly>
 ****************************************************
 */


#include <stdio.h>
#include <glib.h>
#include <windows.h>
#include <assert.h>
#include <unistd.h>


void dump_hex(char* p, int len) {
    for(int i=0; i<len; i++) {
        char cVal = *(p+i);
        unsigned int iVal = (unsigned int)cVal;
        printf("%02x", iVal);
        if(iVal>=32  &&  iVal<=126) printf(" (%c)", cVal);
        printf("\n");
    }
}

gchar* getThisExePath() {
    /* Returns absolute path with UTF-8 encoding. */

    wchar_t* buffer = (wchar_t*)malloc( sizeof(wchar_t)*(MAX_PATH+5) );  // 5 extra for :\\*.*... or something like that.  (Got this from Python's C source code of 'listdir'.)
    assert(buffer!=NULL);
    int pathLen = GetModuleFileNameW(NULL, buffer, MAX_PATH);

    gchar* utf8_string = g_utf16_to_utf8(buffer, pathLen, NULL, NULL, NULL);

    free(buffer);

    return utf8_string;
}

gchar* translateArg(gchar* arg) {
    // If the arg is a path that exists, then it's fine.
    if(g_file_test(arg, G_FILE_TEST_EXISTS)) return arg;

    // Translate embedded variables:
    gchar** pieces = g_strsplit(arg, "${EXEDIR}", 0);
    gchar* newArg = g_strjoinv(g_getenv("EXEDIR"), pieces);
    pieces = g_strsplit(newArg, "${STARTDIR}", 0);   // Ya, i know this is a memory leak (pieces and newArg).  I don't care because it's so small and I'm going to rewrite this in OCaml anyway.
    newArg = g_strjoinv(g_getenv("STARTDIR"), pieces);

    return newArg;
}


int main(int argc, char** argv) {

    /* Get path to bash.exe */
    gchar* exePath = getThisExePath();
    gchar* exeDir = g_path_get_dirname(exePath); g_free(exePath);
    gchar* msysDir = g_build_filename(exeDir, "mini_msys", NULL);
    gchar* binDir = g_build_filename(msysDir, "bin", NULL);
    gchar* bashPath = g_build_filename(binDir, "bash.exe", NULL);
    if(!g_file_test(bashPath, G_FILE_TEST_IS_REGULAR)) {
        printf("Unable to find bash!  %s", bashPath);
        Sleep(3000);
        return 10;
    }

    if(argc == 1) {
        gchar* defaultScriptPath = g_build_filename(exeDir, "default.sh", NULL);
        // Use a default script, if it exists...
        if(g_file_test(defaultScriptPath, G_FILE_TEST_IS_REGULAR)) {
            char** newArgv = (char**)malloc(sizeof(char*)*2);
            newArgv[0] = argv[0];
            newArgv[1] = defaultScriptPath;
            argv = newArgv;
            argc = 2;
        }
    }


    const gchar* origPath = g_getenv("PATH");
    GString* newPath = g_string_new("/bin");
    g_string_append(newPath, ";");
    g_string_append(newPath, origPath);
    g_setenv("PATH", newPath->str, TRUE); g_string_free(newPath, TRUE);
    gchar* startDir = g_get_current_dir();
    g_setenv("STARTDIR", startDir, TRUE); g_free(startDir);  /* Save the start dir because we are going to switch to a safe tmp dir. */
    g_setenv("EXEDIR", exeDir, TRUE);
    

    /* Use the local TMP directory because CMD.exe can't handle UNC paths.
       ...and also because Win7 current working directory acts weird when getting admin priviliges. */
    const gchar* tmpDir = g_get_tmp_dir();
    chdir(tmpDir);



#if 0
    /* Seems to have no effect... (Also requires a reboot to take effect, so it's sort of worthless.) */
    /* Configure the Windows Registry to allow the user to access their network drives while admin.
     * This change is permanent.  (...unless the user un-does it with regedit.)
     * http://support.microsoft.com/kb/937624 */
    HKEY hkey;
    DWORD dwDisposition;
    if(RegCreateKeyEx(HKEY_LOCAL_MACHINE,
                      TEXT("SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System"),
                      0,
                      NULL,
                      0,
                      KEY_WRITE,
                      NULL,
                      &hkey,
                      &dwDisposition) == ERROR_SUCCESS) {
        DWORD dwType, dwSize;
        dwType = REG_DWORD;
        dwSize = sizeof(DWORD);
        DWORD value = 1;
        RegSetValueEx(hkey, TEXT("EnableLinkedConnections"), 0, dwType, (PBYTE)&value, dwSize);
        RegCloseKey(hkey);
    } else {
        printf("There was an error while trying to enable linked connections.  Network drives might not work.\n");
        printf("Attempting to continue...\n\n");
    }
#endif


#if 0
    /* Use 'system', which is less efficient and has more layers that can go wrong.
     * Allows for easier debugging of issues because we can pause upon error. */
    GString* command = g_string_new(bashPath); g_free(bashPath);
    for(int i=1; i<argc; i++) {
        g_string_append(command, " ");
        g_string_append(command, translateArg(argv[i]));
    }
    int retcode = system(command->str);
    if(retcode) {
        fprintf(stderr, "\nThere was an error.  Pausing 10 seconds.");
        Sleep(10000);
    }
    return retcode;
#else
    /* Use 'spawn', which is more direct than system(). */
    char **bashArgs = (char**)malloc(sizeof(char*)*(argc+1));
    for(int i=1; i<argc; i++) bashArgs[i] = translateArg(argv[i]);
    bashArgs[0] = bashPath;
    bashArgs[argc] = NULL;
    int retcode = _spawnv(_P_WAIT, bashPath, bashArgs);  // I'm using spawnv because execv launches processes in the background on Windows.
    if(retcode) {
        fprintf(stderr, "\nThere was an error.  Pausing for 10 seconds.\n");
        Sleep(10000);
    }
    return retcode;
#endif
}


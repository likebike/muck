adminBash.exe is a wrapper around MSYS bash, which automatically requires admin
priviliges on Windows 7.  bash.exe is similar, but does not require admin
priviliges.

It allows you to create bash scripts that can be used for system automation on
Windows (such as installations or data collection).

The EXEDIR environment variable gets defined to be the directory that contains
the adminBash.exe executable, which allows easy access to nearby files from
scripts.

The STARTDIR environment variable gets defined to be the directory that the
command was originally started in.  After setting this environment varible,
the current working directory is set to a local TEMP directory because there
are certain situations that can arise where things break if you try to run
this from a network drive that the admin user does not have access to, and
stuff like that.

You can add ${EXEDIR}  and  ${STARTDIR} to commandline args, and they will be
interpolated.

You can provide a default.sh script in the same directory as adminBash.exe, and
if adminBash.exe is run without any command line args, it will run the
default.sh instead.


=== BUILD DEPENDENCIES ===
    If you want to compile adminBash.exe from source code, you will need some
    things...

        MSYS
        MinGW
        gettext-runtime
        pkg-config
        GLib Runtime
        GLib Dev
            

    === MSYS ===
        An easy way to get MSYS is to download the Portable version of msysGit:

            http://code.google.com/p/msysgit/

        Extract the Portable 7-ZIP file to 'MinGW\msys\1.0' in this directory.
        This exact path is important!  (See below for diagram.)

        If your bash scripts need additional commands and utilities, you can get
        them from the MinGW and MinSYS projects:

            http://www.mingw.org/


    === MinGW ===
        The easiest way to get MinGW is to use the latest mingw-get-inst setup
        program.  Select all packages during installation:

            http://sourceforge.net/projects/mingw/files/Automated%20MinGW%20Installer/mingw-get-inst/

        Install MinGW to 'MinGW' in this directory (the parent directory of the
        MSYS environment that you just installed).


    === GLib ===
        This is sort of tricky.  Glib consists of many pieces.  There are four
        that you need to build adminBash.

        Head over to the GTK+ Windows download page:

            http://www.gtk.org/download/win32.php

        ...and download each of these:

            gettext-runtime Run-Time
            pkg-config Tool
            GLib Run-Time
            GLib Dev

        Unzip each of those and copy them directly on top of your MinGW
        directory structure.


    === Running the Development Environment ===
        After everything is installed, you can launch the environment with the
        msys.bat, or the git-bash.bat.  Both are located in the MinGW/msys/1.0
        directory.

        Use 'make' to build adminBash.



=== FINAL DIRECTORY STRUCTURE ===
    After you have everything installed, the resulting directory structure
    should look like this (most files are not shown, just some critical ones):

    (this Dir)/   
        bash.exe
        adminBash.exe
        adminBash.exe.manifest
        mini_msys/
            bin/
                bash.exe (comes from MSYS.  Required to run adminBash.)
        MinGW/
            bin/
                intl.dll         (comes from gettext-runtime.  Required for
                                                               build.)
                pkg-config.exe   (comes from pkg-config.  Required for build.)
            include/             (comes from MinGW installer.  Required for
                                                               build)
                windows.h
                glib-2.0/        
                    glib.h       (comes from GLib Dev.  Required for build.)
            msys/                
                1.0/
                    msys.bat     (comes from MinGW installer.  Use this to
                                                    launch the dev environment.)



=== HOW TO RE-CREATE MINI_MINGW ===
    Rather than shipping the entire MinGW environment to your customer (over
    500MB), you can create a minimal set of files that your scripts need to run
    (usually under 10MB).

    Step 1:  Modify the bash.c code so that it uses the full 'MinGW'
             environment, rather than the 'mini_msys' environment.
    Step 2:  Start ProcessMonitor and start capturing events.
    Step 3:  Run your desired scripts.  Be sure to access all files that you
             will possibly need.
    Step 4:  Stop capturing events in ProcessMonitor.
    Step 5:  Save the resulting log as a CSV file.
    Step 6:  Use the Christopher's 'procMonParser' tool to get a list of all the
             files that were accessed under the MinGW environment.
    Step 7:  Copy all those files into a new mini_msys structure.  Do not copy
             the '/etc/fstab' file because that will break the portability of
             the environment.
    Step 8:  Re-Modify the bash.c code to use the new mini environment.

    There are more detailed instructions in the 'procMonParser' readme.



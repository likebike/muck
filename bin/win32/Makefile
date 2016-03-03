bash.exe: bash.c
	###gcc -Wall -std=c99 -o bash.exe -DGLIB_STATIC_COMPILATION -DGOBJECT_STATIC_COMPILATION bash.c `pkg-config --cflags --libs glib-2.0` -static
	gcc -Wl,-subsystem,console -Wall -std=c99 -o bash.exe bash.c `pkg-config --cflags --libs glib-2.0`
	strip bash.exe

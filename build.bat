@set NUITKA_CCACHE_BINARY=C:\ccache\ccache.exe

python -X utf8 -m nuitka ^
    --follow-imports ^
    --standalone ^
    --windows-dependency-tool=pefile ^
    --experimental=use_pefile_recurse ^
    --python-flag=no_site ^
    --show-progress ^
    --show-scons ^
    chronicler.py

copy config.ini.template chronicler.dist\config.ini
copy README.txt chronicler.dist\README.txt
copy yajl.dll chronicler.dist\yajl.dll
copy LICENSE chronicler.dist\LICENSE.txt
copy "additional license information.txt" "chronicler.dist\additional license information.txt"
7z a r20chronicler-windows-x86-64.zip chronicler.dist\.

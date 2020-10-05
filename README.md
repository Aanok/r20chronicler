# r20chronicler
A python 3.5+ script to download [Roll20.net](https://roll20.net) chatlogs to a plaintext file.

Currently a work in progress.

## Usage
There is a 64-bit Windows binary you can download from the [latest release](https://github.com/Aanok/r20chronicler/releases/latest), built with [Nuitka](https://nuitka.net/). Do mind it is only tested on Windows 10.

To otherwise run the script directly:
- Satisfy the dependencies as listed below.
  - On Windows, you'll want to put `yajl.dll` into `C:\Windows\System32`. If it doesn't work you'll have to compile it locally.
- Rename `config.ini.template` to `config.ini` and follow the instructions you'll find inside.
- Run `chronicler.py` via the Python interprenter.

If you run into Unicode problems (e.g. a `UnicodeEncodeError` exception, or an odd error in `parse.py` from jsonstreamer) you'll want to use a version 3.7+ runtime with the `-X utf8` argument. Or fix your Locale.

## Dependencies
* [aiohttp](https://github.com/aio-libs/aiohttp)
* [yajl2](https://lloyd.github.io/yajl/)
* [again](https://github.com/kashifrazzaqui/again)
* [json-streamer](https://github.com/kashifrazzaqui/json-streamer/) (packaged, no need to install anything)

## Acknowledgements
The script is loosely based on [code](https://github.com/itamarcu/data_downloaders/blob/master/roll20_archives_downloader.py) by Roll20 user [Shemetz](https://app.roll20.net/users/3564168/shemetz). Thanks for the bootstrap!

A copy of json-streamer is included in this repository, as the version published on PyPI is outdated and doesn't support Windows.

A Windows library file (.dll) for Yajl 2.1.0 64-bit is also included for user convenience.

The code for the progress bar was shamelessly stolen from [Vladimir Ignatyev](https://gist.github.com/vladignatyev).

License information for the three sources is listed in `additional license information.txt`.

![its him its the chronicler](https://user-images.githubusercontent.com/18417628/79206868-3d51d000-7e40-11ea-9cae-a4b91b469db4.jpg)

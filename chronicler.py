import asyncio
from os import path, mkdir
from datetime import date
from sys import exc_info, stderr
from traceback import print_exception
from logging import getLogger, INFO

import config
import roll20

import time


outputdir = 'output'

async def main():
    try:
        config.load()
        await roll20.new_session(
            config.options['user']['email'],
            config.options['user']['password']
            )
        try:
            mkdir('output')
        except FileExistsError:
            pass
        for section in config.options:
            if section == 'DEFAULT' or section == 'user':
                continue
            
            print('Accessing chatlog for {}...'.format(section))
            filepath = ('{}/{}_{}.txt'.format(outputdir, section, date.today()))
            await roll20.dump_chatlog(
                    config.options[section]['id'],
                    filepath
                    )
            print('Successfully saved to file "{}".'.format(filepath))
    except roll20.HTTPError as e:
        if e.status == 302:
            roll20.delete_cookiejar()
        else:
            stderr.write('ERROR: {}\n'.format(e.message))
    except:
        stderr.write('ERROR\n')
        e = exc_info()
        print_exception(e[0], e[1], e[2])
    else:
        print('DONE')
    finally:
        await roll20.close_session()
        print('Press Enter to close.')
        input()


if __name__ == '__main__':
        getLogger('asyncio').setLevel(INFO)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())

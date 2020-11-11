import aiohttp
import asyncio
from http import cookies
from os import path, remove, mkdir, rmdir
from re import compile as re_compile

from parsers import ChatParser, ParseError
from progress import progress


session = None
pages = None
done = None 


# oh how i'd love for this exception to fall under HTTPError with a 401
class LoginError(Exception):
    message = 'Login failed. Please double check your credentials in config.ini.'


class HTTPError(Exception):
    _messages = {
        302: 'The login session has timed out. Please restart the program.',
        403: 'You are not allowed to access this chatlog. Is the ID correct? Are you a member of the campaign?'
        }
        
    def __init__(self, status):
        self.status = status
        self.message = ''.join([
            'HTTP error ',
            str(status),
            ': ' + HTTPError._messages[status] if status in HTTPError._messages else ''
            ])


def _load_rack_session(session, response):
    assert('set-cookie' in response.headers)

    for cookie_header in response.headers.getall('set-cookie'):
        if not cookie_header.startswith('rack.session'):
            continue
        # correct idiocy of Rack not respecting RFC 7231, section 7.1.1.2: Date
        set_rack_cookie = cookie_header.replace('-0000','GMT')
        c = cookies.SimpleCookie()
        c.load(set_rack_cookie)
        session.cookie_jar.update_cookies(c)

    assert('rack.session' in session.cookie_jar._cookies['roll20.net'])


async def login(email, password):
    global session
    response = await session.post(
        'https://app.roll20.net/sessions/create',
        data={'email': email, 'password': password},
        allow_redirects=False
        )

    # check for successful login. believe it or not this is the only thing that
    # changes in the response if the login failed. i'm speechless.
    if response.headers['Location'] == 'https://app.roll20.net/sessions/new':
        raise LoginError

    _load_rack_session(session, response)
    session.cookie_jar.save('cookiejar')
    response.close()

    return session


async def new_session(email, password):
    global session
    if session and not session.closed: session.close()
    session = aiohttp.ClientSession()

    try:
        session.cookie_jar.load('cookiejar')
        response = await session.get(
            'https://app.roll20.net/account/',
            allow_redirects=False
            )
        response.close()
        _load_rack_session(session, response)
        if response.status != 200:
            await login(email, password) 
    except FileNotFoundError:
        await login(email,password)


async def close_session():
    await session.close()


def delete_cookiejar():
    remove('cookiejar')


async def _dump_page(campaign_id, filename, pageno, playerid, is_gm):
    global session, pages, done
    response = await session.get(
            'https://app.roll20.net/campaigns/chatarchive/{}/?p={}'.format(campaign_id, pageno),
            allow_redirects=False
            )
    async with response:
        if response.status != 200:
            raise HTTPError(response.status)
        parser = ChatParser(filename, playerid, is_gm)
        async for chunk in response.content.iter_chunked(64 * 1024):
            encoding = response.charset or 'utf-8'
            parser.process(chunk.decode(encoding))
        parser.finalize()
    done = done + 1
    progress(done, pages)


async def dump_chatlog(campaign_id, filepath):
    global session, pages, done
    is_gm = False
    response = await session.get(
            'https://app.roll20.net/campaigns/chatarchive/{}'.format(campaign_id),
            allow_redirects=False
            )

    # badly and lazily parse first page for page count and playerid
    async with response:
        if response.status != 200:
            raise HTTPError(response.status)
        re_pages = re_compile(b'Page 1/(\d+)</div>')
        re_playerid = re_compile(b'Object\.defineProperty\(window, "currentPlayer", {value: {id: "([^"]+)"}, writable: false }\);')
        re_isgm = re_compile(b'Object\.defineProperty\(window, "is_gm", { value : true, writable : false }\);')
        buf = b''
        # can't use readline because the line with msgdata is too long
        async for chunk in response.content.iter_any():
            start = 0
            buf = b''.join([buf, chunk])
            while True:
                end = buf.find(b'\n', start)
                if end == -1:
                    buf = buf[start:]
                    break
                line = buf[start:end]
                # NB this does a bunch of pointless work after it finds what
                # it's looking for already but i cba
                match_pages = re_pages.search(line)
                if match_pages:
                    pages = int(match_pages.group(1))
                match_playerid = re_playerid.search(line)
                if match_playerid:
                    playerid = match_playerid.group(1).decode(response.charset or 'utf-8')
                match_isgm = re_isgm.search(line)
                if match_isgm:
                    is_gm = True
                start = end + 1
        del buf

    if not pages: raise ParseError('Page count not found in request body.')
    if not playerid: raise ParseError('playerid not found in request body.')

    tmp_dir = '{}_tmp'.format(filepath)
    try:
        mkdir(tmp_dir)
    except:
        pass
    tasks = []
    tmp_filepaths = []
    for page in range(pages, 0, -1):
        tmp_filepath = '{}/{}'.format(tmp_dir, page)
        tmp_filepaths.append(tmp_filepath)
        tasks.append(_dump_page(campaign_id, tmp_filepath, page, playerid, is_gm))
    done = 0
    progress(done, pages)
    await asyncio.gather(*tasks)
    print('') # for the sake of the progress bar

    with open(filepath, 'w') as output_file:
        for i in range(pages):
            with open(tmp_filepaths[i]) as input_file:
                for line in input_file:
                    output_file.write(line)
            remove(tmp_filepaths[i])
    rmdir(tmp_dir)

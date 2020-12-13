from base64 import b64decode
from enum import Enum
from jsonstreamer import JSONStreamer
from json import loads
from sys import exit, stderr
from traceback import print_exc

SaxState = Enum(
    'SaxState',
    'START                      \
    BETWEEN_POSTS               \
    IN_POST                     \
    POST_CONTENTS               \
    IN_WHO                      \
    IN_CONTENT                  \
    IN_ORIGROLL                 \
    IN_TYPE                     \
    IN_INLINEROLLS              \
    IN_INLINEROLLS_EXPRESSION   \
    IN_INLINEROLLS_TOTAL        \
    IN_TARGET_NAME              \
    IN_SELECTED                 \
    IN_PLAYERID                 \
    IN_TARGET_PLAYERID'
    )


class ParseError(Exception):
    def __init__(message):
        self.message = message


class PostType:
    IGNORE = 1
    GENERAL = 2
    DESC = 3
    EMOTE = 4
    ROLLRESULT = 5
    GMROLLRESULT = 6
    WHISPER = 7

    _stringdict = {
            'api' : IGNORE,
            'whisper': WHISPER,
            'desc': DESC,
            'general': GENERAL,
            'emote': EMOTE,
            'rollresult': ROLLRESULT,
            'gmrollresult': GMROLLRESULT,
            }


    @staticmethod
    def from_string(string):
        return PostType._stringdict[string]


class JsonSaxParser:
    # TODO: better roll parsing to show details of single dice
    # TODO: inlinerolls (e.g. macros and calculator-like expressions)

    def __init__(self, filepath, playerid, is_gm):
        self._filepath = filepath 
        self._playerid = playerid
        self._is_gm = is_gm
        self._streamer = JSONStreamer()
        self._streamer.auto_listen(self)
        self._state = SaxState.START
        self._skipping_brackets = 0
        self._post_playerid = None
        self._who = None
        self._content = None
        self._origRoll = None
        self._target_name = None
        self._inlinerolls = []
        self._inlineroll_expression = None


    def _on_doc_start(self):
        self._file = open(self._filepath, 'w')


    def _on_doc_end(self):
        try:
            self._file.close()
        except AttributeError:
            pass


    def _on_object_start(self):
        if self._state == SaxState.START:
            self._state = SaxState.BETWEEN_POSTS
        elif self._state == SaxState.IN_POST:
            self._state = SaxState.POST_CONTENTS
        elif self._state == SaxState.IN_INLINEROLLS or self._state == SaxState.IN_SELECTED:
            self._skipping_brackets += 1


    def _on_object_end(self):
        if self._state == SaxState.POST_CONTENTS:
            for i, roll in enumerate(self._inlinerolls):
                self._content = self._content.replace( '$[[%d]]' % i, roll)

            if self._type == PostType.GENERAL:
                post = ''.join([self._who, ': ', self._content, '\n'])
            elif self._type == PostType.EMOTE:
                post = ''.join([self._who, ' ', self._content, '\n'])
            elif self._type == PostType.DESC:
                post = ''.join([self._content, '\n'])
            elif self._type == PostType.ROLLRESULT:
                # "content" in this case is a JSON... saved as an escaped
                # string. because hail satan, i suppose
                roll = loads(self._content)
                post = ''.join(
                        [
                            self._who,
                            ': ',
                            self._origRoll,
                            ' = ',
                            str(roll['total']),
                            '\n'
                        ]
                    )
            elif self._type == PostType.GMROLLRESULT:
                # same deal...
                # privacy of GM rolls must be enforced client-side
                if self._post_playerid == self._playerid or self._is_gm:
                    roll = loads(self._content)
                    post = ''.join(
                            [
                                self._who,
                                ' (to GM): ',
                                self._origRoll,
                                ' = ',
                                str(roll['total']),
                                '\n'
                            ]
                        )
                else:
                    self._type = PostType.IGNORE
            elif self._type == PostType.WHISPER:
                # privacy of whispers must be enforced client-side
                # note: the target can be a comma-separated list
                # why not a JSON array? belzeebub's will again for sure
                if self._post_playerid == self._playerid \
                        or self._playerid in self._target_playerid:
                    post = ''.join(
                            [
                                self._who,
                                ' (whispering to ',
                                self._target_name,
                                '): ',
                                self._content,
                                '\n'
                            ]
                        )
                else:
                    self._type = PostType.IGNORE


            if self._type != PostType.IGNORE:
                self._file.write(post)

            self._who, self._content, self._origRoll = (None, None, None)
            self._post_playerd, self._target_playerid = (None, None)
            self._inlinerolls = []
            self._state = SaxState.BETWEEN_POSTS
        elif self._state == SaxState.IN_INLINEROLLS or self._state == SaxState.IN_SELECTED:
            self._skipping_brackets -= 1
            if self._skipping_brackets == 0:
                self._state = SaxState.POST_CONTENTS


    def _on_key(self, key):
        if self._state == SaxState.BETWEEN_POSTS:
            self._state = SaxState.IN_POST
        elif self._state == SaxState.POST_CONTENTS:
            if key == 'playerid':
                self._state = SaxState.IN_PLAYERID
            elif key == 'who':
                self._state = SaxState.IN_WHO
            elif key == 'content':
                self._state = SaxState.IN_CONTENT
            elif key == 'type':
                self._state = SaxState.IN_TYPE
            elif key == 'origRoll':
                self._state = SaxState.IN_ORIGROLL
            elif key == 'inlinerolls':
                self._state = SaxState.IN_INLINEROLLS
            elif key == 'target':
                self._state = SaxState.IN_TARGET_PLAYERID
            elif key == 'target_name':
                self._state = SaxState.IN_TARGET_NAME
            elif key == 'selected':
                self._state = SaxState.IN_SELECTED
        elif self._state == SaxState.IN_INLINEROLLS:
            if key == 'expression':
                self._state = SaxState.IN_INLINEROLLS_EXPRESSION
            elif key == 'total':
                self._state = SaxState.IN_INLINEROLLS_TOTAL


    def _on_value(self, value):
        if self._state == SaxState.IN_PLAYERID:
            self._post_playerid = value
            self._state = SaxState.POST_CONTENTS
        elif self._state == SaxState.IN_WHO:
            self._who = value
            self._state = SaxState.POST_CONTENTS
        elif self._state == SaxState.IN_CONTENT:
            self._content = value
            self._state = SaxState.POST_CONTENTS
        elif self._state == SaxState.IN_ORIGROLL:
            self._origRoll = value
            self._state = SaxState.POST_CONTENTS
        elif self._state == SaxState.IN_TYPE:
            self._type = PostType.from_string(value)
            self._state = SaxState.POST_CONTENTS
        elif self._state == SaxState.IN_TARGET_PLAYERID:
            self._target_playerid = value
            self._state = SaxState.POST_CONTENTS
        elif self._state == SaxState.IN_TARGET_NAME:
            self._target_name = value
            self._state = SaxState.POST_CONTENTS
        elif self._state == SaxState.IN_INLINEROLLS_EXPRESSION:
            self._inlineroll_expression = value
            self._state = SaxState.IN_INLINEROLLS
        elif self._state == SaxState.IN_INLINEROLLS_TOTAL:
            self._inlinerolls.append(
                    ''.join([self._inlineroll_expression, ' = ', str(value)])
                    )
            self._inlineroll_expression = None
            self._state = SaxState.IN_INLINEROLLS


    def parse(self, chunk):
        self._streamer.consume(chunk)

    def close(self):
        self._streamer.close()


ChatParserState = Enum(
    'ChatParserState',
    'LOOKING MSGDATA EQ QUOTES PAYLOAD DONE'
    )


class ChatParser:
    
    WHITESPACE = ' \n\r\t'

    def __init__(self, filepath, playerid, is_gm):
        self._filepath = filepath
        self._parser_state = ChatParserState.LOOKING
        self._current_lexeme = []
        self._input_tail = ''
        self._json_parser = JsonSaxParser(filepath, playerid, is_gm)


    def _get_lexemes(self, chunk):
        for char in chunk:
            if char in ChatParser.WHITESPACE:
                if self._current_lexeme != []: yield ''.join(self._current_lexeme)
                self._current_lexeme.clear()
            elif char == '"': # '"' = 34
                if self._current_lexeme != []: yield ''.join(self._current_lexeme)
                yield '"'
            else:
                self._current_lexeme.append(char)
        yield ''.join(self._current_lexeme)
        self._current_lexeme.clear()


    def finalize(self):
        self._json_parser.close()
        self._parser_state = ChatParserState.LOOKING
        self._current_lexeme = ''
        self._input_tail = ''


    def _get_short_lexeme(self):
        if (len(lexeme) > 40):
            return '{}...'.format(lexeme[:40])
        else:
            return lexeme


    def process(self, chunk):
        if self._parser_state == ChatParserState.DONE: return

        for lexeme in self._get_lexemes(chunk):
            if self._parser_state == ChatParserState.LOOKING:
                if (lexeme == 'msgdata'):
                    self._parser_state = ChatParserState.MSGDATA
            elif self._parser_state == ChatParserState.MSGDATA:
                if (lexeme == '='):
                    self._parser_state = ChatParserState.EQ
                else:
                    raise ParseError('ChatParser expected "=" after "msgdata", found "{}"'.format(self._get_short_lexeme()))
            elif self._parser_state == ChatParserState.EQ:
                if lexeme == '"':
                    self._parser_state = ChatParserState.PAYLOAD
                else:
                    raise ParseError('ChatParser expected "\"" after "=", found "{}"'.format(self._get_short_lexeme()))
            elif self._parser_state == ChatParserState.PAYLOAD:
                if (lexeme == '"'):
                    if self._input_tail != '':
                        self._json_parser.parse(b64decode(self._input_tail).decode())
                    self._parser_state = ChatParserState.DONE
                else:
                    to_decode = self._input_tail + lexeme
                    b64_stop_pos = len(to_decode) - (len(to_decode) % 4)
                    while True:
                        try:
                            self._json_parser.parse(b64decode(to_decode[: b64_stop_pos]).decode())
                        except Exception as e:
                            if isinstance(e, UnicodeDecodeError) and e.reason == 'unexpected end of data':
                                # utf-8 character spans two chunks
                                b64_stop_pos = e.start - (e.start % 4)
#                                 self._json_parser.parse(b64decode(to_decode[: b64_stop_pos]).decode())
                            else:
                                stderr.write("\nERROR while processing " + self._filepath +  ", chunk:\n")
                                stderr.write(b64decode(to_decode[: b64_stop_pos]).decode(errors="backslashreplace"))
                                stderr.write("\n")
                                print_exc()
                                exit(1)
                        else:
                            self._input_tail = to_decode[b64_stop_pos :]
                            break

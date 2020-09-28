import configparser

options = configparser.ConfigParser()

def load():
    global options
    options.read('config.ini')

def save():
    global options
    with open('config.ini', 'w') as config_file:
        options.write(config_file)

import curses


def addstr(stdscr, y, x, text, attrs=0):
    try:
        stdscr.addstr(y, x, text, attrs)
    except curses.error:
        pass


def move(stdscr, y, x):
    try:
        stdscr.move(y, x)
    except curses.error:
        pass

CSI             = "\x1b["

def SGR(code):
    return CSI + str(code) + "m"

RESET           = SGR(  0)
BOLD            = SGR(  1)
LIGHT           = SGR(  2)
UNDERLINE       = SGR(  4)
BLINK           = SGR(  5)
INVERSE         = SGR(  7)
NORMAL          = SGR( 22)
NO_UNDERLINE    = SGR( 24)

FG_BLACK        = SGR( 30)
FG_RED          = SGR( 31)
FG_GREEN        = SGR( 32)
FG_YELLOW       = SGR( 33)
FG_BLUE         = SGR( 34)
FG_MAGENTA      = SGR( 35)
FG_CYAN         = SGR( 36)
FG_WHITE        = SGR( 37)

FG_DEFAULT      = SGR( 39)

BG_BLACK        = SGR( 40)
BG_RED          = SGR( 41)
BG_GREEN        = SGR( 42)
BG_YELLOW       = SGR( 43)
BG_BLUE         = SGR( 44)
BG_MAGENTA      = SGR( 45)
BG_CYAN         = SGR( 46)
BG_WHITE        = SGR( 47)

BG_DEFAULT      = SGR( 49)

FG_BR_BLACK     = SGR( 90)
FG_BR_RED       = SGR( 91)
FG_BR_GREEN     = SGR( 92)
FG_BR_YELLOW    = SGR( 93)
FG_BR_BLUE      = SGR( 94)
FG_BR_MAGENTA   = SGR( 95)
FG_BR_CYAN      = SGR( 96)
FG_BR_WHITE     = SGR( 97)

BG_BR_BLACK     = SGR(100)
BG_BR_RED       = SGR(101)
BG_BR_GREEN     = SGR(102)
BG_BR_YELLOW    = SGR(103)
BG_BR_BLUE      = SGR(104)
BG_BR_MAGENTA   = SGR(105)
BG_BR_CYAN      = SGR(106)
BG_BR_WHITE     = SGR(107)


def bold(text):
    return BOLD + text + NORMAL


def underline(text):
    return UNDERLINE + text + NO_UNDERLINE


BLACK   = 0
RED     = 1
GREEN   = 2
YELLOW  = 3
BLUE    = 4
MAGENTA = 5
CYAN    = 6
WHITE   = 7

def fg(text, color, bright=True):
    return SGR((90 if bright else 30) + color) + text + FG_DEFAULT


def bg(text, color, bright=False):
    return SGR((100 if bright else 40) + color) + text + FG_DEFAULT



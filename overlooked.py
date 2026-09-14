"""
Overlooked (by Jon King) - terminal ant

<i>```A lone ant’s wayward journey home, unaware that a giant eye was tracking its every step.```</i>

A fun, self-guided terminal exploration written from scratch without external frameworks.

For more info see ./README.md
"""


# ==========================================
# imports / system stuff
# ==========================================
import sys
import time
import ctypes

# ==========================================
# key down stuff I sorta understand and looked up online and discussed with Claude to understand better
# ==========================================
user32 = ctypes.windll.user32

_GetAsyncKeyState = user32.GetAsyncKeyState # GetAsyncKeyState returns a 16-bit integer where different bits mean different things.
                                            # The highest bit tells you if the key is down right now. (what I cared about)
                                            # the lowest bit tracks if it was pressed since the last call.
_GetAsyncKeyState.argtypes = [ctypes.c_int] # GetAsyncKeyState takes an int32. In ctypes, argtypes expects a list or tuple of types because a C function can take zero, one, or many arguments.
                                            # By using a sequence, ctypes knows how to map each item in the list sequentially to positional C arguments.
                                            # alternatively _GetAsyncKeyState.argtypes = (ctypes.c_int,)                                          
_GetAsyncKeyState.restype = ctypes.c_ushort # return is a 16-bit integer. We are using a bitwise flag. short or ushort should work. ushort seems cleaner

# Virtual-key codes (Win32, hex per Microsoft docs)
VK_ESCAPE = 0x1B
VK_LEFT   = 0x25
VK_UP     = 0x26
VK_RIGHT  = 0x27
VK_DOWN   = 0x28
VK_OEM_3  = 0xC0 #tilde/backtick for debug mode

def is_key_down(vk_code):
    return bool(_GetAsyncKeyState(vk_code) & 0x8000)  # I only care about the highest bit - whether key down (bitmask 0x8000 represents binary 1000000000000000)
def vk_for(direction):
    return _VK_FOR_DIRECTION[direction]

# ==========================================
# 2. DATA STRUCTURES & CLASSES
# ==========================================
#from dataclasses import dataclass
from typing import NamedTuple

#@dataclasses
class Vector2D(NamedTuple):
    x: int
    y: int
        
    def __add__(self, other):                                   # for movement and direction projection
        return Vector2D(self.x + other.x, self.y + other.y)
    
    def __mul__(self, scalar):                                  # for opposite (can't move head behind head direction)
        return Vector2D(self.x * scalar, self.y * scalar)
        
    def __rmul__(self, scalar):                                 # for opposite (can't move head behind head direction)
        return self.__mul__(scalar)                             # I didn't have this at first and this hurt. For checking opposite from the head direction.
                                                                # otherwise it assumes -1 * myVector is trying to make a sequence of -1 Vector2Ds

# ==========================================
# CONSTANTS~
# ==========================================
# frame rate / sleep constant
TICK_RATE = 0.1  # seconds / frame = 1/0.1 = 10 updates (-redraws-frames) per second

#screen offset for displaying other info
GRID_LINES_ABOVE = 2   #based on extra text lines above for title + author
GRID_LINES_BELOW = 3   #based on extra text lines below for controls
GRID_HEIGHT = 5   #could be an arg into main
GRID_WIDTH = 20   #could be an arg into main
ANT_LEN = 4


# GRAPHICAL CONSTANTS
HEAD_UP    = "ᗢ"
HEAD_DOWN  = "ᗣ"
HEAD_LEFT  = "ᗤ"
HEAD_RIGHT = "ᗧ"
BODY_UP    = "Ω"
BODY_DOWN  = "Ʊ"
BODY_LEFT  = "ᘳ"
BODY_RIGHT = "𝈀"

# ORIENTATION CONSTANTS
RIGHT = Vector2D(1, 0)
LEFT  = Vector2D(-1, 0)
UP    = Vector2D(0, -1)
DOWN  = Vector2D(0, 1)

# map of ORIENTATION TO VK
_VK_FOR_DIRECTION = {
    UP:    VK_UP,
    DOWN:  VK_DOWN,
    LEFT:  VK_LEFT,
    RIGHT: VK_RIGHT,
}

# ==========================================
# GLOBAL STATE VARS
# ==========================================
# REMEMBER!! - define primitives as global in funcs that set them (FOR _running, _head_pointer, _debug_mode, _debug_down_now; _pos is a list
_debug_mode = False
_running = True
_head_pointer = 0               # I use _pos as a circular buffer and a pointer to the head
_pos = [                        # list of 2-tuples of (Vector2D pos, Vector2D orientation)
                                # TODO: figure out better naming for the combination of pos + orientation.
                                #       AND/OR make a class for it
    (Vector2D(5,0),RIGHT),      # head is first, all the rest are the next segments: 𝈀𝈀𝈀ᗧ
    (Vector2D(4,0),RIGHT),      # also could generate this based on ANT_LEN and screen parameters
    (Vector2D(3,0),RIGHT),
    (Vector2D(2,0),RIGHT)
    ]

def main():
    global _running     
    draw_initial()
    while _running:
        _running, old_tail_pos = update()   # update calls GetAsyncKeyState(VK_ESCAPE), VK_RIGHT, etc.. Changes state vars. Could return instead
        if _running:
            draw(old_tail_pos)     # reads that state, renders
            time.sleep(TICK_RATE)

def draw_initial():
    """Draws the initial box/movement field. TODO: eventually could be dynamically constructed based on a passed in size"""
    # Total Height (12 lines): 2 lines (blank + title/author) + 1 line (top border) + 5 lines (game grid height) + 1 line (bottom border) + 3 lines (controls)
    # Total Width (24 columns): 1 char (left padding) + 1 char (left border) + 20 chars (game grid width) + 1 char (right border) + 1 char (right padding)
    screen_layout = """
  Overlooked by Jon K
 ╔════════════════════╗ 
 ║                    ║ 
 ║                    ║ 
 ║                    ║ 
 ║                    ║ 
 ║                    ║ 
 ╚════════════════════╝ 
  Move:  ↑↓←→
  Quit:  ESC
  Debug: `"""

    print(screen_layout)
    drawAntFull()

def isDirectionAllowed(direction):
    if direction not in [UP, DOWN, LEFT, RIGHT]:
        return False
    
    #get current pos and orientation and next (proposed direction)
    head_pos, head_dir = _pos[_head_pointer]
    next_pos = head_pos + direction
    
    
    if (direction == -1 * head_dir):    #opposite direction to head not allowed
       return False
    if (next_pos.x < 0 or next_pos.y < 0 or next_pos.x >= GRID_WIDTH or next_pos.y >= GRID_HEIGHT):
        return False
    for i in [1,2]: #no need to check head or last segment
        pos, ori = _pos[(_head_pointer + i) % ANT_LEN]
        if (next_pos == pos):
            return False
    # passes all checks
    return True

def build_write_grid_string(grid_pos, char):
    """Generates the string to write one char/cell and return cursor to the end"""
    
    #must be synced with draw_initial() or redefined to render algorithmically
    
    #  (0,0)                            (23,0)
    #  +-----------------------------+  <- Line 0:  Empty Line
    #  |  Overlooked by Jon K        |  <- Line 1:  Title + Author
    #  | ╔═════════════════════════╗ |  <- Line 2:  Top Border
    #  | ║ 4 3 2 1 0 . . . . . . . ║ |  <- Line 3:  Grid Row 0 -- Playable starts at (X,Y): grid_pos (0,0) ~ actual (2,3)
    #  | ║ . . . . . . . . . . . . ║ |  <- Line 4:  Grid Row 1
    #  | ║ . . . . . . . . . . . . ║ |  <- Line 5:  Grid Row 2
    #  | ║ . . . . . . . . . . . . ║ |  <- Line 6:  Grid Row 3
    #  | ║ . . . . . . . . . . . . ║ |  <- Line 7:  Grid Row 4
    #  | ╚═════════════════════════╝ |  <- Line 8:  Bottom Border
    #  | Move:  ↑↓←→                 |  <- Line 9: Controls (Move)
    #  | Quit:  ESC                  |  <- Line 10: Controls (Quit)
    #  | Debug: `                    |  <- Line 11: Controls (Debug)   
    #  +-----------------------------+  <- Line 12: Empty Line <- CURSOR RESTS HERE before/after each write operation
    
    render_pos = grid_pos + Vector2D(2,2)
    lines_up = GRID_HEIGHT + 1 + GRID_LINES_BELOW  - grid_pos.y   # +1 = bottom border
    
    #TODO: absolute pos I think would be better eventually. cause this is getting a bit whacky. I think these are it:
    #screen_line = GRID_LINES_ABOVE + 1 + grid_pos.y    # +1 for the top border
    #screen_col  = 2 + grid_pos.x                       # 1 pad + 1 border
    
    # "\033[" is the "ANSI Control Sequence Introducer (CSI)"
    #     It is an escape sequence that sorta tells the terminal ~"don't print the next few characters" - used to move cursor, change colors, maybe more?
    # NOTE: I only use 3: 'Cursor Up', 'Cursor Right', and 'Cursor Down'.
    #     wiki: https://en.wikipedia.org/wiki/ANSI_escape_code#CSIsection (more: https://en.wikipedia.org/wiki/ANSI_escape_code#SGR)
    #     found some here: https://student.cs.uwaterloo.ca/~cs452/terminal.html
    # "\033[{n}A" = Cursor Up by n
    # "\033[{n}B" = Cursor Down by n
    # "\033[{n}C" = Cursor Right by n
    # "\033[{n}D" = Cursor Left by n
    # "\033[2J"   = Clears screen 
    # "\033[H"    = Move the cursor to the upper-left corner of the screen
    # "\033[r;cH" = Move the cursor to row r, column c. Note that both the rows and columns are indexed starting at 1
    # "\033[?25l" = Hide the cursor
    # "\033[K"    = Delete everything from the cursor to the end of the line
    # "\033[0m"   = Reset special formatting (such as colour)
    # "\033[30m"  = Black text
    # "\033[31m"  = Red text
    # "\033[32m"  = Green text
    # "\033[33m"  = Yellow text
    # "\033[34m"  = Blue text
    # "\033[35m"  = Magenta text
    # "\033[36m"  = Cyan text
    # "\033[37m"  = White text
    # "\033[38:5:⟨n⟩m" = set foreground color to n from available color table on wiki
    # "\033[48;5;⟨n⟩m" = set background color to n from available color table on wiki
    # "\r"        = carriage return (return to column 0)
    
    return (
        f"\033[{lines_up}A"      # Move UP to target row
        f"\033[{render_pos.x}C"  # Move RIGHT to target column
        f"{char}"                # Print character
        f"\033[{lines_up}B"      # Move DOWN back to resting row
        f"\r"                    # Carriage return to Column 0
    )
    

def graphic_from_type_and_orientation(segment_number, orientation):
    """
    Returns the ASCII character based on type and orientation vector. For now just write 0,1,2,3
    coord_data looks like [x, y, [dx, dy]]. Segment 0 is the head. Segments 1,2,3 are body. otherwise, erasable (old tail)
    """
    if _debug_mode:
        if segment_number >= 0 and segment_number <= 3:
            return segment_number
        else:
            return " " #delete the tail
    else:        
        if segment_number == 0:
            if orientation == UP:    return HEAD_UP
            if orientation == DOWN:  return HEAD_DOWN
            if orientation == LEFT:  return HEAD_LEFT
            if orientation == RIGHT: return HEAD_RIGHT
        elif segment_number > 0 and segment_number < ANT_LEN:
            if orientation == UP:    return BODY_UP
            if orientation == DOWN:  return BODY_DOWN
            if orientation == LEFT:  return BODY_LEFT
            if orientation == RIGHT: return BODY_RIGHT
        else:
            return " "

def update():
    """Checks which keys are pressed, mutates state. Returns (running: bool, old_tail_pos: Vector2D | None)"""
    if is_key_down(VK_ESCAPE):
        return False, None
        
    _debug_down_now = is_key_down(VK_OEM_3)
    global _debug_mode
    if _debug_down_now: 
        _debug_mode = not _debug_mode
        
    for direction in [UP, DOWN, LEFT, RIGHT]:
        down_now = is_key_down(vk_for(direction))
        if down_now and isDirectionAllowed(direction):
            old_tail_pos = move_one_step(direction)
            return True, old_tail_pos #so we can erase it
    
    return True, None #no move!

def move_one_step(direction):
    """assumes the direction is valid. projects the head in the direction passed in and overwrites the old ~tail.
       updates the head pointer. returns the old tail for visual deletion
    
    `_pos` is a fixed 4-slot ring buffer.  (TODO: base initial definition on ANT_LEN)
    
    Moving decrements `_head_pointer`, so walking *backwards* through slots walks *forwards*
    through time. The payoff: the slot immediately behind the head is always
    the oldest segment — the tail — which is exactly the slot the new head
    should overwrite. One pointer decrement, one slot write, no shifting.

    slot:          0                1                2                3
    before:  ((5,0),RIGHT)    ((4,0),RIGHT)    ((3,0),RIGHT)    ((2,0),RIGHT)      # _head_pointer = 0
                   ^head           seg1             seg2             tail

    move DOWN:  _head_pointer = (0 - 1) % 4 = 3
                 new_pos = (5,0) + DOWN = (5,1)     # DOWN = (0,1)
                 pos[3] = new_pos, DOWN             # tail slot reused

    slot:          0                1                2                3
    after:   ((5,0),RIGHT)    ((4,0),RIGHT)    ((3,0),RIGHT)    ((5,1),DOWN)      # _head_pointer = 3
                  seg1         seg2             tail                 ^head

    Returns the old tail position so draw() knows which cell to erase.
    """
    global _head_pointer
    old_tail_pos = _pos[(_head_pointer - 1) % ANT_LEN][0]
    new_pos = _pos[_head_pointer][0] + direction
    _head_pointer = (_head_pointer - 1) % ANT_LEN
    _pos[_head_pointer] = new_pos, direction
    return old_tail_pos
    
def draw(old_tail_pos):
    """draws the new head, changes the old head to a neck, erases the old tail"""
    if (old_tail_pos is None):
        return
    
    head_pos, head_orientation = _pos[_head_pointer]
    segment_pos, segment_orientation = _pos[(_head_pointer + 1) %ANT_LEN]
    update_string=""
    
    if (old_tail_pos != head_pos):
        update_string += build_write_grid_string(old_tail_pos, " ")                                                     # tail     - erase old_tail unless head at same position
    update_string += build_write_grid_string(segment_pos, graphic_from_type_and_orientation(1, segment_orientation))    # old head - draw segment 1 at head + 1
    update_string += build_write_grid_string(head_pos, graphic_from_type_and_orientation(0, head_orientation))          # new head - draw head at head pos
    
    sys.stdout.write(update_string)
    sys.stdout.flush()

def drawAntFull(old_tail_pos = None):
    """for now this is only intended to use at the start but could be extended to use for everything, say for the debug printing."""
    
    update_string=""    
    head_pos, head_orientation = _pos[_head_pointer]
    
    #old tail deletion
    if ((old_tail_pos is not None) and (old_tail_pos != head_pos)):
        update_string += build_write_grid_string(old_tail_pos, " ")
    
    #head
    update_string += build_write_grid_string(head_pos, graphic_from_type_and_orientation(0, head_orientation))
    
    #segments
    for i in range(1,ANT_LEN): #ant len-1. I want [1,2,3] here for the center segments
        segment_pos, segment_orientation = _pos[(_head_pointer + i) %ANT_LEN]
        update_string += build_write_grid_string(segment_pos, graphic_from_type_and_orientation(i, segment_orientation))
    
    sys.stdout.write(update_string)
    sys.stdout.flush()

# could have a debug argument so it does the initial rendering in debug mode. Alternate, change the default value '_debug_mode = True' and re-run.
if __name__ == "__main__":
    main()
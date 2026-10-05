from enum import Enum, auto
import typing
from dataclasses import dataclass

class ins(Enum): #list of all avaliable public instructions
    # public functions begin with 1--
    MOVE = 100
    PONDER = auto()
    SETTINGS = auto()
    RESIGN = auto()
    
class arbins(Enum): #list of all avaliable arbiter instructions
    # Arbiter functions begin with 2--
    PING = 200
    PING_REPLY = auto()
    PIPE_CLOSE = auto()
    PIPE_CLOSED = auto()
    INSTRUCTION_INVALID = auto()

@dataclass
class Instruction_base: 
    string_code: typing.AnyStr = None
    arg_length: int = 0
    send_args: typing.Any = None
    timeout: int | float = 0
    returns: typing.Any = None
    reply: bool | ins | arbins = False 
    engine_first: bool = False
    arbiter: bool = False
    sendable: bool = True
    implemented: bool = True
    function_to_call: typing.Callable | None = None
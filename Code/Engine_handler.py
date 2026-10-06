# fuck me this is the most complicated shit i've written in my entire fucking life

#NOTE: this file must be initiated from main.py . Trying to run this script from this file will result in ModuleNotFoundError because Resources folder is not in sys.path

from multiprocessing import Process
import multiprocessing.connection as mpcon
import hashlib
import psutil
import os
import importlib.util
import inspect
import sys
import errno
from dataclasses import dataclass
import typing

from Resources.program_settings import Engine_Handling as engset
from Resources.instructions import ins,arbins,Instruction_base

@dataclass
class Pipe:
    arbiter: mpcon.PipeConnection
    engine: mpcon.PipeConnection
    was_closed: bool = True

@dataclass
class Request:
    denominator: typing.AnyStr
    instruction: ins | arbins
    parameters: Instruction_base
    arguments: typing.Tuple

@dataclass
class Last_Instruction:
    """
    Basic parameters of the last intruction both sent and received
    """
    code: ins | arbins = None
    parameters: Instruction_base = None
    arguments: int | typing.Tuple | None = None

class Engine_handler:
    class Communications:
        def __init__(self,connection: Pipe, identification: typing.AnyStr):
            self.identificator = identification
            self.pipe = connection
            self.last_tx = Last_Instruction()
            self.last_rx = Last_Instruction()

            self.translate = {               
                    # Public facing functions declarations
                ins.MOVE : Instruction_base(arg_length=0,returns=(NotImplemented),timeout=engset.MOVE_DEFAULT_TIMEOUT,reply=ins.MOVE),
                ins.PONDER : Instruction_base(implemented=False),
                ins.SETTINGS : Instruction_base(implemented=False),
                ins.RESIGN : Instruction_base(engine_first=True, sendable= False),
                    # Arbiter functions declarations
                arbins.PING : Instruction_base(timeout = engset.ARBITER_DEFAULT_TIMEOUT, returns=arbins.PING_REPLY, arbiter=True),
                arbins.PING_REPLY : Instruction_base(arg_length=1, returns=int, reply=arbins.PING, arbiter=True, sendable=False),
                arbins.PIPE_CLOSE : Instruction_base(timeout=engset.ARBITER_DEFAULT_TIMEOUT,arbiter=True),
                arbins.PIPE_CLOSED : Instruction_base(reply=arbins.PIPE_CLOSE, arbiter=True, sendable= False),
                arbins.INSTRUCTION_INVALID : Instruction_base(arg_length=3, returns=(typing.AnyStr,typing.AnyStr,typing.Tuple), reply=True, engine_first=True, arbiter= True, sendable=False)
            }

            # automatically assigns the string version of the instruction to its respective instruction object
            for code in ins:
                self.translate[code].string_code = code.name
            for code in arbins:
                self.translate[code].string_code = code.name


        def send(self, instruction: ins|arbins, function_args: typing.Tuple):
            """
            Verifies, then sends the requested instruction and its arguments to the Arbiter_comms\n
            -If something is amiss, this function raises an exception with a specific error code\n

            Allows for sending both public and arbiter instructions (ins / arbins)
            """

            # checks the current status of the pipe connection object
                # if nothing fails fetches the parameters for the function and the inputted length of args
            try: 
                self._check_pipe()
            except Exception as exc: raise exc
            else:
                param = self.translate.get(instruction,KeyError)
                send_arg_length = self._determine_length(function_args)

            try:
                # Checks too see if all parameters are correct, raises specific exception if not
                if param == KeyError: # if the raised instruction doesnt exist
                    raise KeyError(errno.ENXIO,"Requested function does not exist")
                elif not param.implemented:
                    raise NotImplementedError(errno.ENOSYS,f"The functionality for {instruction} was not yet implemented")
                elif not param.sendable:
                    raise TypeError(errno.ESPIPE,f"instruction {instruction.name} cannot be sent to Engine")
                elif send_arg_length != param.arg_length: #given argument length and expected argument length dont match
                    raise ValueError(errno.E2BIG,f"instruction {instruction.name} expects {param.arg_length} args, but {send_arg_length} were received")
                #elif timeout > engset.MAX_TIMEOUT:
                 #   raise ValueError(errno.EINVAL,f"requested timeout ({timeout} s) exceeds maximum allowed timeout ({engset.MAX_TIMEOUT} s)")
            except Exception as exc: raise exc

            pipe_string = None
            if not param.arbiter:
                pipe_string = ("REQUEST",instruction.name,(function_args))
            else:
                pipe_string = ("ARBITER",instruction.name,(function_args))

            print(f"[{self.identificator}]: {instruction} sent {pipe_string} to Engine")
            self.last_tx.code = instruction
            self.last_tx.arguments = function_args
            self.last_tx.parameters = param
            self.pipe.arbiter.send(pipe_string)


        
        def receive(self, timeout:int=0, ): # FINISH ERRORS
            self._check_pipe()

            if timeout > engset.MAX_TIMEOUT:
                raise ValueError() 

            received_packet = mpcon.wait([self.pipe.arbiter],timeout=timeout) #waits for packet receive - if 0, waits indefinitely
            if self.pipe.arbiter in received_packet:
                unverified_instruction = self.pipe.arbiter.recv()
            else:
                raise ConnectionError()

            instruction_code = self._find_instruction_from_string(unverified_instruction[1])
            if not instruction_code:
                raise ValueError()
            
            request = Request(unverified_instruction[0],instruction_code,self.translate[instruction_code],unverified_instruction[2])

            try:
                if not request.parameters.reply and not request.parameters.engine_first:
                    raise ValueError
                    # if receive is not a reply and also cannot be sent by the engine first
                    # a receive must be either a reply or be engine_first - there is no instruction which behaves differently
                if request.parameters.engine_first:
                    raise StopIteration
                    # if the received instruction is supposed an engine_first call, handle separately
                
                if request.denominator == "REQUEST":
                    raise ValueError
                    # since all engine_first instruction are now excluded, it must be either "reply" or "arbiter"
                else:
                    if request.denominator == "ARBITER" and not request.parameters.arbiter:
                        raise ValueError
                        # Engine wants arbiter processing, however the request parameters dont allow it.
                    elif request.denominator == "REPLY" and not self.last_tx.parameters.reply:
                        raise ValueError
                        # receive is a reply, however last sent instruction does not expect a reply
    
                                        
                if request.instruction != self.last_tx.parameters.reply:
                    raise ValueError
                    # if the receive is a reply, but doesnt match with reply condition last sent instruction expects 
                
                    
            except StopIteration: self._handle_engine_first()
            except Exception as err: raise err

            
        def _handle_engine_first(self,request):
            pass



        def _find_instruction_from_string(self,string_to_search):
            values = self.translate.values()
            at_index = 0
            for item in values:
                if string_to_search == item.string_code:
                    keys = self.translate.keys()
                    return list(keys)[at_index]
                else:
                    at_index += 1
            else:
                return None


        def _check_pipe(self):
            if not self.pipe.arbiter.closed:
                pass
            elif self.pipe.arbiter.closed != self.pipe.was_closed:
                raise ValueError(errno.ENOTCONN,"Pipe to engine is closed!")
            else:
                raise BrokenPipeError(errno.ECONNREFUSED,"Pipe was closed without previous instruction")

        def _determine_length(self,function_arguments):
                """
                Determines the length of the functions argument tuple
                Tuple - returns its len()
                Int,Float - returns 1
                other - returns None
                """
                if isinstance(function_arguments,(list,tuple)):
                    length = len(function_arguments)
                elif isinstance(function_arguments,(int,float)):
                    length = 1
                else:
                    length = None
        
                return length







    def __init__(self,engine_directory, engine_identificator, cpu_affinity:tuple):
        connection = mpcon.Pipe()
        self.pipe = Pipe(*connection,)
        self.comms = self.Communications(self.pipe,engine_identificator)
        self.identificator = engine_identificator

        if not os.path.isdir(engine_directory): # checks if provided engine directory exists
            raise ValueError(f"[{self.identificator}]: The engine directory could not be found")
        else:
            self.path = engine_directory

        if False: # just my switch cuz outside normal functionality this is annoying af
            try: 
                self._verify_comms_file() 
                # communications file match verification
            except Exception as error: raise error 
        
        self.path_main_file = os.path.join(self.path,engset.ENGINE_MAINFILE) #path of the script which will be launched
        if not os.path.isfile(self.path_main_file): #checks if the path is valid and a file
            raise ImportError(f"[{self.identificator}]: {engset.ENGINE_MAINFILE} file does not exist or could not be found")
 
        self.engine = Process(target=Engine_handler._launch_engine_instance,args=(self.pipe.engine,self.identificator,self.path_main_file,self.path))
        self.process = psutil.Process(self.engine.pid)
        self.process.cpu_affinity(cpu_affinity)
        self.engine.start()
        self.comms.send(arbins.PING,())
        self._test_receive()
        print(f"[{self.identificator}]: process start success")
        self._terminate_engine()
        
        
    def _test_receive(self):
        received = mpcon.wait([self.pipe.arbiter],engset.MOVE_DEFAULT_TIMEOUT)
        if self.pipe.arbiter in received:
            print("received:" ,self.pipe.arbiter.recv())
        else: self._terminate_engine()


    # Verification, that the Communications file provided by the engine is the same as the Engine_base - (if the versions match)
    def _verify_comms_file(self):
        comms_address = os.path.join(self.path,engset.COMMS_FILENAME)
        if os.path.isfile(comms_address):
            # only actually checks if the path to engine communications file is valid and is a file directory
            HASH = "sha256" #uses sha256 hashing. Absolutely overkill, but why not

            with open(comms_address, "rb") as engine_file:
                digested_engine_file = hashlib.file_digest(engine_file, HASH)
                digested_engine = digested_engine_file.hexdigest()

            try:
                with open(os.path.join(os.getcwd(),"Engine_base_files",engset.COMMS_FILENAME), "rb") as engine_base_file:
                    digested_arbiter_file = hashlib.file_digest(engine_base_file, HASH)
                    digested_arbiter = digested_arbiter_file.hexdigest()
            except FileNotFoundError: raise FileNotFoundError(f"Arbiter-side {engset.COMMS_FILENAME} does not exist or could not be found")

            # hashes both communications file using the same hashing system. If the files match, the hash will be the same string as generated in .hexdigest()

            if digested_arbiter == digested_engine:
                engine_file.close()
                engine_base_file.close()
                return True
                # if the hashes match both files are closed (I dont know if its neccessary, but im not keeping them open) and True flag is returned
            else:
                raise ImportError(f"Verification {engset.COMMS_FILENAME} file does not match with one found in Engine (root) folder")
                # both files were hashed, but one did not match another
        else:
            raise FileNotFoundError(f"Engine-side {engset.COMMS_FILENAME} does not exist or could not be found")

    ## Functions to initiate the Main_Engine class in Engine_main.py file - both functions need to be bound (static), as they are already executed in a different process - dont have access to this class
    # basically imports Engine_main.py as a module so I can reference stuff inside of it
    @staticmethod
    def _load_top_engine_class(identification,path_to_main):
        Engine_spec = importlib.util.spec_from_file_location(identification,path_to_main)
        module = importlib.util.module_from_spec(Engine_spec)
        Engine_spec.loader.exec_module(module)
        return module

    @staticmethod
    # imports the file as a module, dynamically finds the Main_Engine class (or several), and conditionally creates an instance of it
    def _launch_engine_instance(pipe_connection,identification,path_to_main,path_to_engine):
        sys.path.insert(0,str(path_to_engine))
        module = Engine_handler._load_top_engine_class(identification,path_to_main) # loads the Engine_main.py file as a module
        avaliable_objects = inspect.getmembers(module) # gets all avaliable objects for lookup
        main_engine_class = None
        for name,object_type in avaliable_objects: #checks if the object is a class named Main_Engine
            if inspect.isclass(object_type):
                class_name = name.casefold()
                if class_name == (engset.ENGINE_MAINCLASS).casefold(): # if it is, the class type is as the class that will be initiated
                    if not main_engine_class:
                        main_engine_class = object_type
                    else: # or if there are multiple classes named the same way, nothing will be executed and error will be raised
                        raise ImportError(f"[{identification}]: contains multiple instances of classes named '{engset.ENGINE_MAINCLASS}'")
        else:
            if not main_engine_class:
                raise ImportError(f"[{identification}]: contains no instance of a class named 'Main_Engine")
            else:
                main_engine_class(pipe_connection)



    def _receive_data(self,watchdog=2.5):
        received = mpcon.wait([self.pipe.arbiter],watchdog)
        if self.pipe.arbiter in received:
            return self.pipe.arbiter.recv()
        else: return None

    def move_request(self,*arguments):
        self.pipe.arbiter.send(("MOVE",arguments))
        return self._receive_data()   

    def _terminate_engine(self):
        if not self.pipe.arbiter.closed:
            self.pipe.arbiter.close()
            self.pipe.was_closed = True
        print(f"[{self.identificator}]: terminating engine")
        children = self.process.children(True)
        for process in children:
            try:
                process.terminate()
            except psutil.NoSuchProcess:
                pass
        print(f"[{self.identificator}]: terminated")


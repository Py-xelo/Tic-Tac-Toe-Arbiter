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
import time
from dataclasses import dataclass
from typing import Callable


from Resources.program_settings import Engine_Handling as set

class Engine_handler:

    class Communications:

        class Instruction:
            function = Callable
            args = int
            returns = None or tuple or Callable
            engine_first = bool
            for_arbiter = bool

        def __init__(self):
            self.instruction_send_translate = {
              "MOVE":self.Instruction(self.request_move,int,True,True),
              "PONDER":self.Instruction(NotImplementedError,int,False,True),
              "SETTINGS":self.Instruction(NotImplementedError,int,False,True),
              "RESIGN":self.Instruction(NotImplementedError,int,True,False)
            }

        def execute(function,timeout=0):
            pass

        def request_move():
            pass


    def __init__(self,engine_directory, engine_identificator, cpu_affinity:tuple):
        self.comms = self.Communications()
        self.identificator = engine_identificator

        if not os.path.isdir(engine_directory): # checks if provided engine directory exists
            raise ValueError("The engine directory could not be found")
        else:
            self.path = engine_directory

        if False: # just my switch cuz outside normal functionality this is annoying af
            try: 
                self._verify_comms_file() 
                # communications file match verification
            except Exception as error: raise error 
        
        self.path_main_file = os.path.join(self.path,"Engine_main.py") #path of the script which will be launched
        if not os.path.isfile(self.path_main_file): #checks if the path is valid and a file
            raise ImportError(f"{set.ENGINE_MAINFILE} file does not exist or could not be found")
 
        self.arbiter_conn, self.engine_conn = mpcon.Pipe()
        self.engine = Process(target=Engine_handler._launch_engine_instance,args=(self.engine_conn,self.identificator,self.path_main_file,self.path))
        self.process = psutil.Process(self.engine.pid)
        self.process.cpu_affinity(cpu_affinity)
        self.engine.start()
        self.ping_engine()
        self._terminate()
        


    # Verification, that the Communications file provided by the engine is the same as the Engine_base - (if the versions match)
    def _verify_comms_file(self):
        comms_address = os.path.join(self.path,set.COMMS_FILENAME)
        if os.path.isfile(comms_address):
            # only actually checks if the path to engine communications file is valid and is a file directory
            HASH = "sha256" #uses sha256 hashing. Absolutely overkill, but why not

            with open(comms_address, "rb") as engine_file:
                digested_engine_file = hashlib.file_digest(engine_file, HASH)
                digested_engine = digested_engine_file.hexdigest()

            try:
                with open(os.path.join(os.getcwd(),"Engine_base",set.COMMS_FILENAME), "rb") as engine_base_file:
                    digested_arbiter_file = hashlib.file_digest(engine_base_file, HASH)
                    digested_arbiter = digested_arbiter_file.hexdigest()
            except FileNotFoundError: raise FileNotFoundError(f"Arbiter-side {set.COMMS_FILENAME} does not exist or could not be found")

            # hashes both communications file using the same hashing system. If the files match, the hash will be the same string as generated in .hexdigest()

            if digested_arbiter == digested_engine:
                engine_file.close()
                engine_base_file.close()
                return True
                # if the hashes match both files are closed (I dont know if its neccessary, but im not keeping them open) and True flag is returned
            else:
                raise ImportError(f"Verification {set.COMMS_FILENAME} file does not match with one found in Engine (root) folder")
                # both files were hashed, but one did not match another
        else:
            raise FileNotFoundError(f"Engine-side {set.COMMS_FILENAME} does not exist or could not be found")

    def ping_engine(self,timeout=set.DEFAULT_TIMEOUT):
        """
        Returns True if the engine replies with ("ARBITER","PING-REPLY",(time_ns))
        """
        self.arbiter_conn.send(("ARBITER","PING",()))
        

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
                if class_name.casefold() == ("main_engine"): # if it is, the class type is as the class that will be initiated
                    if not main_engine_class:
                        main_engine_class = object_type
                    else: # or if there are multiple classes named the same way, nothing will be executed and error will be raised
                        raise ImportError(f"{identification} contains multiple instances of classes named 'Main_Engine'")
        else:
            if not main_engine_class:
                raise ImportError(f"{identification} contains no instance of a class named 'Main_Engine")
            else:
                main_engine_class(pipe_connection)



    def _receive_data(self,watchdog=2.5):
        received = mpcon.wait([self.arbiter_conn],watchdog)
        if self.arbiter_conn in received:
            return self.arbiter_conn.recv()
        else: return None

    def move_request(self,*arguments):
        self.arbiter_conn.send(("MOVE",arguments))
        return self._receive_data()   

    def _close(self):
        self.arbiter_conn.send(type(None))
        self.engine.join()
        print(f"Engine {self.identificator} process closed successfully")

    def _terminate(self):
        self.engine.terminate()
        print(f"Engine {self.identificator} process forcefully terminated")

    



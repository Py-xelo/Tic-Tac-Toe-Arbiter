# fuck me this is the most complicated shit i've written in my entire fucking life

from multiprocessing import Process
import multiprocessing.connection as mpcon
import hashlib
import psutil
import os
import importlib.util
import inspect
import sys
import Resources.program_settings as set

class Data_receive:
    def test(self):
        pass


class Engine_handler(Data_receive):
    def __init__(self,engine_directory, engine_identificator, cpu_affinity:tuple):
        self.identificator = engine_identificator

        if not os.path.isdir(engine_directory): # checks if provided engine directory exists
            raise ValueError("The engine directory could not be found")
        else:
            self.path = engine_directory
        try: self._verify_comms_file()
        except Exception as error: raise error 
        
        self.path_main_file = os.path.join(self.path,"Engine_main.py") #path of the script which will be launched
        if not os.path.isfile(self.path_main_file): #checks if the path is valid and a file
            raise ImportError(f"{set.ENGINE_MAINFILE} file does not exist or could not be found")
 
        self.arbiter_conn, self.engine_conn = mpcon.Pipe()
        self.engine = Process(target=Engine_handler._launch_engine_instance,args=(self.engine_conn,self.identificator,self.path_main_file,self.path))
        self.process = psutil.Process(self.engine.pid)
        self.process.cpu_affinity(cpu_affinity)
        self.engine.start()
        self.arbiter_conn.send(("ARBITER","PING",()))
        received = mpcon.wait([self.arbiter_conn],2)
        if self.arbiter_conn in received:
            print(self.arbiter_conn.recv())
        else: raise RuntimeError("Engine did not reply to initial ping")
        self._terminate()

   


    def _verify_comms_file(self):
        comms_address = os.path.join(self.path,set.COMMS_FILENAME)
        if os.path.isfile(comms_address):
            with open(comms_address, "rb") as engine_file:
                digested_engine_file = hashlib.file_digest(engine_file, "sha256")
                digested_engine = digested_engine_file.hexdigest()
            with open(os.path.join(os.getcwd(),"Engine_base",set.COMMS_FILENAME), "rb") as engine_base_file:
                digested_arbiter = hashlib.file_digest(engine_base_file, "sha256")
                digested_arbiter = digested_engine_file.hexdigest()

            if digested_arbiter == digested_engine:
                engine_file.close()
                engine_base_file.close()
                return True
            else:
                raise ImportError(f"Verification {set.COMMS_FILENAME} file does not match with one found in Engine folder")
        else:
            raise FileNotFoundError(f"{set.COMMS_FILENAME} does not exist or could not be found")

    @staticmethod
    def _load_top_engine_class(identification,path_to_main):
        Engine_spec = importlib.util.spec_from_file_location(identification,path_to_main)
        module = importlib.util.module_from_spec(Engine_spec)
        Engine_spec.loader.exec_module(module)
        return module

    @staticmethod
    def _launch_engine_instance(pipe_connection,identification,path_to_main,path_to_engine):
        sys.path.insert(0,str(path_to_engine))
        module = Engine_handler._load_top_engine_class(identification,path_to_main)
        avaliable_classes = inspect.getmembers(module)
        main_engine_class = None
        for name,object_type in avaliable_classes:
            if inspect.isclass(object_type):
                class_name = name.casefold()
                if class_name.casefold() == ("main_engine"):
                    if not main_engine_class:
                        main_engine_class = object_type
                    else:
                        raise ImportError(f"{identification} contains multiple instances of classes named 'Engine_Main'")
                    
        main_engine_class(pipe_connection)



    def _receive_data(self,watchdog=2.5):
        received = mpcon.wait([self.arbiter_conn],watchdog)
        if self.arbiter_conn in received:
            return self.arbiter_conn.recv()
        else: return None

    def move(self,*arguments):
        self.arbiter_conn.send(("move",arguments))
        return self._receive_data()

    def _close(self):
        self.arbiter_conn.send(type(None))
        self.engine.join()
        print(f"Engine {self.identificator} process closed successfully")

    def _terminate(self):
        self.engine.terminate()
        print(f"Engine {self.identificator} process forcefully terminated")

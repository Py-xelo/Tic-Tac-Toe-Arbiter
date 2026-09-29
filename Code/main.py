import sys
import os
sys.path.insert(0,str(os.getcwd())) # sets the sys.path so absolute importing paths like actually work (sets it to Tic_Tac_Arbiter)

# absolute path imports which need the inserted sys.path to be imported from parent folder, not /Code folder
from Code.Engine_handler import Engine_handler
from Resources import program_settings as set


class Engine_instance_management:
    def __init__(self): #makes a list of all avaliable engines
        self.path = os.path.join(os.getcwd(),set.ENGINE_FOLDERNAME)
        if not os.path.isdir(self.path):
            raise ImportError(f"Directory 'Engines' could not be result {os.getcwd()}. Set chdir to Tic_Tac_Arbiter directory!")

        self.engine_dict = {}
        self._calculate_engine_list()

    def _calculate_engine_list(self):
        _folder_scan = os.scandir(self.path)
        engine_id = 0
        for engine in _folder_scan:
            if engine.is_dir() and "engine" in engine.name.casefold():
                self.engine_dict.update({engine_id : (engine.name,engine.path)})
            engine_id += 1

    def get_data(self,engine_id:int):
        """
        Returned value: (engine_name,engine_path)
        """ 
        returned_value = self.engine_dict.get(engine_id,Exception)
        if returned_value == Exception:
            raise KeyError("Requested key does not exist")
        else:
            return returned_value

engines = Engine_instance_management()

def engine_instance_start(engine_id):
    instance_data = engines.get_data(engine_id)
    return Engine_handler(os.path.join(engines.path,instance_data[1]),instance_data[0],(0,1))

if __name__ == "__main__":
    engine_instance = engine_instance_start(0)
    
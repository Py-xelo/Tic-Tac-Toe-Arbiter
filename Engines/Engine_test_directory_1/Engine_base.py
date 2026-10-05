from Arbiter_communications import Arbiter_communication

class Game_settings:
    pass

class Engine_Base_class:
    def __init__(self,pipe_conn):
        self.comms = Arbiter_communication(pipe_conn)

        self.translate = {
            "MOVE": self.move,
            "PONDER" : self.ponder
        }

        self.main_loop()

    def main_loop(self):
        while not self.comms.pipe.closed:
            request = self.comms.receive_arbiter_instruction()
            if not request:
                 continue
            instruction = self.translate.get(request[0],RuntimeError)
            reply = instruction(*request[1])
            self.comms.send_to_arbiter(request[0],reply)

            
    def move(self):
        raise NotImplementedError(f"function '{self.move.__name__}' must be implemented by your Engine!")

    def ponder(self):
        raise NotImplementedError(f"function '{self.ponder.__name__}' must be implemented by your Engine!")

    def resign(self):
        self.comms.send_to_arbiter(("RESIGN",()))

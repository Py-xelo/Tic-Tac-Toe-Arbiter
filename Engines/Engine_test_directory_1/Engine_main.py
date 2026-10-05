from Arbiter_communications import Arbiter_communication


class Main_Engine:
    def __init__(self,pipe_conn):
        self.comms = Arbiter_communication(pipe_conn)

        self.translate = {
            "MOVE": self.check_move,
            "PONDER" : self.ponder
        }
        self.main_loop()

    def main_loop(self):
        while not self.comms.pipe.closed:
            request = self.comms.receive_arbiter_instruction()
            if not request:
                 continue
            instruction = self.translate.get(request[0])
            reply = instruction(request[1])
            self.comms.send_to_arbiter(request[0],reply)

            
    def check_move(self):
        raise NotImplementedError()

    def ponder(self):
        raise NotImplementedError()

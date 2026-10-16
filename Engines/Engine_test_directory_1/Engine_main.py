import Engine_base

class Main_Engine_class(Engine_base.Engine_Base_class):
    def move(self):
        self.comms.send_to_arbiter("test")
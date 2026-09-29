import multiprocessing.connection as mpcon
import time

# VERSION --- V1.0.0
# API --- IAPI 1.0

class Arbiter_communication:
    """IMPORTANT NOTE: YOUR ENGINE WILL NOT EVEN START IF YOU TOUCH ANYTHING IN HERE!
    
        Class which directly communicates with the Arbiter. Create an instance of this class with the pipe connection provided.
    """

    # Public-facing functions, which you can (and need) to use in order to communicate with the Arbiter

    def receive_arbiter_instruction(self): # blocks the program until a data packet from Arbiter is received
        """
        Function which returns the current instruction from the Arbiter.\n
        This function is blocking, meaning your code will stop until a packet from Arbiter is received and correctly read.\n\n
        The return of this function can be either one of these:
        1. ("INSTRUCTION_CODE",(tuple of arguments))
        2. None - An incorrect function was sent by the Arbiter and is currently being handled.
        NOTE: If the receive is None, continue to loop to activate this function again!
        """
        if not self.pipe_open:
            raise RuntimeError("Cannot receive data through closed pipe")
        request = self.pipe.recv() # blocking instruction - waits for data from Arbiter
        return self._handle_received(request)
            

    def send_to_arbiter(self,data_to_send): #sends the inputed data packet to Arbiter through pipe
        """
        Sends a packet back to Arbiter as a mean of replying to a previously sent Arbiter instruction.\n
        BEWARE:
        1. Sending an Empty packet will raise a ValueError. 
        2. Sending an incorrectly formatted packet is an error and will forfeit forfeit game to opponent.
            > Reply packets should be formatted as ("name of received instruction",(docs specified reply))  
        3. Unless otherwise specified, sending a non-reply packet will forfeit the game to opponent
        """
        if not self.pipe_open:
            raise RuntimeError("Cannot send data through closed pipe")
        if not data_to_send:
            raise ValueError("Empty packet cannot be sent to Arbiter!")
        self.pipe.send(data_to_send)


    # Interal back-end functions and workings, you likely wont need these :D

    def __init__(self,pipe_conn: mpcon.Connection): #initiation of the whole class, opens connections and initiates dictionaries
            self.pipe = pipe_conn
            self.pipe_open = True
            self._define_translation_dictionary()
            
            
    def _define_translation_dictionary(self):
        # arbiter functions - functions which will be called directly when called
        self.arbiter_translation = {
            "PIPE_CLOSE": (self.__close_pipe,0),
            "PING": (self._ping,1)
            }

        # dictionary which has the argument details for each function the Arbiter can call
            # currently only checks length of arguments cuz its just easier for now
        self.translate_public_function = {
            "MOVE": int,
            "PONDER" : int,
            "SETTINGS" : int
            }

    def _ping(self): # sends a ping back to Arbiter with current timestamp attached
        self.send_to_arbiter(("ARBITER","PING_REPLY",(time.time_ns(),)))

    def _check_receive_validity(self,input_data): #checks the IAPI validity of received packet
        arbiter_method = False  
        if input_data[0] == "ARBITER":
            # if the function is meant for Arbiter, it gets translated using special dictionary, which also checks if the instruction is a method call
            dictionary_reply = self.arbiter_translation.get(input_data[1],KeyError)
            if dictionary_reply is not KeyError:
                request_arguments = len(input_data[2])
                if callable(dictionary_reply):
                    arbiter_method = True
                else:
                    arbiter_method = False
                # if the packet is an arbiter instruction, however is not a method call, the flag which would trigger the call is turned off
                
                           
        else:
            # if it isnt, its checked with normal translation dictionary, obviously no method_call for arbiter instruction is determined
            dictionary_reply = self.translate_public_function.get(input_data[0],KeyError)
            if not(dictionary_reply == KeyError):
                request_arguments = len(input_data[1])

        # argument lengths are stored in both cases to be compared

        if not(dictionary_reply == KeyError): #if the function actually exists and can be searched up
            function_arguments = dictionary_reply [1]
            if request_arguments == function_arguments: # if the argument lengths match between actually called and expected lengths
                return True, arbiter_method # returns a tuple, first being that it is a valid instruction and flag if its a arbiter method call

        return False, False #function does not exist or lengths do not match, returns False for validity and False for arbiter method call flag


    def _handle_received(self,received_data: tuple):
        valid, for_arbiter_execution = self._check_receive_validity(received_data) #get the validity and arbiter method flags

        if for_arbiter_execution: #if the arbiter method flag is on, execute the arbiter function
            self.arbiter_translation[received_data[1]](received_data[2])
        elif valid: #if its valid but not for arbiter, just return
            return received_data 
        else:
            self.send_to_arbiter(("ARBITER","FUNCTION_INVALID",(received_data))) #incase of invalid receive, let the arbiter know. sends back the whole 
            return None

    def __close_pipe(self): #closes the communication pipe - Arbiter is not gonna be happy with this call unless it was requested
        """
        if this function is triggered without Arbiter specifically asking, the Engine which called this will be terminated right away
        """
        self.send_to_arbiter(("ARBITER","PIPE_CLOSED",()))
        self.pipe.close()
        self.pipe_open = False
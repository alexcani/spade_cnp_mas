import random
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour, CyclicBehaviour, FSMBehaviour
from spade.message import Message
from spade.template import Template


class Initiator(Agent):
    possible_items = []
    shopping_list = []
    i = 0

    def setup(self):
        # Decide how many items we'll buy
        random.shuffle(self.possible_items)
        self.shopping_list = possible_items[0:self.i] # takes i random items
        print("[{}] I want to buy {}".format(self.jid, self.shopping_list))
        for item in self.shopping_list:
            behaviour = CnpBehaviour()
            behaviour.item = item
            template = Template()
            template.set_metadata("performative", )
            self.add_behaviour(CnpBehaviour)
        self.stop()


possible_items = ["banana", "limao", "goiaba", "abacate", "abacaxi", "uva", "tangerina", "laranja", "ameixa",
                  "amora"]

if __name__ == "__main__":
    a = Initiator("receiver@localhost", "123")
    a.possible_items = possible_items
    a.i = 5  # number of items
    a.start()
    while a.is_alive():
        continue

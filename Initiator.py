import random
from datetime import datetime, timedelta
from spade.agent import Agent
from spade.behaviour import TimeoutBehaviour, FSMBehaviour
from spade.behaviour import State
from spade.message import Message
from spade.template import Template

STATE_ONE = "START_CFP"
STATE_TWO = "WAITING_PROPOSALS"
STATE_FOUR = "TIMEOUT"
STATE_FIVE = "IDLE_POST_TIMEOUT"
STATE_SIX = "LATE_PROPOSAL"
STATE_SEVEN = "COMPLETED"


class Timeout(TimeoutBehaviour):
    def __init__(self, start, cnp_behaviour):
        super().__init__(start_at=start)
        self.cnp_behaviour = cnp_behaviour

    async def run(self):
        self.cnp_behaviour = True


class CnpInitiatorBehaviour(FSMBehaviour):
    timeout = False
    item = ""  # stores the item to buy
    proposal_list = []


# Broadcasts the Call for Proposal
class StateOne(State):
    def __init__(self, parent_behaviour):
        super()
        self.behaviour = parent_behaviour

    async def run(self):
        for seller in self.agent.list_of_sellers:
            msg = Message(to=seller)
            msg.set_metadata("performative", "cfp")
            msg.body = self.behaviour.item
            await self.send(msg)

        # Creates the timeout, which is a behaviour
        self.agent.add_behaviour(Timeout(start=(datetime.now() + timedelta(seconds=5)), cnp_behaviour=self.behaviour))
        self.set_next_state(STATE_TWO)


# Waits for proposals or timeout (ignores refusals)
class StateTwo(State):
    def __init__(self, parent_behaviour):
        super()
        self.behaviour = parent_behaviour

    async def run(self):
        if self.behaviour.timeout:
            self.set_next_state(STATE_FOUR)
            return

        msg = await self.receive()
        if msg and msg.metadata["performative"] == "propose":
            self.behaviour.proposal_list += [[float(msg.body), msg.sender]]  # price, seller name
        else:
            self.set_next_state(STATE_TWO)  # no message, refuse or any other unexpected message
        return


# Timeout happened, compare proposals, refuse all but the best one, which is accepted
class StateFour(State):
    def __init__(self, parent_behaviour):
        super()
        self.behaviour = parent_behaviour

    async def run(self):
        return


# Waits for confirmation from the seller, late proposals or a failure
class StateFive(State):
    def __init__(self, parent_behaviour):
        super()
        self.behaviour = parent_behaviour

    async def run(self):
        return


# Late proposal, reject it
class StateSix(State):
    def __init__(self, parent_behaviour):
        super()
        self.behaviour = parent_behaviour

    async def run(self):
        return


# Final state, transaction completed
class StateSeven(State):
    def __init__(self, parent_behaviour):
        super()
        self.behaviour = parent_behaviour

    async def run(self):
        return

class Initiator(Agent):
    list_of_sellers = [] # I couldn't make the notification system work, so every agent will hard-codedly know all other agents
    possible_items = []
    shopping_list = {}
    i = 0

    def setup(self):
        # Decide how many items we'll buy
        aux_shopping_list = [random.choice(possible_items) for _ in range(self.i)] # takes i random items
        for x in aux_shopping_list: # transforms into dict of unique keys with value representing amount
            if x in self.shopping_list:
                self.shopping_list[x] += 1
            else:
                self.shopping_list[x] = 1

        for item in self.shopping_list:
            behaviour = CnpInitiatorBehaviour()
            behaviour.item = item
            behaviour.add_state(name=STATE_ONE, state=StateOne(behaviour), initial=True)
            behaviour.add_state(name=STATE_TWO, state=StateTwo(behaviour))
            behaviour.add_state(name=STATE_FOUR, state=StateFour(behaviour))
            behaviour.add_state(name=STATE_FIVE, state=StateFive(behaviour))
            behaviour.add_state(name=STATE_SIX, state=StateSix(behaviour))
            behaviour.add_state(name=STATE_SEVEN, state=StateSeven(behaviour))
            behaviour.add_transition(STATE_ONE, STATE_TWO)
            behaviour.add_transition(STATE_TWO, STATE_TWO)
            behaviour.add_transition(STATE_TWO, STATE_FOUR)
            behaviour.add_transition(STATE_FOUR, STATE_FIVE)
            behaviour.add_transition(STATE_FIVE, STATE_ONE)
            behaviour.add_transition(STATE_FIVE, STATE_SIX)
            behaviour.add_transition(STATE_SIX, STATE_FIVE)
            behaviour.add_transition(STATE_FIVE, STATE_FIVE)
            behaviour.add_transition(STATE_FIVE, STATE_SEVEN)
            behaviour.add_transition(STATE_SEVEN, STATE_SEVEN)
            behaviour.add_transition(STATE_SEVEN, STATE_ONE)
            template = Template()
            template.set_metadata("item", item) # only receive messages regarding this item
        #     self.add_behaviour(behaviour, template)

possible_items = ["banana", "limao", "goiaba", "abacate", "abacaxi", "uva", "tangerina", "laranja", "ameixa",
                  "amora"]

if __name__ == "__main__":
    a = Initiator("receiver@localhost", "123")
    a.possible_items = possible_items
    a.i = 5  # number of items
    a.start()
    while a.is_alive():
        continue

import random
from datetime import datetime, timedelta
from spade.agent import Agent
from spade.behaviour import TimeoutBehaviour, FSMBehaviour, CyclicBehaviour
from spade.behaviour import State
from spade.message import Message
from spade.template import Template

STATE_ONE = "START_CFP"
STATE_TWO = "WAITING_PROPOSALS"
STATE_THREE = "TIMEOUT"
STATE_FOUR = "IDLE_POST_TIMEOUT"
STATE_FIVE = "COMPLETED"


class Timeout(TimeoutBehaviour):
    def __init__(self, start, cnp_behaviour):
        super().__init__(start_at=start)
        self.cnp_behaviour = cnp_behaviour

    async def run(self):
        self.cnp_behaviour.timeout = True
        self.kill()


class CnpInitiatorBehaviour(FSMBehaviour):
    async def on_start(self):
        self.proposal_list = []


# Broadcasts the Call for Proposal
class StateOne(State):
    def __init__(self, parent_behaviour):
        super()
        self.behaviour = parent_behaviour

    async def run(self):
        self.behaviour.timeout = False
        for seller in self.agent.list_of_sellers:
            msg = Message(to=seller)
            msg.set_metadata("performative", "cfp")
            msg.set_metadata("item", self.behaviour.item)
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
            self.set_next_state(STATE_THREE)
            return

        msg = await self.receive(timeout=0.2)
        if msg and msg.metadata["performative"] == "propose":
            self.behaviour.proposal_list += [[float(msg.body), str(msg.sender).split("/")[0]]]  # price, seller name

        self.set_next_state(STATE_TWO)  # no message, refuse or any other unexpected message are ignored


# Timeout happened, compare proposals, refuse all but the best one, which is accepted
class StateThree(State):
    def __init__(self, parent_behaviour):
        super()
        self.behaviour = parent_behaviour

    async def run(self):
        if len(self.behaviour.proposal_list) == 0:  # didn't receive any proposals =(
            print("[{}] Didn't receive any proposals for {}".format(self.agent.jid, self.behaviour.item))
            self.set_next_state(None)
            return

        self.behaviour.proposal_list.sort()
        for pair in self.behaviour.proposal_list[1:]:  # for everyone that lost
            msg = Message(to=pair[1])
            msg.set_metadata("performative", "reject-proposal")
            msg.body = self.behaviour.item
            await self.send(msg)

        winner_pair = self.behaviour.proposal_list[0]
        msg = Message(to=winner_pair[1])
        msg.set_metadata("performative", "accept-proposal")
        msg.set_metadata("item", self.behaviour.item)
        msg.body = self.behaviour.item
        await self.send(msg)
        self.set_next_state(STATE_FOUR)


# Waits for confirmation from the seller, late proposals or a failure
class StateFour(State):
    def __init__(self, parent_behaviour):
        super()
        self.behaviour = parent_behaviour

    async def run(self):
        msg = await self.receive(timeout=0.2)
        if msg:
            if msg.metadata["performative"] == "propose":  # late proposal
                print("[{}] received a late proposal".format(self.agent.jid))
                reply = Message(to=str(msg.sender).split("/")[0])
                reply.set_metadata("performative", "reject-proposal")
                reply.body = self.behaviour.item
                await self.send(reply)
                self.set_next_state(STATE_FOUR)
            elif msg.metadata["performative"] == "inform-done":  # transaction completed
                self.set_next_state(STATE_FIVE)
            elif msg.metadata["performative"] == "failure":  # an error happened with the seller
                self.set_next_state(STATE_ONE)  # restart
            else:
                self.set_next_state(STATE_FOUR)  # anything else
        else:
            self.set_next_state(STATE_FOUR)


# Final state, transaction completed
class StateFive(State):
    def __init__(self, parent_behaviour):
        super()
        self.behaviour = parent_behaviour

    async def run(self):
        print("[{}] Bought {} for {} from {}".format(self.agent.jid, self.behaviour.item,
                                                     self.behaviour.proposal_list[0][0],
                                                     self.behaviour.proposal_list[0][1]))
        self.behaviour.amount -= 1
        if self.behaviour.amount > 0:
            self.set_next_state(STATE_ONE)  # let's repeat
            return

        # else we end the FSM
        print("[{}] Finished buying all {}".format(self.agent.jid, self.behaviour.item))
        self.set_next_state(None)
        return


class Initiator(Agent):
    class WatchDogBehaviour(CyclicBehaviour):
        async def run(self):
            all_killed = True
            for bh in self.agent.behaviours:
                if bh == self:
                    continue

                all_killed = all_killed and bh.is_killed()
            if all_killed:
                self.agent.stop()

    def setup(self):
        self.shopping_list = {}

        # Decide how many items we'll buy
        aux_shopping_list = [random.choice(self.possible_items) for _ in range(self.i)]  # takes i random items
        for x in aux_shopping_list:  # transforms into dict of unique keys with value representing amount
            if x in self.shopping_list:
                self.shopping_list[x] += 1
            else:
                self.shopping_list[x] = 1

        print("[{}] I want to buy: {}".format(self.jid, self.shopping_list))

        for item in self.shopping_list:
            behaviour = CnpInitiatorBehaviour()
            behaviour.item = item
            behaviour.amount = self.shopping_list[item]
            behaviour.add_state(name=STATE_ONE, state=StateOne(behaviour), initial=True)
            behaviour.add_state(name=STATE_TWO, state=StateTwo(behaviour))
            behaviour.add_state(name=STATE_THREE, state=StateThree(behaviour))
            behaviour.add_state(name=STATE_FOUR, state=StateFour(behaviour))
            behaviour.add_state(name=STATE_FIVE, state=StateFive(behaviour))
            behaviour.add_transition(STATE_ONE, STATE_TWO)
            behaviour.add_transition(STATE_TWO, STATE_TWO)
            behaviour.add_transition(STATE_TWO, STATE_THREE)
            behaviour.add_transition(STATE_THREE, STATE_FOUR)
            behaviour.add_transition(STATE_FOUR, STATE_ONE)
            behaviour.add_transition(STATE_FOUR, STATE_FOUR)
            behaviour.add_transition(STATE_FOUR, STATE_FIVE)
            behaviour.add_transition(STATE_FIVE, STATE_ONE)
            template = Template()
            template.set_metadata("item", item)  # only receive messages regarding this item
            self.add_behaviour(behaviour, template)

        self.add_behaviour(self.WatchDogBehaviour())

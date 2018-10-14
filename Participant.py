import random
from datetime import datetime, timedelta
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, TimeoutBehaviour
from spade.message import Message
from spade.template import Template


class SendProposalBehaviour(TimeoutBehaviour):
    async def run(self):
        if self.agent.stock > 0:  # still have in stock
            proposal = Message(to=str(self.buyer))
            proposal.set_metadata("performative", "propose")
            proposal.set_metadata("item", self.agent.item)
            proposal.body = str(self.agent.price)
            await self.send(proposal)
            self.kill()


class ReceiveCfpBehaviour(CyclicBehaviour):
    async def run(self):
        msg = await self.receive()
        if msg:  # received a cfp
            if msg.metadata["item"] == self.agent.item:
                proposal_behaviour = SendProposalBehaviour(
                    start_at=(datetime.now() + timedelta(seconds=random.randint(0, 7))))
                proposal_behaviour.buyer = str(msg.sender).split("/")[0]
                self.agent.add_behaviour(proposal_behaviour)


class ProposalAcceptedBehaviour(CyclicBehaviour):
    async def run(self):
        msg = await self.receive()
        if msg:
            reply = Message(to=str(msg.sender).split("/")[0])
            reply.set_metadata("item", self.agent.item)
            if self.agent.stock > 0:  # still have in stock
                self.agent.stock -= 1
                reply.set_metadata("performative", "inform-done")
            else:
                reply.set_metadata("performative", "failure")  # we don't have in stock anymore
            await self.send(reply)


class Participant(Agent):
    def __init__(self, item, jid, passwd):
        super().__init__(jid, passwd)
        self.item = item
        # Initial stock
        self.stock = random.randint(1, 5)
        self.price = random.randint(5, 50)

    def setup(self):
        print("[{}] I will sell {} {} for {}".format(self.jid, self.stock, self.item, self.price))

        receive_cfp_behaviour = ReceiveCfpBehaviour()
        cfp_template = Template()
        cfp_template.set_metadata("performative", "cfp")
        self.add_behaviour(receive_cfp_behaviour, cfp_template)  # cfp behaviour only receives cfp messages

        proposal_accepted_behaviour = ProposalAcceptedBehaviour()
        accepted_template = Template()
        accepted_template.set_metadata("performative", "accept-proposal")
        accepted_template.set_metadata("item", self.item)
        self.add_behaviour(proposal_accepted_behaviour, accepted_template)

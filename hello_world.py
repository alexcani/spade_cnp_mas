import time
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from spade.template import Template


class SenderAgent(Agent):
    class InformBehaviour(OneShotBehaviour):
        async def run(self):
            print("setting available")
            self.presence.set_available()
            print("InformBehav running")
            msg = Message(to="receiver@localhost")  # Instantiate the message
            msg.set_metadata("performative", "cfp")  # Set the "inform" FIPA performative
            msg.body = "Hello World"  # Set the message content

            await self.send(msg)
            print("Message sent!")

            self.agent.stop()

    def setup(self):

        print("Sender Agent {} starting".format(self.jid))
        b = self.InformBehaviour()
        self.add_behaviour(b)

class ReceiverAgent(Agent):
    class Behav1(OneShotBehaviour):
        def on_available(self, jid, stanza):
            print("[{}] Agent {} is available.".format(self.agent.name, jid.split("@")[0]))

        def on_subscribed(self, jid):
            print("[{}] Agent {} has accepted the subscription.".format(self.agent.name, jid.split("@")[0]))
            print("[{}] Contacts List: {}".format(self.agent.name, self.agent.presence.get_contacts()))

        def on_subscribe(self, jid):
            print("[{}] Agent {} asked for subscription. Let's aprove it.".format(self.agent.name, jid.split("@")[0]))
            self.presence.approve(jid)

        async def run(self):
            print("Setting stuff")
            self.presence.on_subscribe = self.on_subscribe
            self.presence.on_subscribed = self.on_subscribed
            self.presence.on_available = self.on_available
            self.presence.set_available()

    class ReceiveBehaviour(OneShotBehaviour):
        async def run(self):
            print("RecvBeh is running")

            msg = await self.receive(timeout=10)
            if msg:
                print("Message received: {}".format(msg.body))
            else:
                print("Not received")

            print(self.presence.get_contacts())

            #self.agent.stop()

    def setup(self):
        print("Receiver agent started")
        self.add_behaviour(self.Behav1())
        b = self.ReceiveBehaviour()
        template = Template()
        template.set_metadata("performative", "cfp")
        self.add_behaviour(b, template)


if __name__ == "__main__":
    receiver = ReceiverAgent("receiver@localhost", "123")
    receiver.start(auto_register=True)
    time.sleep(2)
    sender = SenderAgent("sender@localhost", "123")
    sender.start(auto_register=True)

    while receiver.is_alive():
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break

    print("Agents finished")
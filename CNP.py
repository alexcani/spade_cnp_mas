import random
from Initiator import Initiator
from Participant import Participant

possible_items = ["banana", "limao", "goiaba", "abacate", "abacaxi", "uva", "tangerina", "laranja", "ameixa",
                  "amora"]

if __name__ == "__main__":
    n = 2  # number of initiators
    m = 10  # number of participants
    i = 4  # number of items each initiator will buy

    participants_names = []
    participants = []
    initiators = []

    # Create participants
    for j in range(m):
        name = "participant" + str(j) + "@localhost"
        participants_names.append(name)
        agent = Participant(random.choice(possible_items), name, "123")
        participants.append(agent)
        agent.start()

    # Create initiators
    for j in range(n):
        name = "initiator" + str(j) + "@localhost"
        agent = Initiator(name, "123")
        agent.possible_items = possible_items
        agent.list_of_sellers = participants_names
        agent.i = i
        initiators.append(agent)
        agent.start()

    while True:
        in_progress = False
        for initiator in initiators:
            in_progress = in_progress or initiator.is_alive()

        if not in_progress:
            for participant in participants:
                participant.stop()
            break

from direct.directnotify import DirectNotifyGlobal


class QuestManagerAI:
    notify = DirectNotifyGlobal.directNotify.newCategory('QuestManagerAI')

    def __init__(self, air):
        self.air = air

    def recoverItems(self, toon, suitsKilled, zoneId):
        return [], []  # TODO

    def toonKilledCogs(self, toon, suitsKilled, zoneId, activeToonList):
        pass  # TODO

    def requestInteract(self, avId, npc):
        npc.rejectAvatar(avId)  # TODO

    def hasTailorClothingTicket(self, toon, npc):
        return 0  # TODO

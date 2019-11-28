from direct.directnotify import DirectNotifyGlobal

from libtoontown import *
from otp.ai.AIZoneData import AIZoneDataStore
from otp.ai.TimeManagerAI import TimeManagerAI
from otp.distributed.OtpDoGlobals import *
from toontown.ai.HolidayManagerAI import HolidayManagerAI
from toontown.ai.NewsManagerAI import NewsManagerAI
from toontown.building.DistributedTrophyMgrAI import DistributedTrophyMgrAI
from toontown.catalog.CatalogManagerAI import CatalogManagerAI
from toontown.coghq.PromotionManagerAI import PromotionManagerAI
from toontown.distributed.ToontownDistrictAI import ToontownDistrictAI
from toontown.distributed.ToontownDistrictStatsAI import ToontownDistrictStatsAI
from toontown.distributed.ToontownInternalRepository import ToontownInternalRepository
from toontown.hood import ZoneUtil
from toontown.hood.BRHoodDataAI import BRHoodDataAI
from toontown.hood.DDHoodDataAI import DDHoodDataAI
from toontown.hood.DGHoodDataAI import DGHoodDataAI
from toontown.hood.DLHoodDataAI import DLHoodDataAI
from toontown.hood.MMHoodDataAI import MMHoodDataAI
from toontown.hood.TTHoodDataAI import TTHoodDataAI
from toontown.pets.PetManagerAI import PetManagerAI
from toontown.quest.QuestManagerAI import QuestManagerAI
from toontown.shtiker.CogPageManagerAI import CogPageManagerAI
from toontown.suit.SuitInvasionManagerAI import SuitInvasionManagerAI
from toontown.toon import NPCToons
from toontown.toonbase import ToontownGlobals
from toontown.uberdog.DistributedInGameNewsMgrAI import DistributedInGameNewsMgrAI


class ToontownAIRepository(ToontownInternalRepository):
    notify = DirectNotifyGlobal.directNotify.newCategory('ToontownAIRepository')

    def __init__(self, baseChannel, serverId, districtName):
        ToontownInternalRepository.__init__(self, baseChannel, serverId, dcSuffix='AI')
        self.districtName = districtName
        self.doLiveUpdates = config.GetBool('want-live-updates', True)
        self.wantCogdominiums = config.GetBool('want-cogdominiums', True)
        self.districtId = None
        self.district = None
        self.districtStats = None
        self.holidayManager = None
        self.zoneDataStore = None
        self.petMgr = None
        self.suitInvasionManager = None
        self.questManager = None
        self.promotionMgr = None
        self.cogPageManager = None
        self.timeManager = None
        self.newsManager = None
        self.inGameNewsMgr = None
        self.catalogManager = None
        self.trophyMgr = None
        self.zoneTable = {}
        self.dnaStoreMap = {}
        self.dnaDataMap = {}
        self.hoods = []
        self.buildingManagers = {}
        self.suitPlanners = {}

    def handleConnected(self):
        ToontownInternalRepository.handleConnected(self)

        # Generate our district...
        self.districtId = self.allocateChannel()
        self.district = ToontownDistrictAI(self)
        self.district.setName(self.districtName)
        self.district.generateWithRequiredAndId(self.districtId, self.getGameDoId(), OTP_ZONE_ID_DISTRICTS)

        # Claim ownership of that district...
        self.district.setAI(self.ourChannel)

        # Create our local objects.
        self.createLocals()

        # Create our global objects.
        self.createGlobals()

        # Create our zones.
        self.createZones()

        # Make our district available, and we're done.
        self.district.b_setAvailable(True)
        self.notify.info('Done.')

    def createLocals(self):
        """
        Creates "local" (non-distributed) objects.
        """

        # Create our holiday manager...
        self.holidayManager = HolidayManagerAI(self)

        # Create our zone data store...
        self.zoneDataStore = AIZoneDataStore()

        # Create our pet manager...
        self.petMgr = PetManagerAI(self)

        # Create our suit invasion manager...
        self.suitInvasionManager = SuitInvasionManagerAI(self)

        # Create our quest manager...
        self.questManager = QuestManagerAI(self)

        # Create our promotion manager...
        self.promotionMgr = PromotionManagerAI(self)

        # Create our Cog page manager...
        self.cogPageManager = CogPageManagerAI(self)

    def createGlobals(self):
        """
        Creates "global" (distributed) objects.
        """

        # Generate our district stats...
        self.districtStats = ToontownDistrictStatsAI(self)
        self.districtStats.settoontownDistrictId(self.districtId)
        self.districtStats.generateWithRequiredAndId(self.allocateChannel(), self.district.getDoId(),
                                                     OTP_ZONE_ID_DISTRICTS_STATS)

        # Generate our time manager...
        self.timeManager = TimeManagerAI(self)
        self.timeManager.generateWithRequired(OTP_ZONE_ID_MANAGEMENT)

        # Generate our news manager...
        self.newsManager = NewsManagerAI(self)
        self.newsManager.generateWithRequired(OTP_ZONE_ID_MANAGEMENT)

        # Generate our in-game news manager...
        self.inGameNewsMgr = DistributedInGameNewsMgrAI(self)
        self.inGameNewsMgr.generateWithRequired(OTP_ZONE_ID_MANAGEMENT)

        # Generate our catalog manager...
        self.catalogManager = CatalogManagerAI(self)
        self.catalogManager.generateWithRequired(OTP_ZONE_ID_MANAGEMENT)

        # Generate our trophy manager...
        self.trophyMgr = DistributedTrophyMgrAI(self)
        self.trophyMgr.generateWithRequired(OTP_ZONE_ID_MANAGEMENT)

    def generateHood(self, hoodConstructor, zoneId):
        # Bossbot HQ doesn't use DNA, so we skip over that.
        if zoneId != ToontownGlobals.BossbotHQ:
            self.dnaStoreMap[zoneId] = DNAStorage()
            self.dnaDataMap[zoneId] = loadDNAFileAI(self.dnaStoreMap[zoneId], self.genDNAFileName(zoneId))
            if zoneId in ToontownGlobals.HoodHierarchy:
                for streetId in ToontownGlobals.HoodHierarchy[zoneId]:
                    self.dnaStoreMap[streetId] = DNAStorage()
                    self.dnaDataMap[streetId] = loadDNAFileAI(self.dnaStoreMap[streetId], self.genDNAFileName(streetId))

        hood = hoodConstructor(self, zoneId)
        hood.startup()
        self.hoods.append(hood)

    def createZones(self):
        # First, generate our zone2NpcDict...
        NPCToons.generateZone2NpcDict()

        # Donald's Dock
        self.zoneTable[ToontownGlobals.DonaldsDock] = (
            (ToontownGlobals.DonaldsDock, 1, 0), (ToontownGlobals.BarnacleBoulevard, 1, 1),
            (ToontownGlobals.SeaweedStreet, 1, 1), (ToontownGlobals.LighthouseLane, 1, 1)
        )
        self.generateHood(DDHoodDataAI, ToontownGlobals.DonaldsDock)

        # Toontown Central
        self.zoneTable[ToontownGlobals.ToontownCentral] = (
            (ToontownGlobals.ToontownCentral, 1, 0), (ToontownGlobals.SillyStreet, 1, 1),
            (ToontownGlobals.LoopyLane, 1, 1), (ToontownGlobals.PunchlinePlace, 1, 1)
        )
        self.generateHood(TTHoodDataAI, ToontownGlobals.ToontownCentral)

        # The Brrrgh
        self.zoneTable[ToontownGlobals.TheBrrrgh] = (
            (ToontownGlobals.TheBrrrgh, 1, 0), (ToontownGlobals.WalrusWay, 1, 1),
            (ToontownGlobals.SleetStreet, 1, 1), (ToontownGlobals.PolarPlace, 1, 1)
        )
        self.generateHood(BRHoodDataAI, ToontownGlobals.TheBrrrgh)

        # Minnie's Melodyland
        self.zoneTable[ToontownGlobals.MinniesMelodyland] = (
            (ToontownGlobals.MinniesMelodyland, 1, 0), (ToontownGlobals.AltoAvenue, 1, 1),
            (ToontownGlobals.BaritoneBoulevard, 1, 1), (ToontownGlobals.TenorTerrace, 1, 1)
        )
        self.generateHood(MMHoodDataAI, ToontownGlobals.MinniesMelodyland)

        # Daisy Gardens
        self.zoneTable[ToontownGlobals.DaisyGardens] = (
            (ToontownGlobals.DaisyGardens, 1, 0), (ToontownGlobals.ElmStreet, 1, 1),
            (ToontownGlobals.MapleStreet, 1, 1), (ToontownGlobals.OakStreet, 1, 1)
        )
        self.generateHood(DGHoodDataAI, ToontownGlobals.DaisyGardens)

        # Donald's Dreamland
        self.zoneTable[ToontownGlobals.DonaldsDreamland] = (
            (ToontownGlobals.DonaldsDreamland, 1, 0), (ToontownGlobals.LullabyLane, 1, 1),
            (ToontownGlobals.PajamaPlace, 1, 1)
        )
        self.generateHood(DLHoodDataAI, ToontownGlobals.DonaldsDreamland)

        # Assign the initial suit buildings.
        for suitPlanner in self.suitPlanners.values():
            suitPlanner.assignInitialSuitBuildings()

    def genDNAFileName(self, zoneId):
        canonicalZoneId = ZoneUtil.getCanonicalZoneId(zoneId)
        canonicalHoodId = ZoneUtil.getCanonicalHoodId(canonicalZoneId)
        hood = ToontownGlobals.dnaMap[canonicalHoodId]
        if canonicalHoodId == canonicalZoneId:
            canonicalZoneId = 'sz'
            phase = ToontownGlobals.phaseMap[canonicalHoodId]
        else:
            phase = ToontownGlobals.streetPhaseMap[canonicalHoodId]

        return 'phase_%s/dna/%s_%s.dna' % (phase, hood, canonicalZoneId)

    def loadDNAFileAI(self, dnaStore, dnaFileName):
        return loadDNAFileAI(dnaStore, dnaFileName)

    def findFishingPonds(self, dnaData, zoneId, area):
        return [], []  # TODO

    def findPartyHats(self, dnaData, zoneId):
        return []  # TODO

    def getTrackClsends(self):
        return False

    def getAvatarExitEvent(self, avId):
        return 'distObjDelete-%d' % avId

    def getAvatarDisconnectReason(self, avId):
        return self.timeManager.avId2disconnectcode.get(avId, ToontownGlobals.DisconnectUnknown)

    def getZoneDataStore(self):
        return self.zoneDataStore

    def incrementPopulation(self):
        self.districtStats.b_setAvatarCount(self.districtStats.getAvatarCount() + 1)

    def decrementPopulation(self):
        self.districtStats.b_setAvatarCount(self.districtStats.getAvatarCount() - 1)

    def sendQueryToonMaxHp(self, avId, callback):
        pass  # TODO?

from helper import *
from db import saveProps, saveSpreads, saveSummary, getDBSize
import hive
import psutil


class DatabaseManager:
    def __init__(self):
        self.current = "starting"  # current process

    def saveIndefinitely(self, Session, interval=5):
        """
        Takes a sessionmaker object, create session, and save every interval seconds
        """
        session = Session()

        start_time = nowD()
        # create propagator
        beehive = hive.Hive(minnum=2)
        while True:
            # create props
            self.current = "propagating"
            props, globals()["latest_raw_batch"] = beehive.pgator.propagate(
                beehive.idynamics
            )
            self.current = "saving props"
            saveProps(props, session)

            # scan one cycle
            self.current = "solving"
            spreads = beehive.scanFull(props)

            self.current = "saving spreads"
            saveSpreads(spreads, session)
            # summarize one cycle
            self.current = "saving summary"
            saveSummary(spreads, session)

            globals()["latest_solved_batch"] = globals()["latest_raw_batch"]
            # print stats
            mem_usage = round(psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2)
            print(
                colorHigh(
                    f"* ip: {getIP()} - usage: {mem_usage} MB - uptime: {strfdelta(nowD() - start_time)} - db size: {getDBSize(session,'samwise')} *\n"
                )
            )
            self.current = "waiting"
            timer(interval)
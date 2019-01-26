import datetime
from croniter import croniter

import core4.queue.main
import core4.queue.query
import core4.util
import core4.util.node
from core4.queue.daemon import CoreDaemon
import core4.const
from core4.service.introspect.command import ENQUEUE
import core4.service.introspect



class CoreScheduler(CoreDaemon):
    """
    The scheduler enqueues jobs available in core4 projects installed on the
    same node. The scheduler queries the ``schedule`` property of all known
    :class:`.CoreJob` implementations.

    The timing information in the ``schedule`` attribute uses cron format (see
    https://en.wikipedia.org/wiki/Cron). core4 uses :mod:`croniter` to parse
    and to calculate schedules.

    Note that the scheduler keeps track of the last scheduling time and catches
    up with all missed enqueuing, e.g. if the scheduler was down.
    """
    kind = "scheduler"
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.schedule = None
        self.next = None
        self.previous = None
        self.job = None

    def startup(self):
        """
        Implements the **startup** phase of the scheduler. The method is based
        on :class:`.CoreDaemon` implementation and additionally spawns
        :meth:`.collect_job`.
        """
        super().startup()
        self.collect_job()

    def collect_job(self):
        """
        Collects meta data about all known jobs and inserts this information
        into ``sys.job``.

        The following attributes are saved:

        * ``_ie`` - the :meth:`.qual_name`
        * ``author`` - of the job
        * ``schedule`` - in cron format
        * ``hidden`` - job property
        * ``doc`` - the doc string
        * ``tag`` - list
        * ``valid`` - indicates if the job is valid
        * ``exception`` - exception raised with ``traceback``
        * ``python`` - interpreter binary path
        * ``created_at`` - the date/time when the job has be initially released
        * ``updated_at`` - the date/time when the job has been released lately.
          The attribute is ``None`` if the job has not been found during last
          update.
        """
        intro = core4.service.introspect.CoreIntrospector()
        self.config.sys.job.update_many(
            filter={},
            update={
                "$set": {
                    "updated_at": None
                },
            }
        )
        now = core4.util.node.mongo_now()
        self.job = {}
        self.logger.info("start registration")
        for project, data in intro.list_project():
            if data:
                self.logger.info("collecting classes from [%s]", project)
                for job in data["job"]:
                    job_project = job["name"].split(".")[0]
                    if ((job_project != core4.const.CORE4)
                            or (job_project == project)):
                        self.logger.debug("registering job [%s]", job["name"])
                        update = job.copy()
                        del update["name"]
                        update["updated_at"] = now
                        self.config.sys.job.update_one(
                            filter={
                                "_id": job["name"]
                            },
                            update={
                                "$set": update,
                                "$setOnInsert": {
                                    "created_at": now
                                },
                            },
                            upsert=True
                        )
                        if job["valid"] and job["schedule"]:
                            doc = self.config.sys.job.find_one(
                                {"_id": job["name"]},
                                projection=["created_at"])

                            self.job[job["name"]] = {
                                "updated_at": now,
                                "schedule": job["schedule"],
                                "created_at": doc["created_at"]
                            }
                            self.logger.info("schedule [%s] at [%s]",
                                             job["name"], job["schedule"])
        self.logger.info("registered jobs")

    def loop(self):
        """
        This is the main processing phase of the scheduler.
        """
        self.wait_time = 1
        self.previous = None
        doc = self.config.sys.job.find_one({"_id": "__schedule__"})
        if doc:
            self.previous = doc.get("schedule_at", None)
        super().loop()

    def run_step(self):
        """
        The scheduler consists of one step. This time interval of this step
        can be configured by core4 config setting ``scheduler.interval`` and
        defaults to 1 second.
        :return:
        """
        jobs = self.get_next(self.previous, self.at)
        n = 0
        for job, schedule in jobs:
            self.logger.info("enqueue [%s] at [%s]", job, schedule)
            try:
                self.queue.enqueue(name=job)._id
            except ImportError:
                core4.service.introspect.exec_project(
                    job, ENQUEUE, qual_name=job)
            except core4.error.CoreJobExists:
                self.logger.error("job [%s] exists", job)
            except Exception:
                self.logger.critical("failed to enqueue [%s]", job,
                                     exc_info=True)
            else:
                n += 1
        self.previous = self.at
        self.config.sys.job.update_one(
            {
                "_id": "__schedule__"
            },
            update={
                "$set": {
                    "schedule_at": self.previous
                }
            },
            upsert=True
        )
        return n

    def get_next(self, start, end):
        """
        Returns the jobs to be enqueued between ``start`` and ``end``
        date/time.

        :param start: :class:`datetime.datetime` when last scheduling has been
                      executed. Pass ``None`` for the very first schedule.
        :param end: :class:`datetime.datetime` of now
        :return: list of tuples with ``(name, schedule)`` of the job
        """
        ret = []
        if start is None:
            start = end
        for job_name, doc in self.job.items():
            cron = croniter(doc["schedule"], start)
            next_time = cron.get_next(datetime.datetime)
            if next_time <= end:
                ret.append((job_name, doc["schedule"]))
        return ret


if __name__ == '__main__':
    import core4.logger.mixin
    core4.logger.mixin.logon()
    scheduler = CoreScheduler()
    scheduler.start()

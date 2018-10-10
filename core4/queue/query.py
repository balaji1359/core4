"""
This module delivers various MongoDB support methods retrieving information
about collection ``sys.queue``. The main class :class:`QueryMixin` is to be
mixed into a class based on :class:`core4.base.main.CoreBase`.
"""

from collections import OrderedDict

import datetime
import pandas as pd

import core4.util


class QueryMixin:

    def get_worker(self):
        """
        Retrieves information about all workers alive. This includes

        * ``_id`` - the identifier of the worker
        * ``loop`` - the date/time when the working entered looping in UTC
        * ``loop_time`` - the timedelta of the worker looping
        * ``heartbeat`` - the timedelta of the last heartbeat

        .. note:: Workers are considered alive, if their heartbeat is not older
                  then current date/time (all in UTC) plus the alive timeout.
                  The alive timeout can be configured by config section
                  ``alive.timeout``.

        :return: :class:`pandas.DataFrame``
        """
        timeout = self.config.worker.alive_timeout
        cur = self.config.sys.worker.aggregate([
            {
                "$match": {
                    "heartbeat": {"$exists": True},
                    "phase.shutdown": None,
                    "$or": [
                        {"heartbeat": None},
                        {
                            "heartbeat": {
                                "$gte": core4.util.mongo_now() -
                                        datetime.timedelta(seconds=timeout)
                            }
                        }
                    ]
                },
            },
            {
                "$project": {
                    "heartbeat": 1,
                    "loop": "$phase.loop"
                }
            },
            {"$sort": {"_id": 1}}
        ])
        data = []
        for doc in cur:
            if doc["heartbeat"]:
                doc["heartbeat"] = (core4.util.mongo_now() -
                                    doc["heartbeat"].replace(microsecond=0))
            if doc["loop"]:
                doc["loop_time"] = (core4.util.mongo_now() -
                                    doc["loop"].replace(microsecond=0))
            else:
                doc["Loop_time"] = None
            data.append(doc)
        df = pd.DataFrame(data)
        if df.empty:
            return df
        return df[["_id", "loop", "loop_time", "heartbeat"]]

    def get_queue_state(self):
        """
        Retrieves aggregated information about ``sys.queue`` state. This is

        * ``n`` - the number of jobs in the given state
        * ``state`` - job state
        * ``flags`` - job flags ``zombie``, ``wall``, ``removed`` and
          ``killed``
        * ``name`` - job :meth:`.qual_name``

        :return: :class:`pandas.DataFrame``
        """
        sort_dict = OrderedDict()
        sort_dict['state'] = 1
        sort_dict['name'] = 1
        sort_dict['_id'] = -1
        cur = self.config.sys.queue.aggregate([
            {
                '$match': {
                    'state': {'$ne': 'complete'}
                },
            },
            {
                '$project': {
                    "name": 1,
                    "state": 1,
                    "zombie": {"$ne": ["$zombie_at", None]},
                    "wall": {"$ne": ["$wall_at", None]},
                    "removed": {"$ne": ["$removed_at", None]},
                    "killed": {"$ne": ["$killed_at", None]}
                },
            },
            {
                '$group': {
                    '_id': {
                        'name': '$name',
                        'state': '$state',
                        'zombie': '$zombie',
                        'wall': '$wall',
                        'removed': '$removed',
                        'killed': '$killed',
                    },
                    'n': {'$sum': 1}
                }
            },
            {
                '$project': {
                    "name": "$_id.name",
                    "state": "$_id.state",
                    "zombie": "$_id.zombie",
                    "wall": "$_id.wall",
                    "removed": "$_id.removed",
                    "killed": "$_id.killed",
                    "n": "$n",
                    "_id": 0,
                },
            },
            {
                "$sort": sort_dict
            }
        ])
        data = list(cur)
        df = pd.DataFrame(data)
        if df.empty:
            return df
        df["flags"] = df.apply(lambda r: "".join(
            [k[0].upper() if r[k] else "." for k in
             ["zombie", "wall", "removed", "killed"]]), axis=1)
        return df[["n", "state", "flags", "name"]]

    def get_job_listing(self, **kwargs):
        """
        Returns the job listing filtered by {{kwargs}}. This is

        * ``_id`` (ObjectId)
        * ``attempts_left`` (int)
        * ``attempts`` (int)
        * ``started_at`` (datetime)
        * ``enqueued`` (dict)
        * ``priorirty`` (int)
        * ``args`` (dict)
        * ``killed_at`` (datetime)
        * ``removed_at`` (datetime)
        * ``zombie_at`` (datetime)
        * ``wall_at`` (datetime)
        * ``name`` (str)
        * ``state`` (str)
        * ``locked`` (dict)

        :param kwargs: query filter
        :return: dict generator
        """
        return self.config.sys.queue.find(
            filter=kwargs,
            projection={
                '_id': 1,
                'attempts_left': 1,
                'attempts': 1,
                'started_at': 1,
                'enqueued': 1,
                'priority': 1,
                'args': 1,
                'killed_at': 1,
                'removed_at': 1,
                'zombie_at': 1,
                'wall_at': 1,
                'name': 1,
                'state': 1,
                'locked': 1},
            sort=[('_id', 1)])

    def get_job_stdout(self, _id):
        """
        Returns the job STDOUT filtered.

        .. note:: The STDOUT of jobs have a time-to-live and is purged after
                  7 days. You can configure this TTL with config setting
                  ``worker.stdout.ttl``.

        :param _id: :class:`bson.object.ObjectId`
        :return: str
        """
        doc = self.config.sys.stdout.find_one({"_id": _id})
        if doc:
            return doc["stdout"]
        return None

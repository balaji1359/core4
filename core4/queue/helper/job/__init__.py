#
# Copyright 2018 Plan.Net Business Intelligence GmbH & Co. KG
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
This module delivers the :class:`.MailerJob` to send emails using the local
MTA.
"""

import tornado.template

from core4.queue.helper.job.example import DummyJob
from core4.queue.job import CoreJob

# todo: requires implementation
# todo: consider user language CORE4-115

class MailerJob(CoreJob):
    """
    This job takes the template location (absolute path), recipients, subject
    line and any additional arguments and sends an email.
    """
    author = 'mra'

    def execute(self, template, recipients, subject, *args, **kwargs):
        msg = []
        if not isinstance(recipients, list):
            recipients = [recipients]
        msg.append("FROM: ?")
        msg.append("TO: %s" % (", ".join(recipients)))
        msg.append("SUBJECT: %s" % (subject))
        msg.append("")
        t = tornado.template.Template(template)
        kwargs["recipients"] = ", ".join(recipients)
        kwargs["subject"] = subject
        for k, v in kwargs.items():
            msg.append("variable %s = %s" % (k, v))
        msg.append(t.generate(**kwargs).decode("utf-8"))
        print("\n".join(msg))
        self.logger.debug("send mail:\n%s", "\n".join(msg))

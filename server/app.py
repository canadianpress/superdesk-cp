#!/usr/bin/env python
# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import os
import settings

from superdesk.factory import get_app as superdesk_app

SUPERDESK_PATH = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
)


def get_app(config=None):
    """App factory.

    :param config: configuration that can override config from `settings.py`
    :return: a new SuperdeskEve app instance
    """
    if config is None:
        config = {}

    config["APP_ABSPATH"] = os.path.abspath(os.path.dirname(__file__))

    for key in dir(settings):
        if key.isupper():
            config.setdefault(key, getattr(settings, key))

    app = superdesk_app(config)

    app.config["BABEL_TRANSLATION_DIRECTORIES"] = (
        app.config.get("BABEL_TRANSLATION_DIRECTORIES")
        + ";"
        + os.path.join(SUPERDESK_PATH, "server/translations")
    )

    return app


if __name__ == "__main__":
    debug = True
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "5000"))
    app = get_app()
    app.run(host=host, port=port, debug=debug, use_reloader=debug)

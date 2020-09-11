# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:         sfp_bitcoinwhoswho
# Purpose:      Bitcoin Who's Who database lookup module
#
# Author:      Leo Trubach <leotrubach@gmail.com>
#
# Created:     2020-09-09
# Copyright:   (c) Steve Micallef
# Licence:     GPL
# -------------------------------------------------------------------------------

import json
import urllib.parse

from spiderfoot import SpiderFootEvent, SpiderFootPlugin


class sfp_bitcoinwhoswho(SpiderFootPlugin):
    meta = {
        'name': "Bitcoin Who's Who",
        'summary': "Check for malicious Bitcoin address against Bitcoin Who's Who database",
        'flags': ["apikey"],
        'useCases': ["Passive"],
        'categories': ["Reputation Systems"],
        'dataSource': {
            'website': "https://bitcoinwhoswho.com/",
            'model': "FREE_AUTH_LIMITED",
            'references': [
                "https://bitcoinwhoswho.com/api"
            ],
            'apiKeyInstructions': [
                "Visit https://bitcoinwhoswho.com/signup",
                "Register a free account",
                "Verify your email and sign into your account",
                "Visit https://bitcoinwhoswho.com/api/register and request an API Key",
                "Wait for a few days, you'll receive it to your email"
            ],
            'favIcon': "https://bitcoinwhoswho.com/public/images/ico/favicon.ico",
            'logo': "https://bitcoinwhoswho.com/public/images/logo2.png",
            'description': (
                "Bitcoin Who's Who is dedicated to profiling the extraordinary members of the bitcoin "
                "ecosystem.Our goal is to help you verify a bitcoin address owner and avoid a bitcoin "
                "scam or fraud."
            ),
        }
    }

    opts = {
        'api_key': '',
    }

    optdescs = {
        "api_key": "Bitcoin Who's Who API Key."
    }

    results = None

    errorState = False

    def setup(self, sfc, userOpts=None):
        self.sf = sfc
        self.results = self.tempStorage()

        if userOpts:
            self.opts.update(userOpts)

    def watchedEvents(self):
        return ["BITCOIN_ADDRESS"]

    def producedEvents(self):
        return ["MALICIOUS_BITCOIN_ADDRESS"]

    def query(self, qry):
        qs = urllib.parse.urlencode({"address": qry})
        res = self.sf.fetchUrl(
            f"https://bitcoinwhoswho.com/api/scam/{self.opts['api_key']}?{qs}",
            timeout=self.opts["_fetchtimeout"],
            useragent="SpiderFoot",
        )

        if res["content"] is None:
            self.sf.info(f"No {self.meta['name']} info found for {qry}")
            return None

        try:
            info = json.loads(res["content"])
        except Exception as e:
            self.sf.error(
                f"Error processing JSON response from {self.meta['name']}: {e}", False
            )
            return None

        return info

    def emit(self, etype, data, pevent, notify=True):
        evt = SpiderFootEvent(etype, data, self.__name__, pevent)
        if notify:
            self.notifyListeners(evt)
        return evt

    def generate_events(self, data, pevent):
        if not isinstance(data, dict):
            return

        scams = data.get("scams", [])
        if scams:
            self.emit("MALICIOUS_BITCOIN_ADDRESS", f"Bitcoin Who's Who[{pevent.data}]")

    def handleEvent(self, event):
        if self.errorState:
            return None

        self.sf.debug(f"Received event, {event.eventType}, from {event.module}")

        if self.opts["api_key"] == "":
            self.sf.error(f"You enabled {self.__class__.__name__} but did not set an API key!", False)
            self.errorState = True
            return None

        if event.data in self.results:
            self.sf.debug(f"Skipping {event.data}, already checked.")
            return None
        self.results[event.data] = True

        if event.eventType == "BITCOIN_ADDRESS":
            data = self.query(event.data)
            self.generate_events(data, event)

            self.emit("RAW_RIR_DATA", json.dumps(data), event)

# End of sfp_bitcoinwhoswho class
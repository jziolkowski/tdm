import logging

from util import Message, TasmotaDevice, TasmotaEnvironment


def native_discovery():
    pass


def lwt_discovery_stage1():
    pass


def lwt_discovery_stage2(env: TasmotaEnvironment, message: Message):
    if full_topic := message.dict().get("FullTopic"):
        # the device replies with its FullTopic
        # here the Topic is extracted using the returned FullTopic, identifying the device
        match = message.match_fulltopic(full_topic)
        if match:
            _match_topic = match.groupdict()["topic"]
            # got a match, we query the device's MAC address in case it's a known device
            # that had its topic changed

            d = env.find_device(topic=_match_topic)
            if d:
                d.update_property("FullTopic", full_topic)
            else:
                logging.info(
                    "DISCOVERY(LEGACY): Discovered topic=%s with fulltopic=%s",
                    match["topic"],
                    full_topic,
                )
                return TasmotaDevice(_match_topic, full_topic)

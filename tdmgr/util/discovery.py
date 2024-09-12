import logging

from tdmgr.util import Message, TasmotaDevice, TasmotaEnvironment


def native_discovery():
    pass


def lwt_discovery_stage1():
    pass


def lwt_discovery_stage2(env: TasmotaEnvironment, message: Message):
    if full_topic := message.dict().get("FullTopic"):
        # the device replies with its FullTopic
        # here the Topic is extracted using the returned FullTopic, identifying the device
        if match := message.match_fulltopic(full_topic):
            _match_topic = match.groupdict()["topic"]

            if d := env.find_device(topic=_match_topic):
                d.update_property("FullTopic", full_topic)

            else:
                logging.info(
                    "DISCOVERY(LEGACY): Discovered topic=%s with fulltopic=%s",
                    match["topic"],
                    full_topic,
                )
                return TasmotaDevice(_match_topic, full_topic)

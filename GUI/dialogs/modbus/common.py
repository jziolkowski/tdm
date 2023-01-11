import re

RX_INT_OR_HEX = re.compile(r"(\d+)$|(0x[0-9a-f]+$)", re.IGNORECASE)


commands = {
    3: "3: Read holding registers ",
    4: "4: Read input registers",
}

datatypes = {
    0: 'float',
    1: '2-byte signed',
    2: '4-byte signed',
    3: '2-byte unsigned',
    4: '4-byte unsigned',
    # 5: 'unused',
    6: '4-byte signed with swapped words',
    # 7: 'unused',
    8: '4-byte unsigned with swapped words',
}

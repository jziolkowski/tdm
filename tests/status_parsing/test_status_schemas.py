import logging
import os

import pytest
from pydantic import ValidationError

from tdmgr.schemas.status import STATUS_SCHEMA_MAP

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jsonfiles')


def get_status_jsonfiles():
    _files = []
    for _, dirs, _ in os.walk(PATH):
        for dir in dirs:
            for _, _, files in os.walk(os.path.join(PATH, dir)):
                for file in files:
                    _files.append(os.path.join(PATH, dir, file))
    return _files


@pytest.mark.parametrize("jsonfile", get_status_jsonfiles())
def test_status_parsing(caplog, jsonfile):
    status_type = jsonfile.split(os.path.sep)[-1].split('.')[0]
    schema = STATUS_SCHEMA_MAP.get(status_type)

    with open(jsonfile, "r") as payload:
        try:
            with caplog.at_level(logging.DEBUG):
                schema.model_validate_json(payload.read())
                assert "Schema has extra fields" not in caplog.text
        except ValidationError as e:
            pytest.fail(str(e))

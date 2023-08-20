# -*- coding: utf-8 -*-

import re
from typing import List, Dict, Optional

from pydantic import BaseModel, Field

from ._compat import model_rebuild


TYPE_ERROR_RE = re.compile(r'.*# E: (?P<expected>.*)')
REVEAL_TYPE_RE = re.compile(r'\s+reveal_type\(.*\)\s+# T: (?P<expected>.*)')


class Expected(BaseModel):
    message: str
    accessed: bool = False


class PyrightFile(BaseModel):
    errors: Dict[int, Expected]
    informations: Dict[int, Expected]

    @classmethod
    def parse(cls, content: str) -> 'PyrightFile':
        errors: Dict[int, Expected] = {}
        informations: Dict[int, Expected] = {}

        for index, line in enumerate(content.splitlines(), start=1):
            reveal = REVEAL_TYPE_RE.match(line)
            if reveal is not None:
                informations[index] = Expected(message=reveal.group('expected'))
                continue

            error = TYPE_ERROR_RE.match(line)
            if error is not None:
                errors[index] = Expected(message=error.group('expected'))
                continue

        return cls(errors=errors, informations=informations)

    def get_error(self, line: int) -> str:
        error = self.errors[line]
        error.accessed = True
        return error.message

    def get_information(self, line: int) -> str:
        information = self.informations[line]
        information.accessed = True
        return information.message


class PyrightResult(BaseModel):
    time: int
    version: str
    summary: 'PyrightSummary'
    diagnostics: List['PyrightDiagnostic'] = Field(alias='generalDiagnostics')


class PyrightSummary(BaseModel):
    files: int = Field(alias='filesAnalyzed')
    errors: int = Field(alias='errorCount')
    warnings: int = Field(alias='warningCount')
    informations: int = Field(alias='informationCount')
    time_in_seconds: float = Field(alias='timeInSec')


class PyrightDiagnostic(BaseModel):
    file: str
    message: str
    severity: str  # TODO: enum
    range: 'PyrightRange'
    rule: Optional[str] = None


class PyrightRange(BaseModel):
    start: 'PyrightRangeValue'
    end: 'PyrightRangeValue'


class PyrightRangeValue(BaseModel):
    line: int
    character: int


model_rebuild(PyrightRange)
model_rebuild(PyrightResult)
model_rebuild(PyrightDiagnostic)

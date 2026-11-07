"""Adapters own references, descriptions, revalidation, stages and far-side evidence.

execute() is called once, only AFTER submitting is durable. An exception after that
boundary is unknown unless the adapter can prove nothing left. repair() must never
call execute() or a submission transport. See README for the full contract.
"""
from typing import Protocol


class Adapter(Protocol):
    app: str

    def prepare(self, verb, arguments): ...
    def revalidate(self, operation): ...
    def evidence(self, operation_id): ...
    def execute(self, operation, stage): ...
    def repair(self, operation, which): ...


class Uncertain(Exception):
    pass


class NothingLeft(Exception):
    pass

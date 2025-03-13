# Standard Library Imports
from abc import ABC, abstractclassmethod
from datetime import datetime
from json import dump
from os.path import isdir, join
from os import makedirs
# Package Imports
from ..config import Config
from .transaction import Transaction


class InvalidStatusUpdate(RuntimeError):
    """``RuntimeError` that's thrown when a :class:`.PipelineStatusTransaction` is invalid."""


class PipelineStatusTransaction(Transaction, ABC):
    """
    
    Attributes:
        key (str): The :attr:`.Job.id` of the job pipeline being tracked prepended with :attr:`._pipeline_status_prefix`.
        request_payload (dict): Dictionary containing the following items:
            - `job_id` (int): :attr:`.Job.id` of the job pipeline being tracked.
            - `status` (str): String describing this pipeline status update.
            - `when` (str): ISO formatted string of the ``datetime`` this status update took place.
    """

    _pipeline_status_prefix = "__PIPELINE_STATUS_"

    _pipeline_count_key = "__PIPELINES_COUNT"

    _pipeline_total_key = "__PIPELINES_TOTAL_DURATION"

    _dump_dir = ".strmbrkr_pipelines"

    _dump_name = "{0}.json"

    @classmethod
    def _makeSurePathExists(cls):
        """Verify that the path holding the pipeline files exists, or if it doesn't, create it."""
        if not isdir(cls._dump_dir):
            makedirs(cls._dump_dir, exist_ok=True)

    def __init__(self, job_id: int):
        _key = f"{self._pipeline_status_prefix}{job_id}"
        _request_payload = {
            "job_id": job_id,
            "status": self.status(),
            "when": datetime.utcnow().isoformat()
        }
        super(PipelineStatusTransaction, self).__init__(_key, _request_payload)

    @abstractclassmethod
    def status(self) -> str:
        """Return the string describing this pipeline status update."""
        raise NotImplementedError()

    @property
    def job_id(self) -> int:
        """int: :attr:`.Job.id` of the job pipeline being tracked."""
        return self.request_payload["job_id"]

    @property
    def when(self) -> str:
        """str: ISO formatted string of the ``datetime`` this status update took place."""
        return self.request_payload["when"]


class PipelineQueuedTransaction(PipelineStatusTransaction):
    """Concrete :class:`.PipelineStatusTransaction` processed when a job has been sent by :meth:`.QueueManager.queueJobs()` to the :meth:`.WorkerManager.brokerLoop()`."""

    @classmethod
    def status(self) -> str:
        return "QUEUED"

    def transact(self, key_value_store: dict):
        existing_status_report = key_value_store.get(self.key)
        if existing_status_report is not None:
            self.error = InvalidStatusUpdate(f"Queuing {self.request_payload} on pre-existing pipeline: {existing_status_report}")
            return

        key_value_store[self.key] = {
            "job_id": self.job_id,
            self.status(): self.when
        }
        self.response_payload = key_value_store[self.key]


class PipelineDelegatedTransaction(PipelineStatusTransaction):
    """Concrete :class:`.PipelineStatusTransaction` processed when a job has been sent by :meth:`.WorkerManager.brokerLoop()` to the :meth:`.Worker.workLoop()`."""

    @classmethod
    def status(self) -> str:
        return "DELEGATED"

    def transact(self, key_value_store: dict):
        existing_status_report = key_value_store.get(self.key)
        if existing_status_report is None:
            self.error = InvalidStatusUpdate(f"Delegation can't occur before queuing: {self.request_payload}")
            return

        if existing_status_report.get(self.status()):
            self.error = InvalidStatusUpdate(f"Delegating {self.request_payload} on pre-existing pipeline: {existing_status_report}")
            return
        
        key_value_store[self.key].update({self.status(): self.when})
        self.response_payload = key_value_store[self.key]


class PipelineProcessedTransaction(PipelineStatusTransaction):
    """Concrete :class:`.PipelineStatusTransaction` processed when a job has been sent by :meth:`.WorkerManager.brokerLoop()` to the :meth:`.QueueManager._handleProcessedJobs()` thread."""

    @classmethod
    def status(self) -> str:
        return "PROCESSED"

    def transact(self, key_value_store: dict):
        existing_status_report = key_value_store.get(self.key)
        if existing_status_report is None or PipelineDelegatedTransaction.status() not in existing_status_report:
            self.error = InvalidStatusUpdate(f"Processing can't occur before delegation: {self.request_payload}")
            return

        if existing_status_report.get(self.status()):
            self.error = InvalidStatusUpdate(f"Processing {self.request_payload} on pre-existing pipeline: {existing_status_report}")
            return
        
        key_value_store[self.key].update({self.status(): self.when})
        self.response_payload = key_value_store[self.key]


class PipelineReturnedTransaction(PipelineStatusTransaction):
    """Concrete :class:`.PipelineStatusTransaction` processed when a job has been handled by the :meth:`.QueueManager._handleProcessedJobs()` thread."""

    @classmethod
    def status(self) -> str:
        return "RETURNED"

    def transact(self, key_value_store: dict):
        existing_status_report = key_value_store.get(self.key)
        if existing_status_report is None or PipelineProcessedTransaction.status() not in existing_status_report:
            self.error = InvalidStatusUpdate(f"Returning can't occur before processing: {self.request_payload}")
            return
        
        if existing_status_report.get(self.status()):
            self.error = InvalidStatusUpdate(f"Returning {self.request_payload} on pre-existing pipeline: {existing_status_report}")
            return

        key_value_store[self.key].update({self.status(): self.when})
        self.response_payload = key_value_store[self.key]

        returned = datetime.fromisoformat(self.response_payload[self.status()])
        queued = datetime.fromisoformat(self.response_payload[PipelineQueuedTransaction.status()])
        pipeline_duration = (returned - queued).total_seconds()
        total_count = key_value_store.get(self._pipeline_count_key, 0) + 1
        total_duration = key_value_store.get(self._pipeline_total_key, 0) + pipeline_duration
        pipeline_avg = total_duration / total_count

        key_value_store[self._pipeline_count_key] = total_count
        key_value_store[self._pipeline_total_key] = total_duration

        self.response_payload.update({
            self._pipeline_count_key: total_count,
            self._pipeline_total_key: total_duration,
            "pipeline_duration": pipeline_duration,
            "pipeline_avg": pipeline_avg
        })

        if Config.key_value_store.dump_pipeline_status_reports:
            self._makeSurePathExists()
            with open(join(self._dump_dir, self._dump_name.format(self.key)), 'w') as dump_file:
                dump(self.response_payload, dump_file, indent=2)
        del key_value_store[self.key]     

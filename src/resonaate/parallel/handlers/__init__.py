"""Describes the classes for handling parallel job execution logic.

When creating a new portion of parallel code, users must implement a custom :class:`.CallbackRegistration`
and a custom :class:`.JobHandler` class. These define the parallel job callbacks (pre and post job execution)
and the :class:.`Job` generation method, respectively.

Implementors should design the callback class to reference an object via the
:attr:`~.CallbackRegistration.registrant` attribute which is defined on instantiation of the class.
The callback is not typically instantiated directly by users, but done implicitly via
:meth:`~.JobHandler.registerCallback()`. The :attr:`~.CallbackRegistration.registrant` can be any
other object, but is commonly an :class:`~.agent_base.Agent` or whatever class contains the job handler.

Any keyword arguments required by :meth:`~.JobHandler.executeJobs()`, :meth:`~.JobHandler.generateJobs()`,
or :meth:`~.CallbackRegistration.jobCreateCallback()` are passed in :meth:`~.JobHandler.executeJobs()`
by the users, and should be retrieved from a generic `**kwargs` argument to retain the common interface.

Examples:
    Here is a demonstration of how to implement a new :class:`.CallbackRegistration` class.

    .. sourcecode:: python

        from resonaate.parallel.job import CallbackRegistration, Job

        class NewCallback(CallbackRegistration):
            def jobCreateCallback(self, **kwargs):
                return Job(...)

            def jobCompleteCallback(self, job):
                self.registrant.state = job.retval

    Here is a demonstration of how to implement a new :class:`.JobHandler` class using the
    previously defined `NewCallback` class.

    .. sourcecode:: python

        from resonaate.parallel.handlers.job_handler import JobHandler

        class NewJobHandler(JobHandler):

            callback_class = NewCallback

            def generateJobs(self, **kwargs):
                jobs = []
                for registration in self.callback_registry:
                    job = registration.jobCreateCallback()
                    self.job_id_registration_dict[job.id] = registration
                    jobs.append(job)
                return jobs

    Users can now create a parallel processing job simply, and execute the jobs.

    .. sourcecode:: python

        # Create handler and register callback
        handler = NewJobHandler()
        handler.registerCallback(registrant)  # or `self` if implemented in a class

        # Run multiple jobs in parallel
        handler.executeJobs()
"""

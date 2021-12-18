#	calendargen - Photo calendar generator
#	Copyright (C) 2021-2021 Johannes Bauer
#
#	This file is part of calendargen.
#
#	calendargen is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	calendargen is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with calendargen; if not, write to the Free Software
#	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#	Johannes Bauer <JohannesBauer@gmx.de>

import sys
import enum
import multiprocessing
import threading
import traceback
import logging
import collections
import uuid

_log = logging.getLogger("JobServer" if (__spec__ is None) else __spec__.name)

class JobServerExecutionFailed(Exception): pass

JobException = collections.namedtuple("JobException", [ "exception", "stacktrace" ])

class JobState(enum.IntEnum):
	Waiting = 0
	Running = 1
	Blocked = 2
	Finished = 3
	Failed = 4

class JobGraph():
	def __init__(self, filename):
		self._f = open(filename, "w")
		self._seen_nodes = set()
		self._seen_edges = set()
		self._show_uuid = True
		print("digraph jobs {", file = self._f)

	def _dot_str(self, job, raw = False):
		if self._show_uuid:
			if raw:
				return "\"%s\"" % (job.jid)
			else:
				return "\"%s\" [label=\"%s\"]" % (job.jid, str(job.jid)[:8])
		else:
			if (job.info is None) or raw:
				return "\"%s\"" % (job.jid)
			else:
				return "\"%s\" [label=\"%s\"]" % (job.jid, str(job.info))

	def _add_node(self, job):
		if job.jid in self._seen_nodes:
			self._seen_nodes.add(job.jid)
			print("	%s" % (self._dot_str(job)), file = self._f)

	def _add_edge(self, src, dest):
		edge = (src.jid, dest.jid)
		if edge not in self._seen_edges:
			self._seen_edges.add(edge)
			print("	%s -> %s" % (self._dot_str(src, raw = True), self._dot_str(dest, raw = True)), file = self._f)

	def _add_dependency(self, job, depends_on):
		self._add_node(job)
		self._add_node(depends_on)
		self._add_edge(depends_on, job)

	def add_job(self, job):
		print("	%s" % (self._dot_str(job)), file = self._f)
		for notify in job.notify_after:
			self._add_dependency(notify, job)
		for notify in job.cleanup_after:
			self._add_dependency(notify, job)

	def __del__(self):
		print("}", file = self._f)
		self._f.close()
		self._f = None

class Job():
	def __init__(self, callback, args = (), info = None):
		self._callback = callback
		self._args = args
		self._info = info
		self._depends_on = [ ]			# Prerequisites
		self._notify_after = [ ]		# Notify these on success
		self._cleanup_after = [ ]		# Notify these on finish, regardless if successful or not
		self._jobserver = None
		self._state = JobState.Waiting
		self._jid = uuid.uuid4()

	@property
	def jid(self):
		return self._jid

	@property
	def info(self):
		return self._info

	@property
	def jobserver(self):
		return self._jobserver

	@jobserver.setter
	def jobserver(self, value):
		assert(self._jobserver is None)
		self._jobserver = value

	@property
	def notify_after(self):
		return iter(self._notify_after)

	@property
	def cleanup_after(self):
		return iter(self._cleanup_after)

	def recurse_untracked(self):
		if self.jobserver is None:
			yield self
		for parent in self._depends_on:
			if parent.jobserver is None:
				yield from parent.recurse_untracked()
		for child in self._notify_after:
			if child.jobserver is None:
				yield from child.recurse_untracked()
		for child in self._cleanup_after:
			if child.jobserver is None:
				yield from child.recurse_untracked()

	@property
	def state(self):
		return self._state

	def depends_on(self, *parent_jobs):
		if len(parent_jobs) == 0:
			return self
		assert(self._state in [ JobState.Waiting, JobState.Blocked ])
		self._depends_on += parent_jobs
		for parent_job in parent_jobs:
			parent_job._notify_after.append(self)
		self._state = JobState.Blocked
		return self

	def depends_unconditionally_on(self, *parent_jobs):
		if len(parent_jobs) == 0:
			return self
		assert(self._state in [ JobState.Waiting, JobState.Blocked ])
		self._state = JobState.Blocked
		self._depends_on += parent_jobs
		for parent_job in parent_jobs:
			parent_job._cleanup_after.append(self)
		return self

	def finally_do(self, *finalization_jobs):
		for finalization_job in finalization_jobs:
			finalization_job.depends_unconditionally_on(self)
		return self

	def then(self, *chained_jobs):
		for chained_job in chained_jobs:
			chained_job.depends_on(self)
		return self

	def dump(self):
		print("%s: depends on %s, notify %s, finally %s" % (str(self), str(self._depends_on), str(self._notify_after), str(self._cleanup_after)))
		for notify in self._notify_after:
			notify.dump()
		for notify in self._cleanup_after:
			notify.dump()

	def notify_parent_finished(self, parent_job, result):
		# One dependency less.
		self._depends_on.remove(parent_job)
		if (len(self._depends_on) == 0) and (self.state == JobState.Blocked):
			# Ready to be scheduled!
			self._state = JobState.Waiting

	def notify_parent_failed(self, parent_job, exception):
		# If the dependency failed, this job implicitly also failed. Notify all
		# children they won't be able to run.
		self._state = JobState.Failed
		for child in self._notify_after:
			child.notify_parent_failed(self, exception)
		for child in self._cleanup_after:
			child.notify_parent_finished(self, exception)

	def run(self):
		assert(self._state in [ JobState.Waiting ])
		self._state = JobState.Running
		try:
			result = self._callback(*self._args)
			self._state = JobState.Finished
			for child in self._notify_after:
				child.notify_parent_finished(self, result)
			for child in self._cleanup_after:
				child.notify_parent_finished(self, result)
			self.jobserver.notify_success(self)
		except Exception as exception:
			self._state = JobState.Failed
			(exc_type, exc_value, exc_traceback) = sys.exc_info()
			stacktrace = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
			job_exception = JobException(exception = exception, stacktrace = stacktrace)
			for child in self._notify_after:
				child.notify_parent_failed(self, job_exception)
			for child in self._cleanup_after:
				child.notify_parent_finished(self, result)
			self.jobserver.notify_failure(self, job_exception)

	def _custom_str(self, suffix = ""):
		if self.info is None:
			return "Job<%s %s%s>" % (self.state.name, self._jid, suffix)
		else:
			return "Job<%s %s \"%s\"%s>" % (self.state.name, self._jid, str(self.info), suffix)

	@property
	def short_str(self):
		return self._custom_str()

	def __repr__(self):
		if len(self._depends_on) == 0:
			deps = ""
		else:
			deps = " depends on %s" % (" + ".join(dependency.short_str for dependency in self._depends_on))
		return self._custom_str(suffix = deps)

class JobServer():
	def __init__(self, concurrent_job_count = multiprocessing.cpu_count(), exception_on_failed = True, write_graph_file = None):
		self._concurrent_job_count = concurrent_job_count
		self._exception_on_failed = exception_on_failed
		if write_graph_file is not None:
			self._graph_file = JobGraph(write_graph_file)
		else:
			self._graph_file = None
		self._lock = threading.Lock()
		self._cond = threading.Condition(self._lock)
		self._stats = {
			"successful":	0,
			"failed":		0,
		}
		self._running_jobs = [ ]
		self._waiting_jobs = [ ]

	def __enter__(self):
		return self

	def __exit__(self, *args):
		self.await_completion()

	def notify_success(self, job):
		_log.debug("%s successfully terminated.", str(job))
		with self._lock:
			self._stats["successful"] += 1
		self.start_jobs()

	def notify_failure(self, job, exception):
		_log.error("%s failed with %s: %s", str(job), exception.exception.__class__.__name__, str(exception.exception))
		if _log.isEnabledFor(logging.DEBUG):
			_log.error(exception.stacktrace)
		with self._lock:
			self._stats["failed"] += 1
		self.start_jobs()

	def await_completion(self):
		with self._lock:
			while (len(self._waiting_jobs) > 0) or (len(self._running_jobs) > 0):
				try:
					self._cond.wait()
				except KeyboardInterrupt:
					_log.error("Interrupted: %d running jobs, %d waiting", len(self._running_jobs), len(self._waiting_jobs))
					for waiting_job in self._waiting_jobs:
						_log.debug("Waiting when keyboard interrupt hit: %s", str(waiting_job))
					for running_job in self._running_jobs:
						_log.debug("Running when keyboard interrupt hit: %s", str(running_job))
					raise
		if (self._stats["failed"] > 0) and self._exception_on_failed:
			raise JobServerExecutionFailed("There were %d job(s) that failed (%d completed successfully)." % (self._stats["failed"], self._stats["successful"]))

	def __start_job(self, job):
		_log.debug("Starting job [currently %d running %d waiting]: %s", len(self._running_jobs), len(self._waiting_jobs), str(job))
		def run_job_thread():
			job.run()
			with self._lock:
				self._running_jobs.remove(job)
				self._cond.notify_all()
			self.start_jobs()

		self._running_jobs.append(job)
		job.thread = threading.Thread(target = run_job_thread)
		job.thread.start()

	def start_jobs(self):
		with self._lock:
			runnable_jobs = [ ]
			blocked_jobs = [ ]
			for waiting_job in self._waiting_jobs:
				if waiting_job.state == JobState.Waiting:
					runnable_jobs.append(waiting_job)
				elif waiting_job.state == JobState.Blocked:
					blocked_jobs.append(waiting_job)
				else:
					_log.debug("Removed job: %s", waiting_job)
			_log.debug("At start %d jobs runnable, %d blocked", len(runnable_jobs), len(blocked_jobs))
			self._waiting_jobs = blocked_jobs
			while (len(runnable_jobs) > 0) and (len(self._running_jobs) < self._concurrent_job_count):
				next_job = runnable_jobs.pop(0)
				self.__start_job(next_job)
			self._waiting_jobs += runnable_jobs

	def add_jobs(self, *jobs):
		added_jobs = False
		for primary_job in jobs:
			for job in primary_job.recurse_untracked():
				assert(isinstance(job, Job))
				if self._graph_file is not None:
					self._graph_file.add_job(job)
				# Not added yet, claim job
				job.jobserver = self
				added_jobs = True
				with self._lock:
					self._waiting_jobs.append(job)
		if added_jobs:
			self.start_jobs()

	def wait(self, *jobs):
		remaining = list(jobs)
		with self._lock:
			while True:
				still_remaining = [ ]
				for job in remaining:
					if (job in self._running_jobs) or (job in self._waiting_jobs):
						still_remaining.append(job)
				remaining = still_remaining
				if len(remaining) == 0:
					break
				self._cond.wait()

if __name__ == "__main__":
	import time
	logging.basicConfig(format = "{name:>30s} [{levelname:.1s}]: {message}", style = "{", level = logging.DEBUG)

	with JobServer(concurrent_job_count = 3) as js:
		def my_long_job(name):
			print("RUN", name)
			time.sleep(1)

		def my_broken_job(name):
			print("RUN BROKEN", name)
			time.sleep(1)
			this_is_a_deliberate_name_error

		def finalize_job():
			print("FINALIZE RUNNING")

		demo = "finally"

		if demo == "1parent-2child":
			# Run two that depend on one
			job = Job(my_long_job, ("parent", )).then(Job(my_long_job, ("child1", )), Job(my_long_job, ("child2", )))
			job.dump()
			js.add_jobs(job)

		if demo == "3parent-1child":
			# Run one that depends on three
			jobs = [ Job(my_long_job, ("parent1", )), Job(my_long_job, ("parent2", )), Job(my_long_job, ("parent3", )) ]
			Job(my_long_job, ("child ", )).depends_on(*jobs)
			for job in jobs:
				job.dump()
			js.add_jobs(*jobs)

		if demo == "finally":
			# Run one that depends on three
			jobs = [ Job(my_long_job, ("parent1", ), info = "parent1"), Job(my_long_job, ("parent2", ), info = "parent2"), Job(my_broken_job, ("parent3", ), info = "parent3") ]
			Job(my_long_job, ("child ", ), info = "child").depends_on(*jobs).finally_do(Job(finalize_job, info = "finalize"))

			for job in jobs:
				job.dump()
			js.add_jobs(*jobs)

	if demo == "await":
		js = JobServer(concurrent_job_count = 2)
		job = Job(my_long_job, ("will never run", ))
		js.wait(job)

		job1 = Job(my_long_job, ("wll run1", ))
		job2 = Job(my_long_job, ("wll run2", ))
		js.add_jobs(job1, job2)
		js.wait(job1, job2)

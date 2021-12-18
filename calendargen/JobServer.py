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
import multiprocessing
import threading
import traceback
import logging
import collections

_log = logging.getLogger("JobServer" if (__spec__ is None) else __spec__.name)

class JobServerExecutionFailed(Exception): pass

JobException = collections.namedtuple("JobException", [ "exception", "stacktrace" ])

class Job():
	def __init__(self, callback, args = (), info = None):
		self._callback = callback
		self._args = args
		self._info = info
		self._depends_on = [ ]			# Prerequisites
		self._notify_after = [ ]		# Notify these on success
		self._cleanup_after = [ ]		# Notify these on finish, regardless if successful or not
		self._jobserver = None
		self._thread = None

	@property
	def info(self):
		return self._info

	@property
	def jobserver(self):
		return self._jobserver

	@jobserver.setter
	def jobserver(self, value):
		assert((self._jobserver is None) or (self._jobserver is value))
		self._jobserver = value
		for child in self._notify_after:
			child.jobserver = value
		for child in self._cleanup_after:
			child.jobserver = value

	@property
	def thread(self):
		return self._thread

	@thread.setter
	def thread(self, value):
		self._thread = value

	def depends_on(self, *parent_jobs):
		self._depends_on += parent_jobs
		for parent_job in parent_jobs:
			parent_job._notify_after.append(self)
		return self

	def depends_unconditionally_on(self, *parent_jobs):
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

	def cleanup(self, *chained_jobs):
		for chained_job in chained_jobs:
			chained_job.depends_on(self)
		return self

	def dump(self):
		print("%s: depends on %s, notify %s, finally %s" % (str(self), str(self._depends_on), str(self._notify_after), str(self._cleanup_after)))
		for notify in self._notify_after:
			notify.dump()
		for notify in self._cleanup_after:
			notify.dump()

	def _dot_str(self, raw = False):
		if (self.info is None) or raw:
			return "\"job-%d\"" % (id(self))
		else:
			return "\"job-%d\" [label=\"%s\"]" % (id(self), str(self.info))

	def dump_graph_dependency(self, depends_on, f):
		print("	%s" % (self._dot_str()), file = f)
		print("	%s" % (depends_on._dot_str()), file = f)
		print("	%s -> %s" % (self._dot_str(raw = True), depends_on._dot_str(raw = True)), file = f)

	def dump_graph(self, f):
		print("	%s" % (self._dot_str()), file = f)
		for notify in self._notify_after:
			self.dump_graph_dependency(notify, f)
		for notify in self._cleanup_after:
			self.dump_graph_dependency(notify, f)

	def notify_parent_finished(self, parent_job, result):
		# One dependency less.
		self._depends_on.remove(parent_job)
		if len(self._depends_on) == 0:
			# We're now runnable, enter into jobserver.
			self.jobserver.add_jobs(self)

	def notify_parent_failed(self, parent_job, exception):
		# If the dependency failed, this job implicitly also failed. Notify all
		# children they won't be able to run.
		for child in self._notify_after:
			child.notify_parent_failed(self, exception)
		for child in self._cleanup_after:
			child.notify_parent_finished(self, exception)

	def run(self):
		try:
			result = self._callback(*self._args)
			self.jobserver.notify_success()
			for child in self._notify_after:
				child.notify_parent_finished(self, result)
			for child in self._cleanup_after:
				child.notify_parent_finished(self, result)
		except Exception as exception:
			(exc_type, exc_value, exc_traceback) = sys.exc_info()
			stacktrace = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
			job_exception = JobException(exception = exception, stacktrace = stacktrace)
			self.jobserver.notify_failure(self, job_exception)
			for child in self._notify_after:
				child.notify_parent_failed(self, job_exception)
			for child in self._cleanup_after:
				child.notify_parent_finished(self, result)

	def __repr__(self):
		if self.info is None:
			return "Job<%d>" % (id(self))
		else:
			return "Job<%d \"%s\">" % (id(self), str(self.info))

class JobServer():
	def __init__(self, concurrent_job_count = multiprocessing.cpu_count(), exception_on_failed = True, write_graph_file = None):
		self._concurrent_job_count = concurrent_job_count
		self._exception_on_failed = exception_on_failed
		self._write_graph_file = write_graph_file
		self._lock = threading.Lock()
		self._cond = threading.Condition(self._lock)
		self._stats = {
			"successful":	0,
			"failed":		0,
		}
		self._running_jobs = [ ]
		self._waiting_jobs = [ ]
		self._init_graph_file()

	def _init_graph_file(self):
		if self._write_graph_file is not None:
			with open(self._write_graph_file, "w") as f:
				print("digraph jobs {", file = f)

	def __enter__(self):
		return self

	def __exit__(self, *args):
		self.await_completion()

	def notify_success(self):
		with self._lock:
			self._stats["successful"] += 1

	def notify_failure(self, job, exception):
		_log.error("%s failed with %s: %s", str(job), exception.exception.__class__.__name__, str(exception.exception))
		if _log.isEnabledFor(logging.DEBUG):
			_log.error(exception.stacktrace)
		with self._lock:
			self._stats["failed"] += 1

	def await_completion(self):
		with self._lock:
			while (len(self._waiting_jobs) > 0) or (len(self._running_jobs) > 0):
				try:
					self._cond.wait()
				except KeyboardInterrupt:
					_log.error("Interrupted: %d running jobs, %d waiting", len(self._running_jobs), len(self._waiting_jobs))
					for running_job in self._running_jobs:
						_log.debug("Running when keyboard interrupt hit: %s", str(running_job))
					raise
		if (self._stats["failed"] > 0) and self._exception_on_failed:
			raise JobServerExecutionFailed("There were %d job(s) that failed (%d completed successfully)." % (self._stats["failed"], self._stats["successful"]))
		if self._write_graph_file is not None:
			with open(self._write_graph_file, "a") as f:
				print("}", file = f)

	def __start_job(self, job):
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
			while (len(self._waiting_jobs) > 0) and (len(self._running_jobs) < self._concurrent_job_count):
				next_job = self._waiting_jobs.pop(0)
				self.__start_job(next_job)

	def add_jobs(self, *jobs):
		for job in jobs:
			if self._write_graph_file is not None:
				with self._lock, open(self._write_graph_file, "a") as f:
					job.dump_graph(f)
			assert(isinstance(job, Job))
			job.jobserver = self
			with self._lock:
				self._waiting_jobs.append(job)
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

	with JobServer(concurrent_job_count = 3) as js:
		def my_long_job(name):
			print("RUN", name)
			time.sleep(1)

		def my_broken_job(name):
			print("RUN BROKEN", name)
			time.sleep(1)
			asdjoias

		def finalize_job():
			print("FINALIZE")

		demo = "whoami"

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

		if demo == "whoami":
			def whoami_job():
				print("In job:", js.current_job())

			print("In main:", js.current_job())
			job = Job(whoami_job)
			print("Expect:", job)
			js.add_jobs(job)

	if demo == "await":
		js = JobServer(concurrent_job_count = 2)
		job = Job(my_long_job, ("will never run", ))
		js.wait(job)

		job1 = Job(my_long_job, ("wll run1", ))
		job2 = Job(my_long_job, ("wll run2", ))
		js.add_jobs(job1, job2)
		js.wait(job1, job2)

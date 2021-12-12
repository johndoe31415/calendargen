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

import multiprocessing
import threading
import traceback

class JobServerExecutionFailed(Exception): pass

class Job():
	def __init__(self, callback, args = (), name = None):
		self._callback = callback
		self._args = args
		self._name = name
		self._depends_on = [ ]			# Prerequisites
		self._notify_after = [ ]		# Notify these on success
		self._cleanup_after = [ ]		# Notify these on finish, regardless if successful or not
		self._jobserver = None

	@property
	def name(self):
		return self._name

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

	def dump_graph(self):
		if self.name is None:
			print("\"job-%d\" # graphviz" % (id(self)))
		else:
			print("\"job-%d\" [label=\"%s\"] # graphviz" % (id(self), self.name))
		for notify in self._notify_after:
			print("\"job-%d\" -> \"job-%d\" # graphviz" % (id(self), id(notify)))
		for notify in self._cleanup_after:
			print("\"job-%d\" -> \"job-%d\" # graphviz" % (id(self), id(notify)))

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
			self.jobserver.notify_failure(self, exception)
			for child in self._notify_after:
				child.notify_parent_failed(self, exception)
			for child in self._cleanup_after:
				child.notify_parent_finished(self, result)

	def __repr__(self):
		if self.name is None:
			return "Job<%d>" % (id(self))
		else:
			return "Job<%d \"%s\">" % (id(self), self.name)

class JobServer():
	def __init__(self, concurrent_job_count = multiprocessing.cpu_count(), verbose = 0, exception_on_failed = True):
		self._concurrent_job_count = concurrent_job_count
		self._verbose = verbose
		self._exception_on_failed = exception_on_failed
		self._lock = threading.Lock()
		self._cond = threading.Condition(self._lock)
		self._stats = {
			"successful":	0,
			"failed":		0,
		}
		self._running_count = 0
		self._waiting_jobs = [ ]

	def __enter__(self):
		return self

	def __exit__(self, *args):
		self.await_completion()

	def notify_success(self):
		with self._lock:
			self._stats["successful"] += 1

	def notify_failure(self, job, exception):
		if self._verbose >= 1:
			print("%s failed with exception: %s" % (str(job), str(exception)))
		if self._verbose >= 2:
			pass
			# TODO FIXME
			#print(traceback.print_exception(exception))
		with self._lock:
			self._stats["failed"] += 1

	def await_completion(self):
		with self._lock:
			while (len(self._waiting_jobs) > 0) or (self._running_count > 0):
				self._cond.wait()
		if (self._stats["failed"] > 0) and self._exception_on_failed:
			raise JobServerExecutionFailed("There were %d job(s) that failed (%d completed successfully)." % (self._stats["failed"], self._stats["successful"]))

	def __start_job(self, job):
		def run_job_thread():
			job.run()
			with self._lock:
				self._running_count -= 1
				self._cond.notify()
			self.start_jobs()

		self._running_count += 1
		threading.Thread(target = run_job_thread).start()

	def start_jobs(self):
		with self._lock:
			while (len(self._waiting_jobs) > 0) and (self._running_count < self._concurrent_job_count):
				next_job = self._waiting_jobs.pop(0)
				self.__start_job(next_job)

	def add_jobs(self, *jobs):
		for job in jobs:
			if self._verbose >= 3:
				job.dump_graph()
			assert(isinstance(job, Job))
			job.jobserver = self
			with self._lock:
				self._waiting_jobs.append(job)
		self.start_jobs()

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
			jobs = [ Job(my_long_job, ("parent1", ), name = "parent1"), Job(my_long_job, ("parent2", ), name = "parent2"), Job(my_broken_job, ("parent3", ), name = "parent3") ]
			Job(my_long_job, ("child ", ), name = "child").depends_on(*jobs).finally_do(Job(finalize_job, name = "finalize"))

			for job in jobs:
				job.dump()
			js.add_jobs(*jobs)

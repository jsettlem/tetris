from hyperopt import fmin, tpe, hp, Trials
from hyperopt.mongoexp import MongoTrials


def wrapper(params):
	import subprocess
	hole, jag = params['hole'], params['jag']
	proc = subprocess.Popen(
		f"D:\\Downloads\\pypy3-v6.0.0-win32\\pypy3-v6.0.0-win32\\pypy3.exe "
		f"V:\\Dropbox\\PyCharm\\tetris\\tetris-test\\tetris.py {hole} {jag}",
		stdout=subprocess.PIPE)
	proc_out, proc_err = proc.communicate()
	last_line = str(proc_out).split("\\n")[-2]
	return -float(last_line)


def objective(params):
	import random
	import time
	from hyperopt import STATUS_OK
	x, y = params['x'], params['y']
	time.sleep(8)
	return {
		"loss": ((x + y) - 1) ** 2 + 3 + random.random() / 2,
		"status": STATUS_OK,
		'eval_time': time.time()
	}


trials = MongoTrials('mongo://localhost:1234/testdb_2/jobs')

best = fmin(fn=wrapper,
            space={"hole": hp.uniform('hole', 0.9, 2), "jag": hp.uniform('jag', 0, 0.05)},
            algo=tpe.suggest,
            max_evals=1000,
            trials=trials)

print(best)

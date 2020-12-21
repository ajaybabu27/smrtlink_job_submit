import re
import subprocess
import os
import sys
#import urllib2
import mysql.connector

def get_jobs(pp_path,assembly_runid_file):
	pattern = re.compile("^[A-Za-z]{2}[0-9]{5}.[0-9][A-Za-z]")
	table=open(assembly_runid_file,'r')
	table.readline()
	to_submit = set()
	
	for line in table:
		line = line.rstrip()
		name,jobId = line.split('\t')
		
		if not pattern.match(name) is None:

			to_submit.add((jobId, name))	
			
	path = os.path.expanduser('~') + '/.my.cnf'
	with open(path) as cnf_file:
		for line in cnf_file:
			if line.startswith('user='):
				user = line.rstrip()[5:]
			if line.startswith('password='):
				pw = line.rstrip()[9:]
			if line.startswith('host='):
				host = line.rstrip()[5:]
			if line.startswith('database='):
				database = line.rstrip()[9:]

	db = mysql.connector.connect(host=host,user=user,passwd=pw,db=database)
	cur=db.cursor()	
	rejected = []
	for i in to_submit:
					 
		smrtjob, sample = i		
		smrtjob = smrtjob.zfill(6)

		try:
					
			cur.execute("""select STOCK_ID from tExtracts where EXTRACT_ID='""" + sample + "'")
			stock_id=str(cur.fetchone()[0])
			cur.execute("select ISOLATE_ID from tStocks where STOCK_ID='" + stock_id + "'")
			isolate_id = str(cur.fetchone()[0])
			cur.execute("select ORGANISM_ID from tIsolates where ISOLATE_ID='" + isolate_id + "'")
			organism_id =  str(cur.fetchone()[0])
			cur.execute("select abbreviated_name from tOrganisms where ORGANISM_ID='" + organism_id + "'")
			species =  str(cur.fetchone()[0])
			if species == 'MRSA' or species == 'MSSA':
				species = 'S_aureus'
			#cur.execute("Delete from tAssemblies where extract_ID='" + sample + "'")
		except IndexError:
			rejected.append(i[1])
			with open('data/rejected', 'a') as rejects:
				rejects.write(smrtjob + ' : ' + sample + ' not in pathogendb.\n')
			continue
		sample = sample.replace('.', '_')

		#os.system('rm -r /sc/arion/projects/InfectiousDisease/post-assembly-output/' + sample + '_' + smrtjob)
		#os.system('rm -r /sc/arion/projects/InfectiousDisease/post-assembly-output/' + sample + '*')
		#os.system('rm -r /sc/arion/projects/InfectiousDisease/igb/*' + sample + '*')
		
		if os.path.isdir('/sc/arion/projects/InfectiousDisease/post-assembly-output/' + sample + '_' + smrtjob):
			rejected.append(i[1])
			with open('data/rejected', 'a') as rejects:
				rejects.write(smrtjob + ' : ' + sample + ' already in post-assembly-output.\n')
			continue
        
		with open('bsubs/' + i[0] + '.bsub', 'w') as bsub:
			bsub.write('#!/bin/bash\n'
			'#BSUB -J ' + smrtjob + '\n'
			'#BSUB -P acc_InfectiousDisease\n'
			'#BSUB -q private\n'
			'#BSUB -n 12\n'
			'#BSUB -R span[hosts=1]\n'
			'#BSUB -R rusage[mem=4000]\n'
			'#BSUB -W 12:00\n'
			'#BSUB -o %J.stdout\n'
			'#BSUB -eo %J.stderr\n'
			'#BSUB -L /bin/bash\n'
			'cd ' + pp_path + '\n'
			'./post-assemble-pathogen  OUT=/sc/arion/projects/InfectiousDisease/post-assembly-output/' + sample + '_' + smrtjob +
			' SMRT_JOB_ID=' + smrtjob + ' STRAIN_NAME=' + sample + ' SPECIES=' + species + ' LSF_DISABLED=1 CLUSTER=BASH SEQ_PLATFORM=SEQ igb_to_pathogendb\n')

		subprocess.Popen('bsub < ' + 'bsubs/' + i[0] + '.bsub', shell=True).wait()

	cur.close()
	#db.commit()
	db.close()

get_jobs(os.path.abspath(sys.argv[1]),os.path.abspath(sys.argv[2]))

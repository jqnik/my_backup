# Missing: explanatory messages for error scenarios:
# -> cannot run backup (drive not mounted, other)
# -> cannot run and we are really late (overdue)
# -> mount failed
# -> rsync failed
# -> rsync success

# Missing FUNCTIONS
# email
# syslog / wall
# error (using email and syslog)
# warning (dto.)
# info (dto.)
# rsync

import sys
import os
import ConfigParser
import datetime
import subprocess

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

# create pid_file


# Compare if last backup is past longer than intervall
# if yes try to backup, but run checks first
#	has the drive been mounted automatically already?
#		if yes, umount, mount again under uuid, success?
#	is drive there?
#	do all directories (src/dest) exist	?
#	if any errors exit and advance due time just 2 days (or configurable)
#
# if no, see if we are 3 days close to it
# if 3 days close to it, give heads up via mail
# if not 3 days close to it, just echo that no backup is needed until...

# delete pidfile
RSYNC_OPTIONS_DEFAULT = "--stats --del -rt"
RSYNC_LOGDIR_DEFAULT = "/var/log/my_backup.log"
DEFAULT_CFG_FILE = "~/.my_backup.cfg"

CHECK_DEV_MOUNTED = "./check_dev_mounted.sh"
UMOUNT_DEV = "./umount_dev.sh"
MOUNT_DEV = "./mount_dev.sh"

config_file = None
srcpaths = None
dst_uuid = None
dst_mount = None
dst_path = None
rsync_options = None
rsync_logdir = None
config = None
pidfile = None

DEBUG = 0
TESTRUN = 0
PROFILE = 0

__version__ = 0.1
__date__ = '2013-02-18'
__updated__ = '2013-02-18'

class MyError(Exception):
	def __init__(self, value):
		global config, pidfile
		self.value = value
		next_date_to_act = Date + datetime.timedelta(days=2)
		config.set('General', 'next_action', next_date_to_act)
		os.unlink(pidfile)

	def __str__(self):
		return repr(self.value)


def check_srcs_present(srcpaths):
	for path in srcpaths:
		if not os.path.exists(path):
			print("%s does not exist, removing it from the list of sources" % path)
			srcpaths.remove(path)
			continue;
		print("Here is a source path:" + str(path))
		if os.path.isdir(path):
			print("%s is a directoy" % path)
		else:
			print("%s is not a directoy" % path)
			if os.path.isfile(path):
				print("but it is a file")
	return srcpaths


def get_dev_for_uuid(uuid):
	uuids = []
	proc = subprocess.Popen(["ls", "-1", "/dev/disk/by-uuid"], stdout=subprocess.PIPE)
	while True:
		line = proc.stdout.readline()
		if line != '':
			uuids.append(line.rstrip())
		else:
			break
	print("these are the UUIDs:" + str(uuids))
	print("this is the UUID we are looking for:" + str(uuid))

	if uuid[0] in uuids:
		#TODO: more error checking
		proc = subprocess.Popen(["blkid", "-U", str(uuid[0])], stdout=subprocess.PIPE)
		#TODO: more error checking
		dev = proc.stdout.readline()
		print("found block device %s for UUID %s" % (dev, str(uuid[0])))
	else:
		print("UUID %s could not be found" % uuid)
		return None
	return 	dev


# fiddling with mount points in python is quite tedious, hence we use three helper shell scripts

#returns True if uuid is mounted, False otherwise
def check_dev_mounted(dev):
	proc = subprocess.Popen([CHECK_DEV_MOUNTED, dev], stdout=subprocess.PIPE)
	proc.wait()
	if proc.returncode < 1:
		return True
	else:
		return False


def umount_dev(dev):
	proc = subprocess.Popen([UMOUNT_DEV, dev], stdout=subprocess.PIPE)
	proc.wait()
	return proc.returncode

def mount_dev(dev, trgt):
	proc = subprocess.Popen([MOUNT_DEV, dev, trgt], stdout=subprocess.PIPE)
	proc.wait()
	return proc.returncode

def check_trgt_present(trgt):
	#TODO: assuming we get a UUID, but ultimately parse or customize
	# target type via different command line params
	trgt = check_trgt_UUID(trgt)
	return trgt



def main(argv=None): # IGNORE:C0111
    '''Command line options.'''

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)



    try:
        # Setup argument parser
        parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-v", "--verbose", dest="verbose", action="count", help="set verbosity level [default: %(default)s]")
        parser.add_argument("-c", "--config_file", dest="config_file", help="path to config file (default: my_backup.conf")
        parser.add_argument("-u", "--dst_uuid", dest="dst_uuid", help="UUID of the backup disk")
        parser.add_argument("-d", "--dst_path", dest="dst_path", help="Additional path on backup disk")
        parser.add_argument("-m", "--dst_mount", dest="dst_mount", help="mount point for backup disk")
        parser.add_argument("-o", "--rsync_options", dest="rsync_options", help="Options to pass to rsync command")
        parser.add_argument("-l", "--rsync_logdir", dest="rsync_logdir", help="rsync logdir")
        parser.add_argument('-V', '--version', action='version', version=program_version_message)
        parser.add_argument(dest="srcpaths", help="srcpaths to source folders (overrides config file)", nargs='*')

        print("program starts")

        # Process arguments
        args = parser.parse_args()

        verbose = args.verbose
        print("verbose = " + str(verbose))
        config_file = args.config_file
        srcpaths = args.srcpaths
        dst_uuid = args.dst_uuid
	dst_mount = args.dst_mount
        dst_path = args.dst_path
        rsync_options = args.rsync_options
        rsync_logdir = args.rsync_logdir

        pid = str(os.getpid())
        pidfile = "/tmp/mydaemon.pid"

        #if os.path.isfile(pidfile):
        #    print "%s already exists, exiting" % pidfile
        #    sys.exit()
        #else:
        #    file(pidfile, 'w').write(pid)

        if config_file:
            config = ConfigParser.RawConfigParser()
            config.readfp(open(str(config_file).strip()))
            print("Config File: %s" % config_file)
        else:
	    config_file = DEFAULT_CFG_FILE
            config = None

	last_backup_string = config.get('General', 'last_backup')
	backup_interval_days = config.get('General', 'backup_interval_days')
	last_backup = datetime.datetime.strptime(last_backup_string, '%Y-%m-%d').date()
	today = datetime.date.today()

	# missing: check for next_date_to_act

	if today < (last_backup + datetime.timedelta(days=int(backup_interval_days))):
		print("Backup is not due (Last Backup was on %s, today is %s, inteval is %s days)"
			% (str(last_backup), str(today), backup_interval_days))
		# missing: quit
	else:
		print("Backup is due (Last Backup was on %s, today is %s, inteval is %s days)"
			% (str(last_backup), str(today), backup_interval_days))

        if not srcpaths and config:
            srcpaths = config.get('General', 'srcpaths').split()
        if srcpaths:
            print("srcpaths = " + str(srcpaths))
        else:
            print("Source paths are not defined. Pass them on the command line on in the configuration file.")

        if not dst_mount and config:
            dst_mount = config.get('General', 'dst_mount').split()
        if dst_mount:
            print("dst_mount = " + str(dst_mount))
        else:
            print("Destination mount point not defined. Pass it on the command line on in the configuration file.")

        if not dst_uuid and config:
            dst_uuid = config.get('General', 'dst_uuid').split()
        if dst_uuid:
            print("dst_uuid = " + str(dst_uuid))
        else:
            print("Destination UUID not defined. Pass it on the command line on in the configuration file.")

        # Destination path is completely optional
        if not dst_path and config:
            dst_path = config.get('General', 'dst_path').split()
        if dst_path:
            print("dst_path = " + str(dst_uuid))

        if not rsync_options and config:
            rsync_options = config.get('General', 'rsync_options').split()
        if not rsync_options:
            rsync_options = RSYNC_OPTIONS_DEFAULT
        print("rsync_options = " + str(rsync_options))

        if not rsync_logdir and config:
            rsync_logdir = config.get('General', 'rsync_logdir').split()
        if not rsync_logdir:
            rsync_logdir = RSYNC_LOGDIR_DEFAULT
        print("rsync_logdir = " + str(rsync_logdir))


	print("calling check_src_present. here are all the paths before")
	for path in srcpaths:
		print("source path:" + str(path))
	srcspaths = check_srcs_present(srcpaths)
	print("here are all the paths after")
	for path in srcpaths:
		print("source path:" + str(path))

	print("looking for target UUID" + str(dst_uuid))
	dev = get_dev_for_uuid(dst_uuid)
	if dev:
		print("Found %s for UUID %s" % (dev, dst_uuid))
		print("check if target UUID mounted" + str(dst_uuid))
		mounted = check_dev_mounted(dev)
		if mounted:
			print("%s is mounted, umounting it" % (dst_uuid))
			if not umount_dev(dev):
				print("Error unmounting %s" % (dst_uuid))
			else:
				print("Mounting %s again to %s" % (dst_uuid, dst_path))
		else:
			print("%s is not mounted, mounting it to %s" % (dst_uuid, dst_mount))
			print ("call mount %s %s" % (dev, str(dst_mount)))
			mount_dev(dev, ''.join(dst_mount))
	else:
		print("No device found for UUID %s" % dst_uuid )
		# next_date_to_act = config.set('General', 'next_action', _today+2days_)
		sys.exit(1)

	# we made it to this point, disk is properly mounted, now check target path exists
	dst = ''.join((dst_mount + dst_path))
	if not os.path.exists(dst):
		printf("Target path %s on device %s cannot be found" % (dst, dev))
		# next_date_to_act = config.set('General', 'next_action', _today+2days_)
		sys.exit(2)

	# we made it here:
	# src paths all exist, device mounted, target path exists




	# Checks (disk present, directories present, srcpaths present, etc.)
	# if error:
	# change / add
	#
	# next_date_to_act = config.set('General', 'next_action', _today+2days_)
	#
	# if success:
	# change / add
	# config.set('General', 'last_backup', _today_)



    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0


if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-v")
    sys.exit(main())


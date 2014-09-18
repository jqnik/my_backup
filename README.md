my_backup
=========

A python-based backup script that performs regular backups of multiple sources to a disk and reminds you if it cannot find it 

Roadmap:
* Encryption of backup
* Other rsync targets (e.g. sftp accessible locations)
* Support for multiple targets (round-robin/FCFS)
* Setup-dialog that
    * guides the user through finding the correct disk device and updates config accordingly
    * guides the user through entering and testing email account for notification

TODO:
* load script logging dir for logfile location from commandline or cfg file
* load rsync logging options from commandline or cfg file

Enhancements:
* Better email notifications (i.e. give friendly notice ahead of backup due-date)

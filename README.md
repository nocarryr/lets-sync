# lets-sync
A tool to syncronize your account and certificate data from [letsencrypt](https://letsencrypt.org/) across multiple machines.

(WIP)

## Description
*WARNING this is very much a WIP and very beta right now.  You should not use it on anything or bad things will likely happen*

The goals for this are to use SSH for transfer (Paramiko? Fabric?) and to merge/sync data in a non-descructive manner.  Any ambiguous operation should be presented to the caller as a prompt to avoid loss of information.  All data files used should maintain the proper permissions and non-clean exits must ensure this takes place.

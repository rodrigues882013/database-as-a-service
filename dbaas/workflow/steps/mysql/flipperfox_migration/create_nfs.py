# -*- coding: utf-8 -*-
import logging
from util import full_stack
from workflow.steps.util.nfsaas_utils import create_disk, delete_disk
from workflow.steps.util.base import BaseStep
from workflow.exceptions.error_codes import DBAAS_0020

LOG = logging.getLogger(__name__)


class CreateNfs(BaseStep):

    def __unicode__(self):
        return "Requesting NFS volume..."

    def do(self, workflow_dict):
        try:

            workflow_dict['disks'] = []

            for instance in workflow_dict['target_instances']:

                LOG.info("Creating nfsaas disk...")

                databaseinfra = workflow_dict['databaseinfra']
                disk = create_disk(
                    environment=workflow_dict['environment'],
                    host=instance.hostname,
                    size_kb=databaseinfra.disk_offering.size_kb
                )

                if not disk:
                    LOG.info("NFS disk could not be created...")
                    return False

                workflow_dict['disks'].append(disk)

            return True
        except Exception:
            traceback = full_stack()

            workflow_dict['exceptions']['error_codes'].append(DBAAS_0020)
            workflow_dict['exceptions']['traceback'].append(traceback)

            return False

    def undo(self, workflow_dict):
        LOG.info("Running undo...")
        try:
            for host in workflow_dict['target_hosts']:
                LOG.info("Destroying NFS disk...")

                delete_disk(
                    environment=workflow_dict['environment'],
                    host=host
                )

            return True
        except Exception:
            traceback = full_stack()

            workflow_dict['exceptions']['error_codes'].append(DBAAS_0020)
            workflow_dict['exceptions']['traceback'].append(traceback)

            return False

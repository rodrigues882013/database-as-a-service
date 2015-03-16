from util import exec_remote_command
from datetime import datetime
from dbaas.celery import app
import models
import logging
from notification.models import TaskHistory
from util import get_worker_name

LOG = logging.getLogger(__name__)

@app.task(bind=True)
def execute_scheduled_maintenance(self,maintenance):
    main_output = {}
    maintenance = models.Maintenance.objects.get(id=maintenance.id)
    maintenance.status = maintenance.RUNNING
    maintenance.save()
    LOG.info("Maintenance {} is RUNNING".format(maintenance,))

    worker_name = get_worker_name()
    task_history = TaskHistory.register(request=self.request,worker_name= worker_name)

    LOG.info("id: %s | task: %s | kwargs: %s | args: %s" % (
            self.request.id, self.request.task, self.request.kwargs, str(self.request.args)))

    task_history.update_details(persist=True,
        details="Executing Maintenance: {}".format(maintenance))

    for hm in models.HostMaintenance.objects.filter(maintenance=maintenance):
        hm.status = hm.RUNNING
        hm.started_at = datetime.now()
        hm.save()

        host = hm.host
        update_task = "\nRunning Maintenance on {}".format(host)

        cloudstack_host_attributes = host.cs_host_attributes.get()

        exit_status = exec_remote_command(server=host.address,
            username=cloudstack_host_attributes.vm_user,
            password=cloudstack_host_attributes.vm_password,
            command=maintenance.main_script, output=main_output)

        if exit_status == 0:
            hm.status = hm.SUCCESS
        else:

            if maintenance.rollback_script:
                rollback_output = {}
                hm.status = hm.ROLLBACK
                hm.save()

                exit_status = exec_remote_command(server=host.address,
                    username=cloudstack_host_attributes.vm_user,
                    password=cloudstack_host_attributes.vm_password,
                    command=maintenance.rollback_script, output=rollback_output)

                if exit_status ==0:
                    hm.status = hm.ROLLBACK_SUCCESS
                else:
                    hm.status = hm.ROLLBACK_ERROR

                hm.rollback_output = rollback_output

            else:
                hm.status = hm.ERROR

        update_task += "...status: {}".format(hm.status)

        task_history.update_details(persist=True,
            details=update_task)

        hm.main_log = main_output
        hm.finished_at = datetime.now()
        hm.save()

    maintenance.status = maintenance.FINISHED
    maintenance.save()

    task_history.update_status_for(TaskHistory.STATUS_SUCCESS,
        details='Maintenance executed succesfully')

    LOG.info("Maintenance: {} has FINISHED".format(maintenance,))

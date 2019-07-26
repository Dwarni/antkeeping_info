# Create your tasks here
from __future__ import absolute_import, unicode_literals
from celery import task, shared_task
from celery.utils.log import get_task_logger
from ants.models import AntSpecies

logger = get_task_logger(__name__)


@task
def hello_world():
    logger.info('Hello world!')

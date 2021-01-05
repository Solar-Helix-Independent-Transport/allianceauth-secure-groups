from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask


class Command(BaseCommand):
    help = 'Setup/Reset the Periodic Task for the Secure Groups module'

    def handle(self, *args, **options):
        self.stdout.write("Creating/Updating the Secure Groups Update Task")
        schedule, _ = CrontabSchedule.objects.get_or_create(minute='0',
                                                            hour='11',
                                                            day_of_week='*',
                                                            day_of_month='*',
                                                            month_of_year='*',
                                                            timezone='UTC'
                                                            )
        PeriodicTask.objects.update_or_create(
            task='securegroups.tasks.run_smart_groups',
            defaults={
                'crontab': schedule,
                'name': 'Secure Group Updater',
                'enabled': True
            }
        )
        self.stdout.write("Success!")

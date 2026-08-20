from django.core.management.base import BaseCommand

from ekomek_common.constants import Role

from identity.models import User

PASSWORD = "demo123456"


class Command(BaseCommand):
    help = "Seed identity users"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true")

    def handle(self, *args, **options):
        if options["clear"]:
            User.objects.filter(is_superuser=False).delete()
        if User.objects.filter(email="admin@charity.test").exists():
            self.stdout.write("Users already seeded")
            return
        User.objects.create_user(
            email="admin@charity.test",
            password=PASSWORD,
            full_name="Админ Тестов",
            role=Role.ADMIN,
            is_staff=True,
            is_superuser=True,
            iin="870308301456",
        )
        for index in range(1, 3):
            User.objects.create_user(
                email=f"moderator{index}@charity.test",
                password=PASSWORD,
                full_name=f"Модератор {index}",
                role=Role.MODERATOR,
                iin=f"89071140167{index}",
            )
        for index in range(1, 4):
            User.objects.create_user(
                email=f"author{index}@charity.test",
                password=PASSWORD,
                full_name=f"Автор {index}",
                role=Role.AUTHOR,
                iin=f"85031530123{index}",
            )
        for index in range(1, 5):
            User.objects.create_user(
                email=f"donor{index}@charity.test",
                password=PASSWORD,
                full_name=f"Донор {index}",
                role=Role.DONOR,
                iin=f"93061540234{index}",
            )
        self.stdout.write(self.style.SUCCESS("Identity users seeded"))

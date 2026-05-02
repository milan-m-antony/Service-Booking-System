from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0005_usermessage"),
    ]

    operations = [
        migrations.AddField(
            model_name="usermessage",
            name="sender_deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="usermessage",
            name="recipient_deleted",
            field=models.BooleanField(default=False),
        ),
    ]
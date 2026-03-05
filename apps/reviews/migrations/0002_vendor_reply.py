from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='review',
            name='vendor_reply',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='review',
            name='vendor_replied_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='review',
            name='vendor_replied_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='review_replies', to='users.user'),
        ),
    ]

# Generated by Django 4.2.19 on 2025-04-06 15:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('securegroups', '0016_remove_useringroupfilter_group'),
    ]

    operations = [
        migrations.CreateModel(
            name='FilterExpression',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=500)),
                ('description', models.CharField(max_length=500)),
                ('operator', models.CharField(choices=[('and', 'And'), ('or', 'Or'), ('xor', 'Xor')], max_length=10)),
                ('negate_result', models.BooleanField(default=False)),
                ('first_term', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='securegroups.smartfilter')),
                ('second_term', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='securegroups.smartfilter')),
            ],
            options={
                'verbose_name': 'Smart Filter: Expression',
                'verbose_name_plural': 'Smart Filter: Expression',
            },
        ),
    ]

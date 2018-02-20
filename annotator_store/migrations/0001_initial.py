# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields
import uuid
from django.conf import settings
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Annotation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('text', models.TextField()),
                ('quote', models.TextField()),
                ('uri', models.URLField()),
                ('extra_data', jsonfield.fields.JSONField(default=b'{}')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'permissions': (('view_annotation', 'View annotation'), ('admin_annotation', 'Manage annotation')),
            },
        ),
        migrations.CreateModel(
            name='AnnotationGroup',
            fields=[
                ('group_ptr', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, parent_link=True, auto_created=True, primary_key=True, serialize=False, to='auth.Group')),
                ('notes', models.TextField(blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
            bases=('auth.group',),
        ),
    ]

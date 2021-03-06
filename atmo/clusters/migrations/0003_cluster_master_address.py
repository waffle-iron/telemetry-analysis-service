# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-09-27 22:29
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clusters', '0002_cluster_emr_release'),
    ]

    operations = [
        migrations.AddField(
            model_name='cluster',
            name='master_address',
            field=models.CharField(default='', help_text='Public address of the master node.This is only available once the cluster has bootstrapped', max_length=255),
        ),
    ]

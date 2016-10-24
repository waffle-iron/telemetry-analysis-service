# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse_lazy

from . import models
from ..forms.fields import CachedFileField
from ..forms.mixins import (CreatedByFormMixin, CachedFileFormMixin,
                            FormControlFormMixin)


class BaseSparkJobForm(FormControlFormMixin, CachedFileFormMixin,
                       CreatedByFormMixin, forms.ModelForm):
    identifier = forms.RegexField(
        required=True,
        label='Job identifier',
        regex=r'^[\w-]{1,100}$',
        widget=forms.TextInput(attrs={
            'required': 'required',
            'class': 'identifier-taken-check',
            'data-identifier-taken-check-url': reverse_lazy('jobs-identifier-taken'),
        }),
        help_text='A brief description of the scheduled Spark job\'s purpose, '
                  'visible in the AWS management console.'
    )
    result_visibility = forms.ChoiceField(
        choices=models.SparkJob.RESULT_VISIBILITY_CHOICES,
        widget=forms.Select(attrs={
            'required': 'required',
        }),
        label='Job result visibility',
        help_text='Whether notebook results are uploaded to a public '
                  'or private bucket',
    )
    size = forms.IntegerField(
        required=True,
        min_value=1,
        max_value=settings.AWS_CONFIG['MAX_CLUSTER_SIZE'],
        label='Job cluster size',
        widget=forms.NumberInput(attrs={
            'required': 'required',
            'min': '1',
            'max': str(settings.AWS_CONFIG['MAX_CLUSTER_SIZE']),
        }),
        help_text='Number of workers to use when running the Spark job '
                  '(1 is recommended for testing or development).'
    )
    interval_in_hours = forms.ChoiceField(
        choices=models.SparkJob.INTERVAL_CHOICES,
        widget=forms.Select(attrs={
            'required': 'required',
        }),
        label='Job interval',
        help_text='Interval at which the Spark job should be run',
    )
    job_timeout = forms.IntegerField(
        required=True,
        min_value=1,
        max_value=24,
        label='Job timeout',
        widget=forms.NumberInput(attrs={
            'required': 'required',
            'min': '1',
            'max': '24',
        }),
        help_text='Number of hours that a single run of the job can run '
                  'for before timing out and being terminated.'
    )
    start_date = forms.DateTimeField(
        required=True,
        widget=forms.DateTimeInput(attrs={
            'class': 'datetimepicker',
        }),
        label='Job start date',
        help_text='Date and time on which to enable the scheduled Spark job.',
    )
    end_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'datetimepicker',
        }),
        label='Job end date (optional)',
        help_text='Date and time on which to disable the scheduled Spark job '
                  '- leave this blank if the job should not be disabled.',
    )
    notebook = CachedFileField(
        required=True,
        widget=forms.FileInput(attrs={
            'required': 'required',
        }),
        label='Analysis Jupyter Notebook',
        help_text='A Jupyter/IPython Notebook has the file extension .ipynb'
    )

    class Meta:
        model = models.SparkJob
        fields = [
            'identifier', 'notebook', 'result_visibility', 'size',
            'interval_in_hours', 'job_timeout', 'start_date', 'end_date'
        ]

    def clean_notebook(self):
        notebook_file = self.cleaned_data['notebook']
        if notebook_file and not notebook_file.name.endswith(('.ipynb',)):
            raise forms.ValidationError('Only Jupyter/IPython Notebooks are '
                                        'allowed to be uploaded')
        return notebook_file

    def save(self):
        # create the model without committing, since we haven't
        # set the required created_by field yet
        spark_job = super(BaseSparkJobForm, self).save(commit=False)

        # actually save the scheduled Spark job, and return the model object
        spark_job.save(self.cleaned_data['notebook'])
        return spark_job


class NewSparkJobForm(BaseSparkJobForm):
    prefix = 'new'

    class Meta(BaseSparkJobForm.Meta):
        fields = BaseSparkJobForm.Meta.fields + ['emr_release']


class EditSparkJobForm(BaseSparkJobForm):
    prefix = 'edit'

    notebook = CachedFileField(
        required=False,
        widget=forms.FileInput(),
        label='Analysis Jupyter Notebook (optional)',
        help_text='A Jupyter/IPython Notebook has the file '
                  'extension .ipynb.'
    )

    def __init__(self, *args, **kwargs):
        super(EditSparkJobForm, self).__init__(*args, **kwargs)
        if self.instance:
            self.fields['notebook'].help_text += (
                '<br />Current notebook: <strong>%s</strong>' % self.instance.notebook_name
            )


class DeleteSparkJobForm(CreatedByFormMixin, forms.ModelForm):
    prefix = 'delete'

    confirmation = forms.RegexField(
        required=True,
        label='Confirm termination with Spark job identifier',
        regex=r'^[\w-]{1,100}$',
        widget=forms.TextInput(attrs={
            'required': 'required',
        }),
    )

    def clean_confirmation(self):
        confirmation = self.cleaned_data.get('confirmation')
        if confirmation != self.instance.identifier:
            raise forms.ValidationError(
                "Entered Spark job identifier doesn't match"
            )
        return confirmation

    class Meta:
        model = models.SparkJob
        fields = []


class TakenSparkJobForm(forms.Form):
    id = forms.IntegerField(required=False)
    identifier = forms.CharField(required=True)

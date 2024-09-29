from django import forms
import pandas as pd
from django.conf import settings
import os


class DynamicCreditForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(DynamicCreditForm, self).__init__(*args, **kwargs)

        file_path = os.path.join(settings.MEDIA_ROOT, 'Regular_Semester_Data.xlsx')
        if os.path.exists(file_path):
            df = pd.read_excel(file_path, sheet_name=None)
            subjects = []
            for sheet in df.keys():
                temp_df = df[sheet]
                subject_columns = [col for col in temp_df.columns if 'Total' in col]
                subjects.extend(subject_columns)

            subjects = list(set(subjects))  # Remove duplicates
            for subject in subjects:
                subject_name = subject.replace('_Total', '')  # Clean up field name for display
                self.fields[f'{subject}_credit'] = forms.IntegerField(
                    label=f'Credits for {subject_name}',
                    min_value=1,
                    max_value=10,
                    help_text=f'Enter credits for {subject_name}',
                )
        else:
            self.fields['error'] = forms.CharField(
                label='Error',
                initial='Data file not found',
                disabled=True
            )

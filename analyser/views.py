import json
from django.conf import settings
import os
from django.http import HttpResponse
import pandas as pd
from django.shortcuts import render


def marks_analyser(request):
    subjects = {}
    if os.path.exists(os.path.join(settings.MEDIA_ROOT, 'subjects.json')):
        with open(os.path.join(settings.MEDIA_ROOT, 'subjects.json')) as f:
            subjects = json.load(f)
        print(subjects)
    if request.method == 'POST':
        excel_file = request.FILES['excel_file']
        credits_input = request.POST.get('credits')

        file_path = os.path.join(settings.MEDIA_ROOT, excel_file.name)
        with open(file_path, 'wb+') as destination:
            for chunk in excel_file.chunks():
                destination.write(chunk)

        credits = list(map(int, credits_input.split(','))) if credits_input else []
        df = pd.read_excel(file_path, sheet_name=None)
        sheet_names = df.keys()
        data_frames = {sheet: df[sheet] for sheet in sheet_names}

        for sheet_name, df_sem in data_frames.items():
            subjects = subjects.get(sheet_name, [])
            print(subjects, credits)
            if len(credits) != len(subjects):
                return HttpResponse("The number of credits does not match the number of subjects.")

            # Processing logic here...

        output_file_path = os.path.join(settings.MEDIA_ROOT, 'Processed_Data.xlsx')
        with pd.ExcelWriter(output_file_path, engine='xlsxwriter') as writer:
            for sheet_name, df_sem in data_frames.items():
                df_sem.to_excel(writer, sheet_name=sheet_name, index=False)

        return HttpResponse(
            "File uploaded and processed successfully. <a href='/download/Processed_Data.xlsx'>Download the processed file</a>.")

    return render(request, 'analyser.html', {'subjects': subjects})

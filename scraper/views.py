import os
import time
from io import BytesIO

import pandas as pd
import pytesseract
from PIL import Image
from bs4 import BeautifulSoup
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from .forms import UserInput


def index(request):
    return render(request, 'index.html')


def MarksScraper(request):
    if request.method == 'POST':
        form = UserInput(request.POST)
        if form.is_valid():
            prefix_usn = form.cleaned_data['prefix_usn'].upper()
            suffix_usn = form.cleaned_data['suffix_usn']
            main_sem = form.cleaned_data['main_sem']
            url_value = form.cleaned_data['url_value']

            is_reval = 'RV' in url_value
            usn_list = generate_usn_list(prefix_usn, suffix_usn)

            driver = initialize_webdriver(url_value)
            soup_dict = scrape_data(driver, usn_list)
            driver.quit()

            if soup_dict:
                process_and_save_data(soup_dict, is_reval)
                download_url = reverse('download_file', kwargs={'filename': 'Regular_Semester_Data.xlsx'})
                return HttpResponse(f"Data collected and saved successfully. <a href='{download_url}'>Download the file</a>")
            else:
                return HttpResponse("No data collected.")
    else:
        form = UserInput()

    return render(request, 'scraper.html', {'form': form})


def initialize_webdriver(url):
    driver = webdriver.Chrome()
    driver.get(url)
    return driver


def scrape_data(driver, usn_list):
    soup_dict = {}
    for usn in usn_list:
        while True:
            driver.find_element(By.NAME, 'lns').clear()
            driver.find_element(By.NAME, 'lns').send_keys(usn)

            captcha_image = driver.find_element(By.XPATH, '//*[@id="raj"]/div[2]/div[2]/img').screenshot_as_png
            pytesseract.pytesseract.tesseract_cmd = r'Tesseract-OCR/tesseract.exe'

            text = get_captcha_from_image(captcha_image)
            driver.find_element(By.NAME, 'captchacode').clear()
            driver.find_element(By.NAME, 'captchacode').send_keys(text)
            driver.find_element(By.ID, 'submit').click()

            try:
                WebDriverWait(driver, 1).until(EC.alert_is_present())
                alert = driver.switch_to.alert
                alert_text = alert.text
                alert.accept()

                if 'University Seat Number is not available or Invalid..!' in alert_text:
                    break

                print(f"Captcha failed for USN {usn}. Retrying...")

            except:
                print(f"Captcha succeeded for USN {usn}.")
                soup = BeautifulSoup(driver.page_source, 'lxml')
                student_usn = soup.find_all('td')[1].text.split(':')[1].strip().upper()
                student_name = soup.find_all('td')[3].text.split(':')[1].strip()
                key = f'{student_usn}+{student_name}'
                soup_dict[key] = soup
                driver.back()
                break

        time.sleep(2)
    return soup_dict


def get_captcha_from_image(target_image):
    pixel_range = [(i, i, i) for i in range(102, 130)]
    image_data = BytesIO(target_image)
    image = Image.open(image_data)
    width, height = image.size
    image.convert("RGB")
    white_image = Image.new("RGB", (width, height), "white")

    for x in range(width):
        for y in range(height):
            pixel = image.getpixel((x, y))
            if pixel in pixel_range:
                white_image.putpixel((x, y), pixel)

    text = pytesseract.image_to_string(white_image, config='--psm 7 --oem 1').strip()

    if len(text) < 6:
        text = text.ljust(6, 'A')
    elif len(text) > 6:
        text = text[:6]

    return text


def generate_usn_list(prefix_usn, suffix_usn):
    usn_list = []
    for part in suffix_usn.split(','):
        if '-' in part:
            start, end = map(int, part.split('-'))
            usn_list.extend(f"{prefix_usn}{str(num).zfill(3)}" for num in range(start, end + 1))
        else:
            usn_list.append(f"{prefix_usn}{str(int(part)).zfill(3)}")
    return usn_list


def flatten_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join(col).strip() for col in df.columns.values]
    return df


def process_and_save_data(soup_dict, is_reval):
    dict_of_sems_dfs = {str(sem): [] for sem in range(8, 0, -1)}

    for id, soup in soup_dict.items():
        this_usn, this_name = id.split('+')
        sems_divs = soup.find_all('div', style="text-align:center;padding:5px;")
        sems_num = [x.text.split(':')[-1].strip() for x in sems_divs]
        sems_data = [sem_div.find_next_sibling('div') for sem_div in sems_divs]

        for sem, marks_data in zip(sems_num, sems_data):
            rows = marks_data.find_all('div', class_='divTableRow')
            data = [[cell.text.strip() for cell in row.find_all('div', class_='divTableCell')] for row in rows]

            df_temp = pd.DataFrame(data[1:], columns=data[0])
            subjects = [f'{name} ({code})' for name, code in zip(df_temp['Subject Name'], df_temp['Subject Code'])]

            headers = df_temp.columns[2:] if is_reval else df_temp.columns[2:-1]
            ready_columns = [(name, header) for name in subjects for header in headers]

            student_sem_df = pd.DataFrame([this_usn, this_name] + list(
                df_temp.iloc[:, 2:].to_numpy().flatten() if is_reval else df_temp.iloc[:, 2:-1].to_numpy().flatten()),
                                          index=[('USN', ''), ('Student Name', '')] + ready_columns).T
            student_sem_df.columns = pd.MultiIndex.from_tuples(student_sem_df.columns, names=['', ''])
            student_sem_df = flatten_columns(student_sem_df)

            dict_of_sems_dfs[sem].append(student_sem_df)

    dict_of_sems_dfs = {key: value for key, value in dict_of_sems_dfs.items() if value}

    file_path = os.path.join(settings.MEDIA_ROOT, 'Regular_Semester_Data.xlsx')
    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        for sem, dfs in dict_of_sems_dfs.items():
            combined_df = pd.concat(dfs).reset_index(drop=True)
            combined_df = flatten_columns(combined_df)
            combined_df.to_excel(writer, sheet_name=f'Semester_{sem}', index=False)

    return file_path


def download_file(request, filename):
    file_path = os.path.join(settings.MEDIA_ROOT, filename)
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
    return HttpResponse("File not found.")


def Working(request):
    return render(request, 'working.html')

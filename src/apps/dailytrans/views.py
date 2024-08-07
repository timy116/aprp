import os
from django.utils.encoding import escape_uri_path
from os.path import join
from datetime import datetime, timedelta

from django.http import FileResponse, HttpResponse
from django.shortcuts import render
from django.conf import settings

from dashboard.views import login_required
from google_api.backends import DefaultGoogleDriveClient
from apps.dailytrans.models import DailyReport, FestivalReport
from apps.dailytrans.reports.dailyreport import DailyReportFactory
from apps.dailytrans.reports.festivalreport import FestivalReportFactory
from apps.dailytrans.reports.last5yearsreport import Last5YearsReportFactory
from distutils.util import strtobool
import logging
from apps.configs.models import Festival, FestivalItems, FestivalName, AbstractProduct
from django.core.exceptions import ObjectDoesNotExist
import json
import pandas as pd
import numpy as np


# import time

def upload_file2google_client(file_name, file_path, folder_id, from_mimetype='XLSX'):
    google_drive_client = DefaultGoogleDriveClient()
    if from_mimetype == 'XLSX':
        from_mimetype = google_drive_client.XLSX_MIME_TYPE
    response = google_drive_client.media_upload(
        name=file_name,
        file_path=file_path,
        from_mimetype=from_mimetype,
        parents=[folder_id],
    )
    file_id = response.get('id')
    google_drive_client.set_public_permission(file_id)
    return file_id


@login_required
def download_daily_report(request):
    data = request.GET or request.POST

    day = data.get('day')
    month = data.get('month')
    year = data.get('year')

    if not all([day, month, year]):
        yesterday = datetime.now() - timedelta(days=-1)
        day, month, year = yesterday.day, yesterday.month, yesterday.year

    date = datetime(int(year), int(month), int(day))
    date_str = f'{int(year) - 1911}.{str(month).zfill(2)}.{str(day).zfill(2)}'
    file_path = ''
    file_name = ''

    for file in os.listdir(settings.BASE_DIR('apps/dailytrans/reports')):
        if file.find(date_str) > -1:
            file_path = settings.BASE_DIR(f'apps/dailytrans/reports/{file}')
            file_name = file
            break

    if not file_path:
        factory = DailyReportFactory(specify_day=date)
        file_name, file_path = factory()

    with open(file_path, 'rb') as f:

        response = HttpResponse(
            f.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            status=200
        )
        response['Content-Disposition'] = f'attachment; filename={escape_uri_path(file_name)}'
        response['Content-Length'] = os.path.getsize(file_path)

        return response



def render_daily_report(request):
    folder_id = settings.DAILY_REPORT_FOLDER_ID
    google_drive_client = DefaultGoogleDriveClient()

    data = request.GET or request.POST

    day = data.get('day')
    month = data.get('month')
    year = data.get('year')

    if not all([day, month, year]):
        yesterday = datetime.today() - timedelta(days=-1)
        day, month, year = yesterday.day, yesterday.month, yesterday.year

    daily_report = DailyReport.objects.filter(date__year=year, date__month=month, date__day=day).first()
    if daily_report:
        file_id = daily_report.file_id
    else:
        date = datetime(int(year), int(month), int(day))
        # generate file
        factory = DailyReportFactory(specify_day=date)
        file_name, file_path = factory()
        # upload file
        response = google_drive_client.media_upload(
            name=file_name,
            file_path=file_path,
            from_mimetype=google_drive_client.XLSX_MIME_TYPE,
            parents=[folder_id],
        )
        file_id = response.get('id')
        # make public
        google_drive_client.set_public_permission(file_id)
        # write result to database
        DailyReport.objects.create(date=date, file_id=file_id)
        # remove local file
        os.remove(file_path)

    context = {
        'file_id': file_id
    }
    template = 'daily-report-iframe.html'

    return render(request, template, context)


def render_festival_report(request, refresh=False):
    context = {}
    folder_id = settings.FESTIVAL_REPORT_FOLDER_ID
    # google_drive_client = DefaultGoogleDriveClient()
    data = request.GET or request.POST
    roc_year = data.get('roc_year')
    year = int(roc_year) + 1911
    festivalname_id = data.get('festival_id')
    refresh = bool(strtobool(data.get('refresh')))
    oneday = bool(strtobool(data.get('oneday')))
    item_search_list = data.getlist('item_search[]')
    custom_search = bool(strtobool(data.get('custom_search')))
    # start_time = time.time()
    festival_name = FestivalName.objects.filter(id=festivalname_id)

    if oneday:
        day = data.get('day')
        if len(day) == 1:
            day = '0' + day
        month = data.get('month')
        if len(month) == 1:
            month = '0' + month
        year = data.get('year')
        date = year + '-' + month + '-' + day

        factory = FestivalReportFactory(rocyear=roc_year, festival=festivalname_id, oneday=oneday, special_day=date)
        resule_data = factory()
        product_name_list = []
        pid = FestivalItems.objects.filter(festivalname__id__contains=festivalname_id)
        for i in pid.all():
            product_name_list.append(i)

        values_list = []
        for v in resule_data.values():
            if str(v[str(year)][0]) == 'nan':
                v[str(year)][0] = None
            if str(v[str(year)][1]) == 'nan':
                v[str(year)][1] = None
            values_list.append([v[str(year)][0], v[str(year)][1]])

        product_data = {}
        product_data_list = list()
        product_data_list.append([festival_name[0].name + '農產品品項', date + '當日價格'])
        if len(values_list) == len(product_name_list):
            for i in range(len(values_list)):
                product_data[product_name_list[i].name] = values_list[i]
                product_data_list.append([product_name_list[i].name, values_list[i]])

        context = {
            'oneday': oneday,
            'festival_name': festival_name,
            'date': date,
            'product_data': product_data,
            'json_data': json.dumps(product_data_list),
        }

    elif custom_search:
        day = data.get('day')
        if len(day) == 1:
            day = '0' + day
        month = data.get('month')
        if len(month) == 1:
            month = '0' + month
        year = data.get('year')
        date = year + '-' + month + '-' + day
        if item_search_list:
            factory = FestivalReportFactory(custom_search=custom_search, custom_search_item=item_search_list,
                                            special_day=date)
            resule_data, resule_volume = factory()
            # to_htmo
            # product_data = resule_data.to_html()
            # to_json
            json_records = resule_data.reset_index().to_json(orient='records')
            json_records_volume = resule_volume.reset_index().to_json(orient='records')
            product_data = json.loads(json_records)
            product_data_volume = json.loads(json_records_volume)

            context = {
                'custom_search': custom_search,
                'date': date,
                'product_data': product_data,
                'product_data_volume': product_data_volume,
            }
        else:
            context = {
                'custom_search': custom_search,
                'date': date,
                'no_product': True,
            }

    else:
        try:
            festival_id = Festival.objects.get(roc_year=roc_year, name=festival_name)
            festival_report = FestivalReport.objects.filter(festival_id_id=festival_id.id)

        except ObjectDoesNotExist:
            db_logger = logging.getLogger('aprp')
            db_logger.warning(f'search festival report error:{roc_year} {festival_name}',
                              extra={'type_code': 'festivalreport'})
            festival_id = None

        if festival_id is not None and festival_id.id:
            if not refresh:
                if festival_report:
                    file_id = festival_report[0].file_id
                    file_volume_id = festival_report[0].file_volume_id
                else:
                    # generate file
                    factory = FestivalReportFactory(rocyear=roc_year, festival=festivalname_id)
                    file_name, file_path, file_volume_name, file_volume_path = factory()
                    # upload file
                    file_id = upload_file2google_client(file_name, file_path, folder_id)
                    file_volume_id = upload_file2google_client(file_volume_name, file_volume_path, folder_id)
                    # write result to database
                    FestivalReport.objects.create(festival_id_id=festival_id.id, file_id=file_id,
                                                  file_volume_id=file_volume_id)
                    # remove local file
                    os.remove(file_path)
                    os.remove(file_volume_path)

            else:
                # 重新產生報告
                factory = FestivalReportFactory(rocyear=roc_year, festival=festivalname_id)
                file_name, file_path, file_volume_name, file_volume_path = factory()
                # 刪除資料庫中三節報表的id
                file_id = festival_report[0].file_id
                file_volume_id = festival_report[0].file_volume_id
                festival_report[0].delete()
                # 刪除 google drive 報表檔案
                google_drive_client = DefaultGoogleDriveClient()
                response = google_drive_client.delete_file(file_id=file_id)
                response_volume = google_drive_client.delete_file(file_id=file_volume_id)
                if not response and not response_volume:  # google drive 刪除成功返回空值
                    pass
                else:
                    db_logger = logging.getLogger('aprp')
                    db_logger.warning(f'delete google file error:{response}, {response_volume}',
                                      extra={'type_code': 'festivalreport'})
                # 檔案上傳 google drive
                file_id = upload_file2google_client(file_name, file_path, folder_id)
                file_volume_id = upload_file2google_client(file_volume_name, file_volume_path, folder_id)
                FestivalReport.objects.create(festival_id_id=festival_id.id, file_id=file_id,
                                              file_volume_id=file_volume_id)
                # 刪除本地暫存報表檔案
                os.remove(file_path)
                os.remove(file_volume_path)

            refresh = True
            context = {
                'file_id': file_id,
                'file_volume_id': file_volume_id,
                'refresh': refresh,
                'roc_year': roc_year,
                'festival_name': festival_name,
            }
        else:
            context = {
                'no_festival': True,
                'roc_year': roc_year,
                'festival_name': festival_name,
            }
    template = 'festival-report-iframe.html'
    # end_time = time.time()
    # print('spend time=',end_time-start_time)
    return render(request, template, context)


def render_last5years_report(request):
    is_rams = False
    is_hogs = False
    is_flowers = False
    data = request.GET or request.POST
    sel_item_id = data.get('sel_item_id_list')
    sel_item_source = data.get('sel_item_source_list')
    sel_item_name = data.get('sel_item_name')
    sel_item_id_list = [int(i) for i in sel_item_id.split(',')]
    if 80001 <= int(sel_item_id_list[0]) < 80005:
        is_rams = True
    elif 70001 <= int(sel_item_id_list[0]) < 70012:
        is_hogs = True
    elif 30001 <= int(sel_item_id_list[0]) <= 30002 or 60001 <= int(sel_item_id_list[0]) < 70000:
        is_flowers = True

    avgvolume_data = None
    avgweight_data = None
    avgpriceweight_data = None
    hightcharts_avgvolume_data = None
    hightcharts_avgweight_data = None
    hightcharts_avgpriceweight_data = None

    if sel_item_source:
        sel_item_source_list = [int(i) for i in sel_item_source.split(',')]
    else:
        sel_item_source_list = []

    avgprice_data, avgvolume_data, avgweight_data, avgpriceweight_data = Last5YearsReportFactory(
        product_id=sel_item_id_list, source=sel_item_source_list, is_hogs=is_hogs, is_rams=is_rams)()

    # The first column is the yearly average value, it is not needed to display on the chart.
    hightcharts_avgprice_data = avgprice_data[avgprice_data.columns[1:]].replace(np.nan, '', regex=True).to_dict(
        'split')
    avgprice_data = avgprice_data.replace(np.nan, '', regex=True).to_html(classes='table table-striped table-hover')

    context = {
        'avgprice_data': avgprice_data,
        'hightcharts_avgprice_data': hightcharts_avgprice_data,
        'sel_item_name': sel_item_name,
        'is_hogs': json.dumps(is_hogs),
        'is_rams': json.dumps(is_rams),
        'is_flowers': json.dumps(is_flowers),
    }

    if not avgvolume_data.empty:
        hightcharts_avgvolume_data = avgvolume_data[avgvolume_data.columns[1:]].replace(np.nan, '', regex=True).to_dict(
            'split')
        avgvolume_data = avgvolume_data.replace(np.nan, '', regex=True).to_html(
            classes='table table-striped table-hover')
        context['hightcharts_avgvolume_data'] = hightcharts_avgvolume_data
        context['avgvolume_data'] = avgvolume_data

    if not avgweight_data.empty:
        hightcharts_avgweight_data = avgweight_data[avgweight_data.columns[1:]].replace(np.nan, '', regex=True).to_dict(
            'split')
        avgweight_data = avgweight_data.replace(np.nan, '', regex=True).to_html(
            classes='table table-striped table-hover')
        context['hightcharts_avgweight_data'] = hightcharts_avgweight_data
        context['avgweight_data'] = avgweight_data

    if not avgpriceweight_data.empty:
        hightcharts_avgpriceweight_data = avgpriceweight_data[avgpriceweight_data.columns[1:]].replace(np.nan, '',
                                                                                                       regex=True).to_dict(
            'split')
        avgpriceweight_data = avgpriceweight_data.replace(np.nan, '', regex=True).to_html(
            classes='table table-striped table-hover')
        context['hightcharts_avgpriceweight_data'] = hightcharts_avgpriceweight_data
        context['avgpriceweight_data'] = avgpriceweight_data

    template = 'last5years-report-iframe.html'

    return render(request, template, context)

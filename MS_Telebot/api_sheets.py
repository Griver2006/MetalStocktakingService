from __future__ import print_function

import os.path
from googleapiclient.discovery import build
from google.oauth2 import service_account

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'credentials.json')

credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)


# SAMPLE_SPREADSHEET_ID = '1t5OI3AaEjUF7wdeQewDym1Xdmn1n6n37CfqXOAu548k'
SAMPLE_SPREADSHEET_ID = '1oXfqdStLPb7fWZzfVdVr2YU5UdaBfLN171B2d3mrH7k'
ACTUAL_PRICE = 'Актуальный прайс'
KUSH_PRICE = 'Куш прайс'
ALL_OPERATIONS = 'Все операции'
MINUS_OPERATIONS = 'Минусовые операции'
REPORT_DATA = 'Сводная страница'
sheet_id = '1175068379'

service = build('sheets', 'v4', credentials=credentials).spreadsheets()


# Call the Sheets API
def call_metals_prices(kush=False):
    if kush:
        result = service.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                      range=KUSH_PRICE).execute()
    else:
        result = service.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                      range=ACTUAL_PRICE).execute()
    return result.get('values', [])[1:]


def delete_last_row():
    request_body = {
        'requests': [
            {
                'deleteDimension': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'ROWS',
                        'startIndex': 1,
                        'endIndex': 2
                    }
                }
            }
        ]
    }
    try:
        service.batchUpdate(spreadsheetId=SAMPLE_SPREADSHEET_ID, body=request_body).execute()
    except:
        delete_last_row()


def record(values):
    request_body = {
        'requests': [
            {
                'insertDimension': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'ROWS',
                        'startIndex': 1,
                        'endIndex': 2
                    }
                }
            }
        ]
    }
    try:
        service.batchUpdate(spreadsheetId=SAMPLE_SPREADSHEET_ID, body=request_body).execute()
        range_ = f"'{ALL_OPERATIONS}'!A2:G2"
        array = {'values': [values]}
        service.values().update(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                range=range_,
                                valueInputOption='USER_ENTERED',
                                body=array).execute()
    except Exception as e:
        print(e)
        record(values)


def record_minus_operation(values):
    try:
        service.values().append(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                range=f"'{MINUS_OPERATIONS}'",
                                valueInputOption='USER_ENTERED',
                                body={'values': [values]}).execute()
    except:
        record_minus_operation(values)


def get_report(request):
    try:
        if 'all_time' in request:
            result = service.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                          range=f"'{REPORT_DATA}'!A2:B20").execute().get('values')
            return result
        if 'today' in request:
            result = service.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                          range=f"'{REPORT_DATA}'!D2:E19").execute().get('values')
            return result
    except:
        get_report(request)
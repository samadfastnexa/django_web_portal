"""
One-time script: sync designations, regions, zones, territories for agri sales staff
from the SAP data provided by the user.

Usage:
    cd /home/www/django_web_portal/web_portal
    python accounts/scripts/sync_agri_designations.py

Safe to re-run: only updates designation + geo M2M, never touches user accounts or passwords.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
import django
django.setup()

from accounts.models import SalesStaffProfile, DesignationModel
from FieldAdvisoryService.models import Region, Zone, Territory, Company

# ---------------------------------------------------------------------------
# Source data (from SAP / user-provided spreadsheet)
# Columns: emp_code, name, designation, region, zone, territory
# emp_code matches SalesStaffProfile.employee_code
# ---------------------------------------------------------------------------
ROWS = [
    {'emp_code': '1931',  'name': 'Rai Shahzeb',                    'designation': 'ZONAL MANAGER',                          'region': 'Green 3',          'zone': 'Peshawar',              'territory': ''},
    {'emp_code': '3059',  'name': 'Noor Hassan Kalwar',             'designation': 'SALES MANAGER',                          'region': 'White 3',          'zone': 'Sukkur',                'territory': ''},
    {'emp_code': '3111',  'name': 'Mumtaz Ali Sodhro',              'designation': 'GENERAL MANAGER SALES & MARKETING',      'region': 'White Regions',    'zone': '',                      'territory': ''},
    {'emp_code': '3133',  'name': 'Ghulam Murtaza',                 'designation': 'BUSINESS MANAGER',                       'region': 'White 2',          'zone': '',                      'territory': ''},
    {'emp_code': '3384',  'name': 'Muhammad Nawaz Palh',            'designation': 'AREA FARMER SERVICE MANAGER',            'region': 'White 3',          'zone': 'Sukkur',                'territory': 'Rohri'},
    {'emp_code': '3404',  'name': 'Abdul Wahid',                    'designation': 'BUSINESS MANAGER',                       'region': 'Blue',             'zone': '',                      'territory': ''},
    {'emp_code': '3942',  'name': 'Ubaid Ullah',                    'designation': 'ZONAL MANAGER',                          'region': 'White 2',          'zone': 'Rahim Yar Khan',        'territory': ''},
    {'emp_code': '4198',  'name': 'Aqeel Khadim',                   'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Green 2',          'zone': 'Sialkot',               'territory': 'Wahndo'},
    {'emp_code': '4471',  'name': 'Shehroz Rasheed',                'designation': 'CHIEF GENERAL MANAGER OPERATION AND GROWTH', 'region': 'Green,Blue and KPR Regions', 'zone': '',       'territory': ''},
    {'emp_code': '4530',  'name': 'Babar Hussain',                  'designation': 'ZONAL MANAGER',                          'region': 'Green 2',          'zone': 'Sialkot',               'territory': ''},
    {'emp_code': '4764',  'name': 'Muhammad Arif Baig',             'designation': 'FARMER SERVICE MANAGER',                 'region': 'Blue',             'zone': 'MUZAFFAR GARH',         'territory': 'Ali Pur'},
    {'emp_code': '4827',  'name': 'Amir Nawaz',                     'designation': 'SALES MANAGER',                          'region': 'Green 3',          'zone': '',                      'territory': ''},
    {'emp_code': '4843',  'name': 'Nisar Ahmed Kalwar',             'designation': 'REGIONAL SALES LEADER',                  'region': 'White 2',          'zone': 'Ghotki',                'territory': ''},
    {'emp_code': '4909',  'name': 'Fazan Ahmad',                    'designation': 'REGIONAL SALES MANAGER',                 'region': 'Green 1',          'zone': 'Vehari',                'territory': ''},
    {'emp_code': '5264',  'name': 'Fakhar Ul Islam',                'designation': 'ZONAL MANAGER',                          'region': 'GOLD',             'zone': 'QUETTA',                'territory': ''},
    {'emp_code': '5286',  'name': 'Ali Nawaz',                      'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Blue',             'zone': 'Bahawalnagar',          'territory': 'Haroonabad'},
    {'emp_code': '5353',  'name': 'Riaz Ahmad',                     'designation': 'AREA FARMER SERVICE MANAGER',            'region': 'Green 2',          'zone': 'Pakpattan',             'territory': 'Pakpattan-1'},
    {'emp_code': '5462',  'name': 'Rana Muhammad Khalid Khan',      'designation': 'BUSINESS MANAGER',                       'region': 'Blue',             'zone': 'MUZAFFAR GARH',         'territory': ''},
    {'emp_code': '5488',  'name': 'Sajjad Hussain',                 'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Green 1',          'zone': 'Vehari',                'territory': 'Burewala'},
    {'emp_code': '5535',  'name': 'Yar Muhammad Soomro',            'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'White 2',          'zone': 'Ghotki',                'territory': 'Jarwar'},
    {'emp_code': '5548',  'name': 'Muhammad Ahsan Khalid',          'designation': 'ASST. ZONAL MANAGER',                    'region': 'Green 3',          'zone': 'Chiniot',               'territory': ''},
    {'emp_code': '5589',  'name': 'Ghazanfar Ali',                  'designation': 'ASST. ZONAL MANAGER',                    'region': 'Green 2',          'zone': 'Lahore',                'territory': ''},
    {'emp_code': '5639',  'name': 'Muhammad Saqib Shah',            'designation': 'AREA FARMER SERVICE MANAGER',            'region': 'Green 3',          'zone': 'Sargodha',              'territory': 'Sargodha'},
    {'emp_code': '5641',  'name': 'Moazzum Abbas',                  'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 3',          'zone': 'Sargodha',              'territory': 'Mandi Bahaudin'},
    {'emp_code': '5704',  'name': 'Muhammad Waqas',                 'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Blue',             'zone': 'Bhakkar',               'territory': 'Kehror Lal Esan'},
    {'emp_code': '5725',  'name': 'Adnan Asif',                     'designation': 'FARMER SERVICE MANAGER',                 'region': 'White 1',          'zone': 'Nawabshah',             'territory': 'Khipro'},
    {'emp_code': '5750',  'name': 'Muhammad Abdullah',              'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 2',          'zone': 'Sialkot',               'territory': 'Narowal'},
    {'emp_code': '5872',  'name': 'Shoukat Abbas',                  'designation': 'FARMER SERVICE MANAGER',                 'region': 'Blue',             'zone': 'MUZAFFAR GARH',         'territory': 'Layyah'},
    {'emp_code': '5873',  'name': 'Akhtar Hussain',                 'designation': 'AREA FARMER SERVICE MANAGER',            'region': 'White 1',          'zone': 'Umerkot',               'territory': 'Kunri'},
    {'emp_code': '5918',  'name': 'Ashraf Ali',                     'designation': 'REGIONAL SALES MANAGER',                 'region': 'White 2',          'zone': 'Dadu',                  'territory': ''},
    {'emp_code': '5940',  'name': 'Hafiz Abdul Rehman Khalid',      'designation': 'BUSINESS MANAGER',                       'region': 'Green 1 & 2',      'zone': '',                      'territory': ''},
    {'emp_code': '5949',  'name': 'Muhammad Suleman',               'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'White 2',          'zone': 'Ghotki',                'territory': 'Mirpur Mathelo'},
    {'emp_code': '6015',  'name': 'Muhammad Hamid',                 'designation': 'SALES MANAGER',                          'region': 'Green 1',          'zone': 'Arif Wala & Vehari',    'territory': ''},
    {'emp_code': '6020',  'name': 'Imam Bux',                       'designation': 'AREA FARMER SERVICE MANAGER',            'region': 'White 2',          'zone': 'Dadu',                  'territory': 'Mehrabpur'},
    {'emp_code': '6067',  'name': 'Ghazanfar Ali',                  'designation': 'FARMER SERVICE MANAGER',                 'region': 'Blue',             'zone': 'Multan',                'territory': 'Khanewal'},
    {'emp_code': '6143',  'name': 'Muhammad Ahmad Rahman',          'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 2',          'zone': 'Sialkot',               'territory': 'Daska'},
    {'emp_code': '6242',  'name': 'Muhammad Shakeel',               'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Blue',             'zone': 'D.G Khan',              'territory': 'Bhakkar'},
    {'emp_code': '6294',  'name': 'Mudassar Ali Shah',              'designation': 'FARMER SERVICE MANAGER',                 'region': 'White 2',          'zone': 'Rahim Yar Khan',        'territory': 'Sadiqabad'},
    {'emp_code': '6331',  'name': 'Muhammad Asif',                  'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Blue',             'zone': 'MUZAFFAR GARH',         'territory': 'Kot Addu'},
    {'emp_code': '6337',  'name': 'Muhammad Akram',                 'designation': 'REGIONAL SALES MANAGER',                 'region': 'Blue',             'zone': 'Bahawalpur',            'territory': ''},
    {'emp_code': '6380',  'name': 'Muhammad Yasir',                 'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 3',          'zone': 'Faisalabad',            'territory': 'Shorkot'},
    {'emp_code': '6385',  'name': 'Jahanzeb',                       'designation': 'AREA FARMER SERVICE MANAGER',            'region': 'White 3',          'zone': 'Sukkur',                'territory': 'Shikarpur'},
    {'emp_code': '6388',  'name': 'Sajid Mehmood',                  'designation': 'ASST. ZONAL MANAGER',                    'region': 'Blue',             'zone': 'Bahawalnagar',          'territory': 'Bahawalnagar'},
    {'emp_code': '6390',  'name': 'Muhammad Rizwan Bashir',         'designation': 'ZONAL MANAGER',                          'region': 'Green 2',          'zone': 'Gujranwala',            'territory': ''},
    {'emp_code': '6398',  'name': 'Dildar Khan',                    'designation': 'SALES MANAGER',                          'region': 'Green 3',          'zone': 'Sargodha',              'territory': ''},
    {'emp_code': '6400',  'name': 'Ameer Ahmad',                    'designation': 'FARMER SERVICE MANAGER',                 'region': 'Blue',             'zone': 'Bahawalpur',            'territory': 'Zahir Pir'},
    {'emp_code': '6401',  'name': 'Javed Hussain',                  'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 1',          'zone': 'Pakpattan',             'territory': 'Noor Pur'},
    {'emp_code': '6407',  'name': 'Atta Ur Rehman',                 'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Green 3',          'zone': 'Sargodha',              'territory': 'Kot Moman'},
    {'emp_code': '6478',  'name': 'Sadam Hussain',                  'designation': 'FARMER SERVICE MANAGER',                 'region': 'Blue',             'zone': 'Bahawalnagar',          'territory': 'Fortabbas'},
    {'emp_code': '6484',  'name': 'Muhammad Rizwan',                'designation': 'SALES MANAGER',                          'region': 'Blue',             'zone': 'Multan',                'territory': ''},
    {'emp_code': '6537',  'name': 'Shahid Iqbal',                   'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 3',          'zone': 'Chiniot',               'territory': 'Chiniot'},
    {'emp_code': '6613',  'name': 'Sheikh Shahzeb Bin Khalid',      'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 3',          'zone': 'Peshawar',              'territory': 'TAXILA'},
    {'emp_code': '6644',  'name': 'Abdul Rehman Afzal',             'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Blue',             'zone': 'Bahawalpur',            'territory': 'Bahawalpur'},
    {'emp_code': '6666',  'name': 'Javed Iqbal',                    'designation': 'FARMER SERVICE MANAGER',                 'region': 'Blue',             'zone': 'MUZAFFAR GARH',         'territory': 'Jatoi'},
    {'emp_code': '6675',  'name': 'Muhammad Aslam',                 'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Green 1',          'zone': 'Pakpattan',             'territory': 'Haveli Lakha'},
    {'emp_code': '6678',  'name': 'Muhammad Bilal Saleem',          'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Green 2',          'zone': 'Sialkot',               'territory': 'Sialkot'},
    {'emp_code': '6693',  'name': 'Muhammad Ameen',                 'designation': 'FARMER SERVICE MANAGER',                 'region': 'White 2',          'zone': 'Dadu',                  'territory': 'Noshero Feroz'},
    {'emp_code': '6708',  'name': 'Muhammad Saleem',                'designation': 'FARMER SERVICE MANAGER',                 'region': 'Blue',             'zone': 'Bahawalnagar',          'territory': 'Minchenabad'},
    {'emp_code': '6712',  'name': 'Muhammad Anees',                 'designation': 'FARMER SERVICE MANAGER',                 'region': 'Blue',             'zone': 'D.G Khan',              'territory': 'Muhammad Pur'},
    {'emp_code': '6759',  'name': 'Khan Baig',                      'designation': 'FARMER SERVICE MANAGER',                 'region': 'White 3',          'zone': 'SUKKAR',                'territory': 'KASHMORE'},
    {'emp_code': '6776',  'name': 'Syed Muhammad Saqlain Shah',     'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Green 1',          'zone': 'Arifwala',              'territory': 'Mianchannu'},
    {'emp_code': '6809',  'name': 'Muhammad Zubair',                'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Green 3',          'zone': 'Chiniot',               'territory': 'Bhowana'},
    {'emp_code': '6830',  'name': 'Muhammad Bilal Lak',             'designation': 'FARMER SERVICE MANAGER',                 'region': 'Blue',             'zone': 'MUZAFFAR GARH',         'territory': 'Kot Addu'},
    {'emp_code': '6851',  'name': 'Muhammad Ayoub',                 'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 1',          'zone': 'Vehari',                'territory': 'Mailsi'},
    {'emp_code': '6904',  'name': 'Muhammad Shehroz Khan',          'designation': 'FARMER SERVICE MANAGER',                 'region': 'Blue',             'zone': 'D.G Khan',              'territory': 'Jampur'},
    {'emp_code': '6913',  'name': 'Touqeer Ahmad',                  'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Blue',             'zone': 'Bahawalpur',            'territory': 'Dunya Pur'},
    {'emp_code': '6930',  'name': 'Mohib Ullah',                    'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'GOLD',             'zone': 'QUETTA',                'territory': 'PASHIN'},
    {'emp_code': '6931',  'name': 'Abdul Wasay',                    'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'GOLD',             'zone': 'QUETTA',                'territory': 'LORALAI'},
    {'emp_code': '6937',  'name': 'Arshad Ali',                     'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 3',          'zone': 'Peshawar',              'territory': 'CHARSADA'},
    {'emp_code': '6940',  'name': 'Ahsan Ullah',                    'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'GOLD',             'zone': 'QUETTA',                'territory': 'QUETTA'},
    {'emp_code': '6943',  'name': 'Sana Ullah',                     'designation': 'FARMER SERVICE MANAGER',                 'region': 'Blue',             'zone': 'D.G Khan',              'territory': 'Fazil Pur'},
    {'emp_code': '6955',  'name': 'Assad Mahmood',                  'designation': 'FARMER SERVICE MANAGER',                 'region': 'Blue',             'zone': 'D.G Khan',              'territory': 'Choti'},
    {'emp_code': '6958',  'name': 'Basit Ali',                      'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 3',          'zone': 'Peshawar',              'territory': 'SWABI'},
    {'emp_code': '6964',  'name': 'Niaz Ahmad',                     'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Blue',             'zone': 'Bahawalpur',            'territory': 'R.Y. Khan-2'},
    {'emp_code': '6966',  'name': 'Zeeshan Munir',                  'designation': 'FARMER SERVICE MANAGER',                 'region': 'White 2',          'zone': 'Rahim Yar Khan',        'territory': 'Khan Pur'},
    {'emp_code': '6984',  'name': 'Rana Khalid Mehmood',            'designation': 'BUSINESS MANAGER',                       'region': 'White 1',          'zone': 'HYDERABAD & NAWABSHAH', 'territory': ''},
    {'emp_code': '6994',  'name': 'Abdul Malik',                    'designation': 'REGIONAL SALES MANAGER',                 'region': 'White 1',          'zone': 'Nawabshah',             'territory': ''},
    {'emp_code': '6995',  'name': 'Muhammad Saeed',                 'designation': 'AREA FARMER SERVICE MANAGER',            'region': 'White 1',          'zone': 'Nawabshah',             'territory': 'Shahdadpur'},
    {'emp_code': '7007',  'name': 'Abdul Razaque',                  'designation': 'FARMER SERVICE MANAGER',                 'region': 'White 2',          'zone': 'Dadu',                  'territory': 'Dadu'},
    {'emp_code': '7025',  'name': 'Rab Dino',                       'designation': 'FARMER SERVICE MANAGER',                 'region': 'White 1',          'zone': 'Umerkot',               'territory': 'Sufi'},
    {'emp_code': '7029',  'name': 'Shafaqat Ali',                   'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 2',          'zone': 'Gujranwala',            'territory': 'Alipur Chatha'},
    {'emp_code': '7034',  'name': 'Tariq Imran',                    'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Green 3',          'zone': 'Jhang',                 'territory': 'Ahmad Pur Sial'},
    {'emp_code': '7041',  'name': 'Zain Ali',                       'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'White 3',          'zone': 'SUKKAR',                'territory': 'LARKANA'},
    {'emp_code': '7060',  'name': 'Riaz Ahmed Rahu',                'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'White 1',          'zone': 'Nawabshah',             'territory': 'Hala'},
    {'emp_code': '7070',  'name': 'Rao Aurangzaib',                 'designation': 'FARMER SERVICE MANAGER',                 'region': 'White 1',          'zone': 'Hyderabad',             'territory': 'Tando M. Khan'},
    {'emp_code': '7071',  'name': 'Syed Altaf Hussain Shah',        'designation': 'FARMER SERVICE MANAGER',                 'region': 'Blue',             'zone': 'D.G Khan',              'territory': 'Kot Mithan'},
    {'emp_code': '7123',  'name': 'Ishtiaq Ahmad',                  'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 2',          'zone': 'Lahore',                'territory': 'Pattoki'},
    {'emp_code': '7133',  'name': 'Sher Muhammad Jogi',             'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'White 2',          'zone': 'Dadu',                  'territory': 'Chundko'},
    {'emp_code': '7181',  'name': 'Shahzad Mustafa',                'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 1',          'zone': 'Arifwala',              'territory': 'Qabola'},
    {'emp_code': '7185',  'name': 'Hafiz Muhammad Mehmood',         'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Blue',             'zone': 'Multan',                'territory': 'Shujabad'},
    {'emp_code': '7196',  'name': 'Mujeeb Ishaq',                   'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 2',          'zone': 'Gujranwala',            'territory': 'Hafizabad'},
    {'emp_code': '7203',  'name': 'Usman Haider',                   'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 1',          'zone': 'Arifwala',              'territory': 'Sahiwal'},
    {'emp_code': '7225',  'name': 'Yasir Ali',                      'designation': 'FARMER SERVICE MANAGER',                 'region': 'Blue',             'zone': 'D.G Khan',              'territory': 'D.G Khan'},
    {'emp_code': '7236',  'name': 'Muzammil Hussain Khan',          'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 1',          'zone': 'Arifwala',              'territory': 'Chicha Watni'},
    {'emp_code': '7249',  'name': 'Nasir Javed Akhtar',             'designation': 'REGIONAL SALES MANAGER',                 'region': 'Blue',             'zone': 'Bhakkar',               'territory': ''},
    {'emp_code': '7252',  'name': 'Ijaz Ahmad',                     'designation': 'REGIONAL SALES MANAGER',                 'region': 'Green 1',          'zone': 'Pakpattan',             'territory': ''},
    {'emp_code': '7253',  'name': 'Muhammad Abid',                  'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Green 2',          'zone': 'Pakpattan',             'territory': 'Pakpattan-2'},
    {'emp_code': '7254',  'name': 'Sajid Ali',                      'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 1',          'zone': 'Vehari',                'territory': 'Gaggo'},
    {'emp_code': '7263',  'name': 'Muhammad Irshad',                'designation': 'FARMER SERVICE MANAGER',                 'region': 'White 1',          'zone': 'Mirpur Khas',           'territory': 'Umerkot'},
    {'emp_code': '7265',  'name': 'Rahil Ahmed',                    'designation': 'FARMER SERVICE MANAGER',                 'region': 'White 1',          'zone': 'Umerkot',               'territory': 'Umer Kot'},
    {'emp_code': '7268',  'name': 'Sikandar Ali Ujjan',             'designation': 'FARMER SERVICE MANAGER',                 'region': 'White 2',          'zone': 'Dadu',                  'territory': 'Gambat'},
    {'emp_code': '7270',  'name': 'Shahid Ul Karim',                'designation': 'REGIONAL SALES MANAGER',                 'region': 'White 1',          'zone': 'Hyderabad',             'territory': ''},
    {'emp_code': '7271',  'name': 'Muhammad Salih',                 'designation': 'FARMER SERVICE MANAGER',                 'region': 'White 1',          'zone': 'Nawab Shah',            'territory': 'Sakrand'},
    {'emp_code': '7272',  'name': 'Sajid Ali',                      'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 3',          'zone': 'Peshawar',              'territory': 'HAZRO'},
    {'emp_code': '7274',  'name': 'Bilal Ahmad Sajid',              'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 2',          'zone': 'Lahore',                'territory': 'Kasur'},
    {'emp_code': '7277',  'name': 'Sabzal Ali',                     'designation': 'FARMER SERVICE MANAGER',                 'region': 'Blue',             'zone': 'D.G Khan',              'territory': 'Rajan Pur'},
    {'emp_code': '7278',  'name': 'Muhammad Azam Bhutto',           'designation': 'FARMER SERVICE MANAGER',                 'region': 'White 2',          'zone': 'Ghotki',                'territory': 'Dharki'},
    {'emp_code': '7280',  'name': 'Ali Alamgir',                    'designation': 'FARMER SERVICE MANAGER',                 'region': 'White 1',          'zone': 'Umerkot',               'territory': 'Tando Allah Yar'},
    {'emp_code': '7284',  'name': 'Muhammad Arslan',                'designation': 'FARMER SERVICE MANAGER',                 'region': 'Blue',             'zone': 'Bhakkar',               'territory': 'Mianwali'},
    {'emp_code': '7292',  'name': 'Barket Ali',                     'designation': 'FARMER SERVICE MANAGER',                 'region': 'White 3',          'zone': 'SUKKAR',                'territory': 'Kandh Kot'},
    {'emp_code': '7297',  'name': 'Muhammad Mudassar Khan',         'designation': 'AREA FARMER SERVICE MANAGER',            'region': 'Green 2',          'zone': 'Gujranwala',            'territory': 'Gujranwala'},
    {'emp_code': '7299',  'name': 'Hamza Ashraf',                   'designation': 'AREA FARMER SERVICE MANAGER',            'region': 'Green 2',          'zone': 'Lahore',                'territory': 'Lahore'},
    {'emp_code': '7305',  'name': 'Ali Abbas',                      'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 1',          'zone': 'Arifwala',              'territory': 'Arifwala'},
    {'emp_code': '7307',  'name': 'Hafiz Ehsan Ullah Nazar',        'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Green 3',          'zone': 'FAISALABAD,JHANG',      'territory': ''},
    {'emp_code': '7308',  'name': 'Muhammad Ahmad Javed',           'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 3',          'zone': 'Faisalabad',            'territory': 'Kamalia'},
    {'emp_code': '7309',  'name': 'Abdul Razzaq',                   'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Green 1',          'zone': 'Vehari',                'territory': 'Mailsi-2'},
    {'emp_code': '7313',  'name': 'Muhammad Asif',                  'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Blue',             'zone': 'Bhakkar',               'territory': 'D.I Khan'},
    {'emp_code': '7314',  'name': 'Akhtiar Ali',                    'designation': 'FARMER SERVICE MANAGER',                 'region': 'White 2',          'zone': 'Ghotki',                'territory': 'Ghotki'},
    {'emp_code': '7316',  'name': 'Shafqat Rasool',                 'designation': 'AREA FARMER SERVICE MANAGER',            'region': 'Blue',             'zone': 'Multan',                'territory': 'Tibba Sultan Pur'},
    {'emp_code': '7318',  'name': 'Hamza Ijaz',                     'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 2',          'zone': 'Sialkot',               'territory': 'Pasrur'},
    {'emp_code': '7325',  'name': 'Muhammad Imran',                 'designation': 'FARMER SERVICE MANAGER',                 'region': 'Blue',             'zone': 'Bhakkar',               'territory': 'Piplan'},
    {'emp_code': '7335',  'name': 'Muhammad Afzaal',                'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 2',          'zone': 'Lahore',                'territory': 'Nankana'},
    {'emp_code': '7365',  'name': 'Muhammad Imran',                 'designation': 'AREA FARMER SERVICE MANAGER',            'region': 'Green 3',          'zone': 'Chiniot',               'territory': 'Silanwali'},
    {'emp_code': '7371',  'name': 'Haroon Arshad',                  'designation': 'FARMER SERVICE MANAGER',                 'region': 'White 2',          'zone': 'Rahim Yar Khan',        'territory': 'R. Y. Khan 1'},
    {'emp_code': '7372',  'name': 'Muhammad Sohaib',                'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 2',          'zone': 'Lahore',                'territory': 'Theeng Mor'},
    {'emp_code': '7374',  'name': 'Muhammad Amin',                  'designation': 'FARMER SERVICE MANAGER',                 'region': 'Green 1',          'zone': 'Vehari',                'territory': 'Vehari'},
    {'emp_code': '7377',  'name': 'Abdul Rafay',                    'designation': 'FARMER SERVICE MANAGER',                 'region': 'White 1',          'zone': 'Hyderabad',             'territory': 'Hyderabad'},
    {'emp_code': '7379',  'name': 'Zaheer Ahmed',                   'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'White 1',          'zone': 'Nawab Shah',            'territory': 'Sanghar'},
    {'emp_code': '7381',  'name': 'Muhammad Fayaz Ur Rasheed Qureshi', 'designation': 'REGIONAL SALES MANAGER',             'region': 'Blue',             'zone': 'D.G Khan',              'territory': ''},
    {'emp_code': '7384',  'name': 'Muhammad Afzal Nadeem',          'designation': 'ZONAL MANAGER',                          'region': 'Blue',             'zone': 'Bahawalnagar',          'territory': ''},
    {'emp_code': '7388',  'name': 'Sufyan Khalid',                  'designation': 'FARMER SERVICE MANAGER',                 'region': 'White 1',          'zone': 'Hyderabad',             'territory': 'Golarchi'},
    {'emp_code': '7392',  'name': 'Muhammad Akram',                 'designation': 'AREA FARMER SERVICE MANAGER',            'region': 'Green 3',          'zone': 'Sargodha',              'territory': 'Khushab'},
    {'emp_code': '7393',  'name': 'Muhammad Hamza Riaz',            'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Green 3',          'zone': 'Faisalabad',            'territory': 'Faisalabad'},
    {'emp_code': '7401',  'name': 'Ahsan Khan',                     'designation': 'AREA FARMER SERVICE MANAGER',            'region': 'Blue',             'zone': 'Bahawalpur',            'territory': 'Ahmed Pur East'},
    {'emp_code': '7403',  'name': 'Tahir Usman',                    'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Green 1',          'zone': 'Pakpattan',             'territory': 'DEPALPUR'},
    {'emp_code': '7405',  'name': 'Muhammad Zohaib',                'designation': 'FARMER SERVICE MANAGER',                 'region': 'White 1',          'zone': 'Hyderabad',             'territory': 'Matli'},
    {'emp_code': '7409',  'name': 'Imran Ali Khan',                 'designation': 'SENIOR FARMER SERVICE MANAGER',          'region': 'Green 3',          'zone': 'Faisalabad',            'territory': 'Samundari'},
    {'emp_code': '7418',  'name': 'Muhammad Salman',                'designation': 'AREA FARMER SERVICE MANAGER',            'region': 'Green 2',          'zone': 'Gujranwala',            'territory': 'Narang'},
    {'emp_code': '7423',  'name': 'Nauman Ur Rehman Chaudhry',      'designation': 'FARMER SERVICE MANAGER',                 'region': 'Blue',             'zone': 'Multan',                'territory': 'Multan'},
]

# ---------------------------------------------------------------------------
# Region name aliases: SAP spreadsheet name → local DB name
# DB uses GREEN (not GREEN-1) for "Green 1", GREEN-2 for "Green 2", etc.
# WHITE-1/-2/-3 for "White 1/2/3", BLUE, GOLD, etc.
# ---------------------------------------------------------------------------
REGION_ALIASES = {
    'GREEN 1':  'GREEN',
    'GREEN 2':  'GREEN-2',
    'GREEN 3':  'GREEN-3',
    'WHITE 1':  'WHITE-1',
    'WHITE 2':  'WHITE-2',
    'WHITE 3':  'WHITE-3',
    'BLUE':     'BLUE',
    'GOLD':     'GOLD',
    'PLATINUM': 'PLATINUM',
}


# Zone name aliases: spreadsheet name → local DB name
ZONE_ALIASES = {
    'ARIFWALA':     'ARIF WALA',
    'BAHAWALNAGAR': 'BAHAWAL NAGAR',
    'BHAKKAR':      'BHAKHAR',
    'NAWABSHAH':    'NAWAB SHAH',
    'SUKKUR':       'SUKKAR',
    'SUKKAR':       'SUKKAR',
    'D.G KHAN':     'D.G.KHAN',
    'D.G. KHAN':    'D.G.KHAN',
    'MIRPUR KHAS':  'BADIN',       # fallback if not found; will be caught as NO ZONE
    'RAHIM Y. K.':  'RAHIM YAR KHAN',
    'PAKPATTAN':    'Pakpattan',
}


def normalize_region(raw):
    upper = raw.upper().strip()
    return REGION_ALIASES.get(upper, upper)


def normalize_zone(raw):
    upper = raw.upper().strip()
    return ZONE_ALIASES.get(upper, raw)


def is_multi(value):
    """True if value covers multiple zones/regions (contains & or comma)."""
    return bool(value and ('&' in value or ',' in value))


def resolve_designation(name):
    """Get or create a DesignationModel by name (case-insensitive)."""
    obj = DesignationModel.objects.filter(name__iexact=name).first()
    if obj:
        return obj, False
    code = name[:20].upper().replace(' ', '_').replace('.', '').replace('-', '_')
    obj = DesignationModel.objects.create(
        name=name, code=code, level=10, is_active=True,
        description='Auto-created by sync_agri_designations.py',
    )
    return obj, True


def run():
    company = Company.objects.filter(Company_name='4B-AGRI').first()
    if not company:
        print("ERROR: Company '4B-AGRI / FOUR BROTHERS AGRI' not found in DB.")
        return

    print(f"Using company: {company.Company_name} (id={company.pk})\n")

    updated = not_found = desg_created = 0
    geo_miss = {'region': 0, 'zone': 0, 'territory': 0}

    for row in ROWS:
        emp = str(row['emp_code'])
        profile = SalesStaffProfile.objects.filter(employee_code=emp).first()
        if not profile:
            print(f"[NOT FOUND] {emp:6s}  {row['name']}")
            not_found += 1
            continue

        # -- Designation --
        desg, created = resolve_designation(row['designation'])
        if created:
            desg_created += 1
            print(f"  [NEW DESG] Created designation: {row['designation']}")
        profile.designation = desg
        profile.save(update_fields=['designation'])

        # -- Region --
        raw_r = (row.get('region') or '').strip()
        rg_assigned = False
        if raw_r and not is_multi(raw_r) and 'Region' not in raw_r:
            norm = normalize_region(raw_r)
            rg = Region.objects.filter(company=company, name__iexact=norm).first()
            if rg:
                profile.regions.clear()
                profile.regions.add(rg)
                rg_assigned = True
            else:
                geo_miss['region'] += 1
                print(f"  [NO REGION] {emp} '{raw_r}' → '{norm}' not in DB")

        # -- Zone --
        raw_z = (row.get('zone') or '').strip()
        zn_assigned = False
        if raw_z and not is_multi(raw_z):
            norm_z = normalize_zone(raw_z)
            zn = Zone.objects.filter(company=company, name__iexact=norm_z).first()
            if zn:
                profile.zones.clear()
                profile.zones.add(zn)
                zn_assigned = True
            else:
                geo_miss['zone'] += 1
                print(f"  [NO ZONE]   {emp} '{raw_z}' not in DB")

        # -- Territory --
        raw_t = (row.get('territory') or '').strip()
        tr_assigned = False
        if raw_t and not is_multi(raw_t):
            tr = Territory.objects.filter(company=company, name__icontains=raw_t).first()
            if tr:
                profile.territories.clear()
                profile.territories.add(tr)
                tr_assigned = True
            else:
                geo_miss['territory'] += 1
                print(f"  [NO TERR]   {emp} '{raw_t}' not in DB")

        geo_str = f"R={'✓' if rg_assigned else '·'}  Z={'✓' if zn_assigned else '·'}  T={'✓' if tr_assigned else '·'}"
        print(f"[OK] {emp:6s}  {row['name'][:35]:35s}  {row['designation'][:35]:35s}  {geo_str}")
        updated += 1

    print(f"\n{'='*70}")
    print(f"Updated : {updated}")
    print(f"Not found: {not_found}  (no SalesStaffProfile with that employee_code)")
    print(f"New designations created: {desg_created}")
    print(f"Geo misses → region:{geo_miss['region']}  zone:{geo_miss['zone']}  territory:{geo_miss['territory']}")
    print(f"{'='*70}")
    print("Done. No server restart needed.")


if __name__ == '__main__':
    run()

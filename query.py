import json
import requests
import csv
from pathlib import Path
import pandas as pd
import os
from enum import Enum
from datetime import date

#GRAPHQL_URL = 'https://testreservations.uncruise.com:3000/graphql'
GRAPHQL_URL = 'https://reservations.uncruise.com:3000/graphql'
GRAPHQL_PRIVATEURL = 'http://172.16.120.87:3000/graphql'
GRAPHQL_PRIVATEURL2 = 'http://172.16.120.87:3000/graphql'

# AWS - Private Network
#GRAPHQL_URL = 'http://172.16.120.87:3000/graphql'

class RecordType(Enum):
    CLIENT = 1
    AGENT = 2
    AGENCY = 3
    RESERVATION = 4
    CRUISE = 5
    CABIN = 6
    SHIP = 7
    RESERVATION_OTHER = 8

class RecordMode(Enum):
    UPDATE = 1
    DELETE = 2
    QUERY = 3
    SFPUSH = 4
    INSERT = 5

def main():

  import sys

  #
  # Required Parameters
  #

  record_type_input = str(sys.argv[1])
  record_mode_input = str(sys.argv[2])

  if len(sys.argv) < 3:
      print_log("Calling error - missing required inputs.  Expecting " +
              "RecordType RecordMode\n")
      return

  #print_log("\nIncoming required parameters: " +
  #        "RecordType: {} RecordMode: {} sys.argv {}\n"
  #        .format(record_type_input, record_mode_input, sys.argv))

  record_type = RecordType.RESERVATION
  if record_type_input == RecordType.AGENCY.name:
     record_type = RecordType.AGENCY
  elif record_type_input == RecordType.AGENT.name:
     record_type = RecordType.AGENT
  elif record_type_input == RecordType.CLIENT.name:
     record_type = RecordType.CLIENT
  elif record_type_input == RecordType.CRUISE.name:
     record_type = RecordType.CRUISE
  elif record_type_input == RecordType.CABIN.name:
     record_type = RecordType.CABIN

  record_mode = RecordMode.QUERY
  if record_mode_input == RecordMode.UPDATE.name:
     record_mode = RecordMode.UPDATE
  elif record_mode_input == RecordMode.DELETE.name:
     record_mode = RecordMode.DELETE
  elif record_mode_input == RecordMode.SFPUSH.name:
     record_mode = RecordMode.SFPUSH

  if record_mode_input == RecordMode.SFPUSH.name:

    if record_type == RecordType.AGENCY:

      process_salesforce_agencies(record_type, record_mode)       

    elif record_type == RecordType.AGENT:

      process_salesforce_agents(record_type, record_mode) 

    elif record_type == RecordType.CLIENT:

      process_salesforce_clients(record_type, record_mode)       

  else:

    if record_type == RecordType.CRUISE:

      process_inventory_cruise(record_type)
      process_inventory_shipcabin(RecordType.SHIP)

    elif record_type == RecordType.RESERVATION:

      from datetime import datetime, timedelta

      # Get the current time
      now = datetime.now()

      # Transfer and Flight linking happens in 2 different change events which is currently driven by SyncDate__c on Item which takes a day change to be updated the 2nd time
      number_days = 0.2

      delta_days_ago = now - timedelta(days=number_days)

      # Query by hour because as of 1/17/25 the day query is taking too long, investigating but until then do hour query
      if number_days <= 90:

        # Iterate from now to delta days ago, in 1-hour steps
        query_time = now
        while query_time > delta_days_ago:
            end_time = query_time.strftime("%Y-%m-%dT%H:%M:00")
            query_time -= timedelta(hours=1)
            start_time = query_time.strftime("%Y-%m-%dT%H:%M:00")

            process_seaware(record_type, record_mode, start_time, end_time)

      else:

        # Iterate from now to delta days ago, in 1-day steps
        query_time = now
        while query_time > delta_days_ago:
            end_time = query_time.strftime("%Y-%m-%dT%H:%M:00")
            query_time -= timedelta(days=1)
            start_time = query_time.strftime("%Y-%m-%dT%H:%M:00")

            process_seaware(record_type, record_mode, start_time, end_time)

      # Process Seaware Reservations
      full_filename = 'C:/repo/seaware-sync/output_csv/RESERVATION_InvoiceTotals.csv'
      process_bookings_other(full_filename, record_type, record_mode)

      # Process Salesforce Flagged Reservations
      full_filename = 'C:/repo/Salesforce-Exporter-Private/Clients/SEAWARE-BOOKINGS/Salesforce-Exporter/Clients/SEAWARE-BOOKINGS/Export/Booking-Prod.csv'
      process_bookings_salesforce(full_filename, record_type, record_mode)
      process_bookings_other(full_filename, record_type, record_mode)

    else:
      process_seaware(record_type, record_mode, '', '')

  exit

# Function to recursively process the JSON and create CSV for dictionaries and lists
def write_csv_for_level(data, level, parent_key="", depth=1):

    # If the data is neither a dictionary nor a list, skip it
    if not isinstance(data, (dict, list)):
        return
    
    # Prepare the filename based on level and parent key
    path = f"C:/repo/seaware-sync/output_csv/"
    filename = f"{path}level_{depth}_{parent_key}.csv" if parent_key else f"{path}level_{depth}.csv"
    
    # If data is a dictionary, flatten it
    rows = []
    if isinstance(data, dict):
        row = {}
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                # If the value is a dictionary or list, serialize it into a string
                row[key] = json.dumps(value)
            else:
                row[key] = value
        rows.append(row)

    # If data is a list, treat each item as a row
    elif isinstance(data, list):
        for item in data:
            row = {}
            if isinstance(item, (dict, list)):
                row["value"] = json.dumps(item)  # Serialize any dict or list into a string
            else:
                row["value"] = item
            rows.append(row)

    # Write the rows to a CSV file
    if rows:
        with open(filename, mode='w', newline='') as file:
            # Get fieldnames from the first row keys
            fieldnames = rows[0].keys()
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"CSV file for level {depth} written to {filename}")
    
    # Recursively process nested dictionaries and lists
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                # Call recursively for each nested dictionary or list
                write_csv_for_level(value, level, parent_key=key, depth=depth+1)
    elif isinstance(data, list):
        for index, item in enumerate(data):
            if isinstance(item, (dict, list)):
                # Call recursively for each item in the list if it's a dictionary or list
                write_csv_for_level(item, level, parent_key=f"{parent_key}_item{index+1}", depth=depth+1)

#####################################################
#
# get_graphql_url - 
#
#####################################################
def get_graphql_url():

  import socket
  import requests

  url_value = GRAPHQL_URL
  
  hostname = socket.gethostname()

  # Check for AMAZ server
  if 'AMAZ' in hostname:    
    url_value = GRAPHQL_PRIVATEURL

    try:
      response = requests.get(url_value, timeout=2)  # Adjust timeout as needed
      if not response.status_code == 200 and not response.status_code == 400:
        url_value = GRAPHQL_PRIVATEURL2

    except requests.exceptions.RequestException as e:
      url_value = GRAPHQL_PRIVATEURL2

  return url_value

#####################################################
#
# get_csv_dataframe - 
#
#####################################################
def get_csv_dataframe(full_filename):

  fileCheckPath = Path(full_filename)
  fileCheckExists = fileCheckPath.is_file()
  if not fileCheckExists:
     return []
  
  if os.path.exists(full_filename) and os.path.getsize(full_filename) > 0:
    try:
      data_frame = pd.read_csv(full_filename)

      # Check if the DataFrame has columns
      if not data_frame.empty:
       return data_frame
        
    except pd.errors.EmptyDataError:
        print_log(f"Error: The file {full_filename} is empty or doesn't contain valid data.")

    except Exception as e:
        print_log(f"An error occurred: {e}")

  return []

#####################################################
#
# login_graphql - 
#
#####################################################
def print_log(log_message):
  
  import datetime

  current_datetime = datetime.datetime.now()
  formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
  print(formatted_datetime + ' : ' + log_message)

#####################################################
#
# login_graphql - 
#
#####################################################
def login_graphql():
   
  login = """
mutation login {

  login(role:Internal ) {
    token
  }
}
"""

  token = None

  response = requests.post(url=get_graphql_url(), json={"query": login}) 

  if response.status_code == 200:
    data = response.json()
    token = data['data']['login']['token']
  else:
    print_log(f"login_graphql: {response.status_code} {response.text}")
    #raise Exception(f"login_graphql: {response.status_code} {response.text}")
    
  headers = {
    'Authorization': f'Bearer {token}'
  }

  return headers

#####################################################
#
# login_graphql - 
#   (Authorization: Bearer xxx HTTP header) token on the logout mutation needs to match the header received on the login
#   Logout operation should be dropping all the session locks by design
#
#####################################################
def logout_graphql(headers):
   
  logout = """
mutation logout {

  logout
}
"""

  response = requests.post(url=get_graphql_url(), json={"query": logout}, headers=headers) 

  if response.status_code != 200:
    print_log(f"logout_graphql: {response.status_code} {response.text}")
    #raise Exception(f"logout_graphql failed: {response.status_code} {response.text}")
    
#####################################################
#
# process_salesforce_clients - 
#
#####################################################
def process_salesforce_clients(record_type, record_mode):
    
  import pandas as pd
  import math
  import os

  full_filename = 'C:/repo/Salesforce-Exporter-Private/Clients/SEAWARE/Salesforce-Exporter/Clients/SEAWARE/Export/Contact-Prod.csv'

  data_frame = get_csv_dataframe(full_filename)
  if len(data_frame) <= 0:
    return
  
  processed_ids = ''
  full_filename_processed = 'C:/repo/seaware-sync/output_csv/' + record_type.name + '_processed.csv'
  if os.path.exists(full_filename_processed):
    with open(full_filename_processed, 'r') as file:
        processed_ids = file.read()

  for index, row in data_frame.iterrows():

      row = row.apply(lambda x: x.strip("b'") if isinstance(x, str) else x)

      if row['Contact_Type__c'] != 'Guest':
         continue

      id_value = row['Seaware_Id__c']

      # Check for None or len less than 8 (nan is len 3)
      if row['Seaware_Id__c'] == None or len(str(row['Seaware_Id__c'])) <= 8:

        # Query to setup output file for processing in Excel PowerQuery update to SF
        json_res = process_seaware(record_type, RecordMode.QUERY, '', '', row)

        # Check if record found in Seaware by Customer ID
        if len(json_res.get('data').get('clients').get('edges')) <= 0:

          # Check if record found in Seaware by Lookup - FirstName, LastName, DOB
          json_res = process_seaware_bylookup(record_type, RecordMode.QUERY, row)

        # Check if record found in Seaware by Customer ID or Lookup
        if len(json_res.get('data').get('clients').get('edges')) <= 0:

          # Attempt to insert - Seaware DB will fail call if altid already set on a record
          response = insert_row_client(record_type, RecordMode.INSERT, row)

          data = response.json()
          if 'errors' in data:
            continue

          # Query to setup output file for processing in Excel PowerQuery update to SF
          json_res = process_seaware(record_type, RecordMode.QUERY, '', '', row)

        id_value = json_res.get('data').get('clients').get('edges')[0].get('node').get('id')

        if id_value in processed_ids:
          continue        

      else:
          
        id_value = str(id_value)

        if id_value in processed_ids:
          continue        

        # Query to setup output file for processing in Excel PowerQuery update to SF
        json_res = process_seaware(record_type, RecordMode.QUERY, '', '', row)

      # Update Request for complete field updates
      update_row_client(record_type, RecordMode.UPDATE, row, id_value)

      with open(full_filename_processed, 'a+', newline='') as processed_file:
        processed_file.write(id_value + ',')

def process_bookings_salesforce(full_filename, record_type, record_mode):
    
  import pandas as pd
  import math

  fileCheckPath = Path(full_filename)
  fileCheckExists = fileCheckPath.is_file()
  if not fileCheckExists:
     return

  data_frame = get_csv_dataframe(full_filename)
  if len(data_frame) <= 0:
    return

  queries_remaining = 500
  for index, row in data_frame.iterrows():

    row = row.apply(lambda x: x.strip("b'") if isinstance(x, str) else x)

    booking_number_seaware = row['Booking_Number_Seaware__c']
    if booking_number_seaware == '' or (not isinstance(booking_number_seaware, str) and math.isnan(booking_number_seaware)):

      continue

    # Process single reservation
    if not isinstance(booking_number_seaware, str):
      booking_number_seaware = str(math.floor(booking_number_seaware))

    process_seaware(record_type, record_mode, id_value = 'Reservation|' + booking_number_seaware)

    queries_remaining -= 1
    if queries_remaining <= 0:
      break

def process_bookings_other(full_filename, record_type, record_mode):
    
  import pandas as pd
  import math

  fileCheckPath = Path(full_filename)
  fileCheckExists = fileCheckPath.is_file()
  if not fileCheckExists:
     return

  data_frame = get_csv_dataframe(full_filename)
  if len(data_frame) <= 0:
    return

  queries_remaining = 500
  for index, row in data_frame.iterrows():

    row = row.apply(lambda x: x.strip("b'") if isinstance(x, str) else x)

    booking_number_seaware = ''
    if 'Salesforce' in full_filename:
      booking_number_seaware = row['Booking_Number_Seaware__c']
    
    else:
      booking_number_seaware = clean_value(row['reservation'])

    if booking_number_seaware == '' or (not isinstance(booking_number_seaware, str) and math.isnan(booking_number_seaware)):

      continue

    # Process single reservation
    if not isinstance(booking_number_seaware, str):
      booking_number_seaware = str(math.floor(booking_number_seaware))

    # Process single reservation other
    process_seaware(RecordType.RESERVATION_OTHER, record_mode, id_value = 'Reservation|' + str(booking_number_seaware))

    queries_remaining -= 1
    if queries_remaining <= 0:
      break

def process_salesforce_agents(record_type, record_mode):
    
  import pandas as pd

  full_filename = 'C:/repo/Salesforce-Exporter-Private/Clients/SEAWARE/Salesforce-Exporter/Clients/SEAWARE/Export/Contact-Prod.csv'
  fileCheckPath = Path(full_filename)
  fileCheckExists = fileCheckPath.is_file()
  if not fileCheckExists:
     return

  data_frame = get_csv_dataframe(full_filename)
  if len(data_frame) <= 0:
    return

  processed_ids = ''
  full_filename_processed = 'C:/repo/seaware-sync/output_csv/' + record_type.name + '_processed.csv'
  if os.path.exists(full_filename_processed):
    with open(full_filename_processed, 'r') as file:
        processed_ids = file.read()

  for index, row in data_frame.iterrows():

      row = row.apply(lambda x: x.strip("b'") if isinstance(x, str) else x)

      if row['Contact_Type__c'] != 'Representative':
         continue

      # Query to setup output file for processing in Excel PowerQuery update to SF
      json_res = process_seaware(record_type, RecordMode.QUERY, '', '', row)

      if len(json_res.get('data').get('travelAgents').get('edges')) <= 0:

        # Attempt to insert - Seaware DB will fail call if altid already set on a record
        response = insert_row_agent(record_type, RecordMode.INSERT, row)

        data = response.json()
        if 'errors' in data:
          continue

        # Query to setup output file for processing in Excel PowerQuery update to SF
        json_res = process_seaware(record_type, RecordMode.QUERY, '', '', row)

      id_value = json_res.get('data').get('travelAgents').get('edges')[0].get('node').get('id')

      if id_value in processed_ids:
        continue        

      # Update Request for complete field updates
      update_row_agent(record_type, RecordMode.UPDATE, row, id_value)

      with open(full_filename_processed, 'a+', newline='') as processed_file:
        processed_file.write(id_value + ',')

def process_inventory_cruise(record_type):
    
  import pandas as pd

  # Get Available Voyages
  json_res = process_seaware(record_type, RecordMode.QUERY, '', '')
  voyages = json_res.get('data').get('availableVoyages')
  for voyage in voyages:

    # Get Available Cabins
    json_res = process_seaware(RecordType.CABIN, RecordMode.QUERY, '', '', voyage)
#    cabins = json_res.get('data').get('availableCabins')

def process_inventory_shipcabin(record_type):
    
  import pandas as pd

  # Get all Cabins by Ship
  json_res = process_seaware(record_type, RecordMode.QUERY, '', '')

def process_salesforce_agencies(record_type, record_mode):
    
  import pandas as pd

  full_filename = 'C:/repo/Salesforce-Exporter-Private/Clients/SEAWARE/Salesforce-Exporter/Clients/SEAWARE/Export/Contact-Prod.csv'
  fileCheckPath = Path(full_filename)
  fileCheckExists = fileCheckPath.is_file()
  if not fileCheckExists:
     return

  data_frame = get_csv_dataframe(full_filename)
  if len(data_frame) <= 0:
    return

  processed_ids = ''
  full_filename_processed = 'C:/repo/seaware-sync/output_csv/' + record_type.name + '_processed.csv'
  if os.path.exists(full_filename_processed):
    with open(full_filename_processed, 'r') as file:
        processed_ids = file.read()

  for index, row in data_frame.iterrows():

      row = row.apply(lambda x: x.strip("b'") if isinstance(x, str) else x)

      if row['Contact_Type__c'] != 'Representative':
         continue

      # Query to setup output file for processing in Excel PowerQuery update to SF
      json_res = process_seaware(record_type, RecordMode.QUERY, '', '', row)

      if len(json_res.get('data').get('agencies').get('edges')) <= 0:

        # Attempt to insert - Seaware DB will fail call if altid already set on a record
        response = insert_row_agency(record_type, RecordMode.INSERT, row)

        data = response.json()
        if 'errors' in data:
          continue

        # Query to setup output file for processing in Excel PowerQuery update to SF
        json_res = process_seaware(record_type, RecordMode.QUERY, '', '', row)

      id_value = json_res.get('data').get('agencies').get('edges')[0].get('node').get('id')

      if id_value in processed_ids:
        continue        

      # Update Request for complete field updates
      update_row_agency(record_type, RecordMode.UPDATE, row, id_value)

      with open(full_filename_processed, 'a+', newline='') as processed_file:
        processed_file.write(id_value + ',')

def process_seaware(record_type, record_mode, fromDateTime = None, toDateTime = None, row = None, id_value = None): 

  # Record Types
  record_type_value = 'reservationHistory'
  if record_type == RecordType.CLIENT:
    record_type_value = 'clients'
  elif record_type == RecordType.AGENT:
    record_type_value = 'travelAgents'
  elif record_type == RecordType.AGENCY:
    record_type_value = 'agencies'
  elif record_type == RecordType.CRUISE:
    record_type_value = 'availableVoyages'
  elif record_type == RecordType.CABIN:
    record_type_value = 'availableCabins'
  elif record_type == RecordType.SHIP:
    record_type_value = 'cabins'
  elif record_type == RecordType.RESERVATION_OTHER:
    record_type_value = 'reservation'

  headers = login_graphql()

  # Initial request - no cursor
  json_res = fetch_items(record_type, record_mode, fromDateTime, toDateTime, headers, row, id_value=id_value)
  if "errors" in json_res:
    return json_res
  
  incoming_items = len(json_res.get('data').get(record_type_value))

  if record_type != RecordType.CRUISE and record_type != RecordType.CABIN and record_type != RecordType.SHIP and record_type != RecordType.RESERVATION_OTHER:
    incoming_items = len(json_res.get('data').get(record_type_value).get('edges'))
  
  print_log("Initial Query - incoming_items: " + str(incoming_items))     
  if incoming_items >= 500:   
    print_log("CAUTION: Initial Query is 500 which is the MAX result set even with paging, reduce query logic.  incoming_items: " + str(incoming_items)) 

  if incoming_items > 0:
    if record_type != RecordType.CRUISE and record_type != RecordType.CABIN and record_type != RecordType.SHIP and record_type != RecordType.RESERVATION_OTHER:
      print_log(json_res.get('data').get(record_type_value).get('edges')[0].get('node').get('id'))
    elif record_type == RecordType.RESERVATION_OTHER:
      print_log(json_res['data']['reservation']['result']['id'])

  page_info = None

  if record_type_value in json_res['data']: 
    process_record(record_type, record_type_value, record_mode, json_res, row)

    if record_type != RecordType.CRUISE and record_type != RecordType.CABIN and record_type != RecordType.SHIP and record_type != RecordType.RESERVATION_OTHER:
      page_info = json_res['data'][record_type_value]['pageInfo']

  else:
    print_log("unknown response type")
    return json_res

  # Check for next page - max query is total of 500 regardless of the paging request size
  #
  while page_info != None and page_info['hasNextPage'] and incoming_items > 0:
    
    cursor = page_info['endCursor']
    access_token = json_res['extensions']['access_token']
    json_res = fetch_items(record_type, record_mode, fromDateTime, toDateTime, headers, row, cursor, access_token, id_value) 

    # Max query is 500 so if deleting or paging update then just restart the query
    #json_res = fetch_items(record_type, record_mode, fromDateTime, toDateTime, row) 

    incoming_items = len(json_res.get('data').get(record_type_value).get('edges'))

    if incoming_items > 0:   
      print_log("Paging Query - incoming_items: " + str(incoming_items))        

      if record_type != RecordType.CRUISE and record_type != RecordType.CABIN and record_type != RecordType.SHIP and record_type != RecordType.RESERVATION_OTHER:
        print_log(json_res.get('data').get(record_type_value).get('edges')[0].get('node').get('id'))
        #print_log("cursor: " + cursor + " access_token: " + access_token + " incoming_items: " + str(incoming_items))        
        
      if record_type_value in json_res['data']: 
        process_record(record_type, record_type_value, record_mode, json_res, row)
        page_info = json_res['data'][record_type_value]['pageInfo']

      else:
        print_log("unknown query type")       

  logout_graphql(headers)

  # Start the process with the root JSON data
#  if 'reservationHistory' in json_res.get('data'):
#    write_csv_for_level(json_res.get('data').get('reservationHistory').get('edges'), level=1)
#  else:
#    write_csv_for_level(json_res.get('data').get('reservation').get('result'), level=1)

  return json_res

def process_seaware_bylookup(record_type, record_mode, row = None): 

  # Record Types
  record_type_value = 'reservations'
  if record_type == RecordType.CLIENT:
    record_type_value = 'clients'
  elif record_type == RecordType.AGENT:
    record_type_value = 'travelAgents'
  elif record_type == RecordType.AGENCY:
    record_type_value = 'agencies'

  headers = login_graphql()

  # Initial request - no cursor
  json_res = fetch_items_bylookup(record_type, record_mode, headers, row)
  page_info = None

  if record_type_value in json_res['data']: 
    process_record(record_type, record_type_value, record_mode, json_res, row)
    page_info = json_res['data'][record_type_value]['pageInfo']

  else:
    print_log("unknown response type")
    return json_res

  # Check for next page - max query is total of 500 regardless of the paging request size
  #
  while page_info['hasNextPage']:
    
    cursor = page_info['endCursor']
    access_token = json_res['extensions']['access_token']
    json_res = fetch_items_bylookup(record_type, record_mode, headers, row, cursor, access_token) 

    # Max query is 500 so if deleting or paging update then just restart the query
    #json_res = fetch_items(record_type, record_mode, fromDateTime, toDateTime, row) 

    incoming_items = len(json_res.get('data').get(record_type_value).get('edges'))
    print_log("cursor: " + cursor + " access_token: " + access_token + " incoming_items: " + str(incoming_items))        
      
    if record_type_value in json_res['data']: 
      process_record(record_type, record_type_value, record_mode, json_res, row)
      page_info = json_res['data'][record_type_value]['pageInfo']

    else:
      print_log("unknown query type")       

  logout_graphql(headers)

  return json_res

#####################################################
#
# get_safe_string - 
#
#####################################################
def get_safe_string(string_value):

  string_value = string_value.replace(' ', '')
  return string_value

#####################################################
#
# get_safe_phone - 
#
#####################################################
def get_safe_phone(string_value):

  phone_number_string = get_safe_string(string_value)
  found_alpha = any(char.isalpha() for char in phone_number_string)

  if found_alpha:
    return ''
  
  return phone_number_string

#####################################################
#
# update_record - update a specific record by id, update isInternal on all records because that is
#   used as the workaround flag for paging
#
#####################################################
def update_record_paging(record_type, id_value, access_token):
   
  query = "Unknown"
  with open('C:/repo/seaware-sync/queries/update_paging.graphQL', 'r') as file:
    query = file.read()

  query = query.replace('RECORDID_VALUE', id_value)

  # Record Types
  record_type_value = 'reservation'
  if record_type == RecordType.CLIENT:
     record_type_value = 'client'
  elif record_type == RecordType.AGENT:
     record_type_value = 'travelAgent'
  elif record_type == RecordType.AGENCY:
     record_type_value = 'agency'

  query = query.replace('RECORD_TYPE', record_type_value)    

  headers = {
    'Authorization': f'Bearer {access_token}'
  }

  response = requests.post(url=get_graphql_url(), json={"query": query}, headers=headers) 
  
  if response.status_code != 200:
    print_log(f"update_record_paging: {response.status_code} {response.text}")
    #raise Exception(f"update_record_paging: {response.status_code} {response.text}")
  
  elif not '"operationResult":"OK"' in response.text:
     
     print_log(response.text)

     # Add Id to skip queue
     return id_value

  return None

#####################################################
#
# insert_row_client - insert a specific client row
#
#####################################################
def insert_row_client(record_type, record_mode, row):

  print_log('insert_row_client - ' + str(row['FirstName']).strip() + ' ' + str(row['LastName']))

  query = "Unknown"
  with open('C:/repo/seaware-sync/queries/insert_row_' + record_type.name.lower() + '.graphQL', 'r') as file:
    query = file.read()

  # Id	Name	CustomerID__c	Seaware_Id__c	FirstName	LastName	Email	MiddleName	Title
  query = query.replace('ALTID_VALUE', str(row['CustomerID__c']))

  safeValue = ''
  if not pd.isna(row['FirstName']) and not str(row['FirstName']).strip() == '':
    safeValue = row['FirstName']
  
  query = query.replace('FIRSTNAME_VALUE', safeValue)
  query = query.replace('LASTNAME_VALUE', str(row['LastName']))

  safeValue = ''
  if not pd.isna(row['Email']) and not str(row['Email']).strip() == '':
    safeValue = row['Email']

  query = query.replace('EMAIL_VALUE', safeValue)

  safeValue = ''
  if not pd.isna(row['Phone']) and not get_safe_phone(str(row['Phone'])) == '':
    safeValue = get_safe_phone(str(row['Phone']))
    primary_phonenumber_json = '{type:{key:"PRIMARY"} intlCode:1 number:"PRIMARY_PHONENUMBER"}'
    query = query.replace('PRIMARY_PHONENUMBER', primary_phonenumber_json)
  
  query = query.replace('PRIMARY_PHONENUMBER', safeValue)

  safeValue = ''
  if not pd.isna(row['MobilePhone']) and not get_safe_phone(str(row['MobilePhone'])) == '':
    safeValue = get_safe_phone(str(row['MobilePhone']))
    mobile_phonenumber_json = '{type:{key:"MOBILE"} intlCode:1 number:"MOBILE_PHONENUMBER"}'
    query = query.replace('MOBILE_PHONENUMBER', mobile_phonenumber_json)
  
  query = query.replace('MOBILE_PHONENUMBER', safeValue)

  safeValue = ''
  if not pd.isna(row['Birthdate']) and not str(row['Birthdate']).strip() == '':
    safeValue = row['Birthdate']

  query = query.replace('BIRTHDAY_VALUE', safeValue)

  safeValue = ''
  if not pd.isna(row['Gender__c']) and not str(row['Gender__c']).strip() == '':
    safeValue = row['Gender__c'][0]
    
  if safeValue == '':
    query = query.replace('gender: GENDER_VALUE', '')
  else:
    query = query.replace('GENDER_VALUE', safeValue)

  headers = login_graphql()

  response = requests.post(url=get_graphql_url(), json={"query": query}, headers=headers) 
  if response.status_code != 200:
    print_log(f"insert_row_client: {response.status_code} {response.text}")
    #raise Exception(f"insert_row_client: {response.status_code} {response.text}")
  
  # Check for errors
  data = response.json()
  if 'errors' in data:
    error_log = data['errors']
    print_log(error_log[0].get('message'))
    #raise Exception(f"insert_row_client: {error_log[0].get('message')}")

  logout_graphql(headers)
    
  return response

#####################################################
#
# update_row_client - update a specific client row
#
#####################################################
def update_row_client(record_type, record_mode, row, id_value):

  print_log('update_row_client - ' + str(row['FirstName']).strip() + ' ' + str(row['LastName']))

  query = "Unknown"
  with open('C:/repo/seaware-sync/queries/update_row_' + record_type.name.lower() + '.graphQL', 'r') as file:
    query = file.read()

  # Id	Name	CustomerID__c	Seaware_Id__c	FirstName	LastName	Email	MiddleName	Title
  query = query.replace('CLIENTID_VALUE', id_value)
  query = query.replace('ALTID_VALUE', str(row['CustomerID__c']))

  safeValue = ''
  if not pd.isna(row['FirstName']) and not str(row['FirstName']).strip() == '':
    safeValue = row['FirstName']

  query = query.replace('FIRSTNAME_VALUE', safeValue)
  query = query.replace('LASTNAME_VALUE', str(row['LastName']))

  safeValue = ''
  if not pd.isna(row['Email']) and not str(row['Email']).strip() == '':
    safeValue = row['Email']

  query = query.replace('EMAIL_VALUE', safeValue)

  safeValue = ''
  if not pd.isna(row['Phone']) and not get_safe_string(str(row['Phone'])) == '':
    safeValue = get_safe_string(str(row['Phone']))
    primary_phonenumber_json = '{type:{key:"PRIMARY"} intlCode:1 number:"PRIMARY_PHONENUMBER"}'
    query = query.replace('PRIMARY_PHONENUMBER', primary_phonenumber_json)
  
  query = query.replace('PRIMARY_PHONENUMBER', safeValue)

  safeValue = ''
  if not pd.isna(row['MobilePhone']) and not get_safe_string(str(row['MobilePhone'])) == '':
    safeValue = get_safe_string(str(row['MobilePhone']))
    mobile_phonenumber_json = '{type:{key:"MOBILE"} intlCode:1 number:"MOBILE_PHONENUMBER"}'
    query = query.replace('MOBILE_PHONENUMBER', mobile_phonenumber_json)
  
  query = query.replace('MOBILE_PHONENUMBER', safeValue)

  safeValue = ''
  if not pd.isna(row['Birthdate']) and not str(row['Birthdate']).strip() == '':
    safeValue = row['Birthdate']

  query = query.replace('BIRTHDAY_VALUE', safeValue)

  safeValue = ''
  if not pd.isna(row['Gender__c']) and not str(row['Gender__c']).strip() == '':
    safeValue = row['Gender__c'][0]
    
  if safeValue == '':
    query = query.replace('gender: GENDER_VALUE', '')
  else:
    query = query.replace('GENDER_VALUE', safeValue)
     
  safeValue = 'REGULAR'
  # Need to exactly map the Salesforce Passenger Type values to the Guest Type values in Seaware
  #if not pd.isna(row['Passenger_Type__c']) and not str(row['Passenger_Type__c']).strip() == '':
  #  safeValue = round(row['Passenger_Type__c'])

  query = query.replace('GUESTTYPE_VALUE', str(safeValue))

  headers = login_graphql()

  response = requests.post(url=get_graphql_url(), json={"query": query}, headers=headers) 
  if response.status_code != 200:
    print_log(f"update_row_client: {response.status_code} {response.text}")
    #raise Exception(f"update_row_client: {response.status_code} {response.text}")

  # Check for errors
  data = response.json()
  if 'errors' in data:
    error_log = data['errors']
    print_log(error_log[0].get('message'))
    #raise Exception(f"update_row_client: {error_log[0].get('message')}")

  logout_graphql(headers)

  return response

#####################################################
#
# insert_row_agent - insert a specific agent row
#
#####################################################
def insert_row_agent(record_type, record_mode, row):
   
  print_log('insert_row_agent - ' + str(row['FirstName']).strip() + ' ' + str(row['LastName']))

  query = "Unknown"
  with open('C:/repo/seaware-sync/queries/insert_row_' + record_type.name.lower() + '.graphQL', 'r') as file:
    query = file.read()

  # Columns: Id	Name	FirstName	LastName	Email	RepresentativeID__c
  query = query.replace('ALTID_VALUE', str(row['RepresentativeID__c']))

  safeValue = ''
  if not pd.isna(row['FirstName']) and not str(row['FirstName']).strip() == '':
    safeValue = row['FirstName']

  query = query.replace('FIRSTNAME_VALUE', safeValue)
  query = query.replace('LASTNAME_VALUE', str(row['LastName']))

  headers = login_graphql()

  response = requests.post(url=get_graphql_url(), json={"query": query}, headers=headers) 
  if response.status_code != 200:
    print_log(f"insert_row_agent: {response.status_code} {response.text}")
    #raise Exception(f"insert_row_agent: {response.status_code} {response.text}")

  # Check for errors
  data = response.json()
  if 'errors' in data:
    error_log = data['errors']
    print_log(error_log[0].get('message'))
    #raise Exception(f"insert_row_agent: {error_log[0].get('message')}")

  logout_graphql(headers)

  return response

#####################################################
#
# update_row_agent - update a specific agent row
#
#####################################################
def update_row_agent(record_type, record_mode, row, id_value):

  print_log('update_row_agent - ' + str(row['FirstName']).strip() + ' ' + str(row['LastName']))

  query = "Unknown"
  with open('C:/repo/seaware-sync/queries/update_row_' + record_type.name.lower() + '.graphQL', 'r') as file:
    query = file.read()

  # Columns: Id	Name	FirstName	LastName	Email	RepresentativeID__c
  query = query.replace('AGENTID_VALUE', id_value)

  safeValue = ''
  if not pd.isna(row['FirstName']) and not str(row['FirstName']).strip() == '':
    safeValue = row['FirstName']

  query = query.replace('FIRSTNAME_VALUE', safeValue)
  query = query.replace('LASTNAME_VALUE', str(row['LastName']))

  safeValue = ''
  if not pd.isna(row['Email']) and not str(row['Email']).strip() == '':
    safeValue = row['Email']

  query = query.replace('EMAIL_VALUE', safeValue)

  safeValue = ''
  if not pd.isna(row['Account.Seaware_Id__c']) and not str(row['Account.Seaware_Id__c']).strip() == '':
    safeValue = str(row['Account.Seaware_Id__c'])
  else:
    print_log('Agency missing Seaware Id so skipping Agent')
    # No Agency Seaware Id so kick out and wait for one
    return

  query = query.replace('AGENCYKEY_VALUE', str(safeValue))

  headers = login_graphql()

  response = requests.post(url=get_graphql_url(), json={"query": query}, headers=headers) 
  if response.status_code != 200:
    print_log(f"update_row_agent: {response.status_code} {response.text}")
    #raise Exception(f"update_row_agent: {response.status_code} {response.text}")

  # Check for errors
  data = response.json()
  if 'errors' in data:
    error_log = data['errors']
    print_log(error_log[0].get('message'))
    #raise Exception(f"update_row_agent: {error_log[0].get('message')}")

  logout_graphql(headers)

  return response

#####################################################
#
# insert_row_agency - insert a specific agency row
#
#####################################################
def insert_row_agency(record_type, record_mode, row):

  print_log('insert_row_agency - ' + str(row['Account.Name']))

  query = "Unknown"
  with open('C:/repo/seaware-sync/queries/insert_row_' + record_type.name.lower() + '.graphQL', 'r') as file:
    query = file.read()

  # Id	Name	CustomerID__c	Seaware_Id__c	FirstName	LastName	Email	MiddleName	Title
  query = query.replace('ALTID_VALUE', str(row['Account.AgencyID__c']))
  query = query.replace('NAME_VALUE', str(row['Account.Name']))

  headers = login_graphql()

  response = requests.post(url=get_graphql_url(), json={"query": query}, headers=headers) 
  if response.status_code != 200:
    print_log(f"insert_row_agency: {response.status_code} {response.text}")
    #raise Exception(f"insert_row_agency: {response.status_code} {response.text}")

  # Check for errors
  data = response.json()
  if 'errors' in data:
    error_log = data['errors']
    print_log(error_log[0].get('message'))
    #raise Exception(f"insert_row_agency: {error_log[0].get('message')}")

  logout_graphql(headers)

  return response

#####################################################
#
# update_row_agency - update a specific agency row
#
#####################################################
def update_row_agency(record_type, record_mode, row, id_value):

  print_log('update_row_agency - ' + str(row['Account.Name']))

  # Check to ignore the UnCruise Agency 
  if 'UnCruise' in row['Account.Name']:
    return

  query = "Unknown"
  with open('C:/repo/seaware-sync/queries/update_row_' + record_type.name.lower() + '.graphQL', 'r') as file:
    query = file.read()

  # Columns: Id	Name	AgencyID__c	Seaware_Id__c	AgencyType__c	Consortium__c	Consortium_Start_Date__c	Consortium_End_Date__c	IATA_Number__c
  query = query.replace('AGENCYID_VALUE', id_value)
  query = query.replace('AGENCYNAME_VALUE', str(row['Account.Name']))  
  agency_type = str(row['Account.AgencyType__c'])
  query = query.replace('AGENGYTYPE_VALUE', agency_type)

  consortium = ''
  is_consortium = 'false'
  if not pd.isna(row['Account.Consortium__c']) and not str(row['Account.Consortium__c']).strip() == '':
    is_consortium = 'true'
    consortium = row['Account.Consortium__c']

  query = query.replace('CONSORTIUMTYPE_VALUE', consortium)
  query = query.replace('ISCONORTIUM_VALUE', is_consortium)

  fp_rat_gross = 'false'
  if agency_type == 'A' or agency_type == 'Y' or agency_type == 'P':
    fp_rat_gross = 'true'

  force_gross = row['Account.Force_Gross_Pay__c']
  if force_gross:
    fp_rat_gross = 'true'

  force_net = row['Account.Force_NET_Pay__c']
  if force_net:
      fp_rat_gross = 'false'
 
  query = query.replace('FPRATGROSS_VALUE', fp_rat_gross)

  iata = ''
  if not pd.isna(row['Account.IATA_Number__c']) and not str(row['Account.IATA_Number__c']).strip() == '':
     iata = str(row['Account.IATA_Number__c'])

  query = query.replace('IATA_VALUE', iata)

  headers = login_graphql()

  response = requests.post(url=get_graphql_url(), json={"query": query}, headers=headers) 
  if response.status_code != 200:
    print_log(f"update_row_agency: {response.status_code} {response.text}")
    #raise Exception(f"update_row_agency: {response.status_code} {response.text}")

  # Check for errors
  data = response.json()
  if 'errors' in data:
    error_log = data['errors']
    print_log(error_log[0].get('message'))
    #raise Exception(f"update_row_agency: {error_log[0].get('message')}")

  logout_graphql(headers)

  return response

#####################################################
#
# update_record - update a specific record by id
#
#####################################################
def update_record(record_type, id_value, access_token):
   
  query = "Unknown"
  with open('C:/repo/seaware-sync/queries/update_' + record_type.name.lower() + '.graphQL', 'r') as file:
    query = file.read()

  query = query.replace('RECORDID_VALUE', id_value)

  headers = {
    'Authorization': f'Bearer {access_token}'
  }

  response = requests.post(url=get_graphql_url(), json={"query": query}, headers=headers) 
  
  if response.status_code != 200:
    print_log(f"update_record: {response.status_code} {response.text}")
    #raise Exception(f"update_record: {response.status_code} {response.text}")
  
  elif not '"operationResult":"OK"' in response.text:
     
     print_log(response.text)

     # Add Id to skip queue
     return id_value

  return None

#####################################################
#
# delete_record - delete a specific record by id
#
#####################################################
def delete_record(record_type, id_value, access_token):
   
  graphql_query = """
mutation deleteRecord {

  RECORD_TYPE(
    input: {
      id: "RECORDID_VALUE"
    }) {
    
    clientMutationId
    operationResult
  }
}
"""

  graphql_query = graphql_query.replace('RECORDID_VALUE', id_value)

  # Record Types - agencyRemove, travelAgentRemove, clientRemove
  record_type_value = 'Unknown'
  if record_type == RecordType.CLIENT:
     record_type_value = 'clientRemove'
  elif record_type == RecordType.AGENT:
     record_type_value = 'travelAgentRemove'
  elif record_type == RecordType.AGENCY:
     record_type_value = 'agencyRemove'
     
  graphql_query = graphql_query.replace('RECORD_TYPE', record_type_value)

  headers = {
    'Authorization': f'Bearer {access_token}'
  }

  response = requests.post(url=get_graphql_url(), json={"query": graphql_query}, headers=headers) 
  
  if response.status_code != 200:
    print_log(f"delete_record: {response.status_code} {response.text}")
    #raise Exception(f"delete_record: {response.status_code} {response.text}")
  
  elif not '"operationResult":"OK"' in response.text:
     
     print_log(response.text)

     # Add Id to skip queue
     return id_value

  return None

#####################################################
#
# create_record - create a specific record by id
#
#####################################################
def create_record(record_type, id_value, access_token):
   
  graphql_query = """
mutation createRecord {

  RECORD_TYPE(
    input: {
      id: "RECORDID_VALUE"
    }) {
    
    clientMutationId
    operationResult
  }
}
"""

  graphql_query = graphql_query.replace('RECORDID_VALUE', id_value)

  # Record Types - agencyRemove, travelAgentRemove, clientRemove
  record_type_value = 'Unknown'
  if record_type == RecordType.CLIENT:
     record_type_value = 'clientCreate'
  elif record_type == RecordType.AGENT:
     record_type_value = 'travelAgentCreate'
  elif record_type == RecordType.AGENCY:
     record_type_value = 'agencyCreate'
     
  graphql_query = graphql_query.replace('RECORD_TYPE', record_type_value)

  headers = {
    'Authorization': f'Bearer {access_token}'
  }

  response = requests.post(url=get_graphql_url(), json={"query": graphql_query}, headers=headers) 
  
  if response.status_code != 200:
    print_log(f"create_record: {response.status_code} {response.text}")
    #raise Exception(f"create_record: {response.status_code} {response.text}")
  
  elif not '"operationResult":"OK"' in response.text:
     
     print_log(response.text)

     # Add Id to skip queue
     return id_value

  return None

def move_specific_children_to_parent(data, target_parent_keys):
    
  """
  Moves specific children from the target parents to the parent level.
  
  Args:
  - data (dict): The JSON dictionary to process.
  - target_parent_keys (list): A list of parent keys whose children should be moved.
  
  Returns:
  - dict: The updated dictionary with specified children moved to the parent level.
  """

  if 'errors' in data:
    return data

  nodes = data.get('data').get('reservationHistory').get('edges')
  for node in nodes:

    node_data = node.get('node')

    if isinstance(node_data, dict):
      # Iterate through the dictionary
      for parent_key, value in node_data.items():
        if parent_key in target_parent_keys and isinstance(value, dict):
            
          # List of keys to move from the child
          keys_to_move = []
          
          # Iterate through the child dictionary and move each key-value pair to the parent level
          for child_key, child_value in value.items():
              node_data[child_key] = child_value  # Move child to the parent level
              keys_to_move.append(child_key)  # Mark the child key for removal

          # Remove the child keys from the parent after moving them
          for child_key in keys_to_move:
              del node_data[parent_key][child_key]

          break

  return data

#####################################################
#
# fetch_items - responsible for initial page and additional page results based on cursor
#
#####################################################
def fetch_items(record_type, record_mode, fromDateTime, toDateTime, headers, row = None, cursor = None, access_token = None, id_value = None):
   
  input_query = 'Reservations'
  if record_type == RecordType.CLIENT:
     
    input_query = 'Clients'

  elif record_type == RecordType.AGENT:
     
    input_query = 'Agents'

  elif record_type == RecordType.AGENCY:
    
    input_query = 'Agencies'

  elif record_type == RecordType.CRUISE:
    
    input_query = 'AvailableVoyages'

  elif record_type == RecordType.CABIN:
    
    input_query = 'AvailableCabins'

  elif record_type == RecordType.SHIP:
    
    input_query = 'Cabins'

  elif record_type == RecordType.RESERVATION_OTHER:

    input_query = 'ReservationsOther'

  query = None
  with open('C:/repo/seaware-sync/queries/get' + input_query + '.graphQL', 'r') as file:
    query = file.read()

  # Check for UPDATE query then update params - UPDATE is a utility tool for setting a value(s) on multiple records
  if record_mode == RecordMode.UPDATE:

    query = query.replace('altId: "ALTID_VALUE"', 'isInternal: true')
  else:

    if record_type == RecordType.CLIENT:
      
      if row is not None:
        # Columns: Id	Name	CustomerID__c	Seaware_Id__c	FirstName	LastName	Email	MiddleName	Title
        query = query.replace('ALTID_VALUE', str(row['CustomerID__c']))

    elif record_type == RecordType.AGENT:
      
      if row is not None:
        # Columns: Id	Name	FirstName	LastName	Email	RepresentativeID__c
        query = query.replace('ALTID_VALUE', str(row['RepresentativeID__c']))

    elif record_type == RecordType.AGENCY:
      
      if row is not None:
        # Columns: Id	Name	AgencyID__c	Seaware_Id__c
        query = query.replace('ALTID_VALUE', str(row['Account.AgencyID__c']))

    elif record_type == RecordType.CABIN:
      
      if row is not None:
        query = query.replace('SHIP_TODATETIME_VALUE', str(row['sail'].get('to').get('dateTime')))
        query = query.replace('SHIP_FROMDATETIME_VALUE', str(row['sail'].get('from').get('dateTime')))
        query = query.replace('SHIP_VALUE', str(row['sail'].get('ship').get('key')))

    elif record_type == RecordType.CRUISE:

      from datetime import datetime, timedelta

      today = datetime.today()
      number_days = 365 * 3
      #number_days = 3
      end_range = today + timedelta(days=number_days)

      formatted_todate = end_range.strftime("%Y-%m-%d")
      query = query.replace('TODATETIME_VALUE', formatted_todate)

      # Format today's date (e.g., "YYYY-MM-DD")
      formatted_fromdate = today.strftime("%Y-%m-%d")
      query = query.replace('FROMDATETIME_VALUE', formatted_fromdate)

  if id_value is not None:
    fromDateTime = '2024-01-01'
    toDateTime = '2099-01-01'
    query = query.replace('ID_VALUE_TOKEN', id_value)
  else:
    query = query.replace('id: "ID_VALUE_TOKEN"', '')

  variables = {
    'first': 500  # Number of items to fetch (500 is the max)
    ,'after': cursor  # Cursor for pagination
    ,'from': fromDateTime
    ,'to': toDateTime
  }

  if fromDateTime == '':

    # Remove the Sail Date Range
    query = query.replace('$sailStart: Date', '')
    query = query.replace('$sailEnd: Date', '')
    query = query.replace('fromDateTimeRange: { from: $sailStart, to: $sailEnd }', '')

  timeout_value = 120
  response = ''
  try:

    response = requests.post(url=get_graphql_url(), json={'query': query, 'variables': variables}, headers=headers, timeout=timeout_value) 
  except requests.exceptions.Timeout:
      
      print(f"Request timed out after {timeout_value} seconds")

  except requests.exceptions.RequestException as e:
      print(f"An error occurred: {e}")  

  if response.status_code != 200:
    print_log(f"fetch_items: {response.status_code} {response.text}")
    #raise Exception(f"response failed: {response.status_code} {response.text}")

  json_data = response.json()
  if record_type == RecordType.RESERVATION:

    # This is required because all the excel column names would need to change.
    # Thought 1: could just use the currentState query to get the key and then do single calls to reservation query per key for full details
    # Thought 2: Write the column and just include a parent name _ child or something that would work for reservation query or a reservation history query with current state
    # Performance of the conversion probably is not much time though to worry too much about
    parents_to_move = ["currentState"]
    modified_json = move_specific_children_to_parent(json_data, parents_to_move)
    json_data = modified_json

  # response.json() and json.loads(response.content) I think are equivalent methods to create a dictionary of json objects
  return json_data

#####################################################
#
# fetch_items_bylookup - responsible for initial page and additional page results based on cursor
#
#####################################################
def fetch_items_bylookup(record_type, record_mode, headers, row = None, cursor = None, access_token = None):
   
  input_query = 'Reservations'
  if record_type == RecordType.CLIENT:
     
    input_query = 'Clients'

  elif record_type == RecordType.AGENT:
     
    input_query = 'Agents'

  elif record_type == RecordType.AGENCY:
    
    input_query = 'Agencies'

  query = None
  with open('C:/repo/seaware-sync/queries/get' + input_query + 'ByLookup.graphQL', 'r') as file:
    query = file.read()

  # Check for UPDATE query then update params - UPDATE is a utility tool for setting a value(s) on multiple records
  if record_mode == RecordMode.UPDATE:

    query = query.replace('altId: "ALTID_VALUE"', 'isInternal: true')
  else:

    if record_type == RecordType.CLIENT:
      
      if row is not None:
        # Columns: Id	Name	CustomerID__c	Seaware_Id__c	FirstName	LastName	Email	MiddleName	Title

        # Default to NO_MATCH to avoid duplicates due to partial match
        safeValue = 'NO_MATCH'
        if not pd.isna(row['FirstName']) and not str(row['FirstName']).strip() == '':
          safeValue = row['FirstName']

        query = query.replace('FIRSTNAME_VALUE', safeValue)
        query = query.replace('LASTNAME_VALUE', str(row['LastName']))

        # Default to 1900-01-01 to avoid duplicates due to partial match
        safeValue = '1900-01-01'
        if not pd.isna(row['Birthdate']) and not str(row['Birthdate']).strip() == '':
          safeValue = row['Birthdate']

        query = query.replace('BIRTHDAY_VALUE', safeValue)

    elif record_type == RecordType.AGENT:
      
      if row is not None:
        # Columns: Id	Name	FirstName	LastName	Email	RepresentativeID__c
        query = query.replace('ALTID_VALUE', str(row['RepresentativeID__c']))

    elif record_type == RecordType.AGENCY:
      
      if row is not None:
        # Columns: Id	Name	AgencyID__c	Seaware_Id__c
        query = query.replace('ALTID_VALUE', str(row['Account.AgencyID__c']))

  variables = {
    'first': 500  # Number of items to fetch (500 is the max)
    ,'after': cursor  # Cursor for pagination
  }

  response = requests.post(url=get_graphql_url(), json={'query': query, 'variables': variables}, headers=headers) 
  if response.status_code != 200:
    print_log(f"fetch_items_bylookup: {response.status_code} {response.text}")
    #raise Exception(f"response failed: {response.status_code} {response.text}")

  # response.json() and json.loads(response.content) I think are equivalent methods to create a dictionary of json objects
  return response.json()

#####################################################
#
# process_record - 
#
#####################################################
def process_record(record_type, record_type_value, record_mode, json_res, row = None):

  # Flatten the JSON data (results)
  flattened_data = flatten_json_results(json_res)

  if not os.path.exists("C:/repo/seaware-sync/output_csv"):
    os.makedirs("C:/repo/seaware-sync/output_csv")

  bookingUpsertFile = os.path.join("C:/repo/seaware-sync/output_csv", f"{record_type.name}Upsert.csv")
  bookingUpsertFileExists = Path(bookingUpsertFile).is_file()

  # Write to CSV file
  with open(bookingUpsertFile, 'a+', newline='') as csvfile:
      writer = csv.DictWriter(csvfile, fieldnames=flattened_data.keys())
      if not bookingUpsertFileExists:
          writer.writeheader()

      writer.writeheader()
      writer.writerow(flattened_data)

  edges = json_res.get('data').get(record_type_value)
  if record_type != RecordType.CRUISE and record_type != RecordType.CABIN and record_type != RecordType.SHIP and record_type != RecordType.RESERVATION_OTHER:
    edges = json_res.get('data').get(record_type_value).get('edges')

  access_token = json_res['extensions']['access_token']

  if record_type != RecordType.RESERVATION_OTHER:
    da_flatten_list(record_type, record_mode, edges, access_token, row)

  if record_type == RecordType.AGENCY:
    da_flatten_list_agencies(edges, record_type.name + '_Agency', None, None)

  if record_type == RecordType.RESERVATION or record_type == RecordType.RESERVATION_OTHER:
    da_flatten_list_bookings(edges, record_type.name + '_Booking', None, None)

def da_flatten_list(record_type, record_mode, json_list, access_token, row = None):

  # Create a list of dictionaries for CSV writing
  csv_data = []
  for index, item in enumerate(json_list):
      
      if isinstance(item, dict):
          
          if record_type != RecordType.CRUISE and record_type != RecordType.CABIN and record_type != RecordType.SHIP and record_type != RecordType.RESERVATION_OTHER:

            # Check to clear out automation created record
            id_value = item['node']['id']

          should_process_record = False
          if record_type == RecordType.CLIENT:

            should_process_record = True
            
          elif record_type == RecordType.AGENT:

            should_process_record = (not item['node']['iatan'] == None and 'holderName' in item['node']['iatan'])
          elif record_type == RecordType.AGENCY:

            should_process_record = (not item['node']['defaultLanguage'] == None and 'id' in item['node']['defaultLanguage'])

          elif record_type == RecordType.RESERVATION:
             
             should_process_record = True

          if (should_process_record):

            # Update Paging on all Records until 255 paging Jira ticket fixed
            #update_record_paging(record_type, id_value, access_token)

            if record_mode == RecordMode.DELETE:
               
                print_log('Deleting ' + id_value + ' index: ' + str(index))
                id_value = delete_record(record_type, id_value, access_token)

            elif record_mode == RecordMode.UPDATE:

                #should_update_record = (item['node']['isConsortium'] == False and item['node']['type'] != None and item['node']['type']['id'] == 'AgencyType|A')
                should_update_record = True

                if should_update_record:

                    print_log('Updating ' + id_value + ' index: ' + str(index))
                    id_value = update_record(record_type, id_value, access_token)
                else:
                    id_value = None

            elif record_mode == RecordMode.INSERT:

              print_log('Inserting ' + id_value + ' index: ' + str(index))
              #id_value = insert_record(record_type, id_value, access_token)
         
          flattened_item = flatten_json_lists(item)

          if next(iter(flattened_item.values())) == None:
              continue
          
          # Add an identifier for each item in the list  
          flattened_item['index'] = index

          if record_type == RecordType.CABIN:

            #name = json_list.get('name')

            sail_to_datetime = str(row['sail'].get('to').get('dateTime'))
            sail_from_datetime = str(row['sail'].get('from').get('dateTime'))
            sail_ship = str(row['sail'].get('ship').get('key'))
            flattened_item['sail_to_datetime'] = sail_to_datetime
            flattened_item['sail_from_datetime'] = sail_from_datetime
            flattened_item['sail_ship'] = sail_ship

          csv_data.append(flattened_item)

      else:
          print_log(f"Skipping non-dict item in list '{record_type.name}': {item}")

  # Write to CSV file named after the key
  write_to_csv(csv_data, f"{record_type.name}.csv")

def get_values_by_key_substring(d, substring):
    return [value for key, value in d.items() if substring in key]

def da_flatten_list_agencies(json_list, key, agencyKey, agentKey):

  # Create a list of dictionaries for CSV writing
  csv_data = []

  if isinstance(json_list, dict):
      
      #name = json_list.get('name')

      flattened_items = flatten_json_lists(json_list)
      custom_items = {'agency': agencyKey}
      flattened_item = {**custom_items, **flattened_items}

      csv_data.append(flattened_item)

      if 'result_key' in flattened_items:
        agencyKey = flattened_items['result_key']

        filename = RecordType.RESERVATION_OTHER.name + '_history'
        if not json_list.get('result') == None and not json_list.get('result').get('history') == None:
          changes = json_list.get('result').get('history')
          if len(changes) > 0:
            for index, item in enumerate(changes):
              da_flatten_list_agencies(item, filename, agencyKey, agentKey)

  else:

    for index, item in enumerate(json_list):
        
        if isinstance(item, dict):
            
            flattened_items = flatten_json_lists(item)

            if next(iter(flattened_items.values())) == None:
                continue
            
            if 'node_key' in flattened_items:
              agencyKey = flattened_items['node_key']

            agent_ids = get_values_by_key_substring(flattened_items, "agent_id")
            if len(agent_ids) > 0:
              agentKey = agent_ids[len(agent_ids) - 1]

            custom_items = {'index': index, 'agency': agencyKey, 'agent': agentKey}

            flattened_item = {**custom_items, **flattened_items}

            csv_data.append(flattened_item)

            if not item.get('node') == None and not item.get('node').get('agents') == None:
              agents = item.get('node').get('agents')
              da_flatten_list_agencies(agents, RecordType.RESERVATION.name + '_Agents', agencyKey, agentKey)

              for agent in agents:

                da_flatten_list_agencies(agent['transfer'], RecordType.RESERVATION.name + '_Transfers', agencyKey, agentKey)

            filename = RecordType.AGENCY.name + '_Classifications'
            #check_csv(filename)
            if not item.get('node') == None and not item.get('node').get('classifications') == None:
              records = item.get('node').get('classifications')
              if len(records) > 0:
                da_flatten_list_agencies(records, filename, agencyKey, agentKey)

  # Write to CSV file named after the key
  write_to_csv(csv_data, f"{key}.csv")

def da_flatten_list_bookings(json_list, key, reservationKey, guestKey):

  # Create a list of dictionaries for CSV writing
  csv_data = []

  if isinstance(json_list, dict):
      
      #name = json_list.get('name')

      flattened_items = flatten_json_lists(json_list)
      custom_items = {'reservation': reservationKey}
      flattened_item = {**custom_items, **flattened_items}

      csv_data.append(flattened_item)

      if 'result_key' in flattened_items:
        reservationKey = flattened_items['result_key']

        filename = RecordType.RESERVATION_OTHER.name + '_history'
        if not json_list.get('result') == None and not json_list.get('result').get('history') == None:
          changes = json_list.get('result').get('history')
          if len(changes) > 0:
            for index, item in enumerate(changes):
              da_flatten_list_bookings(item, filename, reservationKey, guestKey)

  else:

    for index, item in enumerate(json_list):
        
        if isinstance(item, dict):
            
            flattened_items = flatten_json_lists(item)

            if next(iter(flattened_items.values())) == None:
                continue
            
            if 'node_key' in flattened_items:
              reservationKey = flattened_items['node_key']

            client_ids = get_values_by_key_substring(flattened_items, "client_id")
            if len(client_ids) > 0:
              guestKey = client_ids[len(client_ids) - 1]

            custom_items = {'index': index, 'reservation': reservationKey, 'guest': guestKey}

            flattened_item = {**custom_items, **flattened_items}

            csv_data.append(flattened_item)

            if not item.get('node') == None and not item.get('node').get('guests') == None:
              guests = item.get('node').get('guests')
              da_flatten_list_bookings(guests, RecordType.RESERVATION.name + '_Guests', reservationKey, guestKey)

              for guest in guests:
                da_flatten_list_bookings(guest['voyages'], RecordType.RESERVATION.name + '_Voyages', reservationKey, guestKey)
                da_flatten_list_bookings(guest['transfer'], RecordType.RESERVATION.name + '_Transfers', reservationKey, guestKey)
                da_flatten_list_bookings(guest['addons'], RecordType.RESERVATION.name + '_AddOns', reservationKey, guestKey)

                filename = RecordType.RESERVATION.name + '_VoyagePackages'
                if len(guest['voyages']) > 0 and not guest['voyages'][0]['pkg'] == None:
                  da_flatten_list_bookings(guest['voyages'][0]['pkg'], filename, reservationKey, guestKey)

                filename = RecordType.RESERVATION.name + '_CabinAttributes'
                if len(guest['voyages']) > 0 and not guest['voyages'][0]['cabinAttributes'] == None:
                  if len(guest['voyages'][0]['cabinAttributes']) > 0:
                    da_flatten_list_bookings(guest['voyages'][0]['cabinAttributes'], filename, reservationKey, guestKey)

                filename = RecordType.RESERVATION.name + '_BorderForms'
                if not guest['client'] == None and not guest['client']['borderForms'] == None:
                  if len(guest['client']['borderForms']) > 0:
                    da_flatten_list_bookings(guest['client']['borderForms'], filename, reservationKey, guestKey)

            filename = RecordType.RESERVATION.name + '_UserNotes'
            #check_csv(filename)
            if not item.get('node') == None and not item.get('node').get('userNotes') == None:
              records = item.get('node').get('userNotes')
              if len(records) > 0:
                da_flatten_list_bookings(records, filename, reservationKey, guestKey)

            filename = RecordType.RESERVATION.name + '_Promos'
            #check_csv(filename)
            if not item.get('node') == None and not item.get('node').get('invoice') == None:
              invoices = item.get('node').get('invoice')
              if len(invoices) > 0:
                da_flatten_list_bookings(invoices, filename, reservationKey, guestKey)

            filename = RecordType.RESERVATION.name + '_InvoiceTotals'
            #check_csv(filename)
            if not item.get('node') == None and not item.get('node').get('invoiceTotals') == None:
              invoiceTotals = item.get('node').get('invoiceTotals')
              if len(invoiceTotals) > 0:
                da_flatten_list_bookings(invoiceTotals, filename, reservationKey, guestKey)

            filename = RecordType.RESERVATION.name + '_ReferralSource'
            #check_csv(filename)
            if not item.get('node') == None and not item.get('node').get('referralSource') == None:
              referralSource = item.get('node').get('referralSource')
              if len(referralSource) > 0:
                da_flatten_list_bookings(referralSource, filename, reservationKey, guestKey)

            filename = RecordType.RESERVATION.name + '_ReferralSource'
            #check_csv(filename)
            if not item.get('node') == None and not item.get('node').get('referralSource') == None:
              referralSource = item.get('node').get('referralSource')
              if len(referralSource) > 0:
                da_flatten_list_bookings(referralSource, filename, reservationKey, guestKey)

            filename = RecordType.RESERVATION.name + '_Groups'
            #check_csv(filename)
            if not item.get('node') == None and not item.get('node').get('group') == None:
              groups = item.get('node').get('group')
              if len(groups) > 0:
                da_flatten_list_bookings(groups, filename, reservationKey, guestKey)

            filename = RecordType.RESERVATION.name + '_Agencies'
            #check_csv(filename)
            if not item.get('node') == None and not item.get('node').get('agency') == None:
              agencies = item.get('node').get('agency')
              if len(agencies) > 0:
                da_flatten_list_bookings(agencies, filename, reservationKey, guestKey)

            filename = RecordType.RESERVATION.name + '_secondaryAgent'
            #check_csv(filename)
            if not item.get('node') == None and not item.get('node').get('secondaryAgent') == None:
              secondaryAgent = item.get('node').get('secondaryAgent')
              if len(secondaryAgent) > 0:
                da_flatten_list_bookings(secondaryAgent, filename, reservationKey, guestKey)

            filename = RecordType.RESERVATION.name + '_Contact'
            #check_csv(filename)
            if not item.get('node') == None and not item.get('node').get('contact') == None:
              contact = item.get('node').get('contact')
              if len(contact) > 0:
                da_flatten_list_bookings(contact, filename, reservationKey, guestKey)

  # Write to CSV file named after the key
  write_to_csv(csv_data, f"{key}.csv")

def flatten_json_lists(y):
    
    """Flatten a nested JSON object."""
    out = {}

    def flatten(x, name=''):
        
        # If it's a dictionary, recursively flatten it
        if isinstance(x, dict):
            for a in x:
                flatten(x[a], name + a + '_')

        # If it's a list, return the entire list for further processing
        elif isinstance(x, list):
        
          for i, sub_item in enumerate(x):
            flatten(sub_item, name + str(i) + '_')
               
        else:
            out[name[:-1]] = x  # Remove the trailing underscore

    flatten(y)
    return out

def flatten_json_results(y):
    
    """Flatten a nested JSON object."""
    out = {}

    def flatten(x, name=''):
        
        # If it's a dictionary, recursively flatten it
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '_')

        # If it's a list, ignore
        elif type(x) is list:
          no_action = True
#            print_log('Skipping list: ' + name)

        else:
            
            out[name[:-1]] = x  # Remove the trailing underscore

    flatten(y)
    return out

def clean_value(value):

  return value.strip("b'")

def clean_row_values(dictionary_data):

  #print(type(dictionary_data))
  updated_list = [item.replace('\u0308', '').replace('\u200c', '').replace("\u202c", " ").replace("\u202d", " ").replace("\n", " ").replace("\x92", " ") if isinstance(item, str) else item for item in dictionary_data]

  encoded_list = [str(item).encode('utf-8') if item is not None else None for item in updated_list]

  encoded_list = [str(item).strip("b'") if item is not None else None for item in updated_list]

  import unicodedata
  normalized_list = [unicodedata.normalize('NFKD', item) if isinstance(item, str) else item
        for item in encoded_list]
  
  return normalized_list

def write_to_csv(data, filename):
    
    if not bool(data):
        return
    
    full_filename = os.path.join("C:/repo/seaware-sync/output_csv", filename)

    fileCheckPath = Path(full_filename)
    fileCheckExists = fileCheckPath.is_file()

    # Check to update header
    if fileCheckExists:

      with open(full_filename, mode='r', newline='') as infile:
          reader = csv.reader(infile)
          rows = list(reader)

      for data_row in data:

        if len(rows[0]) < len(data_row):

          rows[0] = data_row.keys()

          with open(full_filename, mode='w', newline='') as outfile:
              writer = csv.writer(outfile)
              writer.writerows(rows)

    """Write flattened data to a CSV file."""
    with open(full_filename, 'a+', newline='') as csvfile:
        
        writer = csv.writer(csvfile)

        if not fileCheckExists:

          # Write header
          row_headers = data[0].keys()
          for data_row in data:

            if len(row_headers) < len(data_row):

              row_headers = data_row.keys()

          writer.writerow(row_headers)

        # Write rows
        for row in data:
            cleaned_values = clean_row_values(row.values())
            writer.writerow(cleaned_values)

#    print_log(f"Written {full_filename}")

def check_csv(filename):
    
    full_filename = os.path.join("C:/repo/seaware-sync/output_csv", filename + '.csv')

    with open(full_filename, 'w') as file:
      pass  # The file is created and immediately closed, leaving it empty

    print_log(f"Created {full_filename}")

# Using the special variable 
# __name__
if __name__== "__main__":
    main()
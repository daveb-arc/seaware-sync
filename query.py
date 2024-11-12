import json
import requests
import csv
from pathlib import Path
import pandas as pd
import os
from enum import Enum
from datetime import date

GRAPHQL_URL = 'https://testreservations.uncruise.com:3000/graphql'
#GRAPHQL_URL = 'https://devreservations.uncruise.com:3000/graphql'
#GRAPHQL_URL = 'https://reservations.uncruise.com:3000/graphql'

class RecordType(Enum):
    CLIENT = 1
    AGENT = 2
    AGENCY = 3
    RESERVATION = 4

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
      print("Calling error - missing required inputs.  Expecting " +
              "RecordType RecordMode\n")
      return

  print("\nIncoming required parameters: " +
          "RecordType: {} RecordMode: {} sys.argv {}\n"
          .format(record_type_input, record_mode_input, sys.argv))

  # Delete previous csv files
  directory_to_search = "C:/repo/seaware-sync/output_csv"
  delete_files_in_directory(directory_to_search, '.csv')

  record_type = RecordType.RESERVATION
  if record_type_input == RecordType.AGENCY.name:
     record_type = RecordType.AGENCY
  elif record_type_input == RecordType.AGENT.name:
     record_type = RecordType.AGENT
  elif record_type_input == RecordType.CLIENT.name:
     record_type = RecordType.CLIENT

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

    process_seaware(record_type, record_mode)

def process_salesforce_clients(record_type: RecordType, record_mode: RecordMode):
    
  import pandas as pd

  data_frame = pd.read_csv('C:/repo/Salesforce-Exporter-Private/Clients/SEAWARE/Salesforce-Exporter/Clients/SEAWARE/Export/Client-Prod.csv')

  for index, row in data_frame.iterrows():

      # Query to setup output file for processing in Excel PowerQuery update to SF
      json_res = process_seaware(RecordType.CLIENT, RecordMode.QUERY, row)

      if len(json_res.get('data').get('clients').get('edges')) <= 0:

        # Attempt to insert - Seaware DB will fail call if altid already set on a record
        insert_row_client(RecordType.CLIENT, RecordMode.INSERT, row)

        # Query to setup output file for processing in Excel PowerQuery update to SF
        process_seaware(RecordType.CLIENT, RecordMode.QUERY, row)

      else:

        id_value = json_res.get('data').get('clients').get('edges')[0].get('node').get('key')

        # Update Request for complete field updates
        update_row_client(RecordType.CLIENT, RecordMode.UPDATE, row, id_value)

def process_salesforce_agents(record_type: RecordType, record_mode: RecordMode):
    
  import pandas as pd

  data_frame = pd.read_csv('C:/repo/Salesforce-Exporter-Private/Clients/SEAWARE/Salesforce-Exporter/Clients/SEAWARE/Export/Agent-Prod.csv')

  for index, row in data_frame.iterrows():

      # Query to setup output file for processing in Excel PowerQuery update to SF
      json_res = process_seaware(RecordType.AGENT, RecordMode.QUERY, row)

      if len(json_res.get('data').get('travelAgents').get('edges')) <= 0:

        # Attempt to insert - Seaware DB will fail call if altid already set on a record
        insert_row_agent(RecordType.AGENT, RecordMode.INSERT, row)

        # Query to setup output file for processing in Excel PowerQuery update to SF
        process_seaware(RecordType.AGENT, RecordMode.QUERY, row)

      else:

        id_value = json_res.get('data').get('agents').get('edges')[0].get('node').get('key')

        # Update Request for complete field updates
        update_row_agent(RecordType.CLIENT, RecordMode.UPDATE, row, id_value)

def process_salesforce_agencies(record_type: RecordType, record_mode: RecordMode):
    
  import pandas as pd

  data_frame = pd.read_csv('C:/repo/Salesforce-Exporter-Private/Clients/SEAWARE/Salesforce-Exporter/Clients/SEAWARE/Export/Agency-Prod.csv')

  for index, row in data_frame.iterrows():

      # Query to setup output file for processing in Excel PowerQuery update to SF
      json_res = process_seaware(RecordType.AGENCY, RecordMode.QUERY, row)

      if len(json_res.get('data').get('agencies').get('edges')) <= 0:

        # Attempt to insert - Seaware DB will fail call if altid already set on a record
        insert_row_agency(RecordType.AGENCY, RecordMode.INSERT, row)

        # Query to setup output file for processing in Excel PowerQuery update to SF
        process_seaware(RecordType.AGENCY, RecordMode.QUERY, row)

      else:

        id_value = json_res.get('data').get('agencies').get('edges')[0].get('node').get('key')

        # Update Request for complete field updates
        update_row_agency(RecordType.AGENCY, RecordMode.UPDATE, row, id_value)

def process_seaware(record_type: RecordType, record_mode: RecordMode, row = None): 

  # Record Types
  record_type_value = 'reservations'
  if record_type == RecordType.CLIENT:
    record_type_value = 'clients'
  elif record_type == RecordType.AGENT:
    record_type_value = 'travelAgents'
  elif record_type == RecordType.AGENCY:
    record_type_value = 'agencies'

  # Initial request - no cursor
  json_res = fetch_items(record_type, row)
  page_info = None

  if record_type_value in json_res['data']: 
    process_record(record_type, record_type_value, record_mode, json_res)
    page_info = json_res['data'][record_type_value]['pageInfo']

  else:
    print("unknown response type")
    return json_res

  # Check for next page - max query is total of 500 regardless of the paging request size
  #
  while page_info['hasNextPage']:
    
    cursor = page_info['endCursor']
    access_token = json_res['extensions']['access_token']
#    json_res = fetch_items(record_type, row, cursor, access_token) 

    # Max query is 500 so if deleting or paging update then just restart the query
    json_res = fetch_items(record_type, row) 

    incoming_items = len(json_res.get('data').get(record_type_value).get('edges'))
    print("cursor: " + cursor + " access_token: " + access_token + " incoming_items: " + str(incoming_items))        
      
    if record_type_value in json_res['data']: 
      process_record(record_type, record_type_value, record_mode, json_res)
      page_info = json_res['data'][record_type_value]['pageInfo']

    else:
      print("unknown query type")       

  return json_res

def delete_files_in_directory(directory, search_string):
    # Walk through the directory
    for foldername, subfolders, filenames in os.walk(directory):
        for filename in filenames:
            # Check if the search string is in the filename
            if search_string in filename:
                file_path = os.path.join(foldername, filename)
                try:
                    # Delete the file
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")

#####################################################
#
# update_record - update a specific record by id, update isInternal on all records because that is
#   used as the workaround flag for paging
#
#####################################################
def update_record_paging(record_type: RecordType, id_value, access_token):
   
  query = "Unknown"
  with open('C:/repo/seaware-sync/queries/update_paging.graphQL', 'r') as file:
    query = file.read()

  query = query.replace('ID_VALUE', id_value)

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

  response = requests.post(url=GRAPHQL_URL, json={"query": query}, headers=headers) 
  
  if response.status_code != 200:
    raise Exception(f"Login failed: {response.status_code} {response.text}")
  
  elif not '"operationResult":"OK"' in response.text:
     
     print(response.text)

     # Add Id to skip queue
     return id_value

  return None

#####################################################
#
# insert_row_client - insert a specific client row
#
#####################################################
def insert_row_client(record_type: RecordType, record_mode: RecordMode, row):
   
  login = """
mutation login {

  login(role:Internal ) {
    token
  }
}
"""

  token = None

  response = requests.post(url=GRAPHQL_URL, json={"query": login}) 

  if response.status_code == 200:
    data = response.json()
    token = data['data']['login']['token']
  else:
    raise Exception(f"Login failed: {response.status_code} {response.text}")
    
  headers = {
    'Authorization': f'Bearer {token}'
  }

  query = "Unknown"
  with open('C:/repo/seaware-sync/queries/insert_row_' + record_type.name.lower() + '.graphQL', 'r') as file:
    query = file.read()

  # Id	Name	CustomerID__c	Seaware_Id__c	FirstName	LastName	Email	MiddleName	Title
  query = query.replace('ALTID_VALUE', row['CustomerID__c'])
  query = query.replace('FIRSTNAME_VALUE', row['FirstName'])
  query = query.replace('LASTNAME_VALUE', row['LastName'])

  response = requests.post(url=GRAPHQL_URL, json={"query": query}, headers=headers) 
  if response.status_code != 200:
    raise Exception(f"Login failed: {response.status_code} {response.text}")
    
  return response

#####################################################
#
# update_row_client - update a specific client row
#
#####################################################
def update_row_client(record_type: RecordType, record_mode: RecordMode, row, id_value):
   
  login = """
mutation login {

  login(role:Internal ) {
    token
  }
}
"""

  token = None

  response = requests.post(url=GRAPHQL_URL, json={"query": login}) 

  if response.status_code == 200:
    data = response.json()
    token = data['data']['login']['token']
  else:
    raise Exception(f"Login failed: {response.status_code} {response.text}")
    
  headers = {
    'Authorization': f'Bearer {token}'
  }

  query = "Unknown"
  with open('C:/repo/seaware-sync/queries/update_row_' + record_type.name.lower() + '.graphQL', 'r') as file:
    query = file.read()

  # Id	Name	CustomerID__c	Seaware_Id__c	FirstName	LastName	Email	MiddleName	Title
  query = query.replace('ID_VALUE', id_value)
  query = query.replace('ALTID_VALUE', row['CustomerID__c'])
  query = query.replace('FIRSTNAME_VALUE', row['FirstName'])
  query = query.replace('LASTNAME_VALUE', row['LastName'])
  query = query.replace('EMAIL_VALUE', row['Email'])
  query = query.replace('BIRTHDAY_VALUE', row['Birthdate'])

  response = requests.post(url=GRAPHQL_URL, json={"query": query}, headers=headers) 
  if response.status_code != 200:
    raise Exception(f"Login failed: {response.status_code} {response.text}")
  
  return response

#####################################################
#
# insert_row_agent - insert a specific agent row
#
#####################################################
def insert_row_agent(record_type: RecordType, record_mode: RecordMode, row):
   
  login = """
mutation login {

  login(role:Internal ) {
    token
  }
}
"""

  token = None

  response = requests.post(url=GRAPHQL_URL, json={"query": login}) 

  if response.status_code == 200:
    data = response.json()
    token = data['data']['login']['token']
  else:
    raise Exception(f"Login failed: {response.status_code} {response.text}")
    
  headers = {
    'Authorization': f'Bearer {token}'
  }

  query = "Unknown"
  with open('C:/repo/seaware-sync/queries/insert_row_' + record_type.name.lower() + '.graphQL', 'r') as file:
    query = file.read()

  # Id	Name	CustomerID__c	Seaware_Id__c	FirstName	LastName	Email	MiddleName	Title
  query = query.replace('ALTID_VALUE', row['CustomerID__c'])
  query = query.replace('FIRSTNAME_VALUE', row['FirstName'])
  query = query.replace('LASTNAME_VALUE', row['LastName'])

  response = requests.post(url=GRAPHQL_URL, json={"query": query}, headers=headers) 
  if response.status_code != 200:
    raise Exception(f"Login failed: {response.status_code} {response.text}")
    
  return response

#####################################################
#
# update_row_agent - update a specific agent row
#
#####################################################
def update_row_agent(record_type: RecordType, record_mode: RecordMode, row, id_value):
   
  login = """
mutation login {

  login(role:Internal ) {
    token
  }
}
"""

  token = None

  response = requests.post(url=GRAPHQL_URL, json={"query": login}) 

  if response.status_code == 200:
    data = response.json()
    token = data['data']['login']['token']
  else:
    raise Exception(f"Login failed: {response.status_code} {response.text}")
    
  headers = {
    'Authorization': f'Bearer {token}'
  }

  query = "Unknown"
  with open('C:/repo/seaware-sync/queries/update_row_' + record_type.name.lower() + '.graphQL', 'r') as file:
    query = file.read()

  # Id	Name	CustomerID__c	Seaware_Id__c	FirstName	LastName	Email	MiddleName	Title
  query = query.replace('ID_VALUE', id_value)
  query = query.replace('NAME_VALUE', row['Name'])

  response = requests.post(url=GRAPHQL_URL, json={"query": query}, headers=headers) 
  if response.status_code != 200:
    raise Exception(f"Login failed: {response.status_code} {response.text}")
  
  return response

#####################################################
#
# insert_row_agency - insert a specific agency row
#
#####################################################
def insert_row_agency(record_type: RecordType, record_mode: RecordMode, row):
   
  login = """
mutation login {

  login(role:Internal ) {
    token
  }
}
"""

  token = None

  response = requests.post(url=GRAPHQL_URL, json={"query": login}) 

  if response.status_code == 200:
    data = response.json()
    token = data['data']['login']['token']
  else:
    raise Exception(f"Login failed: {response.status_code} {response.text}")
    
  headers = {
    'Authorization': f'Bearer {token}'
  }

  query = "Unknown"
  with open('C:/repo/seaware-sync/queries/insert_row_' + record_type.name.lower() + '.graphQL', 'r') as file:
    query = file.read()

  # Id	Name	CustomerID__c	Seaware_Id__c	FirstName	LastName	Email	MiddleName	Title
  query = query.replace('ALTID_VALUE', row['AgencyID__c'])
  query = query.replace('NAME_VALUE', row['Name'])

  response = requests.post(url=GRAPHQL_URL, json={"query": query}, headers=headers) 
  if response.status_code != 200:
    raise Exception(f"Login failed: {response.status_code} {response.text}")
    
  return response

#####################################################
#
# update_row_agency - update a specific agency row
#
#####################################################
def update_row_agency(record_type: RecordType, record_mode: RecordMode, row, id_value):
   
  login = """
mutation login {

  login(role:Internal ) {
    token
  }
}
"""

  token = None

  response = requests.post(url=GRAPHQL_URL, json={"query": login}) 

  if response.status_code == 200:
    data = response.json()
    token = data['data']['login']['token']
  else:
    raise Exception(f"Login failed: {response.status_code} {response.text}")
    
  headers = {
    'Authorization': f'Bearer {token}'
  }

  query = "Unknown"
  with open('C:/repo/seaware-sync/queries/update_row_' + record_type.name.lower() + '.graphQL', 'r') as file:
    query = file.read()

  # Id	Name	CustomerID__c	Seaware_Id__c	FirstName	LastName	Email	MiddleName	Title
  query = query.replace('ID_VALUE', id_value)
  query = query.replace('FIRSTNAME_VALUE', row['FirstName'])
  query = query.replace('LASTNAME_VALUE', row['LastName'])

  response = requests.post(url=GRAPHQL_URL, json={"query": query}, headers=headers) 
  if response.status_code != 200:
    raise Exception(f"Login failed: {response.status_code} {response.text}")
  
  return response

#####################################################
#
# update_record - update a specific record by id
#
#####################################################
def update_record(record_type: RecordType, id_value, access_token):
   
  query = "Unknown"
  with open('C:/repo/seaware-sync/queries/update_' + record_type.name.lower() + '.graphQL', 'r') as file:
    query = file.read()

  query = query.replace('ID_VALUE', id_value)

  headers = {
    'Authorization': f'Bearer {access_token}'
  }

  response = requests.post(url=GRAPHQL_URL, json={"query": query}, headers=headers) 
  
  if response.status_code != 200:
    raise Exception(f"Login failed: {response.status_code} {response.text}")
  
  elif not '"operationResult":"OK"' in response.text:
     
     print(response.text)

     # Add Id to skip queue
     return id_value

  return None

#####################################################
#
# delete_record - delete a specific record by id
#
#####################################################
def delete_record(record_type: RecordType, id_value, access_token):
   
  graphql_query = """
mutation deleteRecord {

  RECORD_TYPE(
    input: {
      id: "ID_VALUE"
    }) {
    
    clientMutationId
    operationResult
  }
}
"""

  graphql_query = graphql_query.replace('ID_VALUE', id_value)

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

  response = requests.post(url=GRAPHQL_URL, json={"query": graphql_query}, headers=headers) 
  
  if response.status_code != 200:
    raise Exception(f"Login failed: {response.status_code} {response.text}")
  
  elif not '"operationResult":"OK"' in response.text:
     
     print(response.text)

     # Add Id to skip queue
     return id_value

  return None

#####################################################
#
# create_record - create a specific record by id
#
#####################################################
def create_record(record_type: RecordType, id_value, access_token):
   
  graphql_query = """
mutation createRecord {

  RECORD_TYPE(
    input: {
      id: "ID_VALUE"
    }) {
    
    clientMutationId
    operationResult
  }
}
"""

  graphql_query = graphql_query.replace('ID_VALUE', id_value)

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

  response = requests.post(url=GRAPHQL_URL, json={"query": graphql_query}, headers=headers) 
  
  if response.status_code != 200:
    raise Exception(f"Login failed: {response.status_code} {response.text}")
  
  elif not '"operationResult":"OK"' in response.text:
     
     print(response.text)

     # Add Id to skip queue
     return id_value

  return None

#####################################################
#
# fetch_items - responsible for initial page and additional page results based on cursor
#
#####################################################
def fetch_items(record_type: RecordType, row = None, cursor = None, access_token = None):
   
  login = """
mutation login {

  login(role:Internal ) {
    token
  }
}
"""

  token = access_token

  if cursor == None:
    
    #login to get token
    #response = requests.post(url=GRAPHQL_URL, json={'query': query, 'variables': variables})
    response = requests.post(url=GRAPHQL_URL, json={"query": login}) 
  
    if response.status_code == 200:
      data = response.json()
      token = data['data']['login']['token']
    else:
      raise Exception(f"Login failed: {response.status_code} {response.text}")
    
  headers = {
    'Authorization': f'Bearer {token}'
  }

  input_query = 'Reservations'
  if record_type == RecordType.CLIENT:
     
    input_query = 'Clients'

  elif record_type == RecordType.AGENT:
     
    input_query = 'Agents'

  elif record_type == RecordType.AGENCY:
    
    input_query = 'Agencies'

  query = None
  with open('C:/repo/seaware-sync/queries/get' + input_query + '.graphQL', 'r') as file:
    query = file.read()

  if record_type == RecordType.CLIENT:
     
    # Columns: Id	Name	CustomerID__c	Seaware_Id__c	FirstName	LastName	Email	MiddleName	Title
    query = query.replace('ALTID_VALUE', row['CustomerID__c'])

  elif record_type == RecordType.AGENT:
     
    # Columns: Id	Name	FirstName	LastName	Email	RepresentativeID__c
    query = query.replace('ALTID_VALUE', row['ReprsentativeID__c'])

  elif record_type == RecordType.AGENCY:
    
    # Columns: Id	Name	AgencyID__c	Seaware_Id__c
    query = query.replace('ALTID_VALUE', row['AgencyID__c'])

  variables = {
    'first': 100  # Number of items to fetch (500 is the max)
    ,'after': cursor  # Cursor for pagination
  }

  response = requests.post(url=GRAPHQL_URL, json={'query': query, 'variables': variables}, headers=headers) 
  print("response status code: ", response.status_code) 
  #if response.status_code == 200: 
  #    print("response : ",response.content) 

  # response.json() and json.loads(response.content) I think are equivalent methods to create a dictionary of json objects
  return response.json()

#####################################################
#
# process_record - 
#
#####################################################
def process_record(record_type: RecordType, record_type_value, record_mode: RecordMode, json_res):

  # Flatten the JSON data (results)
  flattened_data = flatten_json_results(json_res)

  bookingUpsertFile = os.path.join("C:/repo/seaware-sync/output_csv", f"{record_type.name}Upsert.csv")
  bookingUpsertFileExists = Path(bookingUpsertFile).is_file()

  # Write to CSV file
  with open(bookingUpsertFile, 'a+', newline='') as csvfile:
      writer = csv.DictWriter(csvfile, fieldnames=flattened_data.keys())
      if not bookingUpsertFileExists:
          writer.writeheader()
      writer.writerow(flattened_data)

  edges = json_res.get('data').get(record_type_value).get('edges')
  access_token = json_res['extensions']['access_token']

  da_flatten_list(record_type, record_mode, edges, access_token)

  if record_type == RecordType.RESERVATION:
    da_flatten_list_bookings(edges, record_type.name + '_Booking', None)

def da_flatten_list(record_type: RecordType, record_mode: RecordMode, json_list, access_token):

  # Create a list of dictionaries for CSV writing
  csv_data = []
  for index, item in enumerate(json_list):
      
      if isinstance(item, dict):
          
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

            print('Processing ' + id_value + ' index: ' + str(index))

            # Update Paging on all Records until 255 paging Jira ticket fixed
            #update_record_paging(record_type, id_value, access_token)

            if record_mode == RecordMode.DELETE:
               
                print('Deleting ' + id_value + ' index: ' + str(index))
                id_value = delete_record(record_type, id_value, access_token)

            elif record_mode == RecordMode.UPDATE:

                #should_update_record = (item['node']['isConsortium'] == False and item['node']['type'] != None and item['node']['type']['id'] == 'AgencyType|A')
                should_update_record = True

                if should_update_record:

                    print('Updating ' + id_value + ' index: ' + str(index))
                    id_value = update_record(record_type, id_value, access_token)
                else:
                    id_value = None

            elif record_mode == RecordMode.INSERT:

              print('Inserting ' + id_value + ' index: ' + str(index))
              id_value = insert_record(record_type, id_value, access_token)

            else:
                
                # Query Records
                print('Querying ' + id_value + ' index: ' + str(index))
         
          flattened_item = flatten_json_lists(item)

          if next(iter(flattened_item.values())) == None:
              continue
          
          # Add an identifier for each item in the list  
          flattened_item['index'] = index
          csv_data.append(flattened_item)

      else:
          print(f"Skipping non-dict item in list '{record_type.name}': {item}")

  # Write to CSV file named after the key
  write_to_csv(csv_data, f"{record_type.name}.csv")

def da_flatten_list_bookings(json_list, key, reservationKey):

  # Create a list of dictionaries for CSV writing
  csv_data = []
  for index, item in enumerate(json_list):
      
      if isinstance(item, dict):
          
          flattened_items = flatten_json_lists(item)

          if next(iter(flattened_items.values())) == None:
              continue
          
          if next(iter(flattened_items.keys())) == 'node_key':
            reservationKey = next(iter(flattened_items.values()))

          custom_items = {'index': index, 'reservation': reservationKey}

          flattened_item = {**custom_items, **flattened_items}

          csv_data.append(flattened_item)

          if not item.get('node') == None and not item.get('node').get('guests') == None:
            guests = item.get('node').get('guests')
            da_flatten_list_bookings(guests, RecordType.RESERVATION.name + '_Guests', reservationKey)
            da_flatten_list_bookings(guests[0]['voyages'], RecordType.RESERVATION.name + '_Voyages', reservationKey)

          if not item.get('node') == None and not item.get('node').get('agency') == None:
            agencies = item.get('node').get('agency')
            da_flatten_list_bookings(agencies, RecordType.RESERVATION.name + '_Agencies', reservationKey)

      else:
          print(f"Skipping non-dict item in list '{key}': {item}")

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
            print('Skipping list: ' + name)

        else:
            
            out[name[:-1]] = x  # Remove the trailing underscore

    flatten(y)
    return out

def write_to_csv(data, filename):
    
    if not bool(data):
        return
    
    full_filename = os.path.join("C:/repo/seaware-sync/output_csv", filename)

    fileCheckPath = Path(full_filename)
    fileCheckExists = fileCheckPath.is_file()

    """Write flattened data to a CSV file."""
    with open(full_filename, 'a+', newline='') as csvfile:
        
        writer = csv.writer(csvfile)

        if not fileCheckExists:

          # Write header
          writer.writerow(data[0].keys())

        # Write rows
        for row in data:
            writer.writerow(row.values())

    print(f"Written {full_filename}")

# Using the special variable 
# __name__
if __name__== "__main__":
    main()
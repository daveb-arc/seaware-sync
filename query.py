import json
import requests
import csv
from pathlib import Path
import pandas as pd
import os
from enum import Enum

#GRAPHQL_URL = 'https://testreservations.uncruise.com:3000/graphql'
GRAPHQL_URL = 'https://devreservations.uncruise.com:3000/graphql'
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

def main():

  record_type = RecordType.AGENCY
  record_mode = RecordMode.QUERY

  # Record Types - agencyRemove, travelAgentRemove, clientRemove
  record_type_value = 'Unknown'
  if record_type == RecordType.CLIENT:
     record_type_value = 'clients'
  elif record_type == RecordType.AGENT:
     record_type_value = 'travelAgents'
  elif record_type == RecordType.AGENCY:
     record_type_value = 'agencies'

  # Initial request - no cursor
  json_res = fetch_items(record_type)
  incoming_items = len(json_res.get('data').get(record_type_value).get('edges'))

  page_info = None

  if "reservations" in json_res['data']: 
    process_record(RecordType.RESERVATION, record_mode, json_res)
    page_info = json_res['data'][record_type_value]['pageInfo']

  elif "clients" in json_res['data']:
    process_record(RecordType.CLIENT, record_mode, json_res)
    page_info = json_res['data'][record_type_value]['pageInfo']

  elif "travelAgents" in json_res['data']:
    process_record(RecordType.AGENT, record_mode, json_res)
    page_info = json_res['data'][record_type_value]['pageInfo']

  elif "agencies" in json_res['data']:
    process_record(RecordType.AGENCY, record_mode, json_res)
    page_info = json_res['data'][record_type_value]['pageInfo']

  else:
    print("unknown response type")

  # Check for next page
  #
  while page_info['hasNextPage'] or incoming_items == 500:

    cursor = page_info['endCursor']
    access_token = json_res['extensions']['access_token']
    json_res = fetch_items(record_type, cursor, access_token) 
    incoming_items = len(json_res.get('data').get(record_type_value).get('edges'))

    if "reservations" in json_res['data']: 
      process_record(RecordType.RESERVATION, record_mode, json_res)
      page_info = json_res['data'][record_type_value]['pageInfo']

    elif "clients" in json_res['data']:
      process_record(RecordType.CLIENT, record_mode, json_res)
      page_info = json_res['data'][record_type_value]['pageInfo']

    elif "travelAgents" in json_res['data']:
      process_record(RecordType.AGENT, record_mode, json_res)
      page_info = json_res['data'][record_type_value]['pageInfo']

    elif "agencies" in json_res['data']:
      process_record(RecordType.AGENCY, record_mode, json_res)
      page_info = json_res['data'][record_type_value]['pageInfo']

    else:
      print("unknown query type")       

#####################################################
#
# update_record - update a specific record by id, update isInternal on all records because that is
#   used as the workaround flag for paging
#
#####################################################
def update_record_paging(record_type: RecordType, id_value, access_token):
   
  query = "Unknown"
  with open('queries/update_paging.graphQL', 'r') as file:
    query = file.read()

  query = query.replace('ID_VALUE', id_value)

  # Record Types - agencyRemove, travelAgentRemove, clientRemove
  record_type_value = 'Unknown'
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
# update_record - update a specific record by id
#
#####################################################
def update_record(record_type: RecordType, id_value, access_token):
   
  query = "Unknown"
  with open('queries/update_' + record_type.name.lower() + '.graphQL', 'r') as file:
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

def login():

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

#####################################################
#
# fetch_items - responsible for initial page and additional page results based on cursor
#
#####################################################
def fetch_items(record_type: RecordType, cursor = None, access_token = None):
   
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

  input_query = 'Unknown'
  if record_type == RecordType.CLIENT:
     input_query = 'Clients'
  elif record_type == RecordType.AGENT:
     input_query = 'Agents'
  elif record_type == RecordType.AGENCY:
     input_query = 'Agencies'

  with open('queries/get' + input_query + '.graphQL', 'r') as file:
    query = file.read()

  variables = {
    'first': 500,  # Number of items to fetch (500 is the max)
    'after': cursor  # Cursor for pagination
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
def process_record(record_type: RecordType, record_mode: RecordMode, json_res):

  # Flatten the JSON data (results)
  flattened_data = flatten_json_results(json_res)

  bookingUpsertFile = Path(record_type.name + 'Upsert.csv')
  bookingUpsertFileExists = bookingUpsertFile.is_file()

  # Write to CSV file
  with open(record_type.name + 'Upsert.csv', 'a+', newline='') as csvfile:
      writer = csv.DictWriter(csvfile, fieldnames=flattened_data.keys())
      if not bookingUpsertFileExists:
          writer.writeheader()
      writer.writerow(flattened_data)

  # Record Types - agencyRemove, travelAgentRemove, clientRemove
  record_type_value = 'Unknown'
  if record_type == RecordType.CLIENT:
     record_type_value = 'clients'
  elif record_type == RecordType.AGENT:
     record_type_value = 'travelAgents'
  elif record_type == RecordType.AGENCY:
     record_type_value = 'agencies'
  
  edges = json_res.get('data').get(record_type_value).get('edges')
  access_token = json_res['extensions']['access_token']

  da_flatten_list(record_type, record_mode, edges, access_token)

def da_flatten_list(record_type: RecordType, record_mode: RecordMode, json_list, access_token):

  # Create a list of dictionaries for CSV writing
  csv_data = []
  for index, item in enumerate(json_list):
      
      if isinstance(item, dict):
          
          # Check to clear out automation created record
          id_value = item['node']['id']

          should_process_record = False
          if record_type == RecordType.CLIENT:

            should_process_record = ((len(item['node']['classifications']) > 0 and 
              'SAILED' in item['node']['classifications'][0].get('classification').get('type').get('id')) or 
              (not item['node']['guestType'] == None and 'REGULAR' in item['node']['guestType']['code']))
          elif record_type == RecordType.AGENT:

            should_process_record = (not item['node']['iatan'] == None and 'holderName' in item['node']['iatan'])
          elif record_type == RecordType.AGENCY:

            should_process_record = (not item['node']['defaultLanguage'] == None and 'id' in item['node']['defaultLanguage'])

          if (should_process_record):

            print('Processing ' + id_value + ' index: ' + str(index))

            # Update Paging on all Records until 255 paging Jira ticket fixed
            update_record_paging(record_type, id_value, access_token)

            if record_mode == RecordMode.DELETE:
               
                print('Deleting ' + id_value + ' index: ' + str(index))
                id_value = delete_record(record_type, id_value, access_token)

            elif record_mode == RecordMode.UPDATE:

                should_update_record = (item['node']['isConsortium'] == False)
                if should_update_record:

                    print('Updating ' + id_value + ' index: ' + str(index))
                    id_value = update_record(record_type, id_value, access_token)
                else:
                    id_value = None

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
          
          flattened_item = flatten_json_lists(item)

          if next(iter(flattened_item.values())) == None:
              continue
          
          reservationKey = ''
          if next(iter(flattened_item.keys())) == 'node_id':
            reservationKey = next(iter(flattened_item.values()))

          # Add an identifier for each item in the list  
          flattened_item['index'] = index
          csv_data.append(flattened_item)

          if not item.get('node') == None and not item.get('node').get('guests') == None:
            guests = item.get('node').get('guests')
            da_flatten_list_bookings(guests, 'bookings_guests', reservationKey)

          if not item.get('node') == None and not item.get('node').get('agency') == None:
            agencies = item.get('node').get('agency')
            da_flatten_list_bookings(agencies, 'bookings_agencies', reservationKey)

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
            out[name[:-1]] = x  # Save the list under the key

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
    
    full_filename = os.path.join("C:/repo/python-graphql/output_csv", filename)

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
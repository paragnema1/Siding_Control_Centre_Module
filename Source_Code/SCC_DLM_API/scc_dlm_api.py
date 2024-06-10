'''
*****************************************************************************
*File : scc_dlm_api.py
*Module : SCC 
*Purpose : SCC data logging module API class for database operations
*Author : Sumankumar Panchal
*Copyright : Copyright 2020, Lab to Market Innovations Private Limited
*****************************************************************************
'''

'''Import python packages'''
'''Import SCC packages '''
import sys
from scc_dlm_conf import *
from scc_log import *
import json
from peewee import * #module for database operations
from datetime import datetime, timedelta
from scc_dlm_model import *
from scc_layout_model import *
sys.path.insert(2, "./common")


TOTAL_SECTION_TRACE_FOR_TRAIN = 5 #initializing total section trace for train
SECTION_TRACE_FOR_TRAIN_LIST = ["S1", "S2", "S12", "S13", "S14"] #initializing list of section to trace

ENTRY_EXIT_SECTION_LIST = ["S1", "S2"] #initializing list of entry and exit section
UNLOADING_SECTION_LIST = ["S12", "S13", "S14"] #initializing list of unloading section
MIDDLE_SECTION_LIST = [
    "S3",
    "S4",
    "S5",
    "S6",
    "S7",
    "S8",
    "S9",
    "S10",
    "S11"] #initializing list of middle section


class TrainEntryExitTrace(): #class initializing train entry and exit trace variables.
    def __init__(self):
        self.ts = 0.0
        self.section_id = "none"
        self.in_torpedo_axle_count = 0
        self.out_torpedo_axle_count = 0
        self.engine_axle_count = 0
        self.section_status = "none"
        self.direction = "none"
        self.speed = 0.0
        self.torpedo_status = "none"
        self.torpedo_id = 0
        self.engine_id = 0

class SectionConnections: #class for initialization of secion connection variables.
    def __init__(self):
        self.section_id = "none"
        self.left_normal = "none"
        self.right_normal = "none"
        self.left_reverse = "none"
        self.right_reverse = "none"
        self.torpedo_id = 0
        self.engine_id = 0
        self.in_torpedo_axle_count = 0
        self.out_torpedo_axle_count = 0
        self.entry_time = 0
        self.exit_time = 0
        self.torpedo_detected = False
        self.unloaded_entry_time = 0
        self.unloaded_exit_time = 0
        self.in_axles = 0
        self.out_axles = 0


class Torpedo: #class for initialization of torpedo info variables.
    def __init__(self):
        self.section_id = "none"
        self.torpedo_id = 0
        self.engine_id = 0
        self.unloaded_entry_time = 0
        self.unloaded_exit_time = 0
        self.entry_time = 0
        self.exit_time = 0
        self.in_torpedo_axle_count = 0
        self.out_torpedo_axle_count = 0
        self.in_axles = 0
        self.out_axles = 0
        self.torpedo_detected = False


class SccAPI:
    '''OCC DAtabase operations such as Select, Insert, Delete records'''

    def __init__(self): #initializing all variables to empty
        self.train_trace_obj_list = []
        self.section_conn_obj_list = []
        self.torpedo_obj_list = []
        self.entry_torpedo_id = 0
        self.entry_engine_id = 0
        self.torpedo_id = 0
        self.engine_id = 0
        self.last_tt_record_inserted = {
            's3': False, 's4': False, 's7': False, 's8': False, 's11': False}

    #[Connect passed argument file to postgresql database]
    def connect_database(self, config):
        '''Establish connection with database'''
        try:
            #taking connection parameters from passed config file.
            self.json_data = config.json_data
            self.db_name = self.json_data["DATABASE"]["DB_NAME"]
            self.user = self.json_data["DATABASE"]["USER"]
            self.password = self.json_data["DATABASE"]["PASSWORD"]
            self.host = self.json_data["DATABASE"]["HOST"]
            self.port = 5432

            if len(self.db_name) == 0: #checking if database is empty
                Log.logger.critical(
                    "scc_dlm_api: connect_database:  database name missing")
                
            else:
                #[Passing connection parameters as a argument to PostgresqlDatabase function.]
                psql_db = PostgresqlDatabase(
                    self.db_name,
                    user=self.user,
                    password=self.password,
                    host=self.host,
                    port=self.port)
                
                if psql_db: #if psql_db is True.
                    try:
                        psql_db.connect() #connecting psql_db to database
                        Log.logger.info(
                            f'scc_dlm_api: database connection successful')
                        return psql_db #returning psql_db
                    except Exception as e:
                        Log.logger.critical(
                            f'scc_dlm_api: connect_database: {e}')
                        sys.exit(1)
                else:
                    return None
        except Exception as ex:
            Log.logger.critical(
                "scc_dlm_api: connect_database: Exception: ", ex)

    def get_user_roles(self, username_param): #provide user role of passed username from OccUserInfo table in scc_dlm_model.py.
        '''get user roles from database'''
        try:
            user_details_table = OccUserInfo.select().where(
                OccUserInfo.username == username_param).get() #fetches row in OccUserInfo table where username = passed username_param
            Log.logger.info(
                f'Section reset request received from user:{username_param}, and user role is {user_details_table.roles[0]}') #log username and role with level info
            return user_details_table.roles #returns role from fetched row
        except DoesNotExist:
            Log.logger.warning(
                f'Requested username does not exist in the database')
            return None

    def get_dpu_id(self, section_id_param): #provide dpu_id of passed section_id from YardConfigInfo table in scc_layout_model.py.
        '''search dpu id of selected section_id'''
        try:
            yard_config_table = YardConfigInfo.select().where(
                YardConfigInfo.section_id == section_id_param).get() #fetches row in YardConfig Table for which section_id = passed section_id_param
            Log.logger.info(
                f'SECTION ID:{section_id_param} =>  DPU_ID: {yard_config_table.dpu_id}') #log section_id and dpu_id with level info
            return yard_config_table.dpu_id #return dpu_id from fetched row
        except DoesNotExist:
            Log.logger.warning(
                f'Requested DPU_ID does not exist in the database')
            return None

    def insert_section_info(self, data): #method to insert passed data into section info table.
        ''' insert section information '''
        try:
            json_data = json.loads(data) #convert data to python object.
            '''list'''
            list_tuple = []
            d = []
            for i in range(len(json_data["sections"])): #adding passed data to list d.
                d.append(json_data["ts"])
                d.append(json_data["sections"][i]["section_id"])
                d.append(json_data["sections"][i]["section_status"])
                d.append(json_data["sections"][i]["engine_axle_count"])
                d.append(json_data["sections"][i]["torpedo_axle_count"])
                d.append(json_data["sections"][i]["direction"])
                d.append(json_data["sections"][i]["speed"])
                d.append(json_data["sections"][i]["torpedo_status"])
                d.append(json_data["sections"][i]["first_axle"])
                t = tuple(d) #converting list d to tuple t
                list_tuple.append(t) #appending tuple t to list_tuple
                d.clear() #clearing list d

            SectionInfo.insert_many(
                list_tuple,
                fields=[
                    SectionInfo.ts,
                    SectionInfo.section_id,
                    SectionInfo.section_status,
                    SectionInfo.engine_axle_count,
                    SectionInfo.torpedo_axle_count,
                    SectionInfo.direction,
                    SectionInfo.speed,
                    SectionInfo.torpedo_status,
                    SectionInfo.first_axle]).execute() #using insert_many function to insert all data in list_tuple to SectionInfo table

        except Exception as ex:
            Log.logger.critical(
                f'scc_dlm_api: insert_section_info: exception:  {ex}')

    def insert_section_playback_info(self, data): #saving passed data to section_playback_table.
        ''' insert section information '''
        try:
            json_data = json.loads(data) #convert data to python object.

            section_playback_table = SectionPlaybackInfo() #initializing SectionPlaybackInfo class of scc_dlm_model.py containing timestamp and sections.
            section_playback_table.ts = json_data["ts"] #storing timestamp from passed data to section_playback_table object.
            section_playback_table.sections = json_data['sections'] #storing sections from passed data to section_playback_table object.

            section_playback_table.save() #saving passed data to section_playback_table.

        except Exception as ex:
            Log.logger.critical(
                f'scc_dlm_api: insert_section_info: exception:  {ex}')

    def read_section_playback_info(self): #method to print section_id and section_status from section_playback_table in scc_dlm_model.py
        try:
            section_playback_model = SectionPlaybackInfo() #initialising SectionPlaybackInfo class of scc_dlm_model.py
            section_playback_records = section_playback_model.select() #selecting all records from section_playback_table
            
            for i in section_playback_records: #printing all section_id and section_status from all sections in section_playback_records.
                section_msg = i.sections 
                for j in range(len(section_msg)):
                    Log.logger.info(
                        f'ts:{i.ts},{section_msg[j]["section_id"]},{section_msg[j]["section_status"]}')
        except Exception as ex:
            Log.logger.critical(
                f'scc_dlm_api: read_section_playback_info: exception: {ex}')

    def insert_dp_info(self, data): #method to insert passed data to dp_info table in scc_dlm_model.py
        ''' insert DP information '''
        try:
            json_data = json.loads(data) #convert data to python object.

            '''list'''
            list_tuple = []
            d = []
            for i in range(len(json_data["dps"])): #adding passed data to list d.
                d.append(json_data["ts"])
                d.append(json_data["dpu_id"])
                d.append(json_data["dps"][i]["dp_id"])
                d.append(json_data["dps"][i]["axle_count"])
                d.append(json_data["dps"][i]["axle_type"])
                d.append(json_data["dps"][i]["direction"])
                d.append(json_data["dps"][i]["speed"])
                t = tuple(d) 
                list_tuple.append(t)
                d.clear()

            DpInfo.insert_many(
                list_tuple,
                fields=[
                    DpInfo.ts,
                    DpInfo.dpu_id,
                    DpInfo.dp_id,
                    DpInfo.axle_count,
                    DpInfo.axle_type,
                    DpInfo.direction,
                    DpInfo.speed]).execute() #inerting data in dpInfo table.

        except Exception as ex:
            Log.logger.critical(
                f'scc_dlm_api: insert_section_info: exception:  {ex}')

    def select_section_info(self): #method to return all records of section_info table scc_dlm_model.py
        '''Get store records from scc_section_info'''
        try:
            self.model_name = SectionInfo() #initialising SectionInfo class of scc_dlm_model.py
            self.records = self.model_name.select() #selecting all records from section_info table
            return self.records #returning all records
        except Exception as ex:
            Log.logger.critical(
                f'scc_dlm_api: select_section_info: exception: {ex}')

    def read_section_config_info(self): #method to return all records from section_config_info table in scc_layout_model.py
        '''read section configuration information from database'''
        try:
            config_model_name = SectionConfigInfo() #initialising SectionConfigInfo class of scc_layout_model.py
            config_records = config_model_name.select() #select is a sql query under peewee module, it is used to select all records from the table
            return config_records #returning all records
        except Exception as ex:
            Log.logger.critical(
                f'scc_dlm_api: select_scc_config_info: exception: {ex}')

    def read_yard_config_info(self): #method to return all records from yard_config_info table in scc_layout_model.py
        '''read section configuration information from database'''
        try:
            yard_config_model = YardConfigInfo()
            yard_config_records = yard_config_model.select()
            return yard_config_records
        except Exception as ex:
            Log.logger.critical(
                f'scc_dlm_api: read_yard_config_info: exception: {ex}')

    def read_section_connections_info(self): #method to log and return all records form layout section connection table in scc_layout_model.py
        '''read section configuration information from database'''
        try:
            section_connections_model = LayoutSectionConnectionsInfo() #initialising LayoutSectionConnectionsInfo class of scc_layout_model.py
            section_connections_records = section_connections_model.select() #selecting rows from table layout_section_info
            Log.logger.info(section_connections_records) #logging layout_section_info table with level info.
            return section_connections_records #returning section_connections_records
        except Exception as ex: #if any exception occurs then it will show error with level critical
            Log.logger.critical(
                f'scc_dlm_api: select_scc_config_info: exception: {ex}')

    def reset_train_trace_info(self): #method to reset train_trace_obj_list
        '''Reset train trace objects'''
        try:
            for i in range(len(self.train_trace_obj_list)):
                self.train_trace_obj_list[i].ts = 0.0
                self.train_trace_obj_list[i].in_torpedo_axle_count = 0
                self.train_trace_obj_list[i].out_torpedo_axle_count = 0
                self.train_trace_obj_list[i].engine_axle_count = 0
                self.train_trace_obj_list[i].section_status = "cleared"
                self.train_trace_obj_list[i].direction = "none"
                self.train_trace_obj_list[i].speed = 0.0
                self.train_trace_obj_list[i].torpedo_status = "none"
                self.train_trace_obj_list[i].torpedo_id = 0
                self.train_trace_obj_list[i].engine_id = 0

            Log.logger.info(f'reset train trace info...') #logging reset train trace info with level info
        except Exception as ex:
            Log.logger.critical(
                f'scc_dlm_api: init_train_movement_info: excpetion: {ex}')

    def insert_train_trace_info(self, data): 
        #add train trace info into train_trace_table iff in passed data (torpedo_axle_count is 16 and direction is in) OR (torpedo axle count is 0 and direction is out or none)
        #add data into table for each change in torpedo_axle_count
        '''for all sections in train_trace_obj_list, 
                for section id(of passed data) == section_id(of train_trace_obj_list),
                    if in passed data torpedo_axle_count is 16 and direction is in,
                       if in train_trace_obj_list torpedo_axle_count < 16,
                            #save passed data to train_trace_table
                    
                    if for passed data direction is out or none,
                        if torpedo_axle_count of passed data is ==0,
                            if out_torpedo_axle_count of train_trace_obj_list > 0,
                                save passed data to train_trace_table
                '''
        
         
        '''insert section inform to trace train entry and exit'''
        try:
            json_data = json.loads(data) #convert data to python object

            for i in range(TOTAL_SECTION_TRACE_FOR_TRAIN): #looping through all sections in train_trace_obj_list
                for j in range(len(json_data['sections'])): #looping through all sections in json_data
                    if json_data['sections'][j]['section_id'] == self.train_trace_obj_list[i].section_id: #if section_id of passed data matches with section_id of train_trace_obj_list
                        '''compare section torpedo_axle_count is 16 or not'''
                        if json_data['sections'][j]['torpedo_axle_count'] == 16 and json_data['sections'][j]['direction'] == "in": #if in passed data torpedo_axle_count is 16 and direction is in
                            '''check previous section torpedo_axle_count is less than 16 or not'''
                            if self.train_trace_obj_list[i].in_torpedo_axle_count < 16: #if in train_trace_obj_list torpedo_axle_count is less than 16
                                '''insert record if previous section torpedo_axle_count less than 16 and current
                                torpedo_axle_count is 16'''
                                train_trace_table = TrainTraceInfo() #initialising TrainTraceInfo class of scc_dlm_model.py
                                train_trace_table.ts = json_data["ts"]
                                train_trace_table.section_id = json_data["sections"][j]["section_id"]
                                train_trace_table.section_status = json_data["sections"][j]["section_status"]
                                train_trace_table.torpedo_axle_count = json_data[
                                    "sections"][j]["torpedo_axle_count"]
                                train_trace_table.engine_axle_count = json_data[
                                    "sections"][j]["engine_axle_count"]
                                train_trace_table.direction = json_data["sections"][j]["direction"]
                                train_trace_table.speed = json_data["sections"][j]["speed"]
                                train_trace_table.torpedo_status = json_data["sections"][j]["torpedo_status"]
                                train_trace_table.first_axle = json_data["sections"][j]["first_axle"]
                                self.entry_torpedo_id = self.entry_torpedo_id + 1
                                self.entry_engine_id = self.entry_engine_id + 1
                                train_trace_table.torpedo_id = self.entry_torpedo_id
                                train_trace_table.engine_id = self.entry_engine_id
                                train_trace_table.save() #save passed data to train_trace_table
                                '''save it in train_trace_obj_list'''
                                self.train_trace_obj_list[i].in_torpedo_axle_count = json_data['sections'][j]['torpedo_axle_count'] #making torpedo_axle_count of train_trace_obj_list = torpedo_axle_count of passed data
                            else: #if torpedo_axle_count of train_trace_obj_list is >= 16, then it will not add data to train_trace_table.
                                self.train_trace_obj_list[i].in_torpedo_axle_count = json_data['sections'][j]['torpedo_axle_count'] 
                        else: #if torpedo_axle_count of passed data is not 16 and direction is not in
                            self.train_trace_obj_list[i].in_torpedo_axle_count = json_data['sections'][j]['torpedo_axle_count']

                        if json_data['sections'][j]['direction'] == "out" or json_data['sections'][j]['direction'] == "none": #if direction of passed data is out or none
                            if json_data['sections'][j]['torpedo_axle_count'] >= 1: #if torpedo_axle_count of passed data is >= 1
                                self.train_trace_obj_list[i].out_torpedo_axle_count = json_data['sections'][j]['torpedo_axle_count'] #making out_torpedo_axle_count of train_trace_obj_list = torpedo_axle_count of passed data
                            elif json_data['sections'][j]['torpedo_axle_count'] == 0: #if torpedo_axle_count of passed data is 0
                                if self.train_trace_obj_list[i].out_torpedo_axle_count > 0: #if out_torpedo_axle_count of train_trace_obj_list is > 0
                                    train_trace_table = TrainTraceInfo()
                                    train_trace_table.ts = json_data["ts"]
                                    train_trace_table.section_id = json_data["sections"][j]["section_id"]
                                    train_trace_table.section_status = json_data[
                                        "sections"][j]["section_status"]
                                    train_trace_table.torpedo_axle_count = json_data[
                                        "sections"][j]["torpedo_axle_count"]
                                    train_trace_table.engine_axle_count = json_data[
                                        "sections"][j]["engine_axle_count"]
                                    train_trace_table.direction = json_data["sections"][j]["direction"]
                                    train_trace_table.speed = json_data["sections"][j]["speed"]
                                    train_trace_table.torpedo_status = json_data[
                                        "sections"][j]["torpedo_status"]
                                    train_trace_table.first_axle = json_data["sections"][j]["first_axle"]
                                    train_trace_table.torpedo_id = self.entry_torpedo_id
                                    train_trace_table.engine_id = self.entry_engine_id
                                    train_trace_table.save() #save passed data to train_trace_table
                                    self.train_trace_obj_list[i].out_torpedo_axle_count = 0
                                else:
                                    pass
                            else:
                                pass
                        else:
                            pass
                    else:
                        pass
        except Exception as ex:
            Log.logger.critical(
                f'scc_dlm_api: insert_train_trace_info: exception: {ex}')

    def init_section_connections_info(self): #method to store sectiom connections information in section_conn_obj_list and torpedo_obj_list
        try:
            section_connections_db_records = self.read_section_connections_info() #method to read layout section connections information and storing in section_connections_db_records
            for sc in section_connections_db_records:
                Log.logger.info(
                    f'SECTION_ID: {sc.section_id}, LEFT_SECTION: {sc.left_normal}, RIGHT_SECTION: {sc.right_normal}') #logging section_id, left_section and right_section from each record in section_connections_db_records

            for sc in section_connections_db_records:
                self.section_conn_obj_list.append(SectionConnections()) #appending data of all variables from section_connections class to section_conn_obj_list
                self.torpedo_obj_list.append(Torpedo()) #appending data of all variables from Torpedo class to torpedo_obj_list

            sc_idx = 0 
            for sc in section_connections_db_records: #storing data from section_connections_db_records to section_conn_obj_list and torpedo_obj_list
                self.section_conn_obj_list[sc_idx].section_id = sc.section_id #
                self.section_conn_obj_list[sc_idx].left_normal = sc.left_normal
                self.section_conn_obj_list[sc_idx].right_normal = sc.right_normal
                self.section_conn_obj_list[sc_idx].left_reverse = sc.left_reverse
                self.section_conn_obj_list[sc_idx].right_reverse = sc.right_reverse
        
                self.torpedo_obj_list[sc_idx].section_id = sc.section_id
                sc_idx += 1
                
        except Exception as ex: #if any exception occurs then it will show error with level critical
            Log.logger.critical(
                f'init_section_connections_info: exception {ex}')

    def init_train_trace_info(self):  #ADD section id's from Section_trace_for_train_list to section_id in train_trace_obj_list
        '''initialise train trace objects'''
        try:
            for i in range(TOTAL_SECTION_TRACE_FOR_TRAIN): #appending trainEntryExitTrace class variables to train_trace_obj_list
                self.train_trace_obj_list.append(TrainEntryExitTrace())

            for i in range(TOTAL_SECTION_TRACE_FOR_TRAIN): #adding section id of section_trace_for_train_list to section_id variable in train_trace_obj_list
                self.train_trace_obj_list[i].section_id = SECTION_TRACE_FOR_TRAIN_LIST[i] #updating section_id of each section corresponding to train_trace_obj_list

            Log.logger.info(f'init train trace info...')
        except Exception as ex:
            Log.logger.critical(
                f'scc_dlm_api: init_train_movement_info: excpetion: {ex}')

    def update_torpedo_id(self, data): #update torpedo id(in section_conn_obj_list) of all section_id(in passed data).
        try:
            for sc_idx in range(len(self.section_conn_obj_list)): #iterating sc_idx through all records of secion_conn_obj_list
                Log.logger.info(
                    f'{self.section_conn_obj_list[sc_idx].section_id}') #logging section_id from each records of section_conn_obj_list
                if self.section_conn_obj_list[sc_idx].section_id == str(data["section_id"]): #if section_id(passed data) == section_id(section_conn_obj_list), then updata torpedo id in section_conn_obj_list
                    self.section_conn_obj_list[sc_idx].torpedo_id = str(
                        data["torpedo_id"])
                    Log.logger.info(
                        f'Section : {section_id}, Torpedo ID : {torpedo_id} updated') #logging all updated torpedo_id with section_id.
                else:
                    Log.logger.info(
                        f'update torpedo id : section id did not match') #if section_id does not match then log section id did not match.
                    pass
        except Exception as ex:
            Log.logger.critical(f'update_torpedo_id: exception : {ex}')

    def torpedo_info_sub_fn(self, in_client, user_data, message): #update torpedo id of all section_id in passed attribute message.
        try:
            Log.logger.info(f'torepdo_info mqtt msg received')
            msg_payload = json.loads(message.payload) #convert passed message to python object

            self.update_torpedo_id(msg_payload) #update torpedo id of all section_id in passed message
        except Exception as ex:
            Log.logger.critical(f'torpedo_info_sub_fn: exception: {ex}')

    def reset_section_connections_info(self): #reset all section variables in section_conn_obj_list.
        try:
            for sc_idx in range(len(self.section_conn_obj_list)): #iterating sc_idx through all records of secion_conn_obj_list
                self.section_conn_obj_list[sc_idx].torpedo_id = 0
                self.section_conn_obj_list[sc_idx].engine_id = 0
                self.section_conn_obj_list[sc_idx].in_torpedo_axle_count = 0
                self.section_conn_obj_list[sc_idx].out_torpedo_axle_count = 0
                self.section_conn_obj_list[sc_idx].entry_time = 0
                self.section_conn_obj_list[sc_idx].exit_time = 0
                self.section_conn_obj_list[sc_idx].torpedo_detected = False
        except Exception as ex:
            Log.logger.critical(
                f'init_section_connections_info: exception {ex}')

    def torpedo_performance(self, data):
        #updating data into torpedo_obj_list only iff (in passed data torpedo_axle_count is >= 12) OR (in passed data torpedo_axle_count is < 6 and direction is Out)
        
        try:
            json_data = json.loads(data) #convert data to python object
            section_list = {} #created empty dictionary.

            for json_idx in range(len(json_data['sections'])): #json_data ki section key ki jo list hai usko [json_idx] se ek-ek karke call karega.
                section_list[json_data['sections'][json_idx]
                             ['section_id']] = json_data['sections'][json_idx] 
                '''jo list ka index uper se call ho raha hai, usko 'section_list' dictionary mai key 'section_id' ki  value bana ke store kar rahe hai.'''
                '''eg:- json_data = {'sections': [{'section_id': '1', 'section_name': 'section1'}, {'section_id': '2', 'section_name': 'section2'}]}, then
                   section_list = {'1': {'section_id': '1', 'section_name': 'section1'}, '2': {'section_id': '2', 'section_name': 'section2'}}
                '''

            for json_idx in range(len(json_data['sections'])): #iterating through (json_data dictionary's, sections key's Value(which is a list).
                if json_data['sections'][json_idx]['section_id'] in UNLOADING_SECTION_LIST: #uper wali list ka jo index call hua hai yadi uska section_id UNLOADING_SECTION_LIST mai hai
                    for sc_idx in range(len(self.torpedo_obj_list)): #iterating sc_idx through all records of torpedo_obj_list 
                        if json_data['sections'][json_idx]['section_id'] == self.torpedo_obj_list[sc_idx].section_id: #uper wali list ka jo index call hua hai yadi uska section_id == torpedo_obj_list ka kisi record ka section_id
                            if json_data['sections'][json_idx]['section_status'] != "none" or json_data[
                                    'sections'][json_idx]['direction'] != "none": #agar jo index call hua hai uska section_status none nahi hai YA direction none nahi hai
                                if json_data['sections'][json_idx]['torpedo_axle_count'] >= 12 and self.torpedo_obj_list[sc_idx].in_torpedo_axle_count < 12: #Agar called index ka (torpedo_axle_count 12 se barabar ya jyada hai) AUR torpedo_obj_list ka (in_torpedo_axle_count 12 se kam hai)
                                    
                                    #updating torpedo_obj_list sc_idx mai timestamp, torpedo_id, engine_id with json_data
                                    self.torpedo_obj_list[sc_idx].unloaded_entry_time = json_data["ts"] #ts in unix timestamp fomrat (a signed number).
                                    self.torpedo_obj_list[sc_idx].torpedo_id = "T" + time.strftime('%d%m%Y%H%M%S', time.localtime(json_data["ts"])) #converting json_data["ts"] to format (T + 2 digit day + 2 digit month + 4 digit year + 2 digit hour + 2 digit minute + 2 digit second)
                                    self.torpedo_obj_list[sc_idx].engine_id = "E" + time.strftime('%d%m%Y%H%M%S', time.localtime(json_data["ts"]))
                                    
                                    #logging from section_conn_obj_list ka sc_idx se section_id, torpedo_id, engine_id, unloaded_entry_time
                                    Log.logger.info(
                                        f'Section_id : {self.section_conn_obj_list[sc_idx].section_id},'
                                        f'torpedo_id : {self.section_conn_obj_list[sc_idx].torpedo_id},'
                                        f'engine_id: {self.section_conn_obj_list[sc_idx].engine_id},'
                                        f'unloaded entry ts: {self.section_conn_obj_list[sc_idx].unloaded_entry_time}')

                                    self.torpedo_obj_list[sc_idx].in_torpedo_axle_count = json_data[
                                        'sections'][json_idx]['torpedo_axle_count'] #updating (torpedo_obj_list sc_idx mai 'in_torpedo_axle_count') with (json_data ka sections key ki list ka json_idx se torpedo_axle_count)

                                    if self.torpedo_obj_list[sc_idx].torpedo_id != 0 and self.torpedo_obj_list[sc_idx].engine_id != 0: #agar (torpedo_obj_list ka sc_idx ka) 'torpedo_id' aur 'engine_id' 0 nahi hai
                                        '''insert torpedo entry time while entrying unloading section'''
                                        self.insert_torpedo_loaded_entry_info(
                                            self.torpedo_obj_list[sc_idx].torpedo_id,
                                            self.torpedo_obj_list[sc_idx].engine_id,
                                            self.torpedo_obj_list[sc_idx].unloaded_entry_time,
                                            self.torpedo_obj_list[sc_idx].section_id) #adding data into toredoperformance info table
                                    else:
                                        pass
                                else: #Agar isme se ek bhi satisfy na ho to(#Agar called index ka (torpedo_axle_count >= 12) AUR torpedo_obj_list ka (in_torpedo_axle_count < 12))
                                    self.torpedo_obj_list[sc_idx].in_torpedo_axle_count = json_data[
                                        'sections'][json_idx]['torpedo_axle_count'] #torpedo_obj_list ka sc_idx mai 'in_torpedo_axle_count' ko update karega (json_data ka sections key ki list ka json_idx se torpedo_axle_count)
                            else:
                                pass

                            '''-----------------------------------GET UNLOADING EXIT TIME-----------------------------------'''
                            if json_data['sections'][json_idx]['direction'] == "out" or json_data['sections'][json_idx]['direction'] == "none": # agar called index ka direction out ya none hai
                                if json_data['sections'][json_idx]['torpedo_axle_count'] >= 6: #agar called index ka torpedo_axle_count >=6
                                    self.torpedo_obj_list[sc_idx].out_torpedo_axle_count = json_data[
                                        'sections'][json_idx]['torpedo_axle_count'] #torpedo_obj_list ka sc_idx mai 'out_torpedo_axle_count' ko update karega (json_data ka sections key ki list ka json_idx se torpedo_axle_count
                                else:
                                    pass
                                if self.torpedo_obj_list[sc_idx].out_torpedo_axle_count >= 6 and json_data[
                                        'sections'][json_idx]['torpedo_axle_count'] < 6: #agar torpedo_obj_list ka sc_idx ka 'out_torpedo_axle_count' >=6 AUR json_data ka sections key ki list ka json_idx se torpedo_axle_count < 6
                                    self.torpedo_obj_list[sc_idx].unloaded_exit_time = json_data["ts"] #to torpedo_obj_list ka sc_idx mai 'unloaded_exit_time' ko update karega (json_data ka ts)
                                    
                                    #log info from torpedo_obj_list ka sc_idx se section_id, torpedo_id, engine_id, unloaded_exit_time
                                    Log.logger.info(f'Section_id : {self.torpedo_obj_list[sc_idx].section_id},'
                                                    f'torpedo_id : {self.torpedo_obj_list[sc_idx].torpedo_id},'
                                                    f'engine_id: {self.torpedo_obj_list[sc_idx].engine_id},'
                                                    f'unloaded exit ts: {self.torpedo_obj_list[sc_idx].unloaded_exit_time}')

                                    '''do not update db when torpedo id and engine id is 0'''
                                    if self.torpedo_obj_list[sc_idx].torpedo_id != 0 and self.torpedo_obj_list[sc_idx].engine_id != 0: #agar torpedo_obj_list ka sc_idx ka 'torpedo_id' aur 'engine_id' 0 nahi hai
                                        self.update_torpedo_unloaded_exit_info(
                                            self.torpedo_obj_list[sc_idx].torpedo_id,
                                            self.torpedo_obj_list[sc_idx].engine_id,
                                            self.torpedo_obj_list[sc_idx].unloaded_exit_time,
                                            self.torpedo_obj_list[sc_idx].section_id)
                                    else:
                                        pass

                                    self.torpedo_obj_list[sc_idx].out_torpedo_axle_count = 0
                                else:
                                    pass
                            else:
                                pass

                            Log.logger.info(
                                f'Section_id : {self.torpedo_obj_list[sc_idx].section_id},'
                                f'torpedo_id : {self.torpedo_obj_list[sc_idx].torpedo_id},'
                                f'engine_id: {self.torpedo_obj_list[sc_idx].engine_id},')
                                #f'in: {self.torpedo_obj_list[sc_idx].in_torpedo_axle_count},'
                                #f'out: {self.torpedo_obj_list[sc_idx].out_torpedo_axle_count}')
                        else:
                            pass
                else:
                    pass
        except Exception as ex:
            Log.logger.critical(f'torpedo_performance: exception {ex}')

    def yard_performance(self, data):
        try:
            json_data = json.loads(data) 
            section_list = {}

            for json_idx in range(len(json_data['sections'])): #create section_list
                section_list[json_data['sections'][json_idx]
                             ['section_id']] = json_data['sections'][json_idx]

            for json_idx in range(len(json_data['sections'])): #iterating json_idx in json_data['sections'] list.

                '''--------------------------------------ENTRY EXIT SECTION LOGIC ------------------------------'''
                if json_data['sections'][json_idx]['section_id'] in ENTRY_EXIT_SECTION_LIST: #if section_id of json_data['sections'][json_idx] is in ENTRY_EXIT_SECTION_LIST
                    for sc_idx in range(len(self.section_conn_obj_list)): #iterating sc_idx through all records of section_conn_obj_list
                        if json_data['sections'][json_idx]['section_id'] == self.section_conn_obj_list[sc_idx].section_id: #if section_id of json_data['sections'][json_idx] == section_id of section_conn_obj_list[sc_idx]

                            '''--------------------------GET TRAIN ENTRY TIME------------------------------'''
                            if json_data['sections'][json_idx]['section_status'] == "occupied" and json_data[
                                    'sections'][json_idx]['direction'] == "in": #if for json_data['sections'][json_idx] section_status is occupied and direction is in.
                                if json_data['sections'][json_idx]['torpedo_axle_count'] >= 12 and self.section_conn_obj_list[sc_idx].in_torpedo_axle_count < 12: #if for (json_data['sections'][json_idx] torpedo_axle_count >=12) & (section_conn_obj_list[sc_idx] in_torpedo_axle_count < 12)

                                    #update torpedo_id, engine_id and entry time in section_conn_obj_list
                                    self.torpedo_id = "T" + \
                                        time.strftime(
                                            '%d%m%Y%H%M%S', time.localtime(json_data["ts"]))
                                    self.engine_id = "E" + \
                                        time.strftime(
                                            '%d%m%Y%H%M%S', time.localtime(json_data["ts"]))

                                    self.section_conn_obj_list[sc_idx].torpedo_id = self.torpedo_id
                                    self.section_conn_obj_list[sc_idx].engine_id = self.engine_id
                                    self.section_conn_obj_list[sc_idx].entry_time = json_data["ts"]

                                    if self.section_conn_obj_list[sc_idx].torpedo_id != 0 and self.section_conn_obj_list[sc_idx].engine_id != 0: #if torpedo_id and engine_id of section_conn_obj_list[sc_idx] is not 0
                                        '''insert new train entry in db'''
                                        self.insert_train_entry_info(
                                            self.torpedo_id, self.engine_id, json_data["ts"]) #inserting data into train_entry_info table
                                    else:
                                        pass

                                    if self.section_conn_obj_list[sc_idx].left_normal != "NONE":
                                        sec_id = self.section_conn_obj_list[sc_idx].left_normal 

                                    if self.section_conn_obj_list[sc_idx].right_normal != "NONE":
                                        sec_id = self.section_conn_obj_list[sc_idx].right_normal

                                    Log.logger.info(
                                        f'Section_id : {self.section_conn_obj_list[sc_idx].section_id},'
                                        f'torpedo_id : {self.section_conn_obj_list[sc_idx].torpedo_id},'
                                        f'engine_id: {self.section_conn_obj_list[sc_idx].engine_id},'
                                        f'entry ts: {self.section_conn_obj_list[sc_idx].entry_time}')

                                    self.section_conn_obj_list[sc_idx].in_torpedo_axle_count = json_data[
                                        'sections'][json_idx]['torpedo_axle_count']
                                else:
                                    self.section_conn_obj_list[sc_idx].in_torpedo_axle_count = json_data[
                                        'sections'][json_idx]['torpedo_axle_count']
                            else:
                                pass

                            '''-------------------------------------GET TRAIN EXIT TIME---------------------------------'''

                            if json_data['sections'][json_idx]['direction'] == "out": #if json_data['sections'][json_idx]['direction'] == "out"

                                sec_id = self.section_conn_obj_list[sc_idx].left_normal #then sec_id will be left_normal of section_conn_obj_list[sc_idx]

                                for section_idx in range(len(self.section_conn_obj_list)): #iterating section_idx in section_conn_obj_list
                                    if self.section_conn_obj_list[section_idx].section_id == sec_id: #if section_conn_obj_list[section_idx].section_id == sec_id
                                        if self.section_conn_obj_list[section_idx].torpedo_id != 0: #if torpedo_id is not zero
                                            self.section_conn_obj_list[
                                                sc_idx].torpedo_id = self.section_conn_obj_list[section_idx].torpedo_id
                                            self.section_conn_obj_list[
                                                sc_idx].engine_id = self.section_conn_obj_list[section_idx].engine_id #update torpedo id and engine id.
                                        else:
                                            pass
                                    else:
                                        pass

                                if json_data['sections'][json_idx]['torpedo_axle_count'] >= 6: #if torpedo_axle_count >= 6 then update out_torpedo_axle_count
                                    self.section_conn_obj_list[sc_idx].out_torpedo_axle_count = json_data[
                                        'sections'][json_idx]['torpedo_axle_count']
                                else:
                                    pass

                                '''update train exit time in db'''
                                if self.section_conn_obj_list[sc_idx].out_torpedo_axle_count >= 6 and json_data['sections'][json_idx]['torpedo_axle_count'] <= 6: #log torpedo exciting detected

                                    Log.logger.info(
                                        'torpedo exiting detected!!')
                                    self.section_conn_obj_list[sc_idx].exit_time = json_data["ts"]

                                    if self.section_conn_obj_list[sc_idx].torpedo_id != 0 and self.section_conn_obj_list[sc_idx].engine_id != 0: #if torpedo_id & engine_id is not zero.
                                        Log.logger.info(
                                            f'updated train exit info')
                                        self.update_train_exit_info(
                                            self.section_conn_obj_list[sc_idx].torpedo_id,
                                            self.section_conn_obj_list[sc_idx].engine_id,
                                            self.section_conn_obj_list[sc_idx].exit_time)

                                        self.section_conn_obj_list[sc_idx].out_torpedo_axle_count = 0
                                        self.section_conn_obj_list[sc_idx].in_torpedo_axle_count = 0
                                    else:
                                        pass

                                    Log.logger.info(
                                        f'Section_id : {self.section_conn_obj_list[sc_idx].section_id},'
                                        f'torpedo_id : {self.section_conn_obj_list[sc_idx].torpedo_id},'
                                        f'engine_id: {self.section_conn_obj_list[sc_idx].engine_id},'
                                        f'train exit ts: {self.section_conn_obj_list[sc_idx].exit_time}')

                                else:
                                    pass
                            else:
                                pass

                            Log.logger.info(
                                f'Section_id : {self.section_conn_obj_list[sc_idx].section_id},'
                                f'torpedo_id : {self.section_conn_obj_list[sc_idx].torpedo_id},'
                                f'engine_id: {self.section_conn_obj_list[sc_idx].engine_id},')
                                #f'in: {self.section_conn_obj_list[sc_idx].in_torpedo_axle_count},'
                                #f'out: {self.section_conn_obj_list[sc_idx].out_torpedo_axle_count}')
                        else:
                            pass
                else:
                    pass

                '''------------------------------------------MIDDLE SECTIONS LOGIC---------------------------------------'''
                if json_data['sections'][json_idx]['section_id'] in MIDDLE_SECTION_LIST:
                    for sc_idx in range(len(self.section_conn_obj_list)):
                        if json_data['sections'][json_idx]['section_id'] == self.section_conn_obj_list[sc_idx].section_id:
                            if json_data['sections'][json_idx]['section_status'] == "occupied" and json_data[
                                    'sections'][json_idx]['direction'] != "none":

                                if json_data['sections'][json_idx]['direction'] == 'in':
                                    self.section_conn_obj_list[sc_idx].in_torpedo_axle_count = json_data[
                                        'sections'][json_idx]['torpedo_axle_count']
                                elif json_data['sections'][json_idx]['direction'] == 'out':
                                    self.section_conn_obj_list[sc_idx].out_torpedo_axle_count = json_data[
                                        'sections'][json_idx]['torpedo_axle_count']
                                else:
                                    pass

                                if json_data['sections'][json_idx]['direction'] == "out":
                                    if self.section_conn_obj_list[sc_idx].left_normal != "NONE":
                                        sec_id = self.section_conn_obj_list[sc_idx].left_normal

                                        for section_idx in range(
                                                len(self.section_conn_obj_list)):
                                            if self.section_conn_obj_list[section_idx].section_id == sec_id and section_list[
                                                    sec_id]["section_status"] == "occupied":
                                                if section_list[sec_id]["direction"] == "out":
                                                    self.section_conn_obj_list[
                                                        sc_idx].torpedo_id = self.section_conn_obj_list[section_idx].torpedo_id
                                                    self.section_conn_obj_list[
                                                        sc_idx].engine_id = self.section_conn_obj_list[section_idx].engine_id

                                                else:
                                                    pass
                                            else:
                                                pass
                                    else:
                                        pass

                                    if self.section_conn_obj_list[sc_idx].left_reverse != "NONE":
                                        sec_id = self.section_conn_obj_list[sc_idx].left_reverse

                                        for section_idx in range(
                                                len(self.section_conn_obj_list)):
                                            if self.section_conn_obj_list[section_idx].section_id == sec_id and section_list[
                                                    sec_id]["section_status"] == "occupied":
                                                if section_list[sec_id]["direction"] == "out":
                                                    self.section_conn_obj_list[
                                                        sc_idx].torpedo_id = self.section_conn_obj_list[section_idx].torpedo_id
                                                    self.section_conn_obj_list[
                                                        sc_idx].engine_id = self.section_conn_obj_list[section_idx].engine_id
                                                else:
                                                    pass
                                            else:
                                                pass
                                    else:
                                        pass
                                else:
                                    pass

                                if json_data['sections'][json_idx]['direction'] == "in":
                                    if self.section_conn_obj_list[sc_idx].right_normal != "NONE":
                                        sec_id = self.section_conn_obj_list[sc_idx].right_normal

                                        for section_idx in range(
                                                len(self.section_conn_obj_list)):
                                            if self.section_conn_obj_list[section_idx].section_id == sec_id and section_list[
                                                    sec_id]["section_status"] == "occupied":
                                                if section_list[sec_id]["direction"] == "in":
                                                    self.section_conn_obj_list[
                                                        sc_idx].torpedo_id = self.section_conn_obj_list[section_idx].torpedo_id
                                                    self.section_conn_obj_list[
                                                        sc_idx].engine_id = self.section_conn_obj_list[section_idx].engine_id
                                                else:
                                                    pass
                                            else:
                                                pass
                                    else:
                                        pass

                                    if self.section_conn_obj_list[sc_idx].right_reverse != "NONE":
                                        sec_id = self.section_conn_obj_list[sc_idx].right_reverse

                                        for section_idx in range(
                                                len(self.section_conn_obj_list)):
                                            if self.section_conn_obj_list[section_idx].section_id == sec_id and section_list[
                                                    sec_id]["section_status"] == "occupied":
                                                if section_list[sec_id]["direction"] == "in":
                                                    self.section_conn_obj_list[
                                                        sc_idx].torpedo_id = self.section_conn_obj_list[section_idx].torpedo_id
                                                    self.section_conn_obj_list[
                                                        sc_idx].engine_id = self.section_conn_obj_list[section_idx].engine_id
                                                else:
                                                    pass
                                            else:
                                                pass
                                    else:
                                        pass
                                else:
                                    pass

                            else:
                                pass

                            Log.logger.info(
                                f'Section_id : {self.section_conn_obj_list[sc_idx].section_id},'
                                f'torpedo_id : {self.section_conn_obj_list[sc_idx].torpedo_id},'
                                f'engine_id: {self.section_conn_obj_list[sc_idx].engine_id},')
                                #f'in: {self.section_conn_obj_list[sc_idx].in_torpedo_axle_count},'
                                #f'out: {self.section_conn_obj_list[sc_idx].out_torpedo_axle_count}')
                        else:
                            pass
                else:
                    pass
'''------------------------------------------------------------------------------------------------------------------------------------------------------------'''
                if json_data['sections'][json_idx]['section_id'] in UNLOADING_SECTION_LIST:
                    for sc_idx in range(len(self.section_conn_obj_list)):
                        if json_data['sections'][json_idx]['section_id'] == self.section_conn_obj_list[sc_idx].section_id:
                            if json_data['sections'][json_idx]['section_status'] != "none" or json_data[
                                    'sections'][json_idx]['direction'] != "none":
                                if json_data['sections'][json_idx]['torpedo_axle_count'] >= 12 and self.section_conn_obj_list[sc_idx].in_torpedo_axle_count < 12:
                                    self.section_conn_obj_list[sc_idx].unloaded_entry_time = json_data["ts"]

                                    if self.section_conn_obj_list[sc_idx].left_normal != "NONE":
                                        sec_id = self.section_conn_obj_list[sc_idx].left_normal

                                        for section_idx in range(
                                                len(self.section_conn_obj_list)):
                                            if self.section_conn_obj_list[section_idx].section_id == sec_id and section_list[
                                                    sec_id]["section_status"] != "none":
                                                self.section_conn_obj_list[
                                                    sc_idx].torpedo_id = self.section_conn_obj_list[section_idx].torpedo_id
                                                self.section_conn_obj_list[
                                                    sc_idx].engine_id = self.section_conn_obj_list[section_idx].engine_id
                                            else:
                                                pass

                                    if self.section_conn_obj_list[sc_idx].right_normal != "NONE":
                                        sec_id = self.section_conn_obj_list[sc_idx].right_normal

                                        for section_idx in range(
                                                len(self.section_conn_obj_list)):
                                            if self.section_conn_obj_list[section_idx].section_id == sec_id and section_list[
                                                    sec_id]["section_status"] != "none":
                                                self.section_conn_obj_list[
                                                    sc_idx].torpedo_id = self.section_conn_obj_list[section_idx].torpedo_id
                                                self.section_conn_obj_list[
                                                    sc_idx].engine_id = self.section_conn_obj_list[section_idx].engine_id
                                            else:
                                                pass
                                    Log.logger.info(
                                        f'Section_id : {self.section_conn_obj_list[sc_idx].section_id},'
                                        f'torpedo_id : {self.section_conn_obj_list[sc_idx].torpedo_id},'
                                        f'engine_id: {self.section_conn_obj_list[sc_idx].engine_id},'
                                        f'unloaded entry ts: {self.section_conn_obj_list[sc_idx].unloaded_entry_time}')

                                    self.section_conn_obj_list[sc_idx].in_torpedo_axle_count = json_data[
                                        'sections'][json_idx]['torpedo_axle_count']

                                    if self.section_conn_obj_list[sc_idx].torpedo_id != 0 and self.section_conn_obj_list[sc_idx].engine_id != 0:
                                        '''update train entry time while entrying unloading section'''
                                        self.update_train_unloaded_entry_info(
                                            self.section_conn_obj_list[sc_idx].torpedo_id,
                                            self.section_conn_obj_list[sc_idx].engine_id,
                                            self.section_conn_obj_list[sc_idx].unloaded_entry_time,
                                            self.section_conn_obj_list[sc_idx].section_id)
                                    else:
                                        pass
                                else:
                                    self.section_conn_obj_list[sc_idx].in_torpedo_axle_count = json_data[
                                        'sections'][json_idx]['torpedo_axle_count']
                            else:
                                pass

                            '''-----------------------------------GET UNLOADING EXIT TIME-----------------------------------'''
                            if json_data['sections'][json_idx]['direction'] == "out" or json_data['sections'][json_idx]['direction'] == "none":
                                if json_data['sections'][json_idx]['torpedo_axle_count'] >= 6:
                                    self.section_conn_obj_list[sc_idx].out_torpedo_axle_count = json_data[
                                        'sections'][json_idx]['torpedo_axle_count']
                                else:
                                    pass
                                if self.section_conn_obj_list[sc_idx].out_torpedo_axle_count >= 6 and json_data[
                                        'sections'][json_idx]['torpedo_axle_count'] < 6:
                                    self.section_conn_obj_list[sc_idx].unloaded_exit_time = json_data["ts"]

                                    Log.logger.info(f'Section_id : {self.section_conn_obj_list[sc_idx].section_id},'
                                                    f'torpedo_id : {self.section_conn_obj_list[sc_idx].torpedo_id},'
                                                    f'engine_id: {self.section_conn_obj_list[sc_idx].engine_id},'
                                                    f'unloaded exit ts: {self.section_conn_obj_list[sc_idx].unloaded_exit_time}')

                                    '''do not update db when torpedo id and engine id is 0'''
                                    if self.section_conn_obj_list[sc_idx].torpedo_id != 0 and self.section_conn_obj_list[sc_idx].engine_id != 0:
                                        self.update_train_unloaded_exit_info(
                                            self.section_conn_obj_list[sc_idx].torpedo_id,
                                            self.section_conn_obj_list[sc_idx].engine_id,
                                            self.section_conn_obj_list[sc_idx].unloaded_exit_time,
                                            self.section_conn_obj_list[sc_idx].section_id)
                                    else:
                                        pass

                                    self.section_conn_obj_list[sc_idx].out_torpedo_axle_count = 0
                                else:
                                    pass
                            else:
                                pass

                            Log.logger.info(
                                f'Section_id : {self.section_conn_obj_list[sc_idx].section_id},'
                                f'torpedo_id : {self.section_conn_obj_list[sc_idx].torpedo_id},'
                                f'engine_id: {self.section_conn_obj_list[sc_idx].engine_id},')
                                #f'in: {self.section_conn_obj_list[sc_idx].in_torpedo_axle_count},'
                                #f'out: {self.section_conn_obj_list[sc_idx].out_torpedo_axle_count}')
                        else:
                            pass
                else:
                    pass

        except Exception as ex:
            Log.logger.critical(
                f'scc_dlm_api: insert_yard_performance: exception: {ex}')

    def insert_torpedo_loaded_entry_info(self, torpedo_id, engine_id, unloaded_entry_time, unloaded_section_id): #method to update in torpedo_performance_info table in scc_dlm_model.py module.
        try:
            torpedo_performance_table = TorpedoPerformanceInfo()
            torpedo_performance_table.engine_id = engine_id
            torpedo_performance_table.torpedo_id = torpedo_id
            torpedo_performance_table.unload_entry_ts = unloaded_entry_time
            torpedo_performance_table.unload_section_id = unloaded_section_id
            torpedo_performance_table.save()
            Log.logger.info(
                f'inserted torpedo loaded entry time: {entry_time}, torpedo_id: {torpedo_id}')
        except Exception as ex:
            Log.logger.critical(f'insert_torpedo_loaded_entry_info: exception: {ex}')

    def update_torpedo_unloaded_exit_info(self, torpedo_id, engine_id, unloaded_exit_time, unloaded_section_id): #method to update unload_exit_time & unload section_id in torpedo_performance_info table in scc_dlm_model.py module.
        try:
            torpedo_performance_table = TorpedoPerformanceInfo.select().where(
                TorpedoPerformanceInfo.torpedo_id == torpedo_id).get()
            torpedo_performance_table.unload_exit_ts = unloaded_exit_time
            torpedo_performance_table.unload_section_id = unloaded_section_id
            torpedo_performance_table.save()
            Log.logger.info(
                f'inserted unloading zone torpedo exit time: {unloaded_exit_time}, torpedo_id: {torpedo_id}')
        except DoesNotExist:
            Log.logger.critical(
                f'update_torpedo_unloaded_exit_info: record does not exist')

    def insert_train_entry_info(self, torpedo_id, engine_id, entry_time): #update yardperformance info table in scc_dlm_model.py module.
        try:
            yard_performance_table = YardPerformanceInfo()
            yard_performance_table.engine_id = engine_id
            yard_performance_table.torpedo_id = torpedo_id
            yard_performance_table.entry_ts = entry_time
            yard_performance_table.save()
            Log.logger.info(
                f'inserted train entry time: {entry_time}, torpedo_id: {torpedo_id}')
        except Exception as ex:
            Log.logger.critical(f'insert_train_entry_info: exception: {ex}')

    def update_train_exit_info(self, torpedo_id, engine_id, exit_time): #update exit_time in record of yard performance table where torpedo_id == passed torpedo_id.
        try:
            yard_performance_table = YardPerformanceInfo.select().where(
                YardPerformanceInfo.torpedo_id == torpedo_id).get()
            yard_performance_table.exit_ts = exit_time
            yard_performance_table.save()
            Log.logger.info(
                f'inserted train exit time: {exit_time}, torpedo_id: {torpedo_id}')
        except DoesNotExist:
            Log.logger.critical(
                f'update_train_exit_info: record does not exist')

    def update_train_unloaded_entry_info(
            self, torpedo_id, engine_id, unloaded_entry_time, unloaded_section_id): #update unload_entry time & unload section_id in record of yard performance table where torpedo_id == passed torpedo_id.
        try:
            yard_performance_table = YardPerformanceInfo.select().where(
                YardPerformanceInfo.torpedo_id == torpedo_id).get()
            yard_performance_table.unload_entry_ts = unloaded_entry_time
            yard_performance_table.unload_section_id = unloaded_section_id
            yard_performance_table.save()
            Log.logger.info(
                f'inserted unloading zone train entry time: {unloaded_entry_time}, torpedo_id: {torpedo_id}')
        except DoesNotExist:
            Log.logger.critical(
                f'update_train_unloaded_entry_info: record does not exist')

    def update_train_unloaded_exit_info(
            self, torpedo_id, engine_id, unloaded_exit_time, unloaded_section_id): #update unload_exit time & unload section_id in record of yard performance table where torpedo_id == passed torpedo_id.
        try:
            yard_performance_table = YardPerformanceInfo.select().where(
                YardPerformanceInfo.torpedo_id == torpedo_id).get()
            yard_performance_table.unload_exit_ts = unloaded_exit_time
            yard_performance_table.unload_section_id = unloaded_section_id
            yard_performance_table.save()
            Log.logger.info(
                f'inserted unloading zone train exit time: {unloaded_exit_time}, torpedo_id: {torpedo_id}')
        except DoesNotExist:
            Log.logger.critical(
                f'update_train_unloaded_exit_info: record does not exist')

    def insert_event_info(self, event_ts, event_id, event_desc): #method to save event_ts, event_id and event_desc in event_table in scc_dlm_model.py module.
        try:
            event_table = EventInfo() #initialising EventInfo class [containing class object ts, event_id, event_desc] from scc_dlm_model.py.
            event_table.ts = event_ts
            event_table.event_id = event_id
            event_table.event_desc = event_desc
            event_table.save() #saving the data in event_table
        except Exception as ex:
            Log.logger.critical(f'insert_event_info: exception: {ex}')

    def insert_trail_through_info(self, tt_msg): #method to update trail through info in trail_through_info and trail_through_playback table in scc_dlm_model.py module.
        '''insert data into trail through table'''
        try:
            if self.last_tt_record_inserted[tt_msg['section_id']] == False: #if last_tt_record_inserted is false.
                tt_table = TrailThroughInfo()
                tt_table.tt_ts = tt_msg['ts']
                tt_table.section_id = tt_msg['section_id']
                tt_table.confirm_status = False
                tt_table.save() #saving data in trail through table
                self.last_tt_record_inserted[tt_msg['section_id']
                                             ] = True #setting last_tt_record_inserted to true
                Log.logger.info(f'insert trail through: {self.last_tt_record_inserted[tt_msg["section_id"]]}') #logging info 

                '''insert data into trail through playback table'''
                tt_playback_table = TrailThroughPlayback()
                tt_playback_table.ts = tt_msg['ts']
                tt_playback_table.section_id = {"ts": tt_msg['ts'], "section_id": tt_msg['section_id'], "confirm_status": False}
                tt_playback_table.save() #saving data in trail through playback table
            else:
                pass
        except Exception as ex:
            Log.logger.critical(f'insert_trail_through_info: exception: {ex}')

    def clear_trail_through(self, tt_msg): #make last_tt_record_inserted[section_id in passed attribute message] == False  and add info in trail_through_playback table.
        '''clear trail through alert when user sent mqtt message'''
        try:
            if self.last_tt_record_inserted[tt_msg['section_id']] == True:
                self.last_tt_record_inserted[tt_msg['section_id']] = False
                Log.logger.info(f'clear trail through: {self.last_tt_record_inserted[tt_msg["section_id"]]}')

                '''insert data into trail through playback table'''
                tt_playback_table = TrailThroughPlayback()
                tt_playback_table.ts = time.time()
                tt_playback_table.section_id = {"ts": time.time(), "section_id": tt_msg['section_id'], "confirm_status": True}
                tt_playback_table.save()
            else:
                pass
        except Exception as ex:
            Log.logger.critical(f'clear_trail_through: exception: {ex}')

if __name__ == '__main__':
    if Log.logger is None:
        my_log = Log()

    cfg = SccDlmConfRead()
    cfg.read_cfg('../config/scc.conf')

    scc_api = SccAPI()
    db_conn = scc_api.connect_database(cfg)

    if db_conn:
        scc_api.read_section_config_info()
        scc_api.read_section_connections_info()
        # scc_api.read_section_playback_info()
        scc_api.init_train_trace_info()
        scc_api.init_section_connections_info()
    else:
        pass
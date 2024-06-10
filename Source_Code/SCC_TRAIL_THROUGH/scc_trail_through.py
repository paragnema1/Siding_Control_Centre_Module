'''
*****************************************************************************
*File : scc_trail_through.py
*Module : SCC 
*Purpose : SCC trail through detection 
*Author : Sumankumar Panchal
*Copyright : Copyright 2021, Lab to Market Innovations Private Limited
*****************************************************************************
'''

'''Import packages '''
from scc_dlm_conf import *
from scc_log import *
import sys
import json
import os

from peewee import *
from datetime import datetime, timedelta
from scc_dlm_model import *
from scc_layout_model import *
from scc_dlm_api import *
sys.path.insert(1, "./common")

TRAIL_THROUGH_SECTION_LIST = ["S3", "S4", "S7", "S8", "S11"]


class Sec:
    def __init__(self):
        self.section_id = "none"
        self.left_normal = "none"
        self.right_normal = "none"
        self.left_reverse = "none"
        self.right_reverse = "none"
        self.engine_axle_count = 0
        self.torpedo_axle_count = 0
        self.section_status = "none"
        self.point_id = "none"
        self.point_status = "none"
        self.point_mode = "none"
        self.point_error = 0
        self.torpedo_status = "none"
        self.direction = "none"
        self.speed = 10
        self.first_axle = "none"
        self.error_code = 0
        

class Trailthrough:
    def __init__(self, mqtt_client): #constructor connecting to database and initialising variables.
        self.scc_api = SccAPI() #a class of scc_dlm_api.py 
        self.db_conn = self.scc_api.connect_database(cfg) #passing cfg file to connect_database function of SCCAPI class, to connect to postgresql database.
        self.tt_sec_obj_list = [] #list to store section objects like section_id, left_normal, right_normal, left_reverse, right_reverse.
        self.total_sec = 0
        self.mqtt_client = mqtt_client
        self.prev_section_list = {}
        self.TOTAL_SECTION = 14

    def get_point_config(self): #function to get all records (section id & point id) from pms_Config table.
        '''get pms configuration from database table'''
        try:
            point_config_record = PointConfig.select() #selecting all records from pms_Config table which is  created in scc_dlm_model.py
            return point_config_record
        except Exception as ex:
            Log.logger.critical(f'get_point_config: exception: {ex}')

    def init_trail_through_info(self):#update records on tt_sec_obj_list ['section_id and point_id by calling get_point_config' & 'section config objects by calling scc_api.read_section_connections_info() function']
        '''init section connections information'''
        try:

            Log.logger.info(f'init trail through info called')
            if self.db_conn:
                section_connections_db_records = self.scc_api.read_section_connections_info() #it is a method of scc_api class in scc_dlm_api.py which reads section connection info from occ_config table in scc_dlm_model.py

                for sc in section_connections_db_records: #logging message section_id, left_normal, right_normal
                    Log.logger.info(
                        f'SECTION_ID: {sc.section_id}, LEFT_SECTION: {sc.left_normal}, RIGHT_SECTION: {sc.right_normal}')

                for sc in section_connections_db_records:
                    self.tt_sec_obj_list.append(Sec()) #appending sec class variables in tt_sec_obj_list.

                sc_idx = 0
                for sc in section_connections_db_records: #updating sec class variables in sec_obj_list.
                    self.tt_sec_obj_list[sc_idx].section_id = sc.section_id
                    self.tt_sec_obj_list[sc_idx].left_normal = sc.left_normal
                    self.tt_sec_obj_list[sc_idx].right_normal = sc.right_normal
                    self.tt_sec_obj_list[sc_idx].left_reverse = sc.left_reverse
                    self.tt_sec_obj_list[sc_idx].right_reverse = sc.right_reverse
                    sc_idx += 1

                point_config = self.get_point_config() #initialising get_point_config class variables.

                for point in point_config: #updating point id and section id in tt_sec_obj_list.
                    for sec_idx in range(len(self.tt_sec_obj_list)):
                        if self.tt_sec_obj_list[sec_idx].section_id == point.section_id: 
                            self.tt_sec_obj_list[sec_idx].point_id = point.point_id

                            Log.logger.info(
                                f'SECTION_ID: {self.tt_sec_obj_list[sec_idx].section_id}, POINT_ID: {self.tt_sec_obj_list[sec_idx].point_id}')
                        else:
                            pass
                self.total_sec = len(self.tt_sec_obj_list)
            else:
                pass
                Log.logger.warning(f'database not connected!!')

        except Exception as ex:
            Log.logger.critical(
                f'init_section_connections_info: exception {ex}')

    def detect_trail_through(self, section_json_data, point_obj_list):
        '''update records of tt_sec_obj_list [point status and point mode from passed point_obj_list & section objects from passed section_json_data]
            by using objects of tt_sec_obj_list it is detecting trail through'''
         
        '''trail through detection using section status and point status'''
        try:
            section_list = {}
            json_data = json.loads(section_json_data) #convert passed section_json_data to python format.

            for json_idx in range(len(json_data['sections'])): #making dictionary section_list with section_id as key and json_data[sections] as value.
                section_list[json_data['sections'][json_idx]
                             ['section_id']] = json_data['sections'][json_idx]

            '''update point status and point mode'''
            for point_idx in range(len(point_obj_list)): #iterating point_idx in point_obj_list
                #Log.logger.info(
                #    f'{point_obj_list[point_idx].point_id}, {point_obj_list[point_idx].point_status}, {point_obj_list[point_idx].point_mode}')

                for sec_idx in range(self.total_sec): #total sec = len(tt_sec_obj_list) defined in above function.
                    if point_obj_list[point_idx].point_id == self.tt_sec_obj_list[sec_idx].point_id: #if point id in point object list matches with sec_obj) list then [update point_status and point_mode in tt_sec_obj_list from point_obj_list]
                        self.tt_sec_obj_list[sec_idx].point_status = point_obj_list[point_idx].point_status
                        self.tt_sec_obj_list[sec_idx].point_mode = point_obj_list[point_idx].point_mode
                    else:
                        pass

            for sec_idx in range(len(self.tt_sec_obj_list)): #updating tt_sec_obj_list objects from passed section_json_data
                for json_sec_idx in range(len(json_data['sections'])):
                    if self.tt_sec_obj_list[sec_idx].section_id == json_data['sections'][json_sec_idx]['section_id']:
                        self.tt_sec_obj_list[sec_idx].section_status = json_data['sections'][json_sec_idx]['section_status']
                        self.tt_sec_obj_list[sec_idx].direction = json_data['sections'][json_sec_idx]['direction']
                        self.tt_sec_obj_list[sec_idx].torpedo_axle_count = json_data['sections'][json_sec_idx]['torpedo_axle_count']
                        self.tt_sec_obj_list[sec_idx].error_code = json_data['sections'][json_sec_idx]['error_code']
                    else:
                        pass

            tt_sec_list = []

            for sec_idx in range(len(self.tt_sec_obj_list)):
                if self.tt_sec_obj_list[sec_idx].section_id in ['S20', 'S18', 'S12', 'S10', 'S9']: #if in tt_sec_obj_list any section Id mathes with ['S20', 'S18', 'S12', 'S10', 'S9']
                    if self.tt_sec_obj_list[sec_idx].section_status == "occupied" and self.tt_sec_obj_list[sec_idx].direction == "out": #if section_status is occupied and direction is out then this sec_idx left normal is left normal and right normal is right normal
                        left_normal_sec_id = self.tt_sec_obj_list[sec_idx].left_normal
                        left_reverse_sec_id = self.tt_sec_obj_list[sec_idx].left_reverse

                        if section_list[left_normal_sec_id]["section_status"] == "occupied" and section_list[left_normal_sec_id]["direction"] == "out": #if section status of this left normal sec-id is occupied and direction is out.
                            if len(self.prev_section_list)!= 0 and (section_list[left_normal_sec_id]["torpedo_axle_count"] != self.prev_section_list[left_normal_sec_id]["torpedo_axle_count"]): #if 
                                if self.tt_sec_obj_list[sec_idx].point_status == "reverse" and self.tt_sec_obj_list[sec_idx].point_mode != "manual":
                                    Log.logger.info(
                                        f'trail-through detected in Section id:{self.tt_sec_obj_list[sec_idx].section_id}')
                                    tt_sec_list.append(
                                        self.tt_sec_obj_list[sec_idx].section_id)
                                    Log.logger.info(
                                        f'trail-through detected in Section id:{self.tt_sec_obj_list[sec_idx].section_id} due to point fault')
                                    tt_sec_list.append(self.tt_sec_obj_list[sec_idx].section_id)
                                else:
                                    pass
                            else:
                                pass
                        else:
                            pass

                        if section_list[left_reverse_sec_id]["section_status"] == "occupied" and section_list[left_reverse_sec_id]["direction"] == "out":
                            if len(self.prev_section_list)!= 0 and (section_list[left_reverse_sec_id]["torpedo_axle_count"] != self.prev_section_list[left_reverse_sec_id]["torpedo_axle_count"]):
                                if self.tt_sec_obj_list[sec_idx].point_status == "normal" and self.tt_sec_obj_list[sec_idx].point_mode != "manual":
                                    Log.logger.info(
                                        f'trail-through detected in Section id:{self.tt_sec_obj_list[sec_idx].section_id}')
                                    tt_sec_list.append(
                                        self.tt_sec_obj_list[sec_idx].section_id)
                                elif self.tt_sec_obj_list[sec_idx].point_status == "fault":
                                    Log.logger.info(
                                        f'trail-through detected in Section id:{self.tt_sec_obj_list[sec_idx].section_id} due to point fault')
                                    tt_sec_list.append(self.tt_sec_obj_list[sec_idx].section_id)
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

                if self.tt_sec_obj_list[sec_idx].section_id in ['S19', 'S15', 'S13', 'S11']:
                    if self.tt_sec_obj_list[sec_idx].section_status == "occupied" and self.tt_sec_obj_list[sec_idx].direction == "in":
                        right_normal_sec_id = self.tt_sec_obj_list[sec_idx].right_normal
                        right_reverse_sec_id = self.tt_sec_obj_list[sec_idx].right_reverse

                        if section_list[right_normal_sec_id]["section_status"] == "occupied" and section_list[right_normal_sec_id]["direction"] == "in":
                            if len(self.prev_section_list)!= 0 and (section_list[right_normal_sec_id]["torpedo_axle_count"] != self.prev_section_list[right_normal_sec_id]["torpedo_axle_count"]):
                                if self.tt_sec_obj_list[sec_idx].point_status == "reverse" and self.tt_sec_obj_list[sec_idx].point_mode != "manual":
                                    Log.logger.info(
                                        f'trail-through detected in Section id:{self.tt_sec_obj_list[sec_idx].section_id}')
                                    tt_sec_list.append(
                                        self.tt_sec_obj_list[sec_idx].section_id)
                                elif self.tt_sec_obj_list[sec_idx].point_status == "fault":
                                    Log.logger.info(
                                        f'trail-through detected in Section id:{self.tt_sec_obj_list[sec_idx].section_id} due to point fault')
                                    tt_sec_list.append(self.tt_sec_obj_list[sec_idx].section_id)
                                else:
                                    pass
                            else:
                                pass
                        else:
                            pass

                        if section_list[right_reverse_sec_id]["section_status"] == "occupied" and section_list[right_reverse_sec_id]["direction"] == "in":
                            if len(self.prev_section_list)!= 0 and (section_list[right_reverse_sec_id]["torpedo_axle_count"] != self.prev_section_list[right_reverse_sec_id]["torpedo_axle_count"]):
                                if self.tt_sec_obj_list[sec_idx].point_status == "normal" and self.tt_sec_obj_list[sec_idx].point_mode != "manual":
                                    Log.logger.info(
                                        f'trail-through detected in Section id:{self.tt_sec_obj_list[sec_idx].section_id}')
                                    tt_sec_list.append(
                                        self.tt_sec_obj_list[sec_idx].section_id)
                                elif self.tt_sec_obj_list[sec_idx].point_status == "fault":
                                    Log.logger.info(
                                        f'trail-through detected in Section id:{self.tt_sec_obj_list[sec_idx].section_id} due to point fault')
                                    tt_sec_list.append(self.tt_sec_obj_list[sec_idx].section_id)
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

            Log.logger.info(f'return value: {tt_sec_list}')
            self.prev_section_list = section_list
            return tt_sec_list
        except Exception as ex:
            Log.logger.critical(f'find trail through: exception: {ex}')

    def find_torpedo_status(self, section_json_data): #by using objects of tt_sec_obj_list it is finding torpedo status.
        '''find torpedo status'''
        try:
            section_list = {}
            json_data = json.loads(section_json_data)

            Log.logger.info(f'find torpedo status called')
            Log.logger.info(f'{len(self.tt_sec_obj_list)}')

            for json_idx in range(len(json_data['sections'])):
                section_list[json_data['sections'][json_idx]
                             ['section_id']] = json_data['sections'][json_idx]

            for sec_idx in range(len(self.tt_sec_obj_list)): #updating tt_sec_obj_list objects from passed section_json_data
                for json_sec_idx in range(len(json_data['sections'])):
                    if self.tt_sec_obj_list[sec_idx].section_id == json_data['sections'][json_sec_idx]['section_id']:
                        self.tt_sec_obj_list[sec_idx].section_status = json_data['sections'][json_sec_idx]['section_status']
                        self.tt_sec_obj_list[sec_idx].direction = json_data['sections'][json_sec_idx]['direction']
                        self.tt_sec_obj_list[sec_idx].torpedo_axle_count = json_data['sections'][json_sec_idx]['torpedo_axle_count']
                        self.tt_sec_obj_list[sec_idx].error_code = json_data['sections'][json_sec_idx]['error_code']
                        self.tt_sec_obj_list[sec_idx].engine_axle_count = json_data['sections'][json_sec_idx]['engine_axle_count']
                        self.tt_sec_obj_list[sec_idx].speed = json_data['sections'][json_sec_idx]['speed']
                        self.tt_sec_obj_list[sec_idx].first_axle = json_data['sections'][json_sec_idx]['first_axle']

                        if self.tt_sec_obj_list[sec_idx].section_id in ['S1', 'S2', 'S3', 'S4', 'S20', 'S21', 'S22']: #for section id of tt_sec_obj_list matches with ['S1', 'S2', 'S3', 'S4', 'S20', 'S21', 'S22'], update torpedo status from passed data.
                            self.tt_sec_obj_list[sec_idx].torpedo_status = json_data['sections'][json_sec_idx]['torpedo_status']
                            if self.tt_sec_obj_list[sec_idx].torpedo_status != "none":
                                Log.logger.info(f'{self.tt_sec_obj_list[sec_idx].section_id}, {self.tt_sec_obj_list[sec_idx].torpedo_status}')
                            else:
                                pass
                        else:
                            pass
                    else:
                        pass
            
            for sec_idx in range(len(self.tt_sec_obj_list)):
                left_normal_sec_id = self.tt_sec_obj_list[sec_idx].left_normal
                left_reverse_sec_id = self.tt_sec_obj_list[sec_idx].left_reverse
                right_normal_sec_id = self.tt_sec_obj_list[sec_idx].right_normal
                right_reverse_sec_id = self.tt_sec_obj_list[sec_idx].right_reverse
                    
                if self.tt_sec_obj_list[sec_idx].section_id not in ['S1', 'S2', 'S3', 'S4', 'S20', 'S21', 'S22']:
                    if self.tt_sec_obj_list[sec_idx].section_status != "cleared" and self.tt_sec_obj_list[sec_idx].direction == "in":
                        if right_normal_sec_id != "NONE":
                            if len(self.prev_section_list)!= 0 and (section_list[right_normal_sec_id]["torpedo_axle_count"] != self.prev_section_list[right_normal_sec_id]["torpedo_axle_count"]):
                                for rn_sec_idx in range(len(self.tt_sec_obj_list)):
                                    if self.tt_sec_obj_list[rn_sec_idx].section_id == self.tt_sec_obj_list[sec_idx].right_normal:
                                        if self.tt_sec_obj_list[rn_sec_idx].torpedo_status != "none":
                                            self.tt_sec_obj_list[sec_idx].torpedo_status = self.tt_sec_obj_list[rn_sec_idx].torpedo_status
                                        else:
                                            pass
                                    else:
                                        pass
                            else:
                                pass
                        else:
                            pass

                        if right_reverse_sec_id != "NONE":
                            if len(self.prev_section_list)!= 0 and (section_list[right_reverse_sec_id]["torpedo_axle_count"] != self.prev_section_list[right_reverse_sec_id]["torpedo_axle_count"]):
                                for rr_sec_idx in range(len(self.tt_sec_obj_list)):
                                    if self.tt_sec_obj_list[rr_sec_idx].section_id == self.tt_sec_obj_list[sec_idx].right_reverse:
                                        if self.tt_sec_obj_list[rr_sec_idx].torpedo_status != "none":
                                            self.tt_sec_obj_list[sec_idx].torpedo_status = self.tt_sec_obj_list[rr_sec_idx].torpedo_status
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
                else:
                    pass


                if self.tt_sec_obj_list[sec_idx].section_id not in ['S1', 'S2', 'S3', 'S4']:
                    if self.tt_sec_obj_list[sec_idx].section_status != "cleared" and self.tt_sec_obj_list[sec_idx].direction == "out":
                        if left_normal_sec_id != "NONE":
                            if len(self.prev_section_list)!= 0 and (section_list[left_normal_sec_id]["torpedo_axle_count"] != self.prev_section_list[left_normal_sec_id]["torpedo_axle_count"]):
                                for ln_sec_idx in range(len(self.tt_sec_obj_list)):
                                    if self.tt_sec_obj_list[ln_sec_idx].section_id == self.tt_sec_obj_list[sec_idx].left_normal:
                                        if self.tt_sec_obj_list[ln_sec_idx].torpedo_status != "none" and self.tt_sec_obj_list[sec_idx].torpedo_axle_count >= 6 :
                                            self.tt_sec_obj_list[sec_idx].torpedo_status = self.tt_sec_obj_list[ln_sec_idx].torpedo_status
                                        else:
                                            pass
                                    else:
                                        pass
                            else:
                                pass
                        else:
                            pass
                        if left_reverse_sec_id != "NONE":
                            if len(self.prev_section_list)!= 0 and (section_list[left_reverse_sec_id]["torpedo_axle_count"] != self.prev_section_list[left_reverse_sec_id]["torpedo_axle_count"]):
                                for lr_sec_idx in range(len(self.tt_sec_obj_list)):
                                    if self.tt_sec_obj_list[lr_sec_idx].section_id == self.tt_sec_obj_list[sec_idx].left_reverse:
                                        if self.tt_sec_obj_list[lr_sec_idx].torpedo_status != "none" and self.tt_sec_obj_list[sec_idx].torpedo_axle_count >= 6 :
                                            self.tt_sec_obj_list[sec_idx].torpedo_status = self.tt_sec_obj_list[lr_sec_idx].torpedo_status
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

                    if self.tt_sec_obj_list[sec_idx].section_status == "cleared":
                        self.tt_sec_obj_list[sec_idx].torpedo_status = "none"
                        pass
                    else:
                        pass
                else:
                    pass

            #for sec_idx in range(len(self.tt_sec_obj_list)):
            #    Log.logger.info(f'SEC_ID: {self.tt_sec_obj_list[sec_idx].section_id},'
            #                    f'T_STATUS: {self.tt_sec_obj_list[sec_idx].torpedo_status},'
            #                    f'S_STATUS: {self.tt_sec_obj_list[sec_idx].section_status},'
            #                    f'T AC: {self.tt_sec_obj_list[sec_idx].torpedo_axle_count},'
            #                    f'DIR: {self.tt_sec_obj_list[sec_idx].direction}')
            
            self.prev_section_list = section_list
           
            '''return new section message with torpedo status'''
            json_section_msg = self.construct_section_json_msg()
            return json_section_msg

        except Exception as ex:
            Log.logger.critical(f'find_torpedo_status: exception: {ex}')
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            Log.logger.critical(f'{exc_type}, {fname}, {exc_tb.tb_lineno}')

    def construct_section_json_msg(self): #function to return json_msg with key1 as ts & key2 as (object of tt_section_msg_list)
        try:
            section_msg_list = []
            json_occ_msg = ""
            for sec_idx in range(self.TOTAL_SECTION): #total section is a object of class Trailthrough
                section_msg = {
                    "section_id": self.tt_sec_obj_list[sec_idx].section_id,
                    "section_status": self.tt_sec_obj_list[sec_idx].section_status,
                    "engine_axle_count": self.tt_sec_obj_list[sec_idx].engine_axle_count,
                    "torpedo_axle_count": self.tt_sec_obj_list[sec_idx].torpedo_axle_count,
                    "direction": self.tt_sec_obj_list[sec_idx].direction,
                    "speed": self.tt_sec_obj_list[sec_idx].speed,
                    "torpedo_status": self.tt_sec_obj_list[sec_idx].torpedo_status,
                    "first_axle": self.tt_sec_obj_list[sec_idx].first_axle,
                    "error_code": self.tt_sec_obj_list[sec_idx].error_code
                }
                section_msg_list.append(section_msg) #appending section message in section_msg_list.

            occ_msg = {"ts": time.time(), "sections": section_msg_list} #a dictionary with key ts and sections.
            json_occ_msg = json.dumps(occ_msg, indent=0) #converting occ_msg to json format.
            return json_occ_msg
        except Exception as ex:
            Log.logger.critical(
                f'construct_section_json_msg: exception : {ex}')
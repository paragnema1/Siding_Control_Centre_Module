# Siding_Control_Centre_Module
**A Module of Cyber Signalling Software Architecture**

```mermaid
graph TD;
    SCC-->Configuration_file;
    SCC-->Source_code;
    Configuration_file-->SCC.conf;
    Configuration_file-->section_connection.conf;
    Configuration_file-->section_configuration.conf;
    Configuration_file-->yard_configuration.conf;
    Source_code-->insert_conf.py;
    Source_code-->insert_yard_conf.py;
    Source_code-->main.py;
    Source_code-->scc_dlm_conf.py;
    Source_code-->scc_dlm_model.py;
    Source_code-->scc_dlm_api.py;
    Source_code-->scc_layout_model.py;
    Source_code-->scc_trail_trough.py;
```
## SCC - Siding Control Centre Module.

## Configuration File - Files/settings that a program reads before startup.

## Source Code File - Files containing sub-modules.

### SCC.conf - SCC configuration file contains:-

    Comment- Description of file.
    Version - version of module.
    SSC_ID - SSC Identifier.
    Database - Object Containing database of provider, User, Password, HOST Protocol, HOST IP address, Database name
    Local MQTT Broker - Object Containing database of MQTT broker, Broker IP address, Username, Password, Port no. of the broker.
    Total yard.
    Total Section.

### Section.conf - Section Configuration File.

    It is the file containing the Detection Point direction in section IN and section OUT of all data points in a section.
    Syntax:-
    {
    "SECTION":[
    	{
    	"SECTION_ID": "S1",
    	"SECTION_IN":[
    		{
    		"DP_ID": "DP01",
    		"DP_DIRECTION": "IN"
    		},
    		{
    		"DP_ID": "DP02",
    		"DP_DIRECTION": "OUT"
    		},
    		{
    		"DP_ID": "DP03",
    		"DP_DIRECTION": "OUT"
    		}
    		],
    	"SECTION_OUT":[
    		{
    		"DP_ID": "DP01",
    		"DP_DIRECTION": "OUT"
    		},
    		{
    		"DP_ID": "DP02",
    		"DP_DIRECTION": "IN"
    		},
    		{
    		"DP_ID": "DP03",
    		"DP_DIRECTION": "IN"
    		}
    		]
    	}
    	]
    }


### Section_connection.conf - Section Configuration File.

    It is the file containing the state/setting of the section in Left Normal, Right Normal, Left Reverse, Right Reverse.
    Syntax:-
    {
	"SECTIONS": [
			{
			"SECTION_ID": "S1",
			"LEFT_NORMAL": "NONE",
			"RIGHT_NORMAL": "NONE",
			"LEFT_REVERSE": "NONE",
			"RIGHT_REVERSE": "NONE"
			}
		]
     }


### yard_connection.conf - yard Configuration File.

	It is the file containing DPU in the yard, sections under each DPU, and DP's in each section.
	Syntax:- 
	{
	"YARDS": [
		{
		"YARD_ID" : 1,
		"YARD_NAME" : "BHAUPUR_LOGICS",
		"DPU": [
			{
			"DPU_ID": "DPU_01",
			"DPU_NAME": "DPU_01",
			"SECTIONS":[
					{
					"SECTION_ID": "S1",
					"SECTION_NAME": "S1",
					"DPS" : ["DP01"]
					},
					{
					"SECTION_ID": "S2",
					"SECTION_NAME": "S2",
					"DPS" : ["DP01","DP02","DP03"]
					},
					{
					"SECTION_ID": "S3",
					"SECTION_NAME": "S3",
					"DPS" : ["DP02"]
					},	
					{
					"SECTION_ID": "S4",
					"SECTION_NAME": "S4",
					"DPS" : ["DP04","DP03","DP05"]
					}											
	
				]
			   }
			]
		   }
		]
	}
	

### scc_dlm_conf.py - module to load data (comment, version, lmb(local mqtt broker), scc_id) from configuration files.
***Class SccDlmConfRead:***

**def read_cfg(self, file_name):** 

Convert JSON file to python file.

Match this Python file with a Schema dictionary(a class object inside this Class) and validate it by calling the validate_cfg() function.

load data (comment, version, lmb(local mqtt broker), scc_id) from python file to Class DatabaseStruct class objects.

**def validate_cfg(self):** 

function to check if any data (comment, version, lmb(local mqtt broker), scc_id, PROVIDER, USER, PASSWORD, HOST, DB_NAME) is not present, empty, or whitespace.

***Class DatabaseStruct(NamedTuple):***
    PROVIDER: str
    USER: str
    PASSWORD: str
    HOST: str
    DB_NAME: str

                    
### scc_dlm_model.py - data logging module to store data in PostgreSQL.

### scc_layout_model.py - data logging module for layout section data to store data in PostgreSQL.

### scc_dlm_api.py - data logging module to handle all API in scc website.

### scc_trail_through.py - module to detect trail through and torpedo status.

### main.py - main module for yard configuration and section information.

### insert_conf.py - A module containing functions to convert (JSON files to Python) and (Python to JSON).
Class SectonConfig:

def read_cfg(self, file_name): function to convert JSON file to Python file.

def print_cfg(self): function to convert Python file to JSON file.

### insert_yard_conf.py - A module containing functions to convert (JSON file to Python) and (python to JSON).
Class SectonConfig:

def read_cfg(self, file_name): function to convert JSON file to Python file.

def print_cfg(self): function to convert Python file to JSON file.

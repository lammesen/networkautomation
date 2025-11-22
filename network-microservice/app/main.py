from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from nornir import InitNornir
from nornir.core.inventory import Host
from nornir_netmiko.tasks import netmiko_send_command
from nornir_napalm.plugins.tasks import napalm_get
from nornir.core.task import Task, Result
import socket
import yaml
import tempfile
import os
import traceback

app = FastAPI()

class Device(BaseModel):
    hostname: str
    ip: str
    platform: str
    username: str
    password: str
    port: int = 22

class CommandRequest(BaseModel):
    devices: List[Device]
    commands: List[str]

class ComplianceRequest(BaseModel):
    devices: List[Device]
    getters: List[str] 

def adapt_platform(platform: str) -> str:
    pmap = {
        'ios': 'cisco_ios',
        'nxos': 'cisco_nxos',
        'eos': 'arista_eos',
        'junos': 'juniper_junos',
        'iosxr': 'cisco_xr',
        'linux': 'linux'
    }
    return pmap.get(platform, platform)

def get_nornir(devices: List[Device]):
    # Construct hosts dict
    hosts = {
        d.hostname: {
            "hostname": d.ip,
            "port": d.port,
            "username": d.username,
            "password": d.password,
            "platform": adapt_platform(d.platform),
            "connection_options": {
                "netmiko": {
                    "extras": {
                        "use_keys": False,
                        "key_file": None,
                        "ssh_config_file": "/app/ssh_config",
                        "global_delay_factor": 2
                    }
                }
            }
        } for d in devices
    }

    tf = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".yaml")
    yaml.dump(hosts, tf)
    tf.close()
    
    nr = InitNornir(
        inventory={
            "plugin": "SimpleInventory",
            "options": {
                "host_file": tf.name
            }
        },
        dry_run=False,
        logging={"enabled": False}
    )
    
    try:
        os.unlink(tf.name)
    except:
        pass
        
    return nr

def run_commands_task(task: Task, commands: List[str]) -> Dict[str, str]:
    results = {}
    for cmd in commands:
        try:
            res = task.run(task=netmiko_send_command, command_string=cmd)
            results[cmd] = res.result
        except Exception as e:
            results[cmd] = f"ERROR: {str(e)}"
    return results

@app.post("/run_commands")
async def run_commands_endpoint(req: CommandRequest):
    try:
        nr = get_nornir(req.devices)
        result = nr.run(task=run_commands_task, commands=req.commands)
        
        output = {}
        for hostname, host_res in result.items():
            if host_res.failed:
                print(f"ERROR: Task failed for {hostname}")
                
                err_msg = "Unknown error"
                if host_res.result and isinstance(host_res.result, str):
                    err_msg = host_res.result # Netmiko often puts error here
                elif host_res.exception:
                    err_msg = str(host_res.exception)

                print(f"Underlying Error Message: {err_msg}")
                if host_res.exception:
                    traceback.print_exception(type(host_res.exception), host_res.exception, host_res.exception.__traceback__)

                output[hostname] = {"status": "failed", "error": err_msg}
            else:
                task_result = host_res[0].result
                output[hostname] = {"status": "success", "result": task_result}
                
        return output
    except Exception as e:
        print(f"GLOBAL ERROR: {e}")
        traceback.print_exc()
        return {"error": str(e), "status": "failed"}

@app.post("/compliance/getters")
async def run_compliance_endpoint(req: ComplianceRequest):
    try:
        nr = get_nornir(req.devices)
        result = nr.run(task=napalm_get, getters=req.getters)
        
        output = {}
        for hostname, host_res in result.items():
            if host_res.failed:
                 print(f"ERROR: Task failed for {hostname}")

                 err_msg = "Unknown error"
                 if host_res.result and isinstance(host_res.result, str):
                     err_msg = host_res.result
                 elif host_res.exception:
                     err_msg = str(host_res.exception)
                
                 print(f"Underlying Error Message: {err_msg}")
                 if host_res.exception:
                     traceback.print_exception(type(host_res.exception), host_res.exception, host_res.exception.__traceback__)

                 output[hostname] = {"status": "failed", "error": err_msg}
            else:
                 output[hostname] = {"status": "success", "result": host_res[0].result}
                 
        return output
    except Exception as e:
        return {"error": str(e), "status": "failed"}

def check_reachability_task(task: Task) -> str:
    target = task.host.hostname
    port = task.host.port or 22
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2) 
        result = sock.connect_ex((target, port))
        sock.close()
        if result == 0:
            return "reachable"
        else:
            return "unreachable"
    except Exception as e:
        return "unreachable"

@app.post("/check_reachability")
async def check_reachability_endpoint(req: CommandRequest):
    try:
        nr = get_nornir(req.devices)
        result = nr.run(task=check_reachability_task)
        
        output = {}
        for hostname, host_res in result.items():
            if host_res.failed:
                 output[hostname] = {"status": "error", "reachability": "unreachable", "error": str(host_res.exception)}
            else:
                 reachability = host_res[0].result
                 output[hostname] = {"status": "success", "reachability": reachability}
                 
        return output
    except Exception as e:
        return {"error": str(e), "status": "failed"}

@app.get("/health")
def health():
    return {"status": "ok"}

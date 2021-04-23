from libs.webserver.executer_base import ExecuterBase

import logging
import subprocess
import psutil
import os
import re

class SystemInfoExecuter(ExecuterBase):

    def get_system_info_performance(self):
        data = dict()
        data["cpu_info"] = self.get_cpu_info()
        data["memory_info"] = self.get_memory_info()
        data["disk_info"] = self.get_disk_info()
        data["network_info"] = self.get_network_info()
        return data

    def get_cpu_info(self):
        return psutil.cpu_percent(interval=1)

    def get_memory_info(self):
        memory_info = dict()
        svmem_object = psutil.virtual_memory()
        memory_info["total"] = svmem_object.total
        memory_info["available"] = svmem_object.available
        memory_info["percent"] = svmem_object.percent
        memory_info["used"] = svmem_object.used
        memory_info["free"] = svmem_object.free
        return memory_info

    def get_disk_info(self):
        disk_info = dict()
        sdiskusage_object = psutil.disk_usage('/')
        disk_info["total"] = sdiskusage_object.total
        disk_info["used"] = sdiskusage_object.used
        disk_info["free"] = sdiskusage_object.free
        disk_info["percent"] = sdiskusage_object.percent
        return disk_info

    def get_network_info(self):
        network_info = dict()
        all_network_info = psutil.net_if_addrs()
        for current_nic in all_network_info:
            for current_address_family in all_network_info[current_nic]:
                if current_address_family.family == 2:
                    network_info[current_nic] = dict()
                    network_info[current_nic]["address"] = current_address_family.address
                    network_info[current_nic]["netmask"] = current_address_family.netmask
        return network_info

    def get_system_info_temperature(self):
        data = dict()
        data["raspi"] = self.get_raspi_temp()
        return data

    def get_raspi_temp(self):
        temp = os.popen("vcgencmd measure_temp").readline()
        return (re.findall(r"\d+\.\d+", temp)[0])

    def get_system_info_services(self):
        data = dict()
        data["mlsc"] = self.get_service_status("mlsc")
        data["hostapd"] = self.get_service_status("hostapd")
        data["dhcpcd"] = self.get_service_status("dhcpcd")
        data["dnsmasq"] = self.get_service_status("dnsmasq")

        return data

    def get_service_status(self, service_name):
        service_info = dict()
        try:
            stat = subprocess.call(["systemctl", "is-active", "--quiet", service_name])
            service_info["status"] = stat
            if(stat == 0):  # if 0 (active), print "Active"
                service_info["running"] = True
            service_info["service_not_found"] = False
        except Exception as e:
            self.logger.debug(f"Could not get service status: {service_name}")
            service_info["status"] = 9999
            service_info["running"] = False
            service_info["service_not_found"] = True
        return service_info
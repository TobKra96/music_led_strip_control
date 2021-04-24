from libs.webserver.executer_base import ExecuterBase

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
        cpu_info = dict()
        cpu_freq = dict(psutil.cpu_freq()._asdict())
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_info["frequency"] = cpu_freq["current"]
        cpu_info["percent"] = cpu_percent
        return cpu_info

    def get_memory_info(self):
        return dict(psutil.virtual_memory()._asdict())

    def get_disk_info(self):
        return dict(psutil.disk_usage('/')._asdict())

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
        cpu_temp_dict = dict()
        temp = os.popen("vcgencmd measure_temp").readline()
        cpu_temp_c = float(re.findall(r"\d+\.\d+", temp)[0])
        cpu_temp_f = float(f"{(cpu_temp_c * 1.8 + 32):0.1f}")

        cpu_temp_dict["celsius"] = cpu_temp_c
        cpu_temp_dict["fahrenheit"] = cpu_temp_f

        return cpu_temp_dict

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
            if stat == 0:  # if 0 (active), print "Active"
                service_info["running"] = True
            else:
                service_info["running"] = False
            service_info["service_not_found"] = False
        except Exception as e:
            self.logger.debug(f"Could not get service status: {service_name}")
            service_info["status"] = 9999
            service_info["running"] = False
            service_info["service_not_found"] = True
        return service_info


import os
import socket
import platform
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QWidget, QTextEdit, QMessageBox, QTabWidget, QProgressBar, QComboBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
import paramiko

logging.basicConfig(filename='app.log', level=logging.DEBUG)

class PortScannerThread(QThread):
    update_signal = pyqtSignal(list)
    progress_signal = pyqtSignal(int)

    def __init__(self, ip_or_host):
        super().__init__()
        self.ip_or_host = ip_or_host

    def check_port(self, ip_or_host, port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.2)  # Zaman aşımını düşük tutarak hızlı tarama
                result = sock.connect_ex((ip_or_host, port))
                return port if result == 0 else None
        except Exception as e:
            logging.error(f"Error checking port {port}: {e}")
            return None

    def run(self):
        open_ports = []
        total_ports = 1024
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(self.check_port, self.ip_or_host, port) for port in range(1, total_ports + 1)]
            for i, future in enumerate(futures):
                port = future.result()
                if port:
                    open_ports.append(port)
                self.progress_signal.emit(int(((i + 1) / total_ports) * 100))

        self.update_signal.emit(open_ports)

class AdvancedApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Advanced Network and System Tool")
        self.setGeometry(200, 200, 800, 600)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.ip_tab = QWidget()
        self.port_tab = QWidget()
        self.system_tab = QWidget()
        self.devices_tab = QWidget()
        self.command_tab = QWidget()

        self.tabs.addTab(self.ip_tab, "IP Details")
        self.tabs.addTab(self.port_tab, "Port Scanner")
        self.tabs.addTab(self.system_tab, "System Info")
        self.tabs.addTab(self.devices_tab, "Devices on Network")
        self.tabs.addTab(self.command_tab, "Remote Commands")

        self.init_ip_tab()
        self.init_port_tab()
        self.init_system_tab()
        self.init_devices_tab()
        self.init_command_tab()

    def init_ip_tab(self):
        layout = QVBoxLayout()

        self.ip_label = QLabel("Enter IP Address or Hostname:")
        self.ip_input = QLineEdit()
        self.ip_button = QPushButton("Get IP Details")
        self.ip_results = QTextEdit()
        self.ip_results.setReadOnly(True)

        self.ip_button.clicked.connect(self.get_ip_details)

        layout.addWidget(self.ip_label)
        layout.addWidget(self.ip_input)
        layout.addWidget(self.ip_button)
        layout.addWidget(self.ip_results)

        self.ip_tab.setLayout(layout)

    def get_ip_details(self):
        ip_or_host = self.ip_input.text().strip()
        if not ip_or_host:
            QMessageBox.warning(self, "Warning", "Please enter a valid IP address or hostname.")
            return

        try:
            command = ["ping", "-c", "1", ip_or_host] if os.name != "nt" else ["ping", "-n", "1", ip_or_host]
            response = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)
            self.ip_results.setPlainText(response)
        except subprocess.CalledProcessError as e:
            self.ip_results.setPlainText(f"Error: Unable to reach {ip_or_host}.\nDetails:\n{e.output}")
        except Exception as e:
            self.ip_results.setPlainText(f"Unexpected error: {e}")

    def init_port_tab(self):
        layout = QVBoxLayout()

        self.port_label = QLabel("Enter IP Address or Hostname:")
        self.port_input = QLineEdit()
        self.port_button = QPushButton("Scan Open Ports")
        self.port_results = QTextEdit()
        self.port_results.setReadOnly(True)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)

        self.port_button.clicked.connect(self.start_port_scan)

        layout.addWidget(self.port_label)
        layout.addWidget(self.port_input)
        layout.addWidget(self.port_button)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.port_results)

        self.port_tab.setLayout(layout)

    def start_port_scan(self):
        ip_or_host = self.port_input.text().strip()
        if not ip_or_host:
            QMessageBox.warning(self, "Warning", "Please enter a valid IP address or hostname.")
            return

        self.port_results.clear()
        self.progress_bar.setValue(0)

        self.port_scanner_thread = PortScannerThread(ip_or_host)
        self.port_scanner_thread.update_signal.connect(self.update_port_results)
        self.port_scanner_thread.progress_signal.connect(self.update_progress_bar)
        self.port_scanner_thread.start()

    def update_port_results(self, open_ports):
        if open_ports:
            self.port_results.append("=== Open Ports ===")
            self.port_results.append("\n".join(f"Port {port} is open." for port in open_ports))
        else:
            self.port_results.append("No open ports found.")

    def update_progress_bar(self, progress):
        self.progress_bar.setValue(progress)

    def init_system_tab(self):
        layout = QVBoxLayout()

        self.system_label = QLabel("System Info:")
        self.system_results = QTextEdit()
        self.system_results.setReadOnly(True)

        layout.addWidget(self.system_label)
        layout.addWidget(self.system_results)

        self.system_tab.setLayout(layout)
        self.get_system_info()

    def get_system_info(self):
        self.system_results.clear()
        self.system_results.append("=== System Information ===")
        self.system_results.append(f"System: {platform.system()}")
        self.system_results.append(f"Node Name: {platform.node()}")
        self.system_results.append(f"Release: {platform.release()}")
        self.system_results.append(f"Version: {platform.version()}")
        self.system_results.append(f"Machine: {platform.machine()}")
        self.system_results.append(f"Processor: {platform.processor()}")

    def init_devices_tab(self):
        layout = QVBoxLayout()

        self.devices_label = QLabel("Devices on Network:")
        self.devices_button = QPushButton("Scan for Devices")
        self.devices_results = QTextEdit()
        self.devices_results.setReadOnly(True)
        self.device_combobox = QComboBox()  # Dropdown for selecting device

        self.devices_button.clicked.connect(self.scan_network_devices)

        layout.addWidget(self.devices_label)
        layout.addWidget(self.devices_button)
        layout.addWidget(self.device_combobox)
        layout.addWidget(self.devices_results)

        self.devices_tab.setLayout(layout)

    def scan_network_devices(self):
        self.devices_results.clear()
        self.devices_results.append("=== Scanning for Devices ===")
        try:
            result = subprocess.check_output("arp -a", shell=True, universal_newlines=True)
            devices = result.splitlines()
            self.device_combobox.clear()  # Clear previous devices in the dropdown
            for device in devices:
                self.devices_results.append(device)
                # Extract IP address from the result (e.g., "192.168.1.1        00-14-22-01-23-45     dynamic")
                ip = device.split()[1] if len(device.split()) > 1 else None
                if ip:
                    self.device_combobox.addItem(ip)
        except Exception as e:
            self.devices_results.append(f"Error scanning devices: {e}")

    def init_command_tab(self):
        layout = QVBoxLayout()

        self.command_label = QLabel("Send Command to Remote System:")
        self.command_input = QLineEdit()
        self.command_button = QPushButton("Send Command")
        self.command_results = QTextEdit()
        self.command_results.setReadOnly(True)

        self.command_button.clicked.connect(self.execute_remote_command)

        layout.addWidget(self.command_label)
        layout.addWidget(self.command_input)
        layout.addWidget(self.command_button)
        layout.addWidget(self.command_results)

        self.command_tab.setLayout(layout)

    def execute_remote_command(self):
        command = self.command_input.text().strip()
        if not command:
            QMessageBox.warning(self, "Warning", "Please enter a command to execute.")
            return

        device_ip = self.device_combobox.currentText()
        if not device_ip:
            QMessageBox.warning(self, "Warning", "Please select a device from the list.")
            return

        self.execute_remote_whoami(device_ip)

    def execute_remote_whoami(self, device_ip):
        username = "your_username"  # Uzak cihazın kullanıcı adı
        password = "your_password"  # Uzak cihazın şifresi

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(device_ip, username=username, password=password)

            stdin, stdout, stderr = ssh.exec_command("whoami")
            output = stdout.read().decode().strip()
            self.command_results.setPlainText(f"Remote user on {device_ip}: {output}")
            ssh.close()

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Unable to execute command on remote device.\n{str(e)}")

def main():
    app = QApplication([])
    window = AdvancedApp()
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()






















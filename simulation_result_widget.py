import os, sys, subprocess

from PyQt5 import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import xml.etree.ElementTree as ET
from lib.openscenario.client.open_scenario_client_logger import OpenScenarioClientLogger as OSCLogger

class SimulationResultWidget(QWidget):
    def __init__(self, file_io_funcs,
            total_num_label, succeeded_label, failed_label, none_label,
            btn_clear, btn_open_log_folder,
            progressbar_result, result_table_widget, table_widget):
        super(SimulationResultWidget, self).__init__()

        # Initialize member variables
        self.file_io_funcs = file_io_funcs
        self.total_num_label = total_num_label
        self.succeeded_label = succeeded_label
        self.failed_label = failed_label
        self.none_label = none_label
        self.progressbar_result = progressbar_result
        self.btn_clear = btn_clear
        self.btn_open_log_folder = btn_open_log_folder
        self.table_widget:QTableWidget = table_widget
        self.result_widget:QTableWidget = result_table_widget
        self.__clear()

        # Set widget options
        self.table_widget.setColumnWidth(0, 30)
        # Set widget Handlers
        self.table_widget.clicked.connect(lambda:self.__selected_row_cb())
        # Set Button Handlers
        self.btn_clear.clicked.connect(lambda:self.__clear())
        self.btn_open_log_folder.clicked.connect(lambda:self.__open_log_folder())

        # Set Icons (type: PyQt5.QtGui.QIcon)
        self.icon_succeeded = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
        self.icon_failed = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton)
        self.icon_question = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion)

    def initialize(self):
        self.__clear()
        OSCLogger.new_batch()
        
    def set_start_status(self, status:bool):
        self.btn_clear.setEnabled(not status)

    def update_widget(self, scenario_file_list=None):
        # Set Table Widget Row
        if scenario_file_list:
            row_count = self.table_widget.rowCount()
            self.index = row_count
            self.table_widget.setRowCount(row_count + len(scenario_file_list))
            for i, file_path in enumerate(scenario_file_list):
                self._add_test_scenario_to_table(row_count + i, file_path)
        
        # Set number labels
        self.total_num_label.setText(str(self.table_widget.rowCount()))
        self.succeeded_label.setText(str(self.success_count))
        self.failed_label.setText(str(self.fail_count))
        self.none_label.setText(str(self.none_count))

        # Add progress bar
        self.progressbar_result.setMaximum(self.table_widget.rowCount())
        self.progressbar_result.setValue(self.success_count+self.fail_count+self.none_count)

    def _add_test_scenario_to_table(self, idx, file_path):
        # 1. File name
        file_name = QTableWidgetItem()
        file_name.setData(Qt.ToolTipRole, file_path)
        file_name.setData(Qt.DisplayRole, os.path.basename(file_path).split('.')[0]) 
        # 2. Map name
        tree = ET.parse(file_path)
        map_element = tree.find('SimulatorInfo/Map')
        if map_element is not None and 'name' in map_element.attrib:
            map_name = QTableWidgetItem(map_element.attrib['name'])
        # Add filename, mapname
        self.table_widget.setItem(idx, 0, QTableWidgetItem())
        self.table_widget.setItem(idx, 1, file_name)
        self.table_widget.setItem(idx, 2, map_name)
        self.table_widget.setItem(idx, 3, QTableWidgetItem())

    def set_scenario_result(self, is_success:bool, duration, evaluation_item, simulation_logs):
        # Add an icon
        icon_item = self.table_widget.item(self.index, 0)
        if icon_item != None: # new scenario 일 경우
            if is_success is True:
                icon_item.setIcon(self.icon_succeeded)
                self.success_count += 1     # Count success
            elif is_success is False:
                icon_item.setIcon(self.icon_failed)
                self.fail_count += 1        # Count failure
            else:
                icon_item.setIcon(self.icon_question)
                self.none_count += 1        # Count none
            
            # Add duration
            duration_item = self.table_widget.item(self.index, 3)
            duration_item.setData(Qt.DisplayRole, str(float(duration)))

            # Set result
            self.result_dict[self.index] = []
            self.result_dict[self.index].append("Max. Way Off Path (m): {:.3f}".format(evaluation_item.way_off_distance))
            self.result_dict[self.index].append("Max. Lateral Accelation (m/s\u00b2): {:.3f}".format(evaluation_item.lateral_acceleration))
            self.result_dict[self.index].append("Max. Longitudinal Acceleration (m/s\u00b2): {:.3f}".format(evaluation_item.longitudinal_acceleration))
            self.result_dict[self.index].append("Max. Speed Excess (km/h): {:.3f}".format(evaluation_item.exceeding_speed))
            self.result_dict[self.index].append("Max. Speed deficit (km/h): {:.3f}".format(evaluation_item.deficit_speed))
            vtv = "{:.3f}".format(evaluation_item.vtv_distance) if evaluation_item.vtv_distance < 1e9 else "-"
            ttc = "{:.3f}".format(evaluation_item.time_to_collision) if evaluation_item.time_to_collision < 1e9 else "-"
            self.result_dict[self.index].append("Min. Safe Distance (m): " + vtv)
            self.result_dict[self.index].append("Min. Time to Collision (s): " + ttc)
            self.result_dict[self.index].append("----------------------------------------------------------------------------------------------------")
            for log in simulation_logs:
                self.result_dict[self.index].append(log)

            self.index += 1
            self.update_widget()
        else:
            return

    def __clear(self):
        self.table_widget.setRowCount(0)
        self.index = 0
        self.success_count = 0
        self.fail_count = 0
        self.none_count = 0
        self.total_num_label.setText("0")
        self.succeeded_label.setText("0")
        self.failed_label.setText("0")
        self.none_label.setText("0")
        self.result_widget.setRowCount(0)
        self.result_dict = dict()
        self.progressbar_result.setValue(0)
        self.progressbar_result.setMaximum(0)

    def __selected_row_cb(self):
        # Callback tablewidget's current row
        selected_row = self.table_widget.currentRow()
        try:
            results = self.result_dict[selected_row]
            self._add_result_to_table(results)
        except:
            self.result_widget.setRowCount(0)

    def _add_result_to_table(self, results):
        # Initialize
        self.result_widget.setRowCount(0)
        # Add result
        result_row_count = self.result_widget.rowCount()
        self.result_widget.setRowCount(result_row_count + len(results))
        for i, result in enumerate(results):
            self.result_widget.setItem(result_row_count + i, 0, QTableWidgetItem(result))

    def __open_log_folder(self):
        if sys.platform == "win32":
            path = os.path.normpath(".\\logs_scenario_runner")
            os.makedirs(path, exist_ok=True)
            os.startfile(path)
        else:
            path = os.path.normpath("./logs_scenario_runner")
            os.makedirs(path, exist_ok=True)
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.call([opener, path])
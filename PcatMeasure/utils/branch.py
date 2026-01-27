# -*- coding: utf-8 -*-
"""
Created on Sun Nov 30 07:59:03 2025

@author: Hattori
"""
import qt
import slicer
import slicer.util


def showMultiCheckPopup(total_lengths, default_ids=None, coronary_name="Artery",onAcceptedCallback=None):

    if default_ids is None:
        default_ids = []

    dialog = qt.QDialog(slicer.util.mainWindow())
    dialog.setWindowTitle("Select Branches")
    dialog.setModal(False)

    layout = qt.QVBoxLayout(dialog)

    check_boxes = []

    groupBox = qt.QGroupBox(f"Select Branches for {coronary_name}")
    vbox = qt.QVBoxLayout(groupBox)

    for i, length in enumerate(total_lengths):
        cb = qt.QCheckBox(f"Branch {i} - Length: {length:.2f} mm")
        cb.setChecked(i in default_ids)
        vbox.addWidget(cb)
        check_boxes.append(cb)

    layout.addWidget(groupBox)

    total_label = qt.QLabel()
    layout.addWidget(total_label)

    def update_total():
        total = sum(total_lengths[i] for i, cb in enumerate(check_boxes) if cb.isChecked())
        total_label.setText(f"Selected total length: {total:.2f} mm")

    for cb in check_boxes:
        cb.stateChanged.connect(update_total)

    update_total()
    
    buttonBox = qt.QDialogButtonBox(dialog)
    buttonBox.setStandardButtons(
        qt.QDialogButtonBox.Ok | qt.QDialogButtonBox.Cancel
    )
    buttonBox.setOrientation(qt.Qt.Horizontal)
    buttonBox.setMinimumHeight(40)
    
    layout.addWidget(buttonBox)
    

    #buttonBox = qt.QDialogButtonBox(qt.QDialogButtonBox.Ok | qt.QDialogButtonBox.Cancel)
    #layout.addWidget(buttonBox)

    def onAccepted():
        selected_ids = [i for i, cb in enumerate(check_boxes) if cb.isChecked()]
        total_selected_length = sum(total_lengths[i] for i in selected_ids)
        if onAcceptedCallback:
            onAcceptedCallback(selected_ids, total_selected_length)
        dialog.close()

    buttonBox.accepted.connect(onAccepted)
    buttonBox.rejected.connect(dialog.close)

    dialog.show()

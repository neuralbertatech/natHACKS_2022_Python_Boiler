from PyQt5.QtWidgets import QMessageBox

# Alert dialog
# https://marcelozarate.com/simple-alert-dialog-pyqt
# Accessed May 26th, 2022
def showMessageBox(
    title, text, icon="NoIcon", buttons=False, buttonsText=[], callback=None, width=500
):
    qmb = QMessageBox()
    qmb.setText(text)
    qmb.setMinimumWidth(width)
    qmb.setWindowTitle(title)
    if icon == "NoIcon":
        qmb.setIcon(QMessageBox.NoIcon)
    if icon == "Information":
        qmb.setIcon(QMessageBox.Information)
    if icon == "Warning":
        qmb.setIcon(QMessageBox.Warning)
    if icon == "Critical":
        qmb.setIcon(QMessageBox.Critical)
    if icon == "Question":
        qmb.setIcon(QMessageBox.Question)

    if buttons == True:
        qmb.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        if len(buttonsText) == 2:
            qmb.button(QMessageBox.Ok).setText(buttonsText[0])
            qmb.button(QMessageBox.Cancel).setText(buttonsText[1])
    else:
        if len(buttonsText) == 1:
            qmb.setStandardButtons(QMessageBox.Ok)
            qmb.button(QMessageBox.Ok).setText(buttonsText[0])

    if qmb.exec() == QMessageBox.Ok:
        if callback:
            return callback()
        else:
            return None
    else:
        return None

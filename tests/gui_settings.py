import pyforms
from pyforms.basewidget import BaseWidget
from pyforms.controls import ControlButton
from pyforms.controls import ControlText


class SettingsGUI(BaseWidget):
    def __init__(self, s=None):
        super(SettingsGUI, self).__init__("SettingsGUI")

        # Definition of the forms fields
        self._firstname = ControlText("First name", "Default value")
        self._middlename = ControlText("Middle name")
        self._lastname = ControlText("Lastname name")
        self._fullname = ControlText("Full name")
        self._button = ControlButton("Press this button")
        self._test = ControlText("sth")

        self.formset = [
            {
                "Tab1": ["_firstname", "||", "_middlename", "||", "_lastname"],
                "Tab2": ["_fullname"],
            },
            "=",
            (" ", "_button", " "),
            "=",
            "_test",
        ]

    def __dummyEvent(self):
        print("Menu option selected")


##################################################################################################################
##################################################################################################################
##################################################################################################################

# Execute the application
if __name__ == "__main__":
    app = pyforms.start_app(SettingsGUI)
    print("here", app)
    print("done")


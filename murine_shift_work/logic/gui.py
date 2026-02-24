import types

import PySimpleGUI as sg


def ask_water_calibration_ready(
    valve=None,
):  # fixme: remodel into proper pyqt dialog windows
    layout = [
        [sg.Text(f"Ready for calibration of valve #{valve}")],
        [sg.Button("Ok")],
    ]

    # Create the window
    window = sg.Window("Water calibration", layout)

    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED or event == "Ok":
            break

    window.close()
    return True


def ask_water_calibration_weight():
    layout = [
        [sg.Text("Please enter water weight (gram):"), sg.Input(key="WEIGHT")],
        [sg.Button("Ok")],
    ]

    # Create the window
    window = sg.Window("Water calibration", layout)

    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED or event == "Ok":
            break

    window.close()
    return float(values["WEIGHT"])


class SettingsGUI(object):
    settings = None
    layout = []

    def __init__(self, settings=None):
        """

        :param settings: input is whole settings module file
        """
        super(SettingsGUI, self).__init__()

        if not isinstance(settings, types.ModuleType):
            raise TypeError(f"settings have to be of type {types.ModuleType}")
        self.settings = settings

        self.generate_layout()

    def generate_layout(self):
        for setting_name in dir(self.settings):
            if setting_name.startswith("__"):
                continue
            default_value = eval(f"self.settings.{setting_name}")
            if isinstance(default_value, str):
                metadata_type = "str"
            metadata_type = " "
            row = [
                sg.Text(setting_name),
                sg.Input(
                    key=setting_name,
                    default_text=default_value,
                    metadata=metadata_type,
                ),
            ]
            self.layout.append(row)

        self.layout.append([sg.Button("Ok")])

    def show(self):
        # Define the window's contents
        # layout = [
        #     [sg.Text("What's your name?"), sg.Input(key="-INPUT-")],
        #     [sg.Text(size=(40, 1), key="-OUTPUT-"), sg.Input(key="-INPUT2-")],
        #     [sg.Button("Ok"), sg.Button("Quit")],
        # ]

        # Create the window
        window = sg.Window("Task settings", self.layout)

        # Display and interact with the Window using an Event Loop
        while True:
            event, values = window.read()
            # See if user wants to quit or window was closed
            if event == sg.WINDOW_CLOSED or event == "Ok":
                break
            # Output a message to the window
            # window["-OUTPUT-"].update(
            #     "Hello " + values["-INPUT-"] + "! Thanks for trying PySimpleGUI"
            # )

        # Finish up by removing from the screen
        window.close()
        return values


if __name__ == "__main__":
    from murine_shift_work.tasks.probabilistic_switching import task_settings

    s = SettingsGUI(settings=task_settings)
    values = s.show()
    print(values)

import math
import struct

import serial


"""
----------------------------------------------------------------------------

This file is part of the Sanworks Pulse Pal repository
Copyright (C) 2016 Sanworks LLC, Sound Beach, New York, USA

----------------------------------------------------------------------------

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3.

This program is distributed  WITHOUT ANY WARRANTY and without even the
implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
"""
Adaptation of Sanworks PulsePal code for python 3.x
Lars Rollik, 2018, 2019, 2021
"""


class PulsePalObject(object):
    def __init__(self):
        self.serialObject = 0
        self.OpMenuByte = 213
        self.firmwareVersion = 0
        self.model = 0
        self.dac_bitMax = 0
        self.cycleFrequency = 20000
        self.isBiphasic = [float("nan"), 0, 0, 0, 0]
        self.phase1Voltage = [float("nan"), 5, 5, 5, 5]
        self.phase2Voltage = [float("nan"), -5, -5, -5, -5]
        self.restingVoltage = [float("nan"), 0, 0, 0, 0]
        self.phase1Duration = [float("nan"), 0.001, 0.001, 0.001, 0.001]
        self.interPhaseInterval = [float("nan"), 0.001, 0.001, 0.001, 0.001]
        self.phase2Duration = [float("nan"), 0.001, 0.001, 0.001, 0.001]
        self.interPulseInterval = [float("nan"), 0.01, 0.01, 0.01, 0.01]
        self.burstDuration = [float("nan"), 0, 0, 0, 0]
        self.interBurstInterval = [float("nan"), 0, 0, 0, 0]
        self.pulseTrainDuration = [float("nan"), 1, 1, 1, 1]
        self.pulseTrainDelay = [float("nan"), 0, 0, 0, 0]
        self.linkTriggerChannel1 = [float("nan"), 1, 1, 1, 1]
        self.linkTriggerChannel2 = [float("nan"), 0, 0, 0, 0]
        self.customTrainID = [float("nan"), 0, 0, 0, 0]
        self.customTrainTarget = [float("nan"), 0, 0, 0, 0]
        self.customTrainLoop = [float("nan"), 0, 0, 0, 0]
        self.triggerMode = [float("nan"), 0, 0]
        self.outputParameterNames = [
            "isBiphasic",
            "phase1Voltage",
            "phase2Voltage",
            "phase1Duration",
            "interPhaseInterval",
            "phase2Duration",
            "interPulseInterval",
            "burstDuration",
            "interBurstInterval",
            "pulseTrainDuration",
            "pulseTrainDelay",
            "linkTriggerChannel1",
            "linkTriggerChannel2",
            "customTrainID",
            "customTrainTarget",
            "customTrainLoop",
            "restingVoltage",
        ]
        self.triggerParameterNames = ["triggerMode"]

    def connect(self, serial_port_name):
        self.serialObject = serial.Serial(serial_port_name, 115200, timeout=1)
        handshake_byte_string = struct.pack("BB", self.OpMenuByte, 72)
        self.serialObject.write(handshake_byte_string)
        response = self.serialObject.read(5)
        fv_bytes = response[1:5]
        self.firmwareVersion = struct.unpack("<I", fv_bytes)[0]
        if self.firmwareVersion < 20:
            self.model = 1
            self.dac_bitMax = 255
        else:
            self.model = 2
            self.dac_bitMax = 65535
        if self.firmwareVersion == 20:
            print(
                "Notice: NOTE: A firmware update is available. It fixes a bug in Pulse Gated trigger mode when used with multiple inputs."
            )
            print(
                "To update, follow the instructions at https://sites.google.com/site/pulsepalwiki/updating-firmware"
            )
        self.serialObject.write("YPYTHON".encode())

    def disconnect(self):
        terminateByteString = struct.pack("BB", self.OpMenuByte, 81)
        self.serialObject.write(terminateByteString)
        self.serialObject.close()

    def programOutputChannelParam(self, param_name, channel, value):
        original_value = value
        if isinstance(param_name, str):
            param_code = self.outputParameterNames.index(param_name) + 1
        else:
            param_code = param_name

        if 2 <= param_code <= 3:
            value = math.ceil(
                ((value + 10) / float(20)) * self.dac_bitMax
            )  # Convert volts to bits
            if self.model == 1:
                program_byte_string = struct.pack(
                    "BBBBB", self.OpMenuByte, 74, param_code, channel, value
                )
            else:
                program_byte_string = struct.pack(
                    "<BBBBH", self.OpMenuByte, 74, param_code, channel, value
                )
        elif param_code == 17:
            value = math.ceil(
                ((value + 10) / float(20)) * self.dac_bitMax
            )  # Convert volts to bits
            if self.model == 1:
                program_byte_string = struct.pack(
                    "BBBBB", self.OpMenuByte, 74, param_code, channel, value
                )
            else:
                program_byte_string = struct.pack(
                    "<BBBBH", self.OpMenuByte, 74, param_code, channel, value
                )
        elif 4 <= param_code <= 11:
            program_byte_string = struct.pack(
                "<BBBBL",
                self.OpMenuByte,
                74,
                param_code,
                channel,
                value * self.cycleFrequency,
            )
        else:
            program_byte_string = struct.pack(
                "BBBBB", self.OpMenuByte, 74, param_code, channel, value
            )
        self.serialObject.write(program_byte_string)
        # Receive acknowledgement
        ok = self.serialObject.read(1)
        if len(ok) == 0:
            raise PulsePalError(
                "Error: Pulse Pal did not return an acknowledgement byte after a call to programOutputChannelParam."
            )

        self.update_parameter_fields(
            self, param_code=param_code, channel=channel, original_value=original_value
        )

    def update_parameter_fields(
        self, param_code=None, channel=None, original_value=None
    ):
        # Update the PulsePal object's parameter fields
        if param_code == 1:
            self.isBiphasic[channel] = original_value
        elif param_code == 2:
            self.phase1Voltage[channel] = original_value
        elif param_code == 3:
            self.phase2Voltage[channel] = original_value
        elif param_code == 4:
            self.phase1Duration[channel] = original_value
        elif param_code == 5:
            self.interPhaseInterval[channel] = original_value
        elif param_code == 6:
            self.phase2Duration[channel] = original_value
        elif param_code == 7:
            self.interPulseInterval[channel] = original_value
        elif param_code == 8:
            self.burstDuration[channel] = original_value
        elif param_code == 9:
            self.interBurstInterval[channel] = original_value
        elif param_code == 10:
            self.pulseTrainDuration[channel] = original_value
        elif param_code == 11:
            self.pulseTrainDelay[channel] = original_value
        elif param_code == 12:
            self.linkTriggerChannel1[channel] = original_value
        elif param_code == 13:
            self.linkTriggerChannel2[channel] = original_value
        elif param_code == 14:
            self.customTrainID[channel] = original_value
        elif param_code == 15:
            self.customTrainTarget[channel] = original_value
        elif param_code == 16:
            self.customTrainLoop[channel] = original_value
        elif param_code == 17:
            self.restingVoltage[channel] = original_value

    def programTriggerChannelParam(self, paramName, channel, value):
        originalValue = value
        if isinstance(paramName, str):
            paramCode = self.triggerParameterNames.index(paramName) + 1
        else:
            paramCode = paramName
        messageBytes = struct.pack(
            "BBBBB", self.OpMenuByte, 74, paramCode, channel, value
        )
        self.serialObject.write(messageBytes)
        # Receive acknowledgement
        ok = self.serialObject.read(1)
        if len(ok) == 0:
            raise PulsePalError(
                "Error: Pulse Pal did not return an acknowledgement byte after a call to programTriggerChannelParam."
            )
        if paramCode == 1:
            self.triggerMode[channel] = originalValue

    def syncAllParams(self):
        # First make a list data-type with all param values in an iteration of the loop.
        # Then pack them by data-type and append to string with + operation
        programByteString = struct.pack("BB", self.OpMenuByte, 73)

        # Add 32-bit time params
        programValues = [0] * 32
        pos = 0
        for i in range(1, 5):
            programValues[pos] = self.phase1Duration[i] * self.cycleFrequency
            pos += 1
            programValues[pos] = self.interPhaseInterval[i] * self.cycleFrequency
            pos += 1
            programValues[pos] = self.phase2Duration[i] * self.cycleFrequency
            pos += 1
            programValues[pos] = self.interPulseInterval[i] * self.cycleFrequency
            pos += 1
            programValues[pos] = self.burstDuration[i] * self.cycleFrequency
            pos += 1
            programValues[pos] = self.interBurstInterval[i] * self.cycleFrequency
            pos += 1
            programValues[pos] = self.pulseTrainDuration[i] * self.cycleFrequency
            pos += 1
            programValues[pos] = self.pulseTrainDelay[i] * self.cycleFrequency
            pos += 1
        # Pack 32-bit times to bytes and append to program byte-string
        programValues = [int(p) for p in programValues]

        programByteString = programByteString + struct.pack(
            "<LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL", *programValues
        )

        # Add 16-bit voltages
        if self.model == 2:
            programValues = [0] * 12
            pos = 0
            for i in range(1, 5):
                value = math.ceil(
                    ((self.phase1Voltage[i] + 10) / float(20)) * self.dac_bitMax
                )  # Convert volts to bits
                programValues[pos] = value
                pos += 1
                value = math.ceil(
                    ((self.phase2Voltage[i] + 10) / float(20)) * self.dac_bitMax
                )  # Convert volts to bits
                programValues[pos] = value
                pos += 1
                value = math.ceil(
                    ((self.restingVoltage[i] + 10) / float(20)) * self.dac_bitMax
                )  # Convert volts to bits
                programValues[pos] = value
                pos += 1
            programByteString = programByteString + struct.pack(
                "<HHHHHHHHHHHH", *programValues
            )
        # Add 8-bit params
        if self.model == 1:
            programValues = [0] * 28
        else:
            programValues = [0] * 16
        pos = 0
        for i in range(1, 5):
            programValues[pos] = self.isBiphasic[i]
            pos += 1
            if self.model == 1:
                value = math.ceil(
                    ((self.phase1Voltage[i] + 10) / float(20)) * self.dac_bitMax
                )  # Convert volts to bits
                programValues[pos] = value
                pos += 1
                value = math.ceil(
                    ((self.phase2Voltage[i] + 10) / float(20)) * self.dac_bitMax
                )  # Convert volts to bits
                programValues[pos] = value
                pos += 1
            programValues[pos] = self.customTrainID[i]
            pos += 1
            programValues[pos] = self.customTrainTarget[i]
            pos += 1
            programValues[pos] = self.customTrainLoop[i]
            pos += 1
            if self.model == 1:
                value = math.ceil(
                    ((self.restingVoltage[i] + 10) / float(20)) * self.dac_bitMax
                )  # Convert volts to bits
                programValues[pos] = value
                pos += 1
        # Pack 8-bit params to bytes and append to program byte-string
        if self.model == 1:
            programByteString = programByteString + struct.pack(
                "BBBBBBBBBBBBBBBBBBBBBBBBBBBB", *programValues
            )
        else:
            programByteString = programByteString + struct.pack(
                "BBBBBBBBBBBBBBBB", *programValues
            )
        # Add trigger channel link params
        programValues = [0] * 8
        pos = 0
        for i in range(1, 5):
            programValues[pos] = self.linkTriggerChannel1[i]
            pos += 1
        for i in range(1, 5):
            programValues[pos] = self.linkTriggerChannel2[i]
            pos += 1
        # Pack 8-bit params to bytes and append to program byte-string
        programByteString = programByteString + struct.pack("BBBBBBBB", *programValues)

        # Add trigger mode params
        programByteString = programByteString + struct.pack(
            "BB", self.triggerMode[1], self.triggerMode[2]
        )

        # Send program byte string to PulsePal
        self.serialObject.write(programByteString)
        # Receive acknowledgement
        ok = self.serialObject.read(1)
        if len(ok) == 0:
            raise PulsePalError(
                "Error: Pulse Pal did not return an acknowledgement byte after a call to syncAllParams."
            )

    def sendCustomPulseTrain(self, customTrainID, pulseTimes, pulseVoltages):
        nPulses = len(pulseTimes)
        for i in range(0, nPulses):
            pulseTimes[i] = (
                pulseTimes[i] * self.cycleFrequency
            )  # Convert seconds to multiples of minimum cycle (100us)
            pulseVoltages[i] = math.ceil(
                ((pulseVoltages[i] + 10) / float(20)) * self.dac_bitMax
            )  # Convert volts to bytes
        if customTrainID == 1:
            messageBytes = struct.pack(
                "BB", self.OpMenuByte, 75
            )  # Op code for programming train 1
        else:
            messageBytes = struct.pack(
                "BB", self.OpMenuByte, 76
            )  # Op code for programming train 2
        if self.model == 1:
            messageBytes = messageBytes + struct.pack(
                "<BL", 0, nPulses
            )  # 0 is the USB packet correction byte. See PulsePal wiki
        else:
            messageBytes = messageBytes + struct.pack("<L", nPulses)
        messageBytes = messageBytes + struct.pack(
            ("<" + "L" * nPulses), *pulseTimes
        )  # Add pulse times
        if self.model == 1:
            messageBytes = messageBytes + struct.pack(
                ("B" * nPulses), *pulseVoltages
            )  # Add pulse times
        else:
            messageBytes = messageBytes + struct.pack(
                ("<" + "H" * nPulses), *pulseVoltages
            )  # Add pulse times
        self.serialObject.write(messageBytes)
        # Receive acknowledgement
        ok = self.serialObject.read(1)
        if len(ok) == 0:
            raise PulsePalError(
                "Error: Pulse Pal did not return an acknowledgement byte after a call to sendCustomPulseTrain."
            )

    def sendCustomWaveform(
        self, customTrainID, pulseWidth, pulseVoltages
    ):  # For custom pulse trains with pulse times = pulse width
        nPulses = len(pulseVoltages)
        pulseTimes = [0] * nPulses
        pulseWidth = (
            pulseWidth * self.cycleFrequency
        )  # Convert seconds to to multiples of minimum cycle (100us)
        for i in range(0, nPulses):
            pulseTimes[i] = pulseWidth * i  # Add consecutive pulse
            pulseVoltages[i] = math.ceil(
                ((pulseVoltages[i] + 10) / float(20)) * self.dac_bitMax
            )  # Convert volts to bytes
        if customTrainID == 1:
            messageBytes = struct.pack(
                "BB", self.OpMenuByte, 75
            )  # Op code for programming train 1
        else:
            messageBytes = struct.pack(
                "BB", self.OpMenuByte, 76
            )  # Op code for programming train 2
        if self.model == 1:
            messageBytes = messageBytes + struct.pack(
                "<BL", 0, nPulses
            )  # 0 is the USB packet correction byte. See PulsePal wiki
        else:
            messageBytes = messageBytes + struct.pack("<L", nPulses)
        messageBytes = messageBytes + struct.pack(
            ("<" + "L" * nPulses), *pulseTimes
        )  # Add pulse times
        if self.model == 1:
            messageBytes = messageBytes + struct.pack(
                ("B" * nPulses), *pulseVoltages
            )  # Add pulse times
        else:
            messageBytes = messageBytes + struct.pack(
                ("<" + "H" * nPulses), *pulseVoltages
            )  # Add pulse times
        self.serialObject.write(messageBytes)  # Send custom waveform
        # Receive acknowledgement
        ok = self.serialObject.read(1)
        if len(ok) == 0:
            raise PulsePalError(
                "Error: Pulse Pal did not return an acknowledgement byte after a call to sendCustomWaveform."
            )

    def triggerOutputChannels(self, channel1, channel2, channel3, channel4):
        triggerByte = 0
        triggerByte = triggerByte + (1 * channel1)
        triggerByte = triggerByte + (2 * channel2)
        triggerByte = triggerByte + (4 * channel3)
        triggerByte = triggerByte + (8 * channel4)
        messageBytes = struct.pack("BBB", self.OpMenuByte, 77, triggerByte)
        self.serialObject.write(messageBytes)

    def abortPulseTrains(self):
        messageBytes = struct.pack("BB", self.OpMenuByte, 80)
        self.serialObject.write(messageBytes)

    def setContinuousLoop(self, channel, state):
        messageBytes = struct.pack("BBBB", self.OpMenuByte, 82, channel, state)
        self.serialObject.write(messageBytes)

    def setFixedVoltage(self, channel, voltage):
        voltage = math.ceil(
            ((voltage + 10) / float(20)) * self.dac_bitMax
        )  # Convert volts to bytes
        if self.model == 1:
            messageBytes = struct.pack("BBBB", self.OpMenuByte, 79, channel, voltage)
        else:
            messageBytes = struct.pack("<BBBH", self.OpMenuByte, 79, channel, voltage)
        self.serialObject.write(messageBytes)
        # Receive acknowledgement
        ok = self.serialObject.read(1)
        if len(ok) == 0:
            raise PulsePalError(
                "Error: Pulse Pal did not return an acknowledgement byte after a call to setFixedVoltage."
            )

    def setDisplay(self, row1String, row2String):
        messageBytes = row1String + chr(254) + row2String
        messageSize = len(messageBytes)
        messageBytes = chr(self.OpMenuByte) + chr(78) + chr(messageSize) + messageBytes
        self.serialObject.write(messageBytes)

    def saveSDSettings(self, fileName):
        if self.model == 1:
            raise PulsePalError(
                "Pulse Pal 1.X has no microSD card, and therefore does not support on-board settings files."
            )
        else:
            fileNameSize = len(fileName)
            messageBytes = (
                chr(self.OpMenuByte) + chr(90) + chr(1) + chr(fileNameSize) + fileName
            )
            self.serialObject.write(messageBytes)

    def deleteSDSettings(self, fileName):
        if self.model == 1:
            raise PulsePalError(
                "Pulse Pal 1.X has no microSD card, and therefore does not support on-board settings files."
            )
        else:
            fileNameSize = len(fileName)
            messageBytes = (
                chr(self.OpMenuByte) + chr(90) + chr(3) + chr(fileNameSize) + fileName
            )
            self.serialObject.write(messageBytes)

    def loadSDSettings(self, fileName):
        if self.model == 1:
            raise PulsePalError(
                "Pulse Pal 1.X has no microSD card, and therefore does not support on-board settings files."
            )
        else:
            fileNameSize = len(fileName)
            messageBytes = (
                chr(self.OpMenuByte) + chr(90) + chr(2) + chr(fileNameSize) + fileName
            )
            self.serialObject.write(messageBytes)
            response = self.serialObject.read(178)
            ind = 0
            cFreq = float(self.cycleFrequency)
            for i in range(1, 5):
                self.phase1Duration[i] = (
                    struct.unpack("<L", response[ind : ind + 4])[0] / cFreq
                )
                ind += 4
                self.interPhaseInterval[i] = (
                    struct.unpack("<L", response[ind : ind + 4])[0] / cFreq
                )
                ind += 4
                self.phase2Duration[i] = (
                    struct.unpack("<L", response[ind : ind + 4])[0] / cFreq
                )
                ind += 4
                self.interPulseInterval[i] = (
                    struct.unpack("<L", response[ind : ind + 4])[0] / cFreq
                )
                ind += 4
                self.burstDuration[i] = (
                    struct.unpack("<L", response[ind : ind + 4])[0] / cFreq
                )
                ind += 4
                self.interBurstInterval[i] = (
                    struct.unpack("<L", response[ind : ind + 4])[0] / cFreq
                )
                ind += 4
                self.pulseTrainDuration[i] = (
                    struct.unpack("<L", response[ind : ind + 4])[0] / cFreq
                )
                ind += 4
                self.pulseTrainDelay[i] = (
                    struct.unpack("<L", response[ind : ind + 4])[0] / cFreq
                )
                ind += 4
            for i in range(1, 5):
                voltage_bits = struct.unpack("<H", response[ind : ind + 2])[0]
                ind += 2
                self.phase1Voltage[i] = (
                    round((((voltage_bits / float(self.dac_bitMax)) * 20) - 10) * 100)
                    / 100
                )
                voltage_bits = struct.unpack("<H", response[ind : ind + 2])[0]
                ind += 2
                self.phase2Voltage[i] = (
                    round((((voltage_bits / float(self.dac_bitMax)) * 20) - 10) * 100)
                    / 100
                )
                voltage_bits = struct.unpack("<H", response[ind : ind + 2])[0]
                ind += 2
                self.restingVoltage[i] = (
                    round((((voltage_bits / float(self.dac_bitMax)) * 20) - 10) * 100)
                    / 100
                )
            for i in range(1, 5):
                self.isBiphasic[i] = struct.unpack("B", response[ind])[0]
                ind += 1
                self.customTrainID[i] = struct.unpack("B", response[ind])[0]
                ind += 1
                self.customTrainTarget[i] = struct.unpack("B", response[ind])[0]
                ind += 1
                self.customTrainLoop[i] = struct.unpack("B", response[ind])[0]
                ind += 1
            for i in range(1, 5):
                self.linkTriggerChannel1[i] = struct.unpack("B", response[ind])[0]
                ind += 1
            for i in range(1, 5):
                self.linkTriggerChannel2[i] = struct.unpack("B", response[ind])[0]
                ind += 1
            self.triggerMode[1] = struct.unpack("B", response[ind])[0]
            ind += 1
            self.triggerMode[2] = struct.unpack("B", response[ind])[0]

    def __str__(self):
        sb = []
        for key in self.__dict__:
            sb.append("{key}='{value}'".format(key=key, value=self.__dict__[key]))

        return ", ".join(sb)

    def __repr__(self):
        return self.__str__()


class PulsePalError(Exception):
    pass

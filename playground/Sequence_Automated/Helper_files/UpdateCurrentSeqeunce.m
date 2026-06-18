function [Port_1,Port_2] = UpdateCurrentSeqeunce(CurrentTrialType,Gui)
%Set the port order based on the trial type and the GUI settings
    Port_1 = num2str(Gui.Sequence_1((CurrentTrialType*2)-1));
    Port_2 = num2str(Gui.Sequence_1(CurrentTrialType*2));

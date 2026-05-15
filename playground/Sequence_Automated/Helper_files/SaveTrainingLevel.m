function SaveTrainingLevel
global BpodSystem
Data = BpodSystem.Data.SessionVariables.TLevel(end);
Path = strcat(BpodSystem.Path.DataFolder, BpodSystem.GUIData.SubjectName,'\',...
    BpodSystem.GUIData.ProtocolName, '\Session Data\Sequence_Automated_CurrentTrainingLevel.mat');
save(Path,'Data');
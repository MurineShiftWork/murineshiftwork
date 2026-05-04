function [current_level] = UpdateLevel(GUI,Port_1,Port_2,Port_3,Port_4,Port_5,Start_Level)  

global BpodSystem
%current trial:
i = BpodSystem.Data.nTrials;
PortIn = [];
Port_Refs = [];

% Pull out port in events from last trial

if isfield(BpodSystem.Data.RawEvents.Trial{i}.Events, 'Port1In')
    PortIn = [PortIn BpodSystem.Data.RawEvents.Trial{i}.Events.Port1In];
    pokes = length(BpodSystem.Data.RawEvents.Trial{i}.Events.Port1In);
    Port_Refs = [Port_Refs (zeros(1,pokes)+ 1 * 1)];
end
if isfield(BpodSystem.Data.RawEvents.Trial{i}.Events, 'Port2In')
    PortIn = [PortIn BpodSystem.Data.RawEvents.Trial{i}.Events.Port2In];
    pokes = length(BpodSystem.Data.RawEvents.Trial{i}.Events.Port2In);
    Port_Refs = [Port_Refs (zeros(1,pokes)+ 1 * 2)];
end
if isfield(BpodSystem.Data.RawEvents.Trial{i}.Events, 'Port3In')
    PortIn = [PortIn BpodSystem.Data.RawEvents.Trial{i}.Events.Port3In];
    pokes = length(BpodSystem.Data.RawEvents.Trial{i}.Events.Port3In);
    Port_Refs = [Port_Refs (zeros(1,pokes)+ 1 * 3)];
end
if isfield(BpodSystem.Data.RawEvents.Trial{i}.Events, 'Port4In')
    PortIn = [PortIn BpodSystem.Data.RawEvents.Trial{i}.Events.Port4In];
    pokes = length(BpodSystem.Data.RawEvents.Trial{i}.Events.Port4In);
    Port_Refs = [Port_Refs (zeros(1,pokes)+ 1 * 4)];
end
if isfield(BpodSystem.Data.RawEvents.Trial{i}.Events, 'Port5In')
    PortIn = [PortIn BpodSystem.Data.RawEvents.Trial{i}.Events.Port5In];
    pokes = length(BpodSystem.Data.RawEvents.Trial{i}.Events.Port5In);
    Port_Refs = [Port_Refs (zeros(1,pokes)+ 1 * 5)];
end
if isfield(BpodSystem.Data.RawEvents.Trial{i}.Events, 'Port6In')
    PortIn = [PortIn BpodSystem.Data.RawEvents.Trial{i}.Events.Port6In];
    pokes = length(BpodSystem.Data.RawEvents.Trial{i}.Events.Port6In);
    Port_Refs = [Port_Refs (zeros(1,pokes)+ 1 * 6)];
end
if isfield(BpodSystem.Data.RawEvents.Trial{i}.Events, 'Port7In')
    PortIn = [PortIn BpodSystem.Data.RawEvents.Trial{i}.Events.Port7In];
    pokes = length(BpodSystem.Data.RawEvents.Trial{i}.Events.Port7In);
    Port_Refs = [Port_Refs (zeros(1,pokes)+ 1 * 7)];
end
if isfield(BpodSystem.Data.RawEvents.Trial{i}.Events, 'Port8In')
    PortIn = [PortIn BpodSystem.Data.RawEvents.Trial{i}.Events.Port8In];
    pokes = length(BpodSystem.Data.RawEvents.Trial{i}.Events.Port8In);
    Port_Refs = [Port_Refs (zeros(1,pokes)+ 1 * 8)];
end


% reorder these in time and remove (ignore) double pokes
[Sorted_times,Index] = sort(PortIn,'ascend');  %i could use sorted times at some point if I want to filter perfect sequences based on time as well a ssequence order
Sorted_Refs = Port_Refs(Index);
Y = [true,diff(Sorted_Refs)~=0];
Sorted_Refs_doubles_removed = Sorted_Refs(Y);

template_seq = [str2num(Port_1),str2num(Port_2),str2num(Port_3),str2num(Port_4),str2num(Port_5)];
sequence_occurred = strfind(Sorted_Refs_doubles_removed,template_seq);

if isempty(sequence_occurred)
    BpodSystem.Data.SessionVariables.Perfect_Seqs = [BpodSystem.Data.SessionVariables.Perfect_Seqs 0];
else
    BpodSystem.Data.SessionVariables.Perfect_Seqs = [BpodSystem.Data.SessionVariables.Perfect_Seqs 1];
end

BpodSystem.Data.SessionVariables.counter = BpodSystem.Data.SessionVariables.counter + 1;
% increase level:
if BpodSystem.Data.SessionVariables.counter > GUI.BufferTrials + 1
    if GUI.ExperimentType == 1 %dont update if session type is 'experiment'
        % increase level:
        if BpodSystem.Data.TLevel < 50
            if mean(BpodSystem.Data.SessionVariables.Perfect_Seqs(i-GUI.BufferTrials:i)) > GUI.ProgressionThreshold
                BpodSystem.Data.TLevel = BpodSystem.Data.TLevel+1;
                BpodSystem.Data.SessionVariables.counter = 0;
            end
        end
    end
end

% decrease level:
if BpodSystem.Data.SessionVariables.counter > GUI.Regression_BufferTrials + 1
    if GUI.ExperimentType == 1 %dont update if session type is 'experiment'
        %set floor
        if GUI.CurrentLevelisFloor == 1
            floor = Start_Level;
        else
            floor = 1; % previously this was 14: floor effect. This was removed 19.4.21
        end
        
        if BpodSystem.Data.TLevel > floor
            if mean(BpodSystem.Data.SessionVariables.Perfect_Seqs(i-GUI.Regression_BufferTrials:i)) < GUI.RegressionThreshold
                BpodSystem.Data.TLevel = BpodSystem.Data.TLevel-1;
                BpodSystem.Data.SessionVariables.counter = 0;
            end
        end
    end
end
disp(BpodSystem.Data.TLevel)
if i >= GUI.BufferTrials + 1
    disp(mean(BpodSystem.Data.SessionVariables.Perfect_Seqs(i-GUI.BufferTrials:i)))
    BpodSystem.Data.SessionVariables.current_performance =[BpodSystem.Data.SessionVariables.current_performance, mean(BpodSystem.Data.SessionVariables.Perfect_Seqs(i-GUI.BufferTrials:i))];
end


current_level = BpodSystem.Data.TLevel;

    






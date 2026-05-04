%{
---------------------------------------------------------------------------
SequenceAutomated.m
MAIN PROTOCOL
2020
Emmett James Thompson
Sainsbury Wellcome Center
---------------------------------------------------------------------------
Subjects must complete a sequence of 5 pokes, training is initialy guided by
light and reward, then light only. The final task is performed based on
memory alone. 

Training stages:
1 Habituation
2 - 13 Diminish water  
14 - 49 Diminish light
50 Full task

subjects start each session at the level they left off previously.
Subjects progress or regress through training stages automatically. 

Progression:
1. animals must complete 50 trials and then 9/10 perfectly 
2-13 subjects must complete 9/10 to progress
14-49 animals must complete 8/10 to progress

final task is 'sound guided' ie. only correct pokes result in a poke in
sound. This informs the mouse whether the last poke was right/wrong but
does not actually tell the mouse where he should go.
%}


%% Make BpodSystem object
global BpodSystem S

beep('off'); % native matlab error sounds OFF



%% GUI Params
S = BpodSystem.ProtocolSettings; % Load settings chosen in launch manager into current workspace as a struct called S

if isempty(fieldnames(S))  % If settings file was an empty struct, populate struct with default settings
    
    %Task Features
    S.GUI.TrainingLevel = 1; % Default Training Level
    S.GUIMeta.TrainingLevel.Style = 'popupmenu'; % the GUIMeta field is used by the ParameterGUI plugin to customize UI objects.
    S.GUIMeta.TrainingLevel.String = {'AUTO','1_Habituation', '2','3','4','5','6','7','8','9','10','11','12','13','14','15','16','17','18',...
                                     '19','20','21','22','23','24','25','26','27','28','29','30','31','32','33','34','35','36','37',...
                                     '38','39','40','41','42','43','44','45','46','47','48','49','50_FinalTask'};
    S.GUI.Number_of_Sequences = 1; % Default Training Level
    S.GUIMeta.Number_of_Sequences.Style = 'popupmenu'; % the GUIMeta field is used by the ParameterGUI plugin to customize UI objects.
    S.GUIMeta.Number_of_Sequences.String = {'1', '2', '3'};
    
    S.GUI.OptoStim = 0; % off by default
    S.GUIMeta.OptoStim.Style = 'checkbox';
    
    S.GUI.OptoStim_Special = 0; % off by default
    S.GUIMeta.OptoStim_Special.Style = 'checkbox';
    
    S.GUI.RewardSound = 1; %default is on
    S.GUIMeta.RewardSound.Style = 'checkbox';
    
    S.GUI.ExperimentType = 1 ; %default is training
    S.GUIMeta.ExperimentType.Style = 'popupmenu';
    S.GUIMeta.ExperimentType.String = {'1_Training', '2_Experiment','3_EphysExperiment'}; 
    
    S.GUI.CurrentLevelisFloor = 0 ; %default is off
    S.GUIMeta.CurrentLevelisFloor.Style = 'checkbox';
    
    % alter final reward amount - overide auto presets
    S.GUI.AdjustFinalReward = 0 ; %default is off
    S.GUIMeta.AdjustFinalReward.Style = 'checkbox';
    
    S.GUI.AdjustFinalReward_Amount = 2; % ul as default
    
    % special event
    S.GUI.SpecialCondition = 0; % default is none
    S.GUIMeta.SpecialCondition.Style = 'checkbox';
    S.GUI.SpecialConditionEventChance = 0.2;
    S.GUI.SpecialRewardAmount = 5; %ul
    
    %Sequences
    S.GUI.Sequence_1 = 21637;
    S.GUI.Sequence_2 = 00000;
    S.GUI.Sequence_3 = 00000;
    S.GUI.MultiSeq_LowerBlockBound = 15;
    S.GUI.MultiSeq_UpperBlockBound = 30;
    
    % Level change settings
    S.GUI.ProgressionThreshold = 0.9;
    S.GUI.RegressionThreshold = 0.2;
    S.GUI.BufferTrials = 10; % trials after a level change/ at the start of training before anything can change. Also a Window that mean is calculated for to determine whether to pregoress/regress/stay at same level 
    S.GUI.Regression_BufferTrials = 10; % buffer trials for going down a level 
    
    %lag times to allow enough time for trial manager to fully compute sma
    S.GUI.LagTime1 = 0.4;
    S.GUI.LagTime2 = 0.3; % less time needed once there is no lights of cue deval as sma is created faster
    
    %Reward/Punihsment
    S.GUI.RewardDelay = 0; %s
    
    %Sound Feautres
    S.GUI.RewardSoundAmp = 10;
    S.GUI.RewardSoundDuration = 0.5;

    %Stim Feautres
    S.GUI.StimPoke = 1; % poke number that triggers stim, # 
    S.GUIMeta.StimPoke.Style = 'popupmenu';
    S.GUIMeta.StimPoke.String = {'port_1', 'port_2', 'port_3', 'port_4', 'randomly_select_port'};
   
    
    S.GUI.PulsePower = 12; % power in V
    S.GUI.OptoChance = 0.15; % % of trials which will have stimulation
    S.GUI.PulseDuration = 0.005; % Set output channel to produce 5ms pulses
    S.GUI.PulseInterval = 0.045; % Set pulse interval to produce 20Hz pulses
    S.GUI.TrainDuration = 0.5; % Set pulse train to last 0.5 seconds
    S.GUI.TrainDelay = 0; % Set pulse train delay to last 0 seconds
    S.GUI.VariableTrainDelay = 0; % VariableTrainDelay = True selects TrainDelay according to the parameters below 
    S.GUIMeta.VariableTrainDelay.Style = 'checkbox';
    S.GUI.muVariableDelay = 0.4;
    S.GUI.sigmaVariableDelay = 0.3;
    S.GUI.lowerBoundVariableDelay = 0.2;
    S.GUI.upperBoundVariableDelay = 0.6;

    
    S.GUI.SpecialStimTrial = 100; 
    
    % Conditions
    % Treatment
    S.GUI.Treatment = 1;
    S.GUIMeta.Treatment.Style = 'popupmenu';
    S.GUIMeta.Treatment.String = {'not_applicable', 'vehicle', 'CNO', 'muscimol',...
        'AP-5', 'NBQX', 'AP-5 and NBQX', 'others'};
    
    % Route of administration
    S.GUI.Route = 1;
    S.GUIMeta.Route.Style = 'popupmenu';
    S.GUIMeta.Route.String = {'not_applicable', 'icv', 'ip', 'sc', 'im'};
    
    % Dose
    S.GUI.Dose = 0; % sets dose to 0 mg/kg
    
    % Surgery stage
    S.GUI.Surgery = 1;
    S.GUIMeta.Surgery.Style = 'popupmenu';
    S.GUIMeta.Surgery.String = {'not_applicable', 'pre-surgery', 'post-surgery'};
    
    S.GUIPanels.Task = {'TrainingLevel','Number_of_Sequences','ExperimentType','SpecialCondition','CurrentLevelisFloor','Sequence_1', 'Sequence_2', 'Sequence_3', 'OptoStim','OptoStim_Special','RewardSound','AdjustFinalReward','AdjustFinalReward_Amount','Regression_BufferTrials'}; % GUIPanels organize the parameters into groups.
    S.GUIPanels.Conditions = {'Treatment', 'Route', 'Dose', 'Surgery'};
    S.GUIPanels.Settings = {'ProgressionThreshold','RegressionThreshold','BufferTrials','RewardDelay','MultiSeq_LowerBlockBound','MultiSeq_UpperBlockBound', 'LagTime1', 'LagTime2'};
    S.GUIPanels.Sound = { 'RewardSound','RewardSoundAmp'};
    S.GUIPanels.Stim_Settings = {'StimPoke','OptoChance','PulsePower', 'PulseDuration','PulseInterval', 'TrainDuration','TrainDelay','VariableTrainDelay', 'muVariableDelay', 'sigmaVariableDelay', 'lowerBoundVariableDelay', 'upperBoundVariableDelay', 'SpecialStimTrial'};
    S.GUIPanels.SpecialEventSettings = {'SpecialConditionEventChance','SpecialRewardAmount'};
    
    S.GUITabs.Task = {'Task'};
    S.GUITabs.Conditions = {'Conditions'};
    S.GUITabs.Stim_Settings = {'Stim_Settings'};
    S.GUITabs.Settings = {'Settings'};
    S.GUITabs.Sound = {'Sound'};
    S.GUITabs.SpecialEventSettings = {'SpecialEventSettings'};
    
end

% Initialize parameter GUI plugin
BpodParameterGUI_with_tabs('init', S);
set(BpodSystem.ProtocolFigures.ParameterGUI, 'Position', [0 550 450, 680 ]);

%Open the schematic image of the ports...
Protocol_Path = BpodSystem.Path.ProtocolFolder;
PNG_Path = 'Sequence/Sequence_Helper_Files/PortLayout.png';
I = imread(strcat(Protocol_Path,PNG_Path));
figure(10);set(gcf,'Position',[0 1500 5 5]); imshow(I);

% Pause to allow user to change GUI parameters
BpodSystem.Status.Pause=1;
HandlePauseCondition;

%Close the schematic image of the ports...
close(10);

% Sync S to the changed GUI parameters
S = BpodParameterGUI('sync', S);

%% barcode pulse % Hardcoded to output on BNC 2

if S.GUI.ExperimentType== 3
    ttl_sma = protocol_init_ttl(S, 'LsLsss');
    SendStateMatrix(ttl_sma);
    RunStateMatrix;
end

%% Create trial manager object
TrialManager = TrialManagerObject;


%% Define trials
BpodSystem.Data.MaxTrials = 2000;

%If multiple sequences selected then make the trials in blocks with repspect to all possible sequences

switch S.GUI.Number_of_Sequences
    case {1} % 1 sequence
        TrialTypes = linspace(1, 1,BpodSystem.Data.MaxTrials);
    case {2} % 2 sequences
        TrialTypes = make_block_structure(2,S.GUI.MultiSeq_LowerBlockBound,S.GUI.MultiSeq_UpperBlockBound,BpodSystem.Data.MaxTrials);
    case {3} % 3 sequences
        TrialTypes = make_block_structure(3,S.GUI.MultiSeq_LowerBlockBound,S.GUI.MultiSeq_UpperBlockBound,BpodSystem.Data.MaxTrials);
end

%clear variables for saving out data
BpodSystem.Data.TrialTypes = [];
BpodSystem.Data.TrialSequence = [];
BpodSystem.Data.SessionVariables.Punish_condition = [];

%% Generate and Load Sounds
InitializePsychSound

%Sound Parameters:
sampRate = 192000;
widthFreq = 1.002;
nbOfFreq = 4;
punish_rampTime = 0.005;
rampTime = 0.005;

%make reward sound
if S.GUI.RewardSound == 1
    srate=20000; % sampling rate
    freq1=5;
    dur1=1.5*1000;
    RewardSound = S.GUI.RewardSoundAmp*(MakeBupperSwoop(srate,0, freq1 , freq1 , dur1/2 , dur1/2,0,0.1));
else
    RewardSound = zeros(1,sampRate*S.GUI.RewardSoundDuration); %No noise but will still play the 'sound'
end

%Initiate sound server and load sounds:
PsychToolboxSoundServer('init');
PsychToolboxSoundServer('Load', 1, RewardSound);

BpodSystem.SoftCodeHandlerFunction = 'SoftCodeHandler_PlaySound';


%% Initialize Training Level

if S.GUI.TrainingLevel == 1
    
    Path = strcat(BpodSystem.Path.DataFolder, BpodSystem.GUIData.SubjectName,'\',BpodSystem.GUIData.ProtocolName, '\Session Data\Sequence_Automated_CurrentTrainingLevel.mat');
    
    if isfile(Path)
        Level = importdata(Path);
        disp('Training Level Loaded')
        disp(Level)
    else
        disp('Error: No previous Level found, please manually select a level from the GUI')
        return
    end
    
    
else
    Level = (S.GUI.TrainingLevel-1);
end

BpodSystem.Data.SessionVariables.TrainingLevels = csvread('AutomatedTrainingLevels.csv',0,0,[0 0 49 10]);
BpodSystem.Data.FirstTLevel = Level;
BpodSystem.Data.TLevel = Level;

% preset variables that are used to update the lvel with performance 
BpodSystem.Data.SessionVariables.counter = 0;  % counts how mnay trials have gone by without updatng the level (it must be at least 10 before animal can go up a level) 
BpodSystem.Data.SessionVariables.Perfect_Seqs = []; %perfect seqs score is calculated for each trial, 0 = error, 1 = correct - perfect sequence ordeer
BpodSystem.Data.SessionVariables.current_performance = [];

%% Initialize plots

MultiFigureEJT = figure('Position', [10 10 1000 600],'name',SubjectName,'numbertitle','off', 'MenuBar', 'none', 'Resize', 'on');

%Create an object that is called on cleanup to save stuff
[filepath,name,~] = fileparts(BpodSystem.Path.CurrentDataFile);
finishup = onCleanup(@() CleanupFunctionAutoSeq(MultiFigureEJT, filepath, name));

%% Initialize pulsepal
if S.GUI.OptoStim == 1
    try
        evalin('base', 'PulsePalSystem;')
    catch
        try
            PulsePal('COM8');
        catch
            disp('Pulsepal not connected')
        end
    end
    
    %Load parameters to pulsepal
    S.InitialPulsePalParameters = struct;
    load PulsePal_ParameterMatrix;
    try
        ProgramPulsePal(ParameterMatrix);
        S.InitialPulsePalParameters = ParameterMatrix;
    catch
        disp('Pulsepal default parameters failed to load')
    end

    % Specific task-related parameters
    try
        ProgramPulsePalParam(1, 'Phase1Voltage', S.GUI.PulsePower); % Set output channel 1 to produce 5V pulses
        ProgramPulsePalParam(1, 'Phase1Duration', S.GUI.PulseDuration); % Set output channel 1 to produce Xms pulses
        ProgramPulsePalParam(1, 'InterPulseInterval', S.GUI.PulseInterval); % Set pulse interval to produce XHz pulses
        ProgramPulsePalParam(1, 'PulseTrainDuration', S.GUI.TrainDuration); % Set pulse train to last X seconds
%         ProgramPulsePalParam(1, 'PulseTrainDelay', S.GUI.TrainDelay); %
%         This is sey later dynamically within the main loop
        %The following fails to load
        %ProgramPulsePalParam(1, 'LinkedToTriggerCH1', 1); % Set output channel 1 to respond to trigger ch 1
        ProgramPulsePalParam(1, 'TriggerMode', 0); % Set trigger channel 1 to toggle mode
    catch
        disp('Pulsepal specific parameters failed to load')
    end
    
    %Generate trials with optostimulation
    if S.GUI.OptoStim_Special == 0
        OptoStim = WeightedRandomTrials([1-S.GUI.OptoChance S.GUI.OptoChance], BpodSystem.Data.MaxTrials);
        BpodSystem.Data.SessionVariables.OptoStim = OptoStim - 1; % 0s or 1s
    else
        OptoStim = WeightedRandomTrials([1 0], BpodSystem.Data.MaxTrials);
        OptoStim(S.GUI.SpecialStimTrial) = 2; %set nth trial to be a stim trial 
        BpodSystem.Data.SessionVariables.OptoStim = OptoStim - 1; % 0s or 1s
    end
else
    BpodSystem.Data.SessionVariables.OptoStim = linspace(0,0,BpodSystem.Data.MaxTrials);
end

% set up special events for prediction error trials 
if S.GUI.SpecialCondition == 1;
    SpecialEvents = WeightedRandomTrials([1-S.GUI.SpecialConditionEventChance S.GUI.SpecialConditionEventChance], BpodSystem.Data.MaxTrials);
    BpodSystem.Data.SessionVariables.SpecialEvents = SpecialEvents - 1; % 0s or 1s
else
    BpodSystem.Data.SessionVariables.SpecialEvents = linspace(0,0,BpodSystem.Data.MaxTrials);
end         

%% save Optostim condition; 0 --> Port was not stimulated; 1 --> Port was stimulated
BpodSystem.Data.SessionVariables.PortStimulated = linspace(0,0,BpodSystem.Data.MaxTrials);
BpodSystem.Data.SessionVariables.OptoDuration = linspace(0,0,BpodSystem.Data.MaxTrials);
BpodSystem.Data.SessionVariables.OptoDelay = linspace(0,0,BpodSystem.Data.MaxTrials);

%% Setup Trial manager for parallel (speedy) initiation 

%convert the sequence integer back into an array so it can be indexed:
S.GUI.Sequence_1 = num2str(S.GUI.Sequence_1)-'0';
S.GUI.Sequence_2 = num2str(S.GUI.Sequence_2)-'0';
S.GUI.Sequence_3 = num2str(S.GUI.Sequence_3)-'0';

sma = PrepareStateMachine(S, TrialTypes, 1, []); % Prepare state machine for trial 1 with empty "current events" variable
TrialManager.startTrial(sma); % Sends & starts running first trial's state machine. A MATLAB timer object updates the 
                              % console UI, while code below proceeds in parallel.
                                     
%% Initialize notebook
BpodNotebook('init');

%% Main trial loop
for currentTrial = 1:BpodSystem.Data.MaxTrials

    % for variable delay
    % set the variableTrainDelay if VariableTrainDelay = True
    % dynamically set pulsepal delay
    if S.GUI.VariableTrainDelay == 1
        TrainDelay = GetVariableDelay(S.GUI.muVariableDelay, S.GUI.sigmaVariableDelay, S.GUI.lowerBoundVariableDelay, S.GUI.upperBoundVariableDelay);
    else
        TrainDelay = S.GUI.TrainDelay;
    end

    if S.GUI.OptoStim == 1                      
        ProgramPulsePalParam(1, 'PulseTrainDelay', TrainDelay);
        disp(['TrainDelay for upcoming stim is ...', num2str(TrainDelay)]) 
    end

    %save train duration and delay variable
    BpodSystem.Data.SessionVariables.OptoDelay(currentTrial) = TrainDelay;
    BpodSystem.Data.SessionVariables.OptoDuration(currentTrial)= S.GUI.TrainDuration;

    
    currentTrialEvents = TrialManager.getCurrentEvents({'ExitSeq'}); 
                                       % Hangs here until Bpod enters one of the listed trigger states, 
                                       % then returns current trial's states visited + events captured to this point
    if BpodSystem.Status.BeingUsed == 0; return; end % If user hit console "stop" button, end session 
    [sma, S] = PrepareStateMachine(S, TrialTypes, currentTrial+1, currentTrialEvents); % Prepare next state machine.
    % Since PrepareStateMachine is a function with a separate workspace, pass any local variables needed to make 
    % the state machine as fields of settings struct S e.g. S.learningRate = 0.2.
    SendStateMachine(sma, 'RunASAP'); % With TrialManager, you can send the next trial's state machine while the current trial is ongoing
    RawEvents = TrialManager.getTrialData; % Hangs here until trial is over, then retrieves full trial's raw data
    if BpodSystem.Status.BeingUsed == 0; return; end % If user hit console "stop" button, end session 
    HandlePauseCondition; % Checks to see if the protocol is paused. If so, waits until user resumes.
    TrialManager.startTrial(); % Start processing the next trial's events (call with no argument since SM was already sent)
    
    % Save out data, update trialoutcome plot:   
    
    if ~isempty(fieldnames(RawEvents)) % If trial data was returned
        BpodSystem.Data = AddTrialEvents(BpodSystem.Data,RawEvents); % Computes trial events from raw data
        BpodSystem.Data.TrialSettings(currentTrial) = S; % Adds the settings used for the current trial to the Data struct (to be saved after the trial ends)
        BpodSystem.Data.TrialTypes(currentTrial) = TrialTypes(currentTrial);
        BpodSystem.Data.SessionVariables.TLevel(currentTrial)  = BpodSystem.Data.TLevel;
        BpodSystem.Data.SessionVariables.LEDIntensitys.port1(currentTrial) = BpodSystem.Data.sma_vars.LedIntensity1;
        BpodSystem.Data.SessionVariables.LEDIntensitys.port2(currentTrial) = BpodSystem.Data.sma_vars.LedIntensity2;
        BpodSystem.Data.SessionVariables.LEDIntensitys.port3(currentTrial) = BpodSystem.Data.sma_vars.LedIntensity3;
        BpodSystem.Data.SessionVariables.LEDIntensitys.port4(currentTrial) = BpodSystem.Data.sma_vars.LedIntensity4;
        BpodSystem.Data.SessionVariables.LEDIntensitys.port5(currentTrial) = BpodSystem.Data.sma_vars.LedIntensity5;
        BpodSystem.Data.SessionVariables.RewardAmount.port1(currentTrial) = BpodSystem.Data.sma_vars.FirstRewardAmount;
        BpodSystem.Data.SessionVariables.RewardAmount.port2(currentTrial) = BpodSystem.Data.sma_vars.SecondRewardAmount;
        BpodSystem.Data.SessionVariables.RewardAmount.port3(currentTrial) = BpodSystem.Data.sma_vars.ThirdRewardAmount;
        BpodSystem.Data.SessionVariables.RewardAmount.port4(currentTrial) = BpodSystem.Data.sma_vars.FourthRewardAmount;
        BpodSystem.Data.SessionVariables.RewardAmount.port5(currentTrial) = BpodSystem.Data.sma_vars.FinalRewardAmount;
        BpodSystem.Data = BpodNotebook('sync', BpodSystem.Data); % updates notebook 
        
        if currentTrial == 1
            UpdateOnlinePlotFastAuto(S.GUI,BpodSystem.Data,BpodSystem.GUIData.SubjectName,TrialTypes(currentTrial),'Init',MultiFigureEJT); %update online plot
        else
            UpdateOnlinePlotFastAuto(S.GUI,BpodSystem.Data,BpodSystem.GUIData.SubjectName,TrialTypes(currentTrial),'Update',MultiFigureEJT); %update online plot
        end    
        
        if mod((currentTrial-1), 400) == 0
            SaveBpodSessionData; % Saves the field BpodSystem.Data to the current data file
            disp('Data saved');
        end
    end
end

%% Trial specific Matrix outputs

function [sma, S] = PrepareStateMachine(S, TrialTypes, currentTrial, currentTrialEvents)
    
    % In this case, we don't need trial events to build the state machine - but
    % they are available in currentTrialEvents.


    global BpodSystem

    %Set the port order based on the trial type and the GUI settings
    if TrialTypes(currentTrial) == 1
        Port_1 = num2str(S.GUI.Sequence_1(1));
        Port_2 = num2str(S.GUI.Sequence_1(2));
        Port_3 = num2str(S.GUI.Sequence_1(3));
        Port_4 = num2str(S.GUI.Sequence_1(4));
        Port_5 = num2str(S.GUI.Sequence_1(5));
        %for saving out the sequence  and experiment data
        BpodSystem.Data.TrialSequence(currentTrial,1) = S.GUI.Sequence_1(1);
        BpodSystem.Data.TrialSequence(currentTrial,2) = S.GUI.Sequence_1(2);
        BpodSystem.Data.TrialSequence(currentTrial,3) = S.GUI.Sequence_1(3);
        BpodSystem.Data.TrialSequence(currentTrial,4) = S.GUI.Sequence_1(4);
        BpodSystem.Data.TrialSequence(currentTrial,5) = S.GUI.Sequence_1(5);
        BpodSystem.Data.ExperimentType = S.GUI.ExperimentType;
        
    elseif TrialTypes(currentTrial) == 2
        Port_1 = num2str(S.GUI.Sequence_2(1));
        Port_2 = num2str(S.GUI.Sequence_2(2));
        Port_3 = num2str(S.GUI.Sequence_2(3));
        Port_4 = num2str(S.GUI.Sequence_2(4));
        Port_5 = num2str(S.GUI.Sequence_2(5));
        disp(S.GUI.Sequence_2)
        %for saving out the sequence data
        BpodSystem.Data.TrialSequence(currentTrial,1) = S.GUI.Sequence_2(1);
        BpodSystem.Data.TrialSequence(currentTrial,2) = S.GUI.Sequence_2(2);
        BpodSystem.Data.TrialSequence(currentTrial,3) = S.GUI.Sequence_2(3);
        BpodSystem.Data.TrialSequence(currentTrial,4) = S.GUI.Sequence_2(4);
        BpodSystem.Data.TrialSequence(currentTrial,5) = S.GUI.Sequence_2(5);
        
    elseif TrialTypes(currentTrial) == 3
        Port_1 = num2str(S.GUI.Sequence_3(1));
        Port_2 = num2str(S.GUI.Sequence_3(2));
        Port_3 = num2str(S.GUI.Sequence_3(3));
        Port_4 = num2str(S.GUI.Sequence_3(4));
        Port_5 = num2str(S.GUI.Sequence_3(5));
        %for saving out the sequence data
        BpodSystem.Data.TrialSequence(currentTrial,1) = S.GUI.Sequence_3(1);
        BpodSystem.Data.TrialSequence(currentTrial,2) = S.GUI.Sequence_3(2);
        BpodSystem.Data.TrialSequence(currentTrial,3) = S.GUI.Sequence_3(3);
        BpodSystem.Data.TrialSequence(currentTrial,4) = S.GUI.Sequence_3(4);
        BpodSystem.Data.TrialSequence(currentTrial,5) = S.GUI.Sequence_3(5);
        disp(S.GUI.Sequence_3)  
    else
        disp('error, trial type not recognised')
        return
    end
    
    % set special conditon
    if S.GUI.SpecialCondition == 1
        disp('Special trials coming up...')
        disp(BpodSystem.Data.SessionVariables.SpecialEvents(currentTrial:currentTrial+5));
    end
    
    switch BpodSystem.Data.SessionVariables.SpecialEvents(currentTrial)
        case 0 % No special
            SpecialCondition = 0;
        case 1 % Special
            SpecialCondition = 1;
    end
    
    % Set the training level:
    % make is so that level doesnt change (stays at 50 for experiment sessions)
    if currentTrial > 2
        BpodSystem.Data.TLevel = UpdateLevel(S.GUI,Port_1,Port_2,Port_3,Port_4,Port_5,BpodSystem.Data.FirstTLevel);
    end

    %Reward_amounts
    BpodSystem.Data.sma_vars.FirstRewardAmount = BpodSystem.Data.SessionVariables.TrainingLevels(BpodSystem.Data.TLevel ,1);
    BpodSystem.Data.sma_vars.SecondRewardAmount = BpodSystem.Data.SessionVariables.TrainingLevels(BpodSystem.Data.TLevel ,2);
    BpodSystem.Data.sma_vars.ThirdRewardAmount = BpodSystem.Data.SessionVariables.TrainingLevels(BpodSystem.Data.TLevel ,3);
    BpodSystem.Data.sma_vars.FourthRewardAmount = BpodSystem.Data.SessionVariables.TrainingLevels(BpodSystem.Data.TLevel ,4);
    
    %overide auto preset
    if S.GUI.AdjustFinalReward == 1
        BpodSystem.Data.sma_vars.FinalRewardAmount = S.GUI.AdjustFinalReward_Amount;
    elseif SpecialCondition == 1 % special condition
        BpodSystem.Data.sma_vars.FinalRewardAmount = S.GUI.SpecialRewardAmount;
    else
        BpodSystem.Data.sma_vars.FinalRewardAmount = BpodSystem.Data.SessionVariables.TrainingLevels(BpodSystem.Data.TLevel ,5);
    end
 
    FirstValveTime = DetermineValveTime(BpodSystem.Data.sma_vars.FirstRewardAmount, Port_1);
    SecondValveTime = DetermineValveTime(BpodSystem.Data.sma_vars.SecondRewardAmount, Port_2);
    ThirdValveTime = DetermineValveTime(BpodSystem.Data.sma_vars.ThirdRewardAmount, Port_3);
    FourthValveTime = DetermineValveTime(BpodSystem.Data.sma_vars.FourthRewardAmount, Port_4);
    RewardValvetime = DetermineValveTime(BpodSystem.Data.sma_vars.FinalRewardAmount, Port_5);
    
    %Set the LedIntensity
    BpodSystem.Data.sma_vars.LedIntensity1 = BpodSystem.Data.SessionVariables.TrainingLevels(BpodSystem.Data.TLevel ,6);
    BpodSystem.Data.sma_vars.LedIntensity2 = BpodSystem.Data.SessionVariables.TrainingLevels(BpodSystem.Data.TLevel,7);
    BpodSystem.Data.sma_vars.LedIntensity3 = BpodSystem.Data.SessionVariables.TrainingLevels(BpodSystem.Data.TLevel,8);
    BpodSystem.Data.sma_vars.LedIntensity4 = BpodSystem.Data.SessionVariables.TrainingLevels(BpodSystem.Data.TLevel ,9);
    BpodSystem.Data.sma_vars.LedIntensity5 = BpodSystem.Data.SessionVariables.TrainingLevels(BpodSystem.Data.TLevel ,10);

    %Set interpoke timeout limit
    BpodSystem.Data.SessionVariables.ResponseWindow = BpodSystem.Data.SessionVariables.TrainingLevels(BpodSystem.Data.TLevel ,11);
    InterPoke_TimeOut = BpodSystem.Data.SessionVariables.ResponseWindow;
    % set opto conditon 
    if S.GUI.OptoStim == 1
        disp('opto trials coming up...')
        disp(BpodSystem.Data.SessionVariables.OptoStim(currentTrial:currentTrial+5));
    end
      
    switch BpodSystem.Data.SessionVariables.OptoStim(currentTrial)
        case 0 % No opto
            OptoCondition1 = 0;
            OptoCondition2 = 0;
            OptoCondition3 = 0;
            OptoCondition4 = 0;
            BpodSystem.Data.SessionVariables.PortStimulated(1:4, currentTrial) = [OptoCondition1, OptoCondition2, OptoCondition3, OptoCondition4];
        case 1 % Opto
            if S.GUI.StimPoke == 1
                OptoCondition1 = 1; % BNC number 2
                OptoCondition2 = 0;
                OptoCondition3 = 0;
                OptoCondition4 = 0;  
                BpodSystem.Data.SessionVariables.PortStimulated(1:4, currentTrial) = [OptoCondition1, OptoCondition2, OptoCondition3, OptoCondition4];
            elseif S.GUI.StimPoke == 2
                OptoCondition1 = 0;
                OptoCondition2 = 1;
                OptoCondition3 = 0;
                OptoCondition4 = 0;
                BpodSystem.Data.SessionVariables.PortStimulated(1:4, currentTrial) = [OptoCondition1, OptoCondition2, OptoCondition3, OptoCondition4];
            elseif S.GUI.StimPoke == 3
                OptoCondition1 = 0;
                OptoCondition2 = 0;
                OptoCondition3 = 1;
                OptoCondition4 = 0;
                BpodSystem.Data.SessionVariables.PortStimulated(1:4, currentTrial) = [OptoCondition1, OptoCondition2, OptoCondition3, OptoCondition4];
            elseif S.GUI.StimPoke == 4
                OptoCondition1 = 0;
                OptoCondition2 = 0;
                OptoCondition3 = 0;
                OptoCondition4 = 1;
                BpodSystem.Data.SessionVariables.PortStimulated(1:4, currentTrial) = [OptoCondition1, OptoCondition2, OptoCondition3, OptoCondition4];
            elseif S.GUI.StimPoke == 5
                PortList = [0, 0, 0, 1];
                StimCondition = randsample(PortList, numel(PortList));
                OptoCondition1 = StimCondition(1);
                OptoCondition2 = StimCondition(2);
                OptoCondition3 = StimCondition(3);
                OptoCondition4 = StimCondition(4);
                BpodSystem.Data.SessionVariables.PortStimulated(1:4, currentTrial) = [OptoCondition1, OptoCondition2, OptoCondition3, OptoCondition4];
            end        
    end
    
    % if optostim == 1, then display which port was stimulated and what
    % delay
    if S.GUI.OptoStim == 1
        port_stimulated = find([OptoCondition1, OptoCondition2, OptoCondition3, OptoCondition4]);
        disp(['stimulating port...', num2str(port_stimulated)])
    end
    

    %find valve states for each port
    Valvestate1 = FindValveState(str2num(Port_1));
    Valvestate2 = FindValveState(str2num(Port_2));
    Valvestate3 = FindValveState(str2num(Port_3));
    Valvestate4 = FindValveState(str2num(Port_4));
    Valvestate5 = FindValveState(str2num(Port_5));
    
    %Set state conditional outputs}
    if BpodSystem.Data.ExperimentType == 3 %( if an ephys recording)
        %sends both BNCs high to send a TTL to the ephys setup (one output is not enough when split lots of times across many BNCs)  
        First_Condition = {['PWM',Port_1], BpodSystem.Data.sma_vars.LedIntensity1,'BNC1', 1,'BNC2',1}; % removed: 'SoftCode', TrialTypes(currentTrial)% trial specific Cue will always play but if cues are turned off it will play silence
    else
        First_Condition = {['PWM',Port_1], BpodSystem.Data.sma_vars.LedIntensity1,'BNC1', 1}; % removed: 'SoftCode', TrialTypes(currentTrial)% trial specific Cue will always play but if cues are turned off it will play silence 
    end
    
    Second_Condition = {['PWM',Port_2], BpodSystem.Data.sma_vars.LedIntensity2};
    Third_Condition = {['PWM',Port_3], BpodSystem.Data.sma_vars.LedIntensity3};
    Fourth_Condition = {['PWM',Port_4], BpodSystem.Data.sma_vars.LedIntensity4};
    Fifth_Condition = {['PWM',Port_5], BpodSystem.Data.sma_vars.LedIntensity5 };
    
    
    TrialManagerLagTime = S.GUI.LagTime1;
    if mod((currentTrial-1), 100) == 0
        TrialManagerLagTime = 2;
    end

    
    %Reward outputs
    if BpodSystem.Data.TLevel <= 11 %habituation or water dimish stage 
         % sounds for each poke, reward can be set to come from any port as well as final port 
        First_Reward_Output = {'SoftCode', 1, 'ValveState', Valvestate1,'BNC2', OptoCondition1 };
        Second_Reward_Output = {'SoftCode', 1, 'ValveState', Valvestate2,'BNC2', OptoCondition2 };
        Third_Reward_Output = {'SoftCode', 1, 'ValveState', Valvestate3,'BNC2', OptoCondition3 };
        Fourth_Reward_Output = {'SoftCode', 1, 'ValveState', Valvestate4,'BNC2', OptoCondition4 };
        Final_Reward_Output = {'SoftCode', 1, 'ValveState', Valvestate5};
    else % no water
        First_Reward_Output = {'SoftCode', 1,'BNC2', OptoCondition1 };
        Second_Reward_Output = {'SoftCode', 1,'BNC2', OptoCondition2 };
        Third_Reward_Output = {'SoftCode', 1,'BNC2', OptoCondition3 };
        Fourth_Reward_Output = {'SoftCode', 1,'BNC2', OptoCondition4 };
        Final_Reward_Output = {'SoftCode', 1, 'ValveState', Valvestate5};
    end
    
    %State conditions
    %correct pokes only cause a reward noise  
    Init_conditions = {['Port', Port_1, 'In'], 'InitialPokeValve'};
    port2_conditions = {['Port',Port_2, 'In'], 'SecondPokeValve', 'Tup', 'Punish'};
    port3_conditions = {['Port', Port_3, 'In'], 'ThirdPokeValve','Tup', 'Punish'};
    port4_conditions = {['Port', Port_4, 'In'], 'FourthPokeValve','Tup', 'Punish'};
    port5_conditions = {['Port', Port_5, 'In'], 'Reward','Tup', 'Punish'};

    % if optostim tr to prevent repeated stim through looping by making timeout much shorter 
    switch BpodSystem.Data.SessionVariables.OptoStim(currentTrial)
        case {1}
            InterPoke_TimeOut = 5;
    end
           
   
    %% STATE MATRIX
    sma = NewStateMachine(); % Assemble state matrix

    sma = AddState(sma, 'Name', 'WaitForInitialPoke', ...
        'Timer',0,...
        'StateChangeConditions', Init_conditions,...
        'OutputActions', First_Condition);
    
    sma = AddState(sma, 'Name', 'InitialPokeValve', ...
        'Timer', FirstValveTime,...
        'StateChangeConditions', {'Tup', 'WaitForSecondPoke'},...
        'OutputActions', First_Reward_Output); %reward and reward noise
    
    sma = AddState(sma, 'Name', 'WaitForSecondPoke', ...
        'Timer', InterPoke_TimeOut,...
        'StateChangeConditions', port2_conditions,...
        'OutputActions', Second_Condition);
    sma = AddState(sma, 'Name', 'SecondPokeValve', ...
        'Timer', SecondValveTime,...
        'StateChangeConditions', {'Tup', 'WaitForThirdPoke'},...
        'OutputActions', Second_Reward_Output ); %reward and reward noise
    
    sma = AddState(sma, 'Name', 'WaitForThirdPoke', ...
        'Timer', InterPoke_TimeOut,...
        'StateChangeConditions', port3_conditions,...
        'OutputActions', Third_Condition);
    sma = AddState(sma, 'Name', 'ThirdPokeValve', ...
        'Timer', ThirdValveTime,...
        'StateChangeConditions', {'Tup', 'WaitForFourthPoke'},...
        'OutputActions', Third_Reward_Output ); %reward and reward noise
    
    sma = AddState(sma, 'Name', 'WaitForFourthPoke', ...
        'Timer', InterPoke_TimeOut,...
        'StateChangeConditions', port4_conditions,...
        'OutputActions', Fourth_Condition);
    sma = AddState(sma, 'Name', 'FourthPokeValve', ...
        'Timer', FourthValveTime,...
        'StateChangeConditions', {'Tup', 'WaitForFifthPoke'},...
        'OutputActions', Fourth_Reward_Output); %reward and reward noise
    
    sma = AddState(sma, 'Name', 'WaitForFifthPoke', ...
        'Timer', InterPoke_TimeOut,...
        'StateChangeConditions', port5_conditions,...
        'OutputActions', Fifth_Condition);
    sma = AddState(sma, 'Name', 'Reward', ...
        'Timer', RewardValvetime,...
        'StateChangeConditions', {'Tup', 'ExitSeq'},...
        'OutputActions', Final_Reward_Output); %reward and reward noise
    
   sma = AddState(sma, 'Name', 'Punish', ...
        'Timer',  0,...
        'StateChangeConditions', {'Tup', 'ExitSeq'},...
        'OutputActions', {}); %All lights on and punishnoise
    
    sma = AddState(sma, 'Name', 'ExitSeq', ...
        'Timer',  TrialManagerLagTime,...
        'StateChangeConditions', {'Tup', 'exit'},...
        'OutputActions', {});
    
    
end

% Online plotting Helper function for Sequence  
% Emmett Thompson
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 
function UpdateOnlinePlotFastAuto(GUIdata,Data,SubjectName,TrialType,Action,Figurehandle)
% 
global BpodSystem
% CurrentTrial
i = BpodSystem.Data.nTrials;

    %IntialisePlottingParams
    if i == 1
        BpodSystem.Data.OnlinePlotParams.WrongTrials = zeros(1,BpodSystem.Data.MaxTrials);
        BpodSystem.Data.OnlinePlotParams.CorrectTrials = zeros(1,BpodSystem.Data.MaxTrials);
        BpodSystem.Data.OnlinePlotParams.WrongCount = 0;
        BpodSystem.Data.OnlinePlotParams.CorrectCount = 0;
        BpodSystem.Data.OnlinePlotParams.RewardEventTimes = zeros(1,BpodSystem.Data.MaxTrials);
        BpodSystem.Data.OnlinePlotParams.WrongEventTimes = zeros(1,BpodSystem.Data.MaxTrials);
        BpodSystem.Data.OnlinePlotParams.PrcntCorrect = zeros(1,BpodSystem.Data.MaxTrials);
        BpodSystem.Data.OnlinePlotParams.drink_time_mins = zeros(1,BpodSystem.Data.MaxTrials);
        BpodSystem.Data.OnlinePlotParams.wrong_time_mins = zeros(1,BpodSystem.Data.MaxTrials);
        BpodSystem.Data.OnlinePlotParams.cumtrialcount = zeros(1,BpodSystem.Data.MaxTrials);
        BpodSystem.Data.OnlinePlotParams.missedtrials = zeros(1,BpodSystem.Data.MaxTrials);
        BpodSystem.Data.OnlinePlotParams.WithinTrialEventTime = zeros(1,BpodSystem.Data.MaxTrials);
        BpodSystem.Data.OnlinePlotParams.Initialstatetime = zeros(1,BpodSystem.Data.MaxTrials); %so that it plots at zero on log scale
        BpodSystem.Data.OnlinePlotParams.Secondstatetime = zeros(1,BpodSystem.Data.MaxTrials);
        BpodSystem.Data.OnlinePlotParams.Thirdstatetime = zeros(1,BpodSystem.Data.MaxTrials);
        BpodSystem.Data.OnlinePlotParams.Fourthstatetime = zeros(1,BpodSystem.Data.MaxTrials);
        BpodSystem.Data.OnlinePlotParams.Fifthstatetime = zeros(1,BpodSystem.Data.MaxTrials);
        BpodSystem.Data.OnlinePlotParams.PlotColour = {};
        BpodSystem.Data.OnlinePlotParams.Level = zeros(1,BpodSystem.Data.MaxTrials)+ BpodSystem.Data.TLevel;
        BpodSystem.Data.OnlinePlotParams.PerformanceMetric = zeros(1,BpodSystem.Data.MaxTrials) ;
    end
    
    % Determine if last was incorrect and if so change params
    if isnan(Data.RawEvents.Trial{1, i}.States.Punish(1)) == 0
        BpodSystem.Data.OnlinePlotParams.WrongCount = BpodSystem.Data.OnlinePlotParams.WrongCount + 1;
        BpodSystem.Data.OnlinePlotParams.WrongTrials((sum(BpodSystem.Data.OnlinePlotParams.WrongTrials>0)+1)) = BpodSystem.Data.OnlinePlotParams.WrongCount;
        %Find incorrect time stamp and update params
        event_time = Data.RawEvents.Trial{1, i}.States.Punish(1);
        BpodSystem.Data.OnlinePlotParams.WrongEventTimes(i) = BpodSystem.Data.TrialStartTimestamp(i) + event_time;
        %Find within trial event time
        BpodSystem.Data.OnlinePlotParams.WithinTrialEventTime(i) = Data.RawEvents.Trial{1, i}.States.Punish(1);

        % Determine if last was correct and if so change params
    elseif isnan(Data.RawEvents.Trial{1, i}.States.Reward(1)) == 0
        BpodSystem.Data.OnlinePlotParams.CorrectCount = BpodSystem.Data.OnlinePlotParams.CorrectCount + 1;
        BpodSystem.Data.OnlinePlotParams.CorrectTrials((sum(BpodSystem.Data.OnlinePlotParams.CorrectTrials>0)+1)) = BpodSystem.Data.OnlinePlotParams.CorrectCount;
        %Find Correct time stamp and update params
        event_time = Data.RawEvents.Trial{1, i}.States.Reward(1);
        BpodSystem.Data.OnlinePlotParams.RewardEventTimes(i) = BpodSystem.Data.TrialStartTimestamp(i) + event_time;
        %Find within trial event time
        BpodSystem.Data.OnlinePlotParams.WithinTrialEventTime(i) = Data.RawEvents.Trial{1, i}.States.Reward(1);
    end
    
    
    
    %Determine Prct correct and update params
%     BpodSystem.Data.OnlinePlotParams.PrcntCorrect(i) = BpodSystem.Data.OnlinePlotParams.CorrectCount/i;

    BpodSystem.Data.OnlinePlotParams.drink_time_mins((sum(BpodSystem.Data.OnlinePlotParams.drink_time_mins>0)+1)) = (BpodSystem.Data.OnlinePlotParams.RewardEventTimes(i))/60;
    BpodSystem.Data.OnlinePlotParams.wrong_time_mins((sum(BpodSystem.Data.OnlinePlotParams.wrong_time_mins>0)+1)) = (BpodSystem.Data.OnlinePlotParams.WrongEventTimes(i))/60;
    BpodSystem.Data.OnlinePlotParams.cumtrialcount(i) = i;
    
    %Determine port(state) in times:
    BpodSystem.Data.OnlinePlotParams.Initialstatetime(i) = Data.RawEvents.Trial{1, i}.States.InitialPokeValve(1);
    BpodSystem.Data.OnlinePlotParams.Secondstatetime(i) = Data.RawEvents.Trial{1, i}.States.SecondPokeValve(1) - Data.RawEvents.Trial{1, i}.States.InitialPokeValve(1);
    BpodSystem.Data.OnlinePlotParams.Thirdstatetime(i) = Data.RawEvents.Trial{1, i}.States.ThirdPokeValve(1) - Data.RawEvents.Trial{1, i}.States.SecondPokeValve(1);
    BpodSystem.Data.OnlinePlotParams.Fourthstatetime(i) = Data.RawEvents.Trial{1, i}.States.FourthPokeValve(1) - Data.RawEvents.Trial{1, i}.States.ThirdPokeValve(1);
    BpodSystem.Data.OnlinePlotParams.Fifthstatetime(i) = Data.RawEvents.Trial{1, i}.States.Reward(1) - Data.RawEvents.Trial{1, i}.States.FourthPokeValve(1);
    
    %Auto training plots
    if i > (GUIdata.BufferTrials + 2)
        BpodSystem.Data.OnlinePlotParams.Level(i:end) = Data.TLevel;
        BpodSystem.Data.OnlinePlotParams.PerformanceMetric(i:end) = BpodSystem.Data.SessionVariables.current_performance(end);
    end
    
    switch Action
        case('Init')
            figure(Figurehandle);
            %Plot Cumulative correct/incorrect
            subplot(3,4,1)
            BpodSystem.GUIHandles.CI = line(BpodSystem.Data.OnlinePlotParams.wrong_time_mins(1:(sum(BpodSystem.Data.OnlinePlotParams.wrong_time_mins>0))), BpodSystem.Data.OnlinePlotParams.WrongTrials(1:(sum(BpodSystem.Data.OnlinePlotParams.WrongTrials>0))));
            set(BpodSystem.GUIHandles.CI,'Color','blue')
            set(BpodSystem.GUIHandles.CI,'LineWidth',2)
            BpodSystem.GUIHandles.CC = line(BpodSystem.Data.OnlinePlotParams.drink_time_mins(1:(sum(BpodSystem.Data.OnlinePlotParams.drink_time_mins>0))), BpodSystem.Data.OnlinePlotParams.CorrectTrials(1:(sum(BpodSystem.Data.OnlinePlotParams.CorrectTrials>0))));
            set(BpodSystem.GUIHandles.CC,'Color','blue')
            set(BpodSystem.GUIHandles.CC,'LineWidth',2)
            xlabel('Time (mins)','FontSize',12,'FontWeight','bold');
            ylabel('Counts','FontSize',12,'FontWeight','bold');
             
            %Plot histogram of time taken between pokes
            subplot(3,4,[2 4])
            BpodSystem.GUIHandles.T1 = histogram(BpodSystem.Data.OnlinePlotParams.Secondstatetime(1:i));
            BpodSystem.GUIHandles.T1.NumBins = 20;
            BpodSystem.GUIHandles.T1.BinLimits = [0 3];
            BpodSystem.GUIHandles.T1.FaceColor = 'R';
            hold on;
            BpodSystem.GUIHandles.T2 = histogram(BpodSystem.Data.OnlinePlotParams.Thirdstatetime(1:i));
            BpodSystem.GUIHandles.T2.NumBins = 20;
            BpodSystem.GUIHandles.T2.BinLimits = [0 3];
            BpodSystem.GUIHandles.T2.FaceColor = 'G';
            hold on;
            BpodSystem.GUIHandles.T3 = histogram(BpodSystem.Data.OnlinePlotParams.Fourthstatetime(1:i));
            BpodSystem.GUIHandles.T3.NumBins = 20;
            BpodSystem.GUIHandles.T3.BinLimits = [0 3];
            BpodSystem.GUIHandles.T3.FaceColor = 'B';
            hold on;
            BpodSystem.GUIHandles.T4 = histogram(BpodSystem.Data.OnlinePlotParams.Fifthstatetime(1:i));
            BpodSystem.GUIHandles.T4.NumBins = 20;
            BpodSystem.GUIHandles.T4.BinLimits = [0 3];
            BpodSystem.GUIHandles.T4.FaceColor = 'Y';
            
            BpodSystem.GUIHandles.lgd1 = legend([BpodSystem.GUIHandles.T1 BpodSystem.GUIHandles.T2 BpodSystem.GUIHandles.T3 BpodSystem.GUIHandles.T4],{'1 > 2','2 > 3','3 > 4', '4 > 5'});



            xlabel('Transition latencies (s)','FontSize',12,'FontWeight','bold');
            %Plot real time poke for each trial + average line.
            subplot(3,4,[5 6 7 8])

            BpodSystem.GUIHandles.P1 = line(BpodSystem.Data.OnlinePlotParams.cumtrialcount,BpodSystem.Data.OnlinePlotParams.Secondstatetime);
            BpodSystem.GUIHandles.P1.LineWidth = 2;
            BpodSystem.GUIHandles.P1.Color = 'green';
            BpodSystem.GUIHandles.P1.Marker = 'o';
            BpodSystem.GUIHandles.P1.LineStyle = 'none';

            BpodSystem.GUIHandles.P2 = line(BpodSystem.Data.OnlinePlotParams.cumtrialcount,BpodSystem.Data.OnlinePlotParams.Thirdstatetime);
            BpodSystem.GUIHandles.P2.LineWidth = 2;
            BpodSystem.GUIHandles.P2.Color = 'green';
            BpodSystem.GUIHandles.P2.Marker = 'o';
            BpodSystem.GUIHandles.P2.LineStyle = 'none';

            BpodSystem.GUIHandles.P3 = line(BpodSystem.Data.OnlinePlotParams.cumtrialcount,BpodSystem.Data.OnlinePlotParams.Fourthstatetime);
            BpodSystem.GUIHandles.P3.LineWidth = 2;
            BpodSystem.GUIHandles.P3.Color = 'green';
            BpodSystem.GUIHandles.P3.Marker = 'o';
            BpodSystem.GUIHandles.P3.LineStyle = 'none';

            BpodSystem.GUIHandles.P4 = line(BpodSystem.Data.OnlinePlotParams.cumtrialcount,BpodSystem.Data.OnlinePlotParams.Fifthstatetime);
            BpodSystem.GUIHandles.P4.LineWidth = 2;
            BpodSystem.GUIHandles.P4.Color = 'green';
            BpodSystem.GUIHandles.P4.Marker = 'o';
            BpodSystem.GUIHandles.P4.LineStyle = 'none';

            xlabel('Trials','FontSize',12,'FontWeight','bold');
            ylabel('Log Transition time (s)','FontSize',12,'FontWeight','bold');
            
            subplot(3,4,[9 10])
            BpodSystem.GUIHandles.A1 = line((1:10),BpodSystem.Data.OnlinePlotParams.Level(1:10));
            set(BpodSystem.GUIHandles.A1,'Color','Red')
            set(BpodSystem.GUIHandles.A1,'LineWidth',2)
            xlabel('Trials','FontSize',12,'FontWeight','bold');
            ylabel('Level','FontSize',12,'FontWeight','bold');
                   
            subplot(3,4,[11 12])
            BpodSystem.GUIHandles.A2 = line((1:10),BpodSystem.Data.OnlinePlotParams.PerformanceMetric(1:10));
            set(BpodSystem.GUIHandles.A2,'Color','Blue')
            set(BpodSystem.GUIHandles.A2,'LineWidth',2)
            xlabel('Trials','FontSize',12,'FontWeight','bold');
            ylabel('Performance','FontSize',12,'FontWeight','bold');



        case('Update')
            
                set(BpodSystem.GUIHandles.CI,'XData',BpodSystem.Data.OnlinePlotParams.wrong_time_mins(1:(sum(BpodSystem.Data.OnlinePlotParams.wrong_time_mins>0))),'YData',BpodSystem.Data.OnlinePlotParams.WrongTrials(1:(sum(BpodSystem.Data.OnlinePlotParams.WrongTrials>0))));
                set(BpodSystem.GUIHandles.CC,'XData',BpodSystem.Data.OnlinePlotParams.drink_time_mins(1:(sum(BpodSystem.Data.OnlinePlotParams.drink_time_mins>0))),'YData',BpodSystem.Data.OnlinePlotParams.CorrectTrials(1:(sum(BpodSystem.Data.OnlinePlotParams.CorrectTrials>0))));

                set(BpodSystem.GUIHandles.T1,'Data',BpodSystem.Data.OnlinePlotParams.Secondstatetime(1:i));
                set(BpodSystem.GUIHandles.T2,'Data',BpodSystem.Data.OnlinePlotParams.Thirdstatetime(1:i));
                set(BpodSystem.GUIHandles.T3,'Data',BpodSystem.Data.OnlinePlotParams.Fourthstatetime(1:i));
                set(BpodSystem.GUIHandles.T4,'Data',BpodSystem.Data.OnlinePlotParams.Fifthstatetime(1:i));

                set(BpodSystem.GUIHandles.P1,'XData',BpodSystem.Data.OnlinePlotParams.cumtrialcount(1:i),'YData',log(BpodSystem.Data.OnlinePlotParams.Secondstatetime(1:i)));
                set(BpodSystem.GUIHandles.P2,'XData',BpodSystem.Data.OnlinePlotParams.cumtrialcount(1:i),'YData',log(BpodSystem.Data.OnlinePlotParams.Thirdstatetime(1:i)));
                set(BpodSystem.GUIHandles.P3,'XData',BpodSystem.Data.OnlinePlotParams.cumtrialcount(1:i),'YData',log(BpodSystem.Data.OnlinePlotParams.Fourthstatetime(1:i)));
                set(BpodSystem.GUIHandles.P4,'XData',BpodSystem.Data.OnlinePlotParams.cumtrialcount(1:i),'YData',log(BpodSystem.Data.OnlinePlotParams.Fifthstatetime(1:i)));
                
                if i > GUIdata.BufferTrials + 2
                set(BpodSystem.GUIHandles.A1,'YData',BpodSystem.Data.OnlinePlotParams.Level(1:i),'XData',(1:i));             
                set(BpodSystem.GUIHandles.A2,'YData',BpodSystem.Data.OnlinePlotParams.PerformanceMetric(1:i),'XData',(1:i));
                end 
                
                drawnow()
    end
end

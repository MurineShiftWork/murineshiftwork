function sma = protocol_init_ttl(S, sequence, varargin)
%% protocol_tools.protocol_init_ttl
% On the first trial of a given protocol, send TTL sequence to identify
% start of this protocol.
% E.g.: Morse code style opening sequence - instead of first trial.
% Paradigm starts afterwards. - ! Shift all trials by one and ignore first
% one for analysis.
%
% How it works:
%   1 pulse duration
%   short and long inter-pulse intervals
%
% How to make new sequence:
% - use binary code with first 5 bits of sequence. Last one is just closing
% the sequence to be able to determine the inter-pulse interval after the
% last meaningful pulse (nr 5 of 6 pulses here).

% Copyright 2019. (c) Lars Rollik, LarsRollik@gmail.com.

bnc_state_on = 2;
bnc_state_off = 0;

pulse_duration = .05;

if isempty(varargin)
    time_definition_inter_pulse_interval = .500;
else
    time_definition_inter_pulse_interval = varargin{1};
end

%% SEQUENCE
% L = long, S = short
% Pre Sleep Video
%   S S L S S S
% Post Sleep Video
%   L S S S S S
% Sequence Behaviour
%   L S L S S S

% sequence_tagging =   'ssssLs';
% sequence_oc_reward = 'Lsssss';
% sequence_oc_punish = 'LLssss';
% sequence_ps_task =   'ssLsss';
% sequence = sequence_tagging;

%%
sma = NewStateMatrix();

%% PULSE # 1
idx = 1;
[state_1, state_2, next_state, inter_pulse_interval] = make_next_vars(...
    sequence, idx, time_definition_inter_pulse_interval);

sma = AddState(sma, 'Name', state_1,...
    'Timer', pulse_duration,...
    'StateChangeConditions', {'Tup', state_2},...
    'OutputActions', {'BNCState', bnc_state_on}...
    );

sma = AddState(sma, 'Name', state_2,...
    'Timer', inter_pulse_interval,...
    'StateChangeConditions', {'Tup', next_state},...
    'OutputActions', {'BNCState', bnc_state_off}...
    );

%% PULSE # 2
idx = 2;
[state_1, state_2, next_state, inter_pulse_interval] = make_next_vars(...
    sequence, idx, time_definition_inter_pulse_interval);

sma = AddState(sma, 'Name', state_1,...
    'Timer', pulse_duration,...
    'StateChangeConditions', {'Tup', state_2},...
    'OutputActions', {'BNCState', bnc_state_on}...
    );

sma = AddState(sma, 'Name', state_2,...
    'Timer', inter_pulse_interval,...
    'StateChangeConditions', {'Tup', next_state},...
    'OutputActions', {'BNCState', bnc_state_off}...
    );

%% PULSE # 3
idx = 3;
[state_1, state_2, next_state, inter_pulse_interval] = make_next_vars(...
    sequence, idx, time_definition_inter_pulse_interval);

sma = AddState(sma, 'Name', state_1,...
    'Timer', pulse_duration,...
    'StateChangeConditions', {'Tup', state_2},...
    'OutputActions', {'BNCState', bnc_state_on}...
    );

sma = AddState(sma, 'Name', state_2,...
    'Timer', inter_pulse_interval,...
    'StateChangeConditions', {'Tup', next_state},...
    'OutputActions', {'BNCState', bnc_state_off}...
    );

%% PULSE # 4
idx = 4;
[state_1, state_2, next_state, inter_pulse_interval] = make_next_vars(...
    sequence, idx, time_definition_inter_pulse_interval);

sma = AddState(sma, 'Name', state_1,...
    'Timer', pulse_duration,...
    'StateChangeConditions', {'Tup', state_2},...
    'OutputActions', {'BNCState', bnc_state_on}...
    );

sma = AddState(sma, 'Name', state_2,...
    'Timer', inter_pulse_interval,...
    'StateChangeConditions', {'Tup', next_state},...
    'OutputActions', {'BNCState', bnc_state_off}...
    );

%% PULSE # 5
idx = 5;
[state_1, state_2, next_state, inter_pulse_interval] = make_next_vars(...
    sequence, idx, time_definition_inter_pulse_interval);

sma = AddState(sma, 'Name', state_1,...
    'Timer', pulse_duration,...
    'StateChangeConditions', {'Tup', state_2},...
    'OutputActions', {'BNCState', bnc_state_on}...
    );

sma = AddState(sma, 'Name', state_2,...
    'Timer', inter_pulse_interval,...
    'StateChangeConditions', {'Tup', next_state},...% next_state
    'OutputActions', {'BNCState', bnc_state_off}...
    );

%% PULSE # 6
idx = 6;
[state_1, state_2, ~, inter_pulse_interval] = make_next_vars(...
    sequence, idx, time_definition_inter_pulse_interval);

sma = AddState(sma, 'Name', state_1,...
    'Timer', pulse_duration,...
    'StateChangeConditions', {'Tup', state_2},...
    'OutputActions', {'BNCState', bnc_state_on}...
    );

sma = AddState(sma, 'Name', state_2,...
    'Timer', inter_pulse_interval,...
    'StateChangeConditions', {'Tup', 'post_pulse_interval'},...% next_state
    'OutputActions', {'BNCState', bnc_state_off}...
    );

%% POST PULSE INTERVAL: delay before first trial
sma = AddState(sma, 'Name', 'post_pulse_interval',...
    'Timer', 5,...
    'StateChangeConditions', {'Tup', 'exit'},...
    'OutputActions', {'BNCState', bnc_state_off}...
    );

%%
disp('Init TTL sequence made...')

end%end



function [state_1, state_2, next_state, inter_pulse_interval] = make_next_vars(...
    sequence, idx, time_definition_inter_pulse_interval)
%%
ipi_factor = 2; %% most important: this prolongs the inter-pulse interval -
% for the long pulse to distinguish from the short one

current_pulse = sequence(idx);
disp(current_pulse)

state_1 = make_state_name(idx, 1);
state_2 = make_state_name(idx, 2);

%if idx < length(sequence)
next_state = make_state_name(idx + 1, 1);
% else
%     next_state = 'exit';
% end

if contains(current_pulse, 's', 'IgnoreCase', 1)
    inter_pulse_interval = time_definition_inter_pulse_interval;
elseif contains(current_pulse, 'l', 'IgnoreCase', 1)
    inter_pulse_interval = time_definition_inter_pulse_interval * ipi_factor;
end

end%fct

function state_name = make_state_name(idx, state_idx)
state_name = ['pulse_', num2str(idx), '_', num2str(state_idx)];
end






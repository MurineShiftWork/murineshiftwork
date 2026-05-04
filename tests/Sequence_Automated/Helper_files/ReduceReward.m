function SessionVariable_IRA = ReduceReward(IRA,Reduction_rate)

SessionVariable_IRA = IRA * Reduction_rate;
disp('Intermediate reward size =');
SessionVariable_IRA %leave uncommented
if SessionVariable_IRA < 1.5 % if the reward gets very small then switch it off
    SessionVariable_IRA = 0;
    disp('Intermediate rewards turned off for port');
end
end

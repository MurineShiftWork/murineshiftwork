function Valvetime = DetermineValveTime(RewardAmount,Port)

if RewardAmount == 0
    Valvetime = 0;
else
    Valvetime = GetValveTimes(RewardAmount, str2num(Port));
end
end

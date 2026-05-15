% the variableDelay points are sampled using rejection sampling of the
% gaussian with mu and sigma i.e. keep generating a new value from the 
% Gaussian distribution until it falls within the specified bounds

function TrainDelay = GetVariableDelay(mu, sigma, lowerBound, upperBound)
    TrainDelay = lowerBound - 1; % Initialize outside the bounds
    while (TrainDelay < lowerBound) || (TrainDelay > upperBound)
        TrainDelay = mu + sigma * randn(1,1);
    end
    TrainDelay = round(TrainDelay, 2);
end  
